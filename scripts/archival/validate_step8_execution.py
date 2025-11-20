#!/usr/bin/env python3
"""
Step 8 Enforcement Gate

Validates that Domain Tutor Enrichment (Step 8) was properly executed
for domains where it's MANDATORY.

Usage:
    python scripts/archival/validate_step8_execution.py \\
        --enriched-rems enriched_rems.json \\
        --domain finance

Exit Codes:
    0 = Pass (Step 8 properly executed)
    1 = Warning (typed_relations empty but not critical)
    2 = Critical (Step 8 skipped for mandatory domain)
"""

import json
import sys
import argparse
from pathlib import Path


MANDATORY_DOMAINS = {
    'programming',
    'language',
    'finance',
    'science',
    'medicine',
    'law'
}


def validate_step8(enriched_rems, domain):
    """
    Validate Step 8 execution.

    Returns: (exit_code, message)
    """

    # Check 1: typed_relations field exists
    for rem in enriched_rems:
        if 'typed_relations' not in rem:
            return (
                2,
                f"CRITICAL: Rem '{rem.get('rem_id', 'unknown')}' missing 'typed_relations' field\n"
                f"Step 8 (Domain Tutor Enrichment) was not executed"
            )

    # Check 2: For mandatory domains, verify relations were added
    if domain in MANDATORY_DOMAINS:
        total_relations = sum(len(r.get('typed_relations', [])) for r in enriched_rems)

        if total_relations == 0:
            # Check if this is inter-candidate-only scenario
            rem_count = len(enriched_rems)

            if rem_count <= 1:
                # Single Rem: typed_relations might be empty if no existing concepts to relate to
                return (
                    1,
                    f"WARNING: No typed_relations found for {domain} domain\n"
                    f"Single Rem with no existing concepts to relate to - acceptable but verify tutor was called"
                )
            else:
                # Multiple Rems: Should have inter-candidate relations at minimum
                return (
                    2,
                    f"CRITICAL: Zero typed_relations for {domain} domain with {rem_count} Rems\n"
                    f"Domain Tutor Enrichment (Step 8) is MANDATORY for {domain}\n"
                    f"Expected inter-candidate relations between new concepts"
                )

        # Relations found - check quality
        avg_relations = total_relations / len(enriched_rems)

        if avg_relations < 0.5:
            return (
                1,
                f"WARNING: Low typed_relations density ({avg_relations:.1f} per Rem)\n"
                f"Tutor may not have identified pedagogical relationships effectively"
            )

        return (
            0,
            f"✓ Step 8 executed correctly ({total_relations} relations across {len(enriched_rems)} Rems)"
        )

    else:
        # Non-mandatory domain - just verify field exists
        return (
            0,
            f"✓ Step 8 optional for {domain} domain (typed_relations field present)"
        )


def main():
    parser = argparse.ArgumentParser(description='Validate Step 8 Execution')
    parser.add_argument('--enriched-rems', required=True, help='Path to enriched_rems.json')
    parser.add_argument('--domain', required=True, help='Domain classification')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    try:
        # Load enriched Rems
        with open(args.enriched_rems, 'r', encoding='utf-8') as f:
            enriched_rems = json.load(f)

        if args.verbose:
            print(f"Loaded {len(enriched_rems)} Rems from {args.enriched_rems}", file=sys.stderr)
            print(f"Domain: {args.domain}", file=sys.stderr)
            print(f"Mandatory enrichment: {args.domain in MANDATORY_DOMAINS}", file=sys.stderr)

        # Validate
        exit_code, message = validate_step8(enriched_rems, args.domain)

        if exit_code == 0:
            print(message)
        elif exit_code == 1:
            print(message, file=sys.stderr)
        else:  # exit_code == 2
            print(message, file=sys.stderr)

        return exit_code

    except FileNotFoundError:
        print(f"❌ Error: {args.enriched_rems} not found", file=sys.stderr)
        return 2

    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {args.enriched_rems}: {e}", file=sys.stderr)
        return 2

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
