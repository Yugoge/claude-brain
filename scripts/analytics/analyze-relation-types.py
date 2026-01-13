#!/usr/bin/env python3
"""
Analyze Relation Types in Knowledge Base

Analyzes all relation types used in knowledge base, comparing against
official standard types. Useful for monitoring type consistency.

Usage:
    source venv/bin/activate && source venv/bin/activate && python scripts/analytics/analyze-relation-types.py [--format json|text] [--threshold N]

Options:
    --format json|text    Output format (default: text)
    --threshold N         Only show types with >N occurrences
    --verbose             Show detailed examples

Exit codes:
    0 - All types are standard
    1 - Non-standard types found
    2 - Error during execution
"""

import json
import sys
import argparse
from pathlib import Path
from collections import Counter

# Add scripts to path
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "scripts"))

from archival.relation_types import ALL_TYPES as OFFICIAL_TYPES


def analyze_relation_types(threshold=0):
    """
    Analyze all relation types in knowledge base.

    Args:
        threshold: Only show types with more than N occurrences

    Returns:
        dict with analysis results
    """
    # Load backlinks
    backlinks_path = ROOT / 'knowledge-base/_index/backlinks.json'
    with open(backlinks_path, 'r', encoding='utf-8') as f:
        backlinks_data = json.load(f)

    # Extract links dict
    backlinks = backlinks_data.get('links', {})

    all_types = []
    non_standard_examples = []

    # Collect all relation types
    for concept_id, data in backlinks.items():
        for rel in data.get('typed_links_to', []):
            rel_type = rel.get('type')
            target = rel.get('to')
            if rel_type:
                all_types.append(rel_type)
                if rel_type not in OFFICIAL_TYPES:
                    non_standard_examples.append({
                        'from': concept_id,
                        'to': target,
                        'type': rel_type
                    })

    # Count occurrences
    type_counts = Counter(all_types)
    unique_types = set(all_types)
    non_standard_types = unique_types - OFFICIAL_TYPES

    # Filter by threshold
    if threshold > 0:
        type_counts = {t: c for t, c in type_counts.items() if c > threshold}

    return {
        'total_relations': len(all_types),
        'unique_types': len(unique_types),
        'official_types_defined': len(OFFICIAL_TYPES),
        'non_standard_types': len(non_standard_types),
        'type_counts': dict(type_counts),
        'non_standard_list': sorted(non_standard_types),
        'non_standard_examples': non_standard_examples[:50],  # Limit examples
        'has_non_standard': len(non_standard_types) > 0
    }


def format_text_output(analysis, verbose=False):
    """Format analysis as human-readable text"""
    lines = []

    lines.append('=== RELATION TYPE ANALYSIS ===\n')
    lines.append(f'Total relation instances: {analysis["total_relations"]}')
    lines.append(f'Unique relation types found: {analysis["unique_types"]}')
    lines.append(f'Official types defined: {analysis["official_types_defined"]}')
    lines.append(f'Non-standard types: {analysis["non_standard_types"]}\n')

    if analysis['has_non_standard']:
        lines.append('❌ NON-STANDARD RELATION TYPES:')
        for t in analysis['non_standard_list']:
            count = analysis['type_counts'].get(t, 0)
            lines.append(f'  • "{t}": {count} occurrence(s)')

        if verbose and analysis['non_standard_examples']:
            lines.append('\nEXAMPLES (first 20):')
            for i, ex in enumerate(analysis['non_standard_examples'][:20], 1):
                lines.append(f'  {i}. [[{ex["from"]}]] --[{ex["type"]}]--> [[{ex["to"]}]]')
    else:
        lines.append('✅ All relation types are standard!')

    lines.append(f'\nOFFICIAL TYPES ({analysis["official_types_defined"]}):')
    for t in sorted(OFFICIAL_TYPES):
        count = analysis['type_counts'].get(t, 0)
        lines.append(f'  • "{t}": {count} uses')

    return '\n'.join(lines)


def format_json_output(analysis):
    """Format analysis as JSON"""
    return json.dumps(analysis, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze relation types in knowledge base',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--threshold', type=int, default=0,
                        help='Only show types with >N occurrences')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed examples (text mode only)')

    args = parser.parse_args()

    try:
        # Run analysis
        analysis = analyze_relation_types(threshold=args.threshold)

        # Output results
        if args.format == 'json':
            print(format_json_output(analysis))
        else:
            print(format_text_output(analysis, verbose=args.verbose))

        # Exit code based on results
        if analysis['has_non_standard']:
            return 1  # Non-standard types found
        else:
            return 0  # All standard

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
