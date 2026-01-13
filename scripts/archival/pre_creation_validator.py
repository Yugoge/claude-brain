#!/usr/bin/env python3
"""
Pre-Creation Validation for Rem Files

Unified validation before creating Rem files. Checks:
1. Typed relations validity (concepts exist, types valid)
2. Duplicate concepts (fuzzy matching)
3. rem_id collision (uniqueness)
4. Frontmatter schema (required fields)
5. ISCED path existence
6. Source conversation file existence

Usage:
    source venv/bin/activate && source venv/bin/activate && python scripts/archival/pre_creation_validator.py \\
        --concepts-json '{"concepts": [...]}' \\
        --domain-path "NNNN-domain-slug" \\
        --source-file "chats/YYYY-MM/conversation.md"

Exit Codes:
    0 = All validations passed
    1 = Warnings (non-blocking, user can proceed)
    2 = Critical errors (blocking, must fix)
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set

# Add scripts directory to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Constants
KB_DIR = ROOT / "knowledge-base"
BACKLINKS_FILE = KB_DIR / "_index" / "backlinks.json"

# Valid relation types (from RELATION_TYPES.md)
VALID_RELATION_TYPES = {
    # Lexical
    'synonym', 'antonym', 'hypernym', 'hyponym',
    'part_of', 'has_part', 'derivationally_related',
    'cognate', 'collocates_with', 'translation_of',
    # Conceptual
    'is_a', 'has_subtype', 'instance_of', 'has_instance',
    'prerequisite_of', 'has_prerequisite',
    'cause_of', 'caused_by',
    'example_of', 'has_example',
    'uses', 'used_by',
    'defines', 'defined_by',
    'generalizes', 'specializes',
    # Comparative/Associative
    'contrasts_with', 'complements', 'complemented_by',
    'analogous_to',
    # Fallback
    'related'
}

# Required frontmatter fields
REQUIRED_FRONTMATTER_FIELDS = {'rem_id', 'subdomain', 'isced', 'created', 'source'}


class ValidationResult:
    """Stores validation results"""
    def __init__(self):
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.auto_fixes: List[str] = []

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_auto_fix(self, msg: str):
        self.auto_fixes.append(msg)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def get_exit_code(self) -> int:
        if self.has_errors():
            return 2  # Critical errors
        elif self.has_warnings():
            return 1  # Warnings only
        else:
            return 0  # All passed


def load_backlinks() -> Dict:
    """Load backlinks.json"""
    if not BACKLINKS_FILE.exists():
        return {'concepts': {}}

    with open(BACKLINKS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_existing_concepts(domain_path: str) -> Set[str]:
    """Get all existing concept IDs in domain"""
    backlinks = load_backlinks()
    concepts = backlinks.get('concepts', {})

    existing = set()
    for concept_id, meta in concepts.items():
        file_path = meta.get('file', '')
        if domain_path in file_path:
            existing.add(concept_id)

    return existing


def validate_typed_relations(concept: Dict, existing_concepts: Set[str], result: ValidationResult):
    """
    Validation 1: Check typed relations
    - Verify target concepts exist
    - Verify relation types are valid
    """
    typed_relations = concept.get('typed_relations', [])
    if not typed_relations:
        return  # No relations to validate

    valid_relations = []

    for rel in typed_relations:
        rel_to = rel.get('to', '')
        rel_type = rel.get('type', '')

        # Check if target concept exists
        if rel_to not in existing_concepts:
            result.add_warning(
                f"[{concept['rem_id']}] Relation target not found: [[{rel_to}]] "
                f"(will be filtered out)"
            )
            result.add_auto_fix(f"Removed invalid relation: [[{rel_to}]]")
            continue

        # Check if relation type is valid
        if rel_type not in VALID_RELATION_TYPES:
            result.add_warning(
                f"[{concept['rem_id']}] Invalid relation type: {rel_type} "
                f"(changing to 'related')"
            )
            rel['type'] = 'related'
            result.add_auto_fix(f"Changed {rel_type} → 'related' for [[{rel_to}]]")

        valid_relations.append(rel)

    # Update concept with valid relations only
    concept['typed_relations'] = valid_relations


def check_duplicates(concept: Dict, existing_concepts_data: Dict, domain_path: str, result: ValidationResult):
    """
    Validation 2: Check for duplicate concepts using fuzzy matching
    - Jaccard similarity >60% = potential duplicate
    - Non-blocking warning
    """
    concept_title = concept.get('title', '').lower()
    concept_words = set(concept_title.split())

    if len(concept_words) == 0:
        return

    backlinks = load_backlinks()
    concepts_meta = backlinks.get('concepts', {})

    for existing_id, meta in concepts_meta.items():
        file_path = meta.get('file', '')
        if domain_path not in file_path:
            continue  # Different domain

        existing_title = meta.get('title', existing_id).lower()
        existing_words = set(existing_title.split())

        if len(existing_words) == 0:
            continue

        # Jaccard similarity
        intersection = len(concept_words & existing_words)
        union = len(concept_words | existing_words)
        similarity = intersection / union if union > 0 else 0

        if similarity > 0.6:
            result.add_warning(
                f"[{concept['rem_id']}] Potential duplicate: "
                f"'{concept_title}' similar to existing '{existing_title}' "
                f"(similarity: {similarity:.0%})"
            )


def check_rem_id_collision(concept: Dict, result: ValidationResult):
    """
    Validation 3: Check rem_id uniqueness
    - Blocking error if rem_id already exists
    """
    rem_id = concept.get('rem_id', '')

    backlinks = load_backlinks()
    existing_ids = set(backlinks.get('concepts', {}).keys())

    if rem_id in existing_ids:
        result.add_error(
            f"❌ rem_id collision: '{rem_id}' already exists! "
            f"Choose a different concept-slug."
        )


def validate_frontmatter_schema(concept: Dict, result: ValidationResult):
    """
    Validation 4: Check frontmatter has all required fields
    - Blocking error if missing critical fields
    """
    concept_id = concept.get('rem_id', 'unknown')
    missing_fields = []

    for field in REQUIRED_FRONTMATTER_FIELDS:
        if field not in concept or not concept[field]:
            missing_fields.append(field)

    if missing_fields:
        result.add_error(
            f"❌ [{concept_id}] Missing required frontmatter fields: {', '.join(missing_fields)}"
        )


def validate_isced_path(domain_path: str, result: ValidationResult):
    """
    Validation 5: Check ISCED path exists in knowledge-base
    - Blocking error if path doesn't exist
    """
    # Parse domain_path to get ISCED hierarchy
    # Format: "NNNN-domain-slug"
    parts = domain_path.split('-')
    if len(parts) < 2:
        result.add_error(f"❌ Invalid ISCED path format: {domain_path}")
        return

    isced_code = parts[0]  # 4-digit ISCED code

    # Map ISCED code to directory structure
    # Format: NN-broad/NNN-narrow/NNNN-detailed/
    broad_code = isced_code[:2]  # First 2 digits
    narrow_code = isced_code[:3]  # First 3 digits
    detailed_code = isced_code  # All 4 digits

    # Find matching directory
    isced_dirs = list(KB_DIR.glob(f"{broad_code}-*/{narrow_code}-*/{domain_path}/"))

    if not isced_dirs:
        result.add_error(
            f"❌ ISCED path not found: {domain_path}\n"
            f"   Expected directory structure: {broad_code}-*/{narrow_code}-*/{domain_path}/"
        )
    elif len(isced_dirs) > 1:
        result.add_warning(
            f"⚠️  Multiple ISCED paths found for {domain_path}: {[str(d) for d in isced_dirs]}"
        )


def validate_source_file(source_file: str, result: ValidationResult):
    """
    Validation 6: Check source conversation file exists
    - Warning if file doesn't exist (may not be critical)
    """
    source_path = ROOT / source_file

    if not source_path.exists():
        result.add_warning(
            f"⚠️  Source conversation file not found: {source_file}\n"
            f"   (This may be OK if conversation is in active session)"
        )


def validate_concepts(concepts_data: Dict, domain_path: str, source_file: str) -> ValidationResult:
    """
    Run all validations on extracted concepts

    Args:
        concepts_data: Dict with 'concepts' array
        domain_path: ISCED domain path
        source_file: Path to source conversation file

    Returns:
        ValidationResult with warnings/errors/auto_fixes
    """
    result = ValidationResult()
    concepts = concepts_data.get('concepts', [])

    if not concepts:
        result.add_error("❌ No concepts provided for validation")
        return result

    # Get existing concepts in domain
    existing_concepts = get_existing_concepts(domain_path)

    # Validate ISCED path (once)
    validate_isced_path(domain_path, result)

    # Validate source file (once)
    if source_file:
        validate_source_file(source_file, result)

    # Validate each concept
    for concept in concepts:
        # 1. Typed relations
        validate_typed_relations(concept, existing_concepts, result)

        # 2. Duplicates
        check_duplicates(concept, existing_concepts, domain_path, result)

        # 3. rem_id collision
        check_rem_id_collision(concept, result)

        # 4. Frontmatter schema
        validate_frontmatter_schema(concept, result)

    return result


def print_validation_report(result: ValidationResult):
    """Print validation results to console"""
    print("\n" + "="*60)
    print("📋 PRE-CREATION VALIDATION REPORT")
    print("="*60)

    # Auto-fixes
    if result.auto_fixes:
        print(f"\n✅ AUTO-FIXES APPLIED ({len(result.auto_fixes)}):")
        for fix in result.auto_fixes:
            print(f"   {fix}")

    # Warnings
    if result.warnings:
        print(f"\n⚠️  WARNINGS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"   {warning}")

    # Errors
    if result.errors:
        print(f"\n❌ CRITICAL ERRORS ({len(result.errors)}):")
        for error in result.errors:
            print(f"   {error}")
        print("\n🚫 Cannot proceed with Rem creation until errors are fixed.")

    # Summary
    print("\n" + "-"*60)
    if result.has_errors():
        print("❌ VALIDATION FAILED (critical errors found)")
        print("   Please fix the errors above and try again.")
    elif result.has_warnings():
        print("⚠️  VALIDATION PASSED WITH WARNINGS")
        print("   You can proceed, but review warnings carefully.")
    else:
        print("✅ VALIDATION PASSED (all checks successful)")
        print("   Safe to proceed with Rem creation.")
    print("="*60 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Pre-creation validation for Rem files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--concepts-json', required=True,
                        help='JSON string with concepts array')
    parser.add_argument('--domain-path', required=True,
                        help='ISCED domain path')
    parser.add_argument('--source-file', default='',
                        help='Path to source conversation file (optional)')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress output (only exit code)')

    args = parser.parse_args()

    try:
        # Parse concepts JSON
        concepts_data = json.loads(args.concepts_json)

        # Run validations
        result = validate_concepts(concepts_data, args.domain_path, args.source_file)

        # Print report
        if not args.quiet:
            print_validation_report(result)

        # Return exit code
        return result.get_exit_code()

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"❌ Validation error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
