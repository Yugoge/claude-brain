#!/usr/bin/env python3
"""
Validate Typed Relations

Validate tutor-suggested relations against knowledge base index.
Filter out invalid relations (non-existent concepts, invalid types).

Usage:
    python scripts/archival/validate_relations.py --relations-json '{...}' --domain-path "domain-path"

Returns:
    JSON with valid_relations and invalid_relations arrays
"""

import json
import sys
import argparse
from pathlib import Path

# Constants
ROOT = Path(__file__).parent.parent.parent

# Add scripts to path for imports
sys.path.append(str(ROOT / "scripts"))

# Import valid relation types from central configuration
from archival.relation_types import ALL_TYPES as VALID_RELATION_TYPES


def load_domain_concepts(domain_path):
    """
    Load concepts in a specific domain from backlinks.json.

    Args:
        domain_path: ISCED domain path

    Returns:
        Set of concept IDs in this domain
    """
    from archival.get_domain_concepts import load_backlinks, extract_domain_concepts

    backlinks_data = load_backlinks()
    concepts = extract_domain_concepts(backlinks_data, domain_path)

    return {c['rem_id'] for c in concepts}


def normalize_concept_id(concept_id, domain_concepts=None):
    """
    Normalize concept ID by stripping filename prefix if present.

    Handles cases where tutor returns filename format instead of rem_id:
    - Input: "002-equity-derivatives-option-delta-universal-definition"
    - Output: "option-delta-universal-definition"

    Strategy: Try stripping prefixes until we find a match in domain_concepts.
    Pattern: NNN-subdomain-rem-id -> rem-id
    """
    import re

    # If no domain_concepts provided, use simple regex strip
    if domain_concepts is None:
        # Pattern: starts with 3 digits, strip everything up to 3rd hyphen
        match = re.match(r'^\d{3}-[a-z]+-[a-z]+-(.+)$', concept_id)
        if match:
            return match.group(1)
        return concept_id

    # Smart matching: try stripping prefixes until we find a match
    parts = concept_id.split('-')

    # Try progressively stripping parts from the front
    for i in range(len(parts)):
        candidate = '-'.join(parts[i:])
        if candidate in domain_concepts:
            return candidate

    # No match found, return original
    return concept_id


def validate_relations(typed_relations, domain_concepts):
    """
    Validate typed relations.

    Args:
        typed_relations: List of {"to": concept_id, "type": rel_type, "rationale": ...}
        domain_concepts: Set of valid concept IDs in this domain

    Returns:
        Tuple of (valid_relations, invalid_relations, normalized_count)
    """
    valid_relations = []
    invalid_relations = []
    normalized_count = 0

    for rel in typed_relations:
        target_id = rel.get('to')
        rel_type = rel.get('type')
        rationale = rel.get('rationale', '')

        # Try to normalize ID (strip filename prefix if present)
        normalized_id = normalize_concept_id(target_id, domain_concepts)
        if normalized_id != target_id:
            normalized_count += 1
            target_id = normalized_id

        # Validation 1: Check if target concept exists (after normalization)
        if target_id not in domain_concepts:
            invalid_relations.append({
                'to': target_id,
                'type': rel_type,
                'reason': 'concept_not_found',
                'rationale': rationale
            })
            continue

        # Validation 2: Check if relation type is valid
        if rel_type not in VALID_RELATION_TYPES:
            invalid_relations.append({
                'to': target_id,
                'type': rel_type,
                'reason': f'invalid_type',
                'rationale': rationale,
                'suggestion': 'Use types from RELATION_TYPES.md'
            })
            continue

        # Passed validation (use normalized ID)
        valid_relations.append({
            'to': target_id,
            'type': rel_type,
            'rationale': rationale
        })

    return valid_relations, invalid_relations, normalized_count


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Validate typed relations against knowledge base',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--relations-json', required=True,
                        help='JSON array of typed relations')
    parser.add_argument('--domain-path', required=True,
                        help='ISCED domain path')
    parser.add_argument('--verbose', action='store_true',
                        help='Print detailed validation report')

    args = parser.parse_args()

    try:
        # Parse relations
        typed_relations = json.loads(args.relations_json)

        # Load domain concepts
        domain_concepts = load_domain_concepts(args.domain_path)

        # Validate
        valid_rels, invalid_rels, normalized_count = validate_relations(typed_relations, domain_concepts)

        # Output result
        result = {
            'valid_relations': valid_rels,
            'invalid_relations': invalid_rels,
            'summary': {
                'total': len(typed_relations),
                'valid': len(valid_rels),
                'invalid': len(invalid_rels),
                'normalized': normalized_count
            }
        }

        print(json.dumps(result, indent=2, ensure_ascii=False))

        # Verbose report
        if args.verbose:
            print(f"\n📊 Validation Summary:", file=sys.stderr)
            print(f"   Total relations: {result['summary']['total']}", file=sys.stderr)
            print(f"   ✅ Valid: {result['summary']['valid']}", file=sys.stderr)
            print(f"   ❌ Invalid: {result['summary']['invalid']}", file=sys.stderr)

            if invalid_rels:
                print(f"\n❌ Invalid Relations:", file=sys.stderr)
                for inv in invalid_rels:
                    print(f"   - {inv['to']} ({inv['type']}): {inv['reason']}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
