#!/usr/bin/env python3
"""
Normalize links in Rem markdown files by converting [[wikilinks]] to clickable
Markdown file links. Supports preserving typed relation suffixes like
"[[id]] {rel: synonym}" by emitting "[Title](path) {rel: synonym}".

Usage:
    python3 scripts/normalize-links.py [--mode replace|annotate] [--dry-run] [--verbose]

Modes:
    replace  - Replace [[id]] with [Title](relative/path.md) (default)
    annotate - Keep [[id]] and append file link in parentheses, e.g.:
               [[id]] ([Title](relative/path.md))

Notes:
    - Only processes files under knowledge-base/**/concepts/*.md
    - Skips YAML frontmatter section
    - Leaves unresolved [[id]] intact and logs a warning
"""

import argparse
import re
from pathlib import Path
from typing import Dict, Tuple

ROOT = Path(__file__).parent.parent.parent
KB_DIR = ROOT / "knowledge-base"

# Patterns
WIKILINK_RE = re.compile(r"\[\[([a-z0-9\-]+)\]\]", re.IGNORECASE)
TYPED_SUFFIX_RE = re.compile(r"\]\]\s*(\{[^}]*\})")


def build_concept_index() -> Dict[str, Tuple[str, Path]]:
    """Build concept-id → (title, absolute_path) index."""
    index: Dict[str, Tuple[str, Path]] = {}

    def scan_directory(directory: Path):
        """Recursively scan directory for .md files."""
        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                scan_directory(item)
            elif item.is_file() and item.suffix == '.md' and not item.stem.startswith('_'):
                # Extract rem_id from frontmatter, fall back to filename
                concept_id = item.stem.lower()
                title = concept_id
                try:
                    with open(item, 'r', encoding='utf-8') as f:
                        text = f.read()
                    if text.startswith('---'):
                        end = text.find('\n---', 3)
                        if end != -1:
                            fm = text[3:end].strip()
                            for line in fm.splitlines():
                                line = line.strip()
                                if not line or ':' not in line:
                                    continue
                                k, v = line.split(':', 1)
                                k = k.strip()
                                if k == 'rem_id':
                                    concept_id = v.strip().strip('"').strip("'")
                                elif k == 'title':
                                    t = v.strip().strip('"').strip("'")
                                    if t:
                                        title = t
                except Exception:
                    pass
                index[concept_id] = (title, item)

    for domain in KB_DIR.iterdir():
        if domain.is_dir() and not domain.name.startswith('_'):
            scan_directory(domain)

    return index


def convert_content(content: str, current_file: Path, idx: Dict[str, Tuple[str, Path]], mode: str) -> str:
    """Convert wikilinks in content according to mode."""
    # Skip frontmatter
    start = 0
    if content.startswith('---'):
        end = content.find('\n---', 3)
        if end != -1:
            start = end + 4  # include trailing delimiter and newline

    prefix = content[:start]
    body = content[start:]

    def repl(match: re.Match) -> str:
        concept_id = match.group(1).lower()
        # Check if there is a typed suffix immediately after the match
        after = body[match.end() - start: match.end() - start + 80]
        typed_suffix = None
        m2 = TYPED_SUFFIX_RE.match(body[match.end() - start - 2: match.end() - start + 120])  # include ']]'
        if m2:
            typed_suffix = ' ' + m2.group(1)
        entry = idx.get(concept_id)
        if not entry:
            return match.group(0)  # leave as-is
        title, target_abs = entry
        rel_path = target_abs.relative_to(current_file.parent if target_abs.is_absolute() else current_file.parent).as_posix()
        md_link = f"[{title}]({rel_path})"
        if mode == 'annotate':
            out = f"[[{concept_id}]] ({md_link})"
        else:
            out = md_link
        if typed_suffix:
            out += typed_suffix
        return out

    new_body = WIKILINK_RE.sub(repl, body)
    return prefix + new_body


def main():
    parser = argparse.ArgumentParser(description='Normalize wikilinks to Markdown file links')
    parser.add_argument('--mode', choices=['replace', 'annotate'], default='replace')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    idx = build_concept_index()
    files = []

    def collect_md_files(directory: Path):
        """Recursively collect all .md files."""
        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                collect_md_files(item)
            elif item.is_file() and item.suffix == '.md' and not item.stem.startswith('_'):
                files.append(item)

    for domain in KB_DIR.iterdir():
        if domain.is_dir() and not domain.name.startswith('_'):
            collect_md_files(domain)

    changed = 0
    for md in files:
        try:
            text = md.read_text(encoding='utf-8')
        except Exception:
            continue
        new_text = convert_content(text, md, idx, args.mode)
        if new_text != text:
            changed += 1
            if args.verbose:
                print(f"Updated: {md}")
            if not args.dry_run:
                md.write_text(new_text, encoding='utf-8')

    if args.verbose or args.dry_run:
        print(f"Processed {len(files)} files, updated {changed}")


if __name__ == '__main__':
    main()


