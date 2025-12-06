#!/usr/bin/env python3
"""
Fix Multi-Pair Relations in Source Files

Detects and removes redundant paired relations between two Rems in source .md files.
Uses semantic priority to decide which relation to keep.

Example problem:
- File A has: `{rel: example_of}` → B
- File B has: `{rel: uses}` → A
Result: TWO paired relations (example_of↔has_example AND uses↔used_in)

Solution: Remove the lower-priority relation from source files.

Semantic Priority (highest to lowest):
1. is_a / has_subtype
2. prerequisite_of / depends_on
3. example_of / has_example
4. extends / is_extended_by
5. uses / used_in
6. Other pairs (lowest)
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Asymmetric paired relation types
ASYMMETRIC_PAIRS = {
    'is_a': 'has_subtype',
    'has_subtype': 'is_a',
    'prerequisite_of': 'depends_on',
    'depends_on': 'prerequisite_of',
    'example_of': 'has_example',
    'has_example': 'example_of',
    'extends': 'is_extended_by',
    'is_extended_by': 'extends',
    'uses': 'used_in',
    'used_in': 'uses',
    'generalizes': 'specializes',
    'specializes': 'generalizes',
    'member_of': 'has_member',
    'has_member': 'member_of',
    'part_of': 'has_part',
    'has_part': 'part_of',
    'applies_to': 'applied_by',
    'applied_by': 'applies_to',
}

# Semantic priority for relation types (higher number = higher priority)
RELATION_PRIORITY = {
    'is_a': 10,
    'has_subtype': 10,
    'prerequisite_of': 9,
    'depends_on': 9,
    'example_of': 8,
    'has_example': 8,
    'extends': 7,
    'is_extended_by': 7,
    'uses': 6,
    'used_in': 6,
    'generalizes': 5,
    'specializes': 5,
    'member_of': 4,
    'has_member': 4,
    'part_of': 3,
    'has_part': 3,
    'applies_to': 2,
    'applied_by': 2,
}


def load_backlinks(backlinks_path: Path) -> Dict:
    """Load backlinks index"""
    with open(backlinks_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('links', {})


def get_paired_relations_between_nodes(backlinks: Dict, node_a: str, node_b: str) -> List[Tuple[str, str]]:
    """
    Get all paired relations between two nodes.
    Returns list of (forward_type, reverse_type) tuples.
    """
    pairs = []

    # Check all relations from A to B
    if node_a in backlinks:
        for link in backlinks[node_a].get('typed_links_to', []):
            if link.get('to') == node_b:
                rel_type = link.get('type')
                if rel_type in ASYMMETRIC_PAIRS:
                    expected_reverse = ASYMMETRIC_PAIRS[rel_type]
                    # Check if reverse exists
                    if node_b in backlinks:
                        for reverse_link in backlinks[node_b].get('typed_links_to', []):
                            if reverse_link.get('to') == node_a and reverse_link.get('type') == expected_reverse:
                                pairs.append((rel_type, expected_reverse))
                                break

    return pairs


def find_multi_pair_problems(backlinks: Dict) -> List[Dict]:
    """
    Find all node pairs with multiple paired relations.
    Returns list of problem descriptions.
    """
    problems = []
    checked_pairs = set()

    for source_id, source_data in backlinks.items():
        for link in source_data.get('typed_links_to', []):
            target_id = link.get('to')

            # Create canonical pair key (sorted to avoid duplicates)
            pair_key = tuple(sorted([source_id, target_id]))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            # Get all paired relations between these nodes
            pairs = get_paired_relations_between_nodes(backlinks, source_id, target_id)

            if len(pairs) > 1:
                problems.append({
                    'node_a': source_id,
                    'node_b': target_id,
                    'paired_relations': pairs,
                    'count': len(pairs)
                })

    return problems


def find_rem_file(knowledge_base: Path, rem_id: str) -> Path:
    """Find the .md file for a given rem_id"""
    # Search recursively for files matching the rem_id pattern
    for md_file in knowledge_base.rglob('*.md'):
        if md_file.stem.endswith(rem_id):
            return md_file
    return None


def get_relations_from_file(file_path: Path) -> List[Tuple[str, str, int]]:
    """
    Extract typed relations from a Rem file.
    Returns list of (target_rem_id, rel_type, line_number) tuples.
    """
    relations = []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Pattern: [title](path.md) {rel: type}
    pattern = r'\[([^\]]+)\]\(([^\)]+\.md)\)\s*\{rel:\s*([^}]+)\}'

    for i, line in enumerate(lines, 1):
        matches = re.finditer(pattern, line)
        for match in matches:
            target_path = match.group(2)
            rel_type = match.group(3).strip()

            # Extract rem_id from filename
            target_filename = Path(target_path).stem
            # Handle numbered prefixes (001-rem-id.md -> rem-id)
            target_rem_id = re.sub(r'^\d+-', '', target_filename)

            relations.append((target_rem_id, rel_type, i))

    return relations


def choose_relation_to_keep(pairs: List[Tuple[str, str]]) -> Tuple[str, str]:
    """
    Choose which paired relation to keep based on semantic priority.
    Returns (forward_type, reverse_type) to keep.
    """
    # Sort by priority (highest first)
    sorted_pairs = sorted(
        pairs,
        key=lambda p: RELATION_PRIORITY.get(p[0], 0),
        reverse=True
    )
    return sorted_pairs[0]


def remove_relation_from_file(file_path: Path, target_rem_id: str, rel_type: str, dry_run: bool = True) -> bool:
    """
    Remove a specific typed relation from a Rem file.
    Returns True if removal was successful.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match the relation line
    # Need to be flexible with path formats
    pattern = rf'\[([^\]]+)\]\([^\)]*{re.escape(target_rem_id)}\.md\)\s*\{{rel:\s*{re.escape(rel_type)}\}}\s*\n'

    matches = list(re.finditer(pattern, content))

    if not matches:
        print(f"  ⚠️  Could not find relation to remove: {target_rem_id} [{rel_type}] in {file_path}", file=sys.stderr)
        return False

    if len(matches) > 1:
        print(f"  ⚠️  Multiple matches found for {target_rem_id} [{rel_type}] in {file_path}", file=sys.stderr)
        return False

    new_content = re.sub(pattern, '', content)

    if dry_run:
        print(f"  [DRY-RUN] Would remove from {file_path}: {target_rem_id} [{rel_type}]")
        return True
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✅ Removed from {file_path}: {target_rem_id} [{rel_type}]")
        return True


