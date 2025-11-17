#!/usr/bin/env python3
"""
Add a typed relation between two concepts by appending a line in the
"Related Concepts" section of their markdown files.

Usage:
    python3 scripts/add-relation.py --from A --to B --type synonym [--dry-run] [--verbose]

Rules:
    - If relation is symmetric (e.g., synonym, antonym, related, contrasts_with, cognate),
      the same relation is added in both A and B.
    - If relation has an inverse (e.g., is_a ↔ has_subtype, part_of ↔ has_part, hypernym ↔ hyponym,
      prerequisite_of ↔ has_prerequisite), the inverse is added to the target.

Format inserted:
    - [[to_id]] {rel: relation_type}

Notes:
    - Creates "## Related Concepts" section if missing
    - Avoids duplicate identical lines
"""

import argparse
from pathlib import Path
from typing import Dict, Tuple

ROOT = Path(__file__).parent.parent
KB_DIR = ROOT / 'knowledge-base'

SYMMETRIC_TYPES = {
    'synonym',
    'antonym',
    'related',
    'contrasts_with',
    'cognate',
    'cooccurs_with',
}

INVERSE_MAP = {
    'is_a': 'has_subtype',
    'has_subtype': 'is_a',
    'part_of': 'has_part',
    'has_part': 'part_of',
    'hypernym': 'hyponym',
    'hyponym': 'hypernym',
    'prerequisite_of': 'has_prerequisite',
    'has_prerequisite': 'prerequisite_of',
    'example_of': 'has_example',
    'has_example': 'example_of',
    'cause_of': 'caused_by',
    'caused_by': 'cause_of',
}


def build_index() -> Dict[str, Path]:
    idx: Dict[str, Path] = {}
    for domain in KB_DIR.iterdir():
        if not domain.is_dir() or domain.name.startswith('_'):
            continue
        cdir = domain / 'concepts'
        if not cdir.exists():
            continue
        for md in cdir.glob('*.md'):
            idx[md.stem.lower()] = md
    return idx


def ensure_related_section(text: str) -> Tuple[str, int]:
    # Return updated text and index where to append under Related Concepts section
    lines = text.splitlines()
    # Skip frontmatter if present
    start_idx = 0
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            start_idx = text[: end + 4].count('\n')

    # Find a header line for Related Concepts
    insert_idx = None
    for i in range(start_idx, len(lines)):
        if lines[i].strip().lower().lstrip('#').strip() == 'related concepts':
            insert_idx = i + 1
            break
    if insert_idx is None:
        # Append section at end
        if lines and lines[-1].strip() != '':
            lines.append('')
        lines.append('## Related Concepts')
        lines.append('')
        insert_idx = len(lines)
        return ('\n'.join(lines), insert_idx)
    return (text, insert_idx)


def add_line_if_missing(text: str, to_id: str, rel_type: str) -> str:
    bullet = f"- [[{to_id}]] {{rel: {rel_type}}}"
    # Avoid duplicate
    if bullet in text:
        return text
    updated, insert_idx = ensure_related_section(text)
    lines = updated.splitlines()
    lines.insert(insert_idx, bullet)
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Add a typed relation between two concepts')
    parser.add_argument('--from', dest='from_id', required=True, help='Source concept ID')
    parser.add_argument('--to', dest='to_id', required=True, help='Target concept ID')
    parser.add_argument('--type', dest='rel_type', required=True, help='Relation type (e.g., synonym, is_a, part_of)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    from_id = args.from_id.lower()
    to_id = args.to_id.lower()
    rel_type = args.rel_type.lower()

    idx = build_index()
    if from_id not in idx:
        raise SystemExit(f"Source concept not found: {from_id}")
    if to_id not in idx:
        raise SystemExit(f"Target concept not found: {to_id}")

    # Update source
    src_path = idx[from_id]
    src_text = src_path.read_text(encoding='utf-8')
    new_src = add_line_if_missing(src_text, to_id, rel_type)
    if args.verbose and new_src != src_text:
        print(f"Updated {src_path}")
    if not args.dry_run and new_src != src_text:
        src_path.write_text(new_src, encoding='utf-8')

    # Determine reciprocal relation for target
    if rel_type in SYMMETRIC_TYPES:
        back_type = rel_type
    else:
        back_type = INVERSE_MAP.get(rel_type)

    if back_type:
        tgt_path = idx[to_id]
        tgt_text = tgt_path.read_text(encoding='utf-8')
        new_tgt = add_line_if_missing(tgt_text, from_id, back_type)
        if args.verbose and new_tgt != tgt_text:
            print(f"Updated {tgt_path}")
        if not args.dry_run and new_tgt != tgt_text:
            tgt_path.write_text(new_tgt, encoding='utf-8')


if __name__ == '__main__':
    main()


