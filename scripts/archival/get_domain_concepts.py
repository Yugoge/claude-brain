#!/usr/bin/env python3
"""
Get Domain Concepts from Backlinks Index

Extract all concepts in a specific ISCED domain for KB context injection.

Usage:
    python scripts/archival/get_domain_concepts.py --domain-path "0231-language-acquisition"
    python scripts/archival/get_domain_concepts.py --domain-path "0412-finance-banking-insurance"

Returns JSON array of concepts for tutor consultation context.
"""

import json
import sys
import argparse
from pathlib import Path

# Constants
ROOT = Path(__file__).parent.parent.parent
KB_DIR = ROOT / "knowledge-base"
BACKLINKS_FILE = KB_DIR / "_index" / "backlinks.json"


def load_backlinks():
    """Load backlinks.json"""
    if not BACKLINKS_FILE.exists():
        raise FileNotFoundError(
            f"❌ Error: {BACKLINKS_FILE} not found.\n"
            f"Run: python scripts/knowledge-graph/rebuild-backlinks.py"
        )

    with open(BACKLINKS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_domain_concepts(backlinks_data, domain_path):
    """
    Extract all concepts in a specific ISCED domain.

    Args:
        backlinks_data: Complete backlinks.json data
        domain_path: ISCED domain path (e.g., "0231-language-acquisition")

    Returns:
        List of {"id": concept_id, "title": title} dicts
    """
    concepts = []
    concepts_meta = backlinks_data.get('concepts', {})

    for concept_id, meta in concepts_meta.items():
        file_path = meta.get('file', '')

        # Check if this concept belongs to the specified domain
        if domain_path in file_path:
            concepts.append({
                'id': concept_id,
                'title': meta.get('title', concept_id),
                'file': file_path
            })

    return sorted(concepts, key=lambda x: x['id'])


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Extract domain concepts for KB context injection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--domain-path', required=True,
                        help='ISCED domain path (e.g., "0231-language-acquisition")')
    parser.add_argument('--format', choices=['json', 'compact'], default='json',
                        help='Output format (json or compact)')

    args = parser.parse_args()

    try:
        # Load backlinks
        backlinks_data = load_backlinks()

        # Extract concepts
        concepts = extract_domain_concepts(backlinks_data, args.domain_path)

        if args.format == 'json':
            # Full JSON output (for tutor context)
            print(json.dumps(concepts, indent=2, ensure_ascii=False))
        else:
            # Compact format (for logging)
            print(f"Found {len(concepts)} concepts in {args.domain_path}:")
            for concept in concepts[:10]:  # Show first 10
                print(f"  - {concept['id']}: {concept['title']}")
            if len(concepts) > 10:
                print(f"  ... and {len(concepts) - 10} more")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