def fix_multi_pair_problem(problem: Dict, knowledge_base: Path, dry_run: bool = True) -> bool:
    """
    Fix a multi-pair problem by removing lower-priority relations.
    Returns True if fix was successful.
    """
    node_a = problem['node_a']
    node_b = problem['node_b']
    pairs = problem['paired_relations']

    # Choose which pair to keep
    keep_pair = choose_relation_to_keep(pairs)
    remove_pairs = [p for p in pairs if p != keep_pair]

    print(f"\n🔧 Fixing: {node_a} ↔ {node_b}")
    print(f"   Keeping: {keep_pair[0]} ↔ {keep_pair[1]} (priority: {RELATION_PRIORITY.get(keep_pair[0], 0)})")
    print(f"   Removing: {', '.join([f'{p[0]}↔{p[1]}' for p in remove_pairs])}")

    success = True

    for forward_type, reverse_type in remove_pairs:
        # Determine which file has which relation
        # Check node_a's file for forward_type
        file_a = find_rem_file(knowledge_base, node_a)
        if file_a:
            relations_a = get_relations_from_file(file_a)
            has_forward = any(r[0] == node_b and r[1] == forward_type for r in relations_a)
            if has_forward:
                if not remove_relation_from_file(file_a, node_b, forward_type, dry_run):
                    success = False

        # Check node_b's file for reverse_type
        file_b = find_rem_file(knowledge_base, node_b)
        if file_b:
            relations_b = get_relations_from_file(file_b)
            has_reverse = any(r[0] == node_a and r[1] == reverse_type for r in relations_b)
            if has_reverse:
                if not remove_relation_from_file(file_b, node_a, reverse_type, dry_run):
                    success = False

    return success


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Fix multi-pair relations in source Rem files')
    parser.add_argument('--execute', action='store_true', help='Actually modify files (default is dry-run)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    dry_run = not args.execute

    # Paths
    repo_root = Path(__file__).resolve().parents[2]
    knowledge_base = repo_root / 'knowledge-base'
    backlinks_path = knowledge_base / '_index' / 'backlinks.json'

    if not backlinks_path.exists():
        print(f"❌ Backlinks index not found: {backlinks_path}", file=sys.stderr)
        print("   Run: python scripts/knowledge-graph/rebuild-backlinks.py", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("Fix Multi-Pair Relations in Source Files")
    print("=" * 80)
    print()

    if dry_run:
        print("🔍 DRY-RUN MODE (use --execute to apply changes)")
        print()

    # Load backlinks
    print("Loading backlinks index...")
    backlinks = load_backlinks(backlinks_path)
    print(f"Loaded {len(backlinks)} nodes")
    print()

    # Find multi-pair problems
    print("Scanning for multi-pair relations...")
    problems = find_multi_pair_problems(backlinks)

    if not problems:
        print("✅ No multi-pair relations found!")
        print()
        return 0

    print(f"❌ Found {len(problems)} node pairs with multiple paired relations")
    print()

    # Fix each problem
    fixed_count = 0
    failed_count = 0

    for problem in problems:
        if fix_multi_pair_problem(problem, knowledge_base, dry_run):
            fixed_count += 1
        else:
            failed_count += 1

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)

    if dry_run:
        print(f"Would fix {fixed_count} multi-pair problems")
        if failed_count > 0:
            print(f"Failed to locate {failed_count} relations")
        print()
        print("Run with --execute to apply changes")
    else:
        print(f"✅ Fixed {fixed_count} multi-pair problems")
        if failed_count > 0:
            print(f"❌ Failed to fix {failed_count} problems")
        print()
        print("Next steps:")
        print("1. Run: python scripts/knowledge-graph/rebuild-backlinks.py")
        print("2. Run: python scripts/fix-bidirectional-links.py")
        print("3. Verify: python /tmp/check_duplicate_pairs.py")

    return 0 if failed_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
