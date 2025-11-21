#!/usr/bin/env python3
"""
Pre-flight Checker for /save Step 5.5
Validates Step 3.5 execution before file creation.

Usage:
    python scripts/archival/preflight_checker.py \\
        --enriched-rems enriched_rems.json \\
        --domain programming

Exit codes:
    0 = Pass
    1 = Warnings (non-blocking)
    2 = Critical errors (blocking)
"""

import json
import sys
import argparse


def check_enrichment_executed(enriched_rems, domain):
    """
    Verify domain tutor enrichment was executed for mandatory domains.

    Args:
        enriched_rems: List of enriched Rem dictionaries
        domain: Domain name (programming, language, finance, science)

    Returns:
        dict: {
            "passed": bool,
            "warnings": [str],
            "errors": [str]
        }
    """
    warnings = []
    errors = []

    # Step 3.5 is mandatory for these domains
    if domain in ["programming", "language", "finance", "science"]:
        for rem in enriched_rems:
            rem_id = rem.get("id", "unknown")

            # Check typed_relations field exists
            if "typed_relations" not in rem:
                errors.append(f"{rem_id}: missing typed_relations field")

            # Warn if empty (might be legitimate)
            elif len(rem.get("typed_relations", [])) == 0:
                warnings.append(f"{rem_id}: empty typed_relations (no relations found)")

    passed = len(errors) == 0

    return {
        "passed": passed,
        "warnings": warnings,
        "errors": errors
    }


def main():
    parser = argparse.ArgumentParser(description='Pre-flight check for enrichment execution')
    parser.add_argument('--enriched-rems', required=True, help='JSON file with enriched Rems')
    parser.add_argument('--domain', required=True, help='Domain: programming|language|finance|science')

    args = parser.parse_args()

    try:
        # Load enriched Rems
        with open(args.enriched_rems, 'r', encoding='utf-8') as f:
            enriched_rems = json.load(f)

        # Run check
        result = check_enrichment_executed(enriched_rems, args.domain)

        # Report results
        if result["passed"]:
            print("✅ Pre-flight check PASSED", file=sys.stderr)

            if result["warnings"]:
                print(f"\n⚠️  Warnings ({len(result['warnings'])}):", file=sys.stderr)
                for warning in result["warnings"]:
                    print(f"   - {warning}", file=sys.stderr)

            return 0 if not result["warnings"] else 1

        else:
            print("❌ Pre-flight check FAILED\n", file=sys.stderr)
            print("Step 3.5 (Domain Tutor Enrichment) was NOT executed.\n", file=sys.stderr)

            if result["errors"]:
                print(f"Errors ({len(result['errors'])}):", file=sys.stderr)
                for error in result["errors"]:
                    print(f"   - {error}", file=sys.stderr)

            print("\n⚠️  This will result in:", file=sys.stderr)
            print("   - No relationship discovery with existing concepts", file=sys.stderr)
            print("   - Missing typed relations (synonym, prerequisite_of, etc.)", file=sys.stderr)
            print("   - Lower Rem quality (no tutor enhancements)", file=sys.stderr)
            print("\nCannot proceed to file creation. Re-run /save with Step 3.5.\n", file=sys.stderr)

            return 2

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
