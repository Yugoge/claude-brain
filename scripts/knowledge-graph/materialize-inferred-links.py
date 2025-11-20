#!/usr/bin/env python3
"""
Materialize two-hop inferred links (A→B→C ⇒ A⇒C) into concept markdown files
under the "Related Concepts" section as typed relations with rel: inferred.

Usage:
    python3 scripts/materialize-inferred-links.py [--dry-run] [--verbose]

Notes:
    - Requires up-to-date knowledge-base/_index/backlinks.json
    - Skips if a direct link to C already exists in A (to avoid duplicates)
    - Writes: "- [[c_id]] {rel: inferred, via: b_id}"
"""

import json
from pathlib import Path
from typing import Dict, List
import argparse

ROOT = Path(__file__).parent.parent.parent  # Project root: /root/knowledge-system
KB_DIR = ROOT / 'knowledge-base'
IDX_FILE = KB_DIR / '_index' / 'backlinks.json'


def add_line_if_missing(text: str, to_id: str, via_id: str) -> str:
    bullet = f"- [[{to_id}]] {{rel: inferred, via: {via_id}}}"
    if bullet in text:
        return text
    # Avoid adding if a direct line already exists for to_id
    if f"[[{to_id}]]" in text:
        return text
    lines = text.splitlines()
    # Ensure related section exists
    # Skip frontmatter
    start_idx = 0
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            start_idx = text[: end + 4].count('\n')
    insert_idx = None
    for i in range(start_idx, len(lines)):
        if lines[i].strip().lower().lstrip('#').strip() == 'related concepts':
            insert_idx = i + 1
            break
    if insert_idx is None:
        if lines and lines[-1].strip() != '':
            lines.append('')
        lines.append('## Related Concepts')
        lines.append('')
        insert_idx = len(lines)
    lines.insert(insert_idx, bullet)
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Materialize inferred links into markdown files')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    if not IDX_FILE.exists():
        raise SystemExit(f"Index not found: {IDX_FILE}. Run rebuild-backlinks.py first.")

    data = json.loads(IDX_FILE.read_text(encoding='utf-8'))
    links: Dict[str, Dict] = data.get('links', {})

    # Build concept path index
    concepts_meta: Dict[str, Dict] = data.get('concepts', {})
    updated_files: List[Path] = []

    for a_id, a_data in links.items():
        inferred = a_data.get('inferred_links_to', [])
        if not inferred:
            continue
        meta = concepts_meta.get(a_id)
        if not meta:
            continue
        file_rel = meta.get('file')
        if not file_rel:
            continue
        a_path = KB_DIR / file_rel
        if not a_path.exists():
            continue
        text = a_path.read_text(encoding='utf-8')
        new_text = text
        for item in inferred:
            c_id = item.get('to')
            via = item.get('via')
            if not c_id or not via:
                continue
            new_text = add_line_if_missing(new_text, c_id, via)
        if new_text != text:
            updated_files.append(a_path)
            if args.verbose:
                print(f"Updated {a_path}")
            if not args.dry_run:
                a_path.write_text(new_text, encoding='utf-8')

    if args.verbose or args.dry_run:
        print(f"Updated {len(updated_files)} files")


if __name__ == '__main__':
    main()


