#!/usr/bin/env python3
"""Fix all missing bidirectional links in the knowledge graph."""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent))

# Symmetric relations that MUST be bidirectional
SYMMETRIC_TYPES = {
    'related_to', 'contrasts_with', 'complements',
    'analogous_to', 'synonym', 'antonym'
}

# Asymmetric relation pairs
ASYMMETRIC_PAIRS = {
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
    'applies_to': 'applied_by',
    'applied_by': 'applies_to',
    'used_in': 'uses',
    'uses': 'used_in',
    'part_of': 'has_part',
    'has_part': 'part_of'
}

def load_backlinks():
    """Load the backlinks index."""
    backlinks_path = Path('knowledge-base/_index/backlinks.json')
    with open(backlinks_path, 'r') as f:
        data = json.load(f)
    return data

def find_missing_bidirectional(backlinks_data):
    """Find all missing bidirectional links with duplicate prevention."""
    backlinks = backlinks_data.get('links', {})
    missing = []
    checked_pairs = set()  # Track processed pairs to prevent duplicates

    for source_id, source_data in backlinks.items():
        # Check outgoing typed links
        for link_info in source_data.get('typed_links_to', []):
            if not isinstance(link_info, dict):
                continue

            target_id = link_info.get('to')
            rel_type = link_info.get('type')

            if not target_id or not rel_type:
                continue

            # Check if target exists
            if target_id not in backlinks:
                print(f"Warning: Target {target_id} not in backlinks index", file=sys.stderr)
                continue

            # Create canonical pair key to prevent duplicate processing
            if rel_type in SYMMETRIC_TYPES:
                # For symmetric: (A,B) same as (B,A), use sorted tuple
                pair_key = tuple(sorted([source_id, target_id])) + (rel_type,)
            else:
                # For asymmetric: (A,B,prerequisite_of) is unique
                pair_key = (source_id, target_id, rel_type)

            # Skip if already processed
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)

            target_data = backlinks[target_id]

            # Determine expected reverse type
            if rel_type in SYMMETRIC_TYPES:
                expected_reverse = rel_type
            elif rel_type in ASYMMETRIC_PAIRS:
                expected_reverse = ASYMMETRIC_PAIRS[rel_type]
            else:
                continue

            # Check if reverse exists
            has_reverse = False
            for reverse_link in target_data.get('typed_links_to', []):
                if reverse_link.get('to') == source_id and reverse_link.get('type') == expected_reverse:
                    has_reverse = True
                    break

            # Add to missing if no reverse found
            if not has_reverse:
                missing.append({
                    'source': target_id,           # Reverse: target becomes source
                    'target': source_id,           # source becomes target
                    'type': expected_reverse,      # Use expected reverse type
                    'reason': f'Missing reverse of {source_id} -> {target_id} [{rel_type}]'
                })

    return missing

def add_missing_links(backlinks_data, missing_links):
    """Add the missing bidirectional links."""
    backlinks = backlinks_data.get('links', {})
    added_count = 0

    for link in missing_links:
        source_id = link['source']
        target_id = link['target']
        rel_type = link['type']

        # Ensure source exists in backlinks
        if source_id not in backlinks:
            print(f"Creating new entry for {source_id}", file=sys.stderr)
            backlinks[source_id] = {
                'links_to': [],
                'typed_links_to': [],
                'linked_from': [],
                'typed_linked_from': [],
                'inferred_links_to': []
            }

        source_data = backlinks[source_id]

        # Check if link already exists (avoid duplicates)
        exists = False
        for existing_link in source_data.get('typed_links_to', []):
            if existing_link.get('to') == target_id and existing_link.get('type') == rel_type:
                exists = True
                break

        if not exists:
            # Add to typed_links_to
            if 'typed_links_to' not in source_data:
                source_data['typed_links_to'] = []

            source_data['typed_links_to'].append({
                'to': target_id,
                'type': rel_type
            })

            # Also update typed_linked_from for the target
            if target_id in backlinks:
                target_data = backlinks[target_id]
                if 'typed_linked_from' not in target_data:
                    target_data['typed_linked_from'] = []

                # Check if already in typed_linked_from
                from_exists = False
                for existing_from in target_data['typed_linked_from']:
                    if existing_from.get('from') == source_id and existing_from.get('type') == rel_type:
                        from_exists = True
                        break

                if not from_exists:
                    target_data['typed_linked_from'].append({
                        'from': source_id,
                        'type': rel_type
                    })

            added_count += 1
            print(f"Added: {source_id} -> {target_id} [{rel_type}]")

    return added_count

def save_backlinks(backlinks_data):
    """Save the updated backlinks index."""
    backlinks_path = Path('knowledge-base/_index/backlinks.json')

    # Create backup
    backup_path = backlinks_path.with_suffix('.backup.json')
    with open(backlinks_path, 'r') as f:
        backup_data = f.read()
    with open(backup_path, 'w') as f:
        f.write(backup_data)
    print(f"Created backup at {backup_path}", file=sys.stderr)

    # Save updated data
    with open(backlinks_path, 'w') as f:
        json.dump(backlinks_data, f, indent=2, ensure_ascii=False)
    print(f"Saved updated backlinks to {backlinks_path}", file=sys.stderr)

def main():
    """Main function."""
    print("Loading backlinks index...", file=sys.stderr)
    backlinks_data = load_backlinks()

    print("Finding missing bidirectional links...", file=sys.stderr)
    missing_links = find_missing_bidirectional(backlinks_data)

    print(f"\nFound {len(missing_links)} missing bidirectional links", file=sys.stderr)

    # Group by type for summary
    by_type = defaultdict(int)
    for link in missing_links:
        by_type[link['type']] += 1

    print("\nMissing links by type:", file=sys.stderr)
    for rel_type, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {rel_type}: {count}", file=sys.stderr)

    if missing_links:
        print(f"\nAdding {len(missing_links)} missing links...", file=sys.stderr)
        added = add_missing_links(backlinks_data, missing_links)
        print(f"Successfully added {added} links", file=sys.stderr)

        print("\nSaving updated backlinks...", file=sys.stderr)
        save_backlinks(backlinks_data)

        print(f"\n✅ Fixed {added} missing bidirectional links!", file=sys.stderr)
    else:
        print("\n✅ No missing bidirectional links found - graph is already correct!", file=sys.stderr)

    return 0

if __name__ == "__main__":
    sys.exit(main())