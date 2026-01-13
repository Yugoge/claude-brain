#!/usr/bin/env python3
"""
Get Linked Rems for Review Context

Load typed relations from backlinks index for a specific Rem.
Prioritize relations by pedagogical value.

Usage:
    source venv/bin/activate && source venv/bin/activate && python scripts/review/get_linked_rems.py <rem-id>
    source venv/bin/activate && source venv/bin/activate && python scripts/review/get_linked_rems.py <rem-id> --priority prerequisites

Output: JSON with linked Rems sorted by priority
"""

import json
import sys
import argparse
from pathlib import Path

# Relation priority for review (higher = review first)
RELATION_PRIORITY = {
    # Prerequisites must be mastered first
    'has_prerequisite': 10,
    'prerequisite_of': 9,

    # Contrasts help differentiate
    'antonym': 8,
    'contrasts_with': 7,

    # Examples aid understanding
    'example_of': 6,
    'has_example': 5,

    # Structural relations
    'is_a': 4,
    'hypernym': 4,
    'specializes': 3,

    # Usage context
    'uses': 2,
    'used_by': 2,

    # General associations (lowest priority)
    'related': 1,
    'analogous_to': 1
}

def load_backlinks():
    """Load backlinks index"""
    backlinks_path = Path('knowledge-base/_index/backlinks.json')
    if not backlinks_path.exists():
        return {}

    with open(backlinks_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('links', {})

def get_linked_rems(rem_id, priority_filter=None):
    """
    Get linked Rems for a specific Rem.

    Args:
        rem_id: Target Rem ID
        priority_filter: Optional filter ('prerequisites', 'contrasts', 'examples')

    Returns:
        Dict with linked_rems array sorted by priority
    """
    backlinks = load_backlinks()

    if rem_id not in backlinks:
        return {
            'rem_id': rem_id,
            'linked_rems': [],
            'summary': {
                'total': 0,
                'by_type': {}
            }
        }

    rem_data = backlinks[rem_id]
    linked = []

    # Process typed_links_to (outgoing)
    for link in rem_data.get('typed_links_to', []):
        linked.append({
            'id': link['to'],
            'type': link['type'],
            'direction': 'outgoing',
            'priority': RELATION_PRIORITY.get(link['type'], 0)
        })

    # Process typed_linked_from (incoming)
    for link in rem_data.get('typed_linked_from', []):
        linked.append({
            'id': link['from'],
            'type': link['type'],
            'direction': 'incoming',
            'priority': RELATION_PRIORITY.get(link['type'], 0)
        })

    # Apply priority filter
    if priority_filter == 'prerequisites':
        linked = [l for l in linked if l['type'] in ['has_prerequisite', 'prerequisite_of']]
    elif priority_filter == 'contrasts':
        linked = [l for l in linked if l['type'] in ['antonym', 'contrasts_with']]
    elif priority_filter == 'examples':
        linked = [l for l in linked if l['type'] in ['example_of', 'has_example']]

    # Sort by priority (highest first)
    linked.sort(key=lambda x: x['priority'], reverse=True)

    # Build summary
    by_type = {}
    for l in linked:
        rel_type = l['type']
        by_type[rel_type] = by_type.get(rel_type, 0) + 1

    return {
        'rem_id': rem_id,
        'linked_rems': linked,
        'summary': {
            'total': len(linked),
            'by_type': by_type
        }
    }

def main():
    parser = argparse.ArgumentParser(description='Get linked Rems for review context')
    parser.add_argument('rem_id', help='Rem ID to get links for')
    parser.add_argument('--priority', choices=['prerequisites', 'contrasts', 'examples'],
                        help='Filter by relation priority')

    args = parser.parse_args()

    result = get_linked_rems(args.rem_id, args.priority)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
