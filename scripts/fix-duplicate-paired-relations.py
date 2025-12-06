#!/usr/bin/env python3
"""
Fix duplicate paired relations in source markdown files.

Problem: Source files contain BOTH forward AND reverse of paired relations.
Example: File A has both "prerequisite_of → B" AND "depends_on → B" (wrong!)

Solution: Keep only the FORWARD relation in each file.
- File A keeps: "prerequisite_of → B"
- File A removes: "depends_on → B" (this should only be in File B)
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

# Paired relation types (forward → reverse)
PAIRED_TYPES = {
    'example_of': 'has_example',
    'has_example': 'example_of',
    'prerequisite_of': 'depends_on',
    'depends_on': 'prerequisite_of',
    'extends': 'is_extended_by',
    'is_extended_by': 'extends',
    'generalizes': 'specializes',
    'specializes': 'generalizes',
    'cause_of': 'effect_of',
    'effect_of': 'cause_of',
    'is_a': 'has_subtype',
    'has_subtype': 'is_a',
    'member_of': 'has_member',
    'has_member': 'member_of',
    'used_in': 'uses',
    'uses': 'used_in',
    'part_of': 'has_part',
    'has_part': 'part_of',
    'applies_to': 'applied_by',
    'applied_by': 'applies_to'
}

def find_rem_file(rem_id):
    """Find the markdown file for a given rem_id."""
    import subprocess
    result = subprocess.run(
        ['grep', '-rl', f'rem_id: {rem_id}', 'knowledge-base/'],
        capture_output=True,
        text=True
    )
    files = [f.strip() for f in result.stdout.split('\n') if f.strip() and f.endswith('.md')]
    return files[0] if files else None

def parse_related_rems(content):
    """Extract Related Rems section and parse each relation."""
    match = re.search(r'## Related Rems\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if not match:
        return []

    section = match.group(1)
    relations = []

    # Parse each line like: - [filename](filename.md) {rel: type}
    for line in section.split('\n'):
        line = line.strip()
        if not line or not line.startswith('- ['):
            continue

        # Extract target and type
        # Format: - [NNN-target-name](NNN-target-name.md) {rel: type}
        link_match = re.match(r'- \[([^\]]+)\]\([^\)]+\) \{rel: ([^\}]+)\}', line)
        if link_match:
            target_filename = link_match.group(1)
            rel_type = link_match.group(2)

            # Extract rem_id from filename (remove numerical prefix)
            # e.g., "043-equity-derivatives-..." → "equity-derivatives-..."
            target_id = re.sub(r'^\d+-', '', target_filename)

            relations.append({
                'target_id': target_id,
                'type': rel_type,
                'original_line': line
            })

    return relations

def fix_duplicate_pairs(rem_file_path):
    """
    Fix duplicate paired relations in a single file.

    Strategy:
    - If file has both X and PAIRED_TYPES[X] to same target, keep only X
    - Heuristic: Keep the "forward" relation (first in PAIRED_TYPES dict)
    """
    with open(rem_file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse current relations
    relations = parse_related_rems(content)

    # Group by target
    by_target = defaultdict(list)
    for rel in relations:
        by_target[rel['target_id']].append(rel)

    # Find duplicates
    to_remove = []
    for target_id, rels in by_target.items():
        if len(rels) < 2:
            continue

        types = [r['type'] for r in rels]

        # Check if we have both X and PAIRED_TYPES[X]
        for rel in rels:
            rel_type = rel['type']
            if rel_type in PAIRED_TYPES:
                paired_type = PAIRED_TYPES[rel_type]
                if paired_type in types:
                    # We have a duplicate pair!
                    # Keep the "forward" one (lower in dictionary order as heuristic)
                    if rel_type > paired_type:
                        to_remove.append(rel['original_line'])

    if not to_remove:
        return 0  # No changes needed

    # Remove duplicate relations from content
    new_content = content
    for line in to_remove:
        # Remove the entire line including newline
        new_content = new_content.replace(line + '\n', '')

    # Write back
    with open(rem_file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return len(to_remove)

def main():
    """Main function."""
    print("Loading duplicate pairs list...", file=sys.stderr)

    # Load the list of affected pairs
    with open('/tmp/duplicate_pair_investigation/complete_list.json', 'r') as f:
        duplicate_pairs = json.load(f)

    print(f"Found {len(duplicate_pairs)} duplicate pairs", file=sys.stderr)

    # Get unique rem_ids
    rem_ids = set()
    for pair in duplicate_pairs:
        rem_ids.add(pair['node1'])
        rem_ids.add(pair['node2'])

    print(f"Unique rems to fix: {len(rem_ids)}", file=sys.stderr)

    # Process each rem file
    total_removed = 0
    files_modified = 0

    for rem_id in sorted(rem_ids):
        rem_file = find_rem_file(rem_id)
        if not rem_file:
            print(f"WARNING: File not found for {rem_id}", file=sys.stderr)
            continue

        removed = fix_duplicate_pairs(rem_file)
        if removed > 0:
            total_removed += removed
            files_modified += 1
            print(f"Fixed {rem_file}: removed {removed} duplicate relations")

    print(f"\n✅ SUMMARY:", file=sys.stderr)
    print(f"   Files modified: {files_modified}", file=sys.stderr)
    print(f"   Duplicate relations removed: {total_removed}", file=sys.stderr)

    return 0

if __name__ == "__main__":
    sys.exit(main())
