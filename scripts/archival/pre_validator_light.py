#!/usr/bin/env python3
"""
Lightweight Pre-Creation Validator for Enriched Rems

Validates only what can be checked BEFORE file creation:
1. rem_id uniqueness (no collisions)
2. typed_relations target existence
3. Duplicate detection (Jaccard similarity >60%)

Does NOT validate frontmatter fields (subdomain, isced, created, source)
because those are added during file creation (Step 16.1).

Usage:
    python scripts/archival/pre_validator_light.py \\
        --enriched-rems /tmp/enriched_rems_final.json \\
        --domain-path "0412-finance-banking-insurance"

Exit Codes:
    0 = All validations passed
    1 = Warnings (non-blocking)
    2 = Critical errors (blocking)
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Set

# Constants
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

KB_DIR = ROOT / "knowledge-base"
BACKLINKS_FILE = KB_DIR / "_index" / "backlinks.json"

# Valid relation types (from RELATION_TYPES.md)
VALID_RELATION_TYPES = {
    'synonym', 'antonym', 'hypernym', 'hyponym',
    'part_of', 'has_part', 'derivationally_related',
    'cognate', 'collocates_with', 'translation_of',
    'is_a', 'has_subtype', 'instance_of', 'has_instance',
    'prerequisite_of', 'has_prerequisite',
    'cause_of', 'caused_by',
    'example_of', 'has_example',
    'uses', 'used_by',
    'defines', 'defined_by',
    'generalizes', 'specializes',
    'contrasts_with', 'complements', 'complemented_by',
    'analogous_to',
    'related'
}


def load_backlinks() -> Dict:
    """Load backlinks.json"""
    if not BACKLINKS_FILE.exists():
        return {'concepts': {}}

    with open(BACKLINKS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_existing_concepts(domain_path: str) -> Dict[str, Dict]:
    """Get all existing concepts in domain with metadata"""
    backlinks = load_backlinks()
    concepts_meta = backlinks.get('concepts', {})

    existing = {}
    for concept_id, meta in concepts_meta.items():
        file_path = meta.get('file', '')
        if domain_path in file_path:
            existing[concept_id] = meta

    return existing


def check_rem_id_collisions(enriched_rems: List[Dict], existing: Dict[str, Dict]) -> tuple:
    """Check rem_id uniqueness"""
    errors = []
    warnings = []

    for rem in enriched_rems:
        rem_id = rem.get('rem_id', '')

        if not rem_id:
            errors.append(f"❌ Missing rem_id field in: {rem.get('title', 'unknown')}")
            continue

        if rem_id in existing:
            errors.append(
                f"❌ rem_id collision: '{rem_id}' already exists!\n"
                f"   Existing: {existing[rem_id].get('file', 'unknown')}"
            )

    return errors, warnings


def check_typed_relations(enriched_rems: List[Dict], existing: Dict[str, Dict]) -> tuple:
    """Check typed_relations target existence and validity"""
    errors = []
    warnings = []
    auto_fixes = []

    # Valid IDs include BOTH existing concepts AND current batch of candidate Rems
    existing_ids = set(existing.keys())
    candidate_ids = {rem.get('rem_id') for rem in enriched_rems if rem.get('rem_id')}
    valid_ids = existing_ids | candidate_ids  # Union of both sets

    for rem in enriched_rems:
        rem_id = rem.get('rem_id', 'unknown')
        typed_relations = rem.get('typed_relations', [])

        if not typed_relations:
            warnings.append(f"⚠️  [{rem_id}] No typed_relations (empty)")
            continue

        valid_relations = []
        for rel in typed_relations:
            to_id = rel.get('to', '')
            rel_type = rel.get('type', '')

            # Check target exists (in existing concepts OR current batch)
            if to_id not in valid_ids:
                warnings.append(
                    f"⚠️  [{rem_id}] Relation target not found: [[{to_id}]] (will be removed)"
                )
                auto_fixes.append(f"Removed invalid target: [[{to_id}]] from [{rem_id}]")
                continue

            # Check relation type valid
            if rel_type not in VALID_RELATION_TYPES:
                warnings.append(
                    f"⚠️  [{rem_id}] Invalid relation type: {rel_type} → 'related'"
                )
                rel['type'] = 'related'
                auto_fixes.append(f"Changed {rel_type} → 'related' for [[{to_id}]]")

            valid_relations.append(rel)

        # Update rem with valid relations only
        rem['typed_relations'] = valid_relations

    return errors, warnings, auto_fixes


def check_duplicates(enriched_rems: List[Dict], existing: Dict[str, Dict]) -> tuple:
    """Check for duplicate concepts using Jaccard similarity"""
    errors = []
    warnings = []

    for rem in enriched_rems:
        rem_id = rem.get('rem_id', 'unknown')
        title = rem.get('title', '').lower()
        title_words = set(title.split())

        if len(title_words) == 0:
            continue

        for existing_id, meta in existing.items():
            existing_title = meta.get('title', existing_id).lower()
            existing_words = set(existing_title.split())

            if len(existing_words) == 0:
                continue

            # Jaccard similarity
            intersection = len(title_words & existing_words)
            union = len(title_words | existing_words)
            similarity = intersection / union if union > 0 else 0

            if similarity > 0.6:
                warnings.append(
                    f"⚠️  [{rem_id}] Potential duplicate: "
                    f"'{title}' similar to existing '{existing_title}' "
                    f"(similarity: {similarity:.0%})"
                )

    return errors, warnings


def validate_enriched_rems(enriched_rems: List[Dict], domain_path: str) -> Dict:
    """Run all validations"""
    existing = get_existing_concepts(domain_path)

    all_errors = []
    all_warnings = []
    all_auto_fixes = []

    # 1. Check rem_id collisions
    errors, warnings = check_rem_id_collisions(enriched_rems, existing)
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    # 2. Check typed_relations
    errors, warnings, auto_fixes = check_typed_relations(enriched_rems, existing)
    all_errors.extend(errors)
    all_warnings.extend(warnings)
    all_auto_fixes.extend(auto_fixes)

    # 3. Check duplicates
    errors, warnings = check_duplicates(enriched_rems, existing)
    all_errors.extend(errors)
    all_warnings.extend(warnings)

    return {
        'passed': len(all_errors) == 0,
        'errors': all_errors,
        'warnings': all_warnings,
        'auto_fixes': all_auto_fixes
    }


def print_report(result: Dict):
    """Print validation report"""
    print("\n" + "="*60)
    print("📋 PRE-CREATION VALIDATION REPORT (Lightweight)")
    print("="*60)

    # Auto-fixes
    if result['auto_fixes']:
        print(f"\n✅ AUTO-FIXES APPLIED ({len(result['auto_fixes'])}):")
        for fix in result['auto_fixes']:
            print(f"   {fix}")

    # Warnings
    if result['warnings']:
        print(f"\n⚠️  WARNINGS ({len(result['warnings'])}):")
        for warning in result['warnings']:
            print(f"   {warning}")

    # Errors
    if result['errors']:
        print(f"\n❌ CRITICAL ERRORS ({len(result['errors'])}):")
        for error in result['errors']:
            print(f"   {error}")
        print("\n🚫 Cannot proceed with Rem creation until errors are fixed.")

    # Summary
    print("\n" + "-"*60)
    if result['passed']:
        if result['warnings']:
            print("⚠️  VALIDATION PASSED WITH WARNINGS")
            print("   You can proceed, but review warnings carefully.")
        else:
            print("✅ VALIDATION PASSED (all checks successful)")
            print("   Safe to proceed with Rem creation.")
    else:
        print("❌ VALIDATION FAILED (critical errors found)")
        print("   Please fix the errors above and try again.")
    print("="*60 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Lightweight pre-creation validation for enriched Rems',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--enriched-rems', required=True,
                        help='Path to enriched_rems JSON file')
    parser.add_argument('--domain-path', required=True,
                        help='ISCED domain path (e.g., "0412-finance-banking-insurance")')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress output (only exit code)')

    args = parser.parse_args()

    try:
        # Load enriched Rems
        with open(args.enriched_rems, 'r', encoding='utf-8') as f:
            enriched_rems = json.load(f)

        # Run validations
        result = validate_enriched_rems(enriched_rems, args.domain_path)

        # Print report
        if not args.quiet:
            print_report(result)

        # Write back auto-fixed Rems
        with open(args.enriched_rems, 'w', encoding='utf-8') as f:
            json.dump(enriched_rems, f, indent=2, ensure_ascii=False)

        # Return exit code
        if result['passed']:
            return 1 if result['warnings'] else 0
        else:
            return 2

    except Exception as e:
        print(f"❌ Validation error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
