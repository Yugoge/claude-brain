#!/usr/bin/env python3
"""
Validate Rem Extraction Format (Step 3 of /save workflow)

Early validation to prevent wrong data format from propagating through pipeline.

Validates:
- Required fields: rem_id, title, core_points, usage_scenario, my_mistakes
- Optional fields: domain, isced, typed_relations
- Forbidden fields: content, source, created, subdomain, output_path (auto-generated)
- core_points must be array (1-3 items recommended), not string
- usage_scenario must be string
- my_mistakes must be array
- rem_id must be kebab-case
- No duplicate rem_ids
- typed_relations (if present) must follow RELATION_TYPES.md standard

Usage:
    source venv/bin/activate && python scripts/archival/validate_extraction_format.py \
      --candidate-rems /tmp/candidate_rems.json

Exit Codes:
    0 = Valid format, continue pipeline
    1 = Invalid format, BLOCK pipeline
"""

import json
import sys
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Any, Set


def validate_rem_id(rem_id: str) -> Tuple[bool, str]:
    """Validate rem_id format (kebab-case)"""
    if not isinstance(rem_id, str):
        return (False, f"rem_id must be string, got {type(rem_id).__name__}")

    if not rem_id.strip():
        return (False, "rem_id is empty")

    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', rem_id):
        return (False, f"rem_id must be kebab-case (lowercase, hyphens only): '{rem_id}'")

    return (True, "")


def validate_core_points(core_points, rem_id: str) -> Tuple[bool, str]:
    """Validate core_points field (Section 1: Core Memory Points)"""
    if not isinstance(core_points, list):
        return (False, f"'core_points' must be array, got {type(core_points).__name__}")

    if len(core_points) == 0:
        return (False, "'core_points' array is empty (need at least 1 point)")

    for i, point in enumerate(core_points):
        if not isinstance(point, str):
            return (False, f"core_points[{i}] must be string, got {type(point).__name__}")

        stripped = point.strip()
        if not stripped:
            return (False, f"core_points[{i}] is empty")

    return (True, "")


def validate_usage_scenario(usage_scenario: Any, rem_id: str) -> Tuple[bool, str]:
    """Validate usage_scenario field (Section 2: Usage Scenario)"""
    if not isinstance(usage_scenario, str):
        return (False, f"'usage_scenario' must be string, got {type(usage_scenario).__name__}")

    # Empty string is allowed (can be filled later by domain tutor)
    return (True, "")


def validate_my_mistakes(my_mistakes: Any, rem_id: str) -> Tuple[bool, str]:
    """Validate my_mistakes field (Section 3: My Mistakes)"""
    if not isinstance(my_mistakes, list):
        return (False, f"'my_mistakes' must be array, got {type(my_mistakes).__name__}")

    # Empty array is allowed (can be filled later or left empty)
    for i, mistake in enumerate(my_mistakes):
        if not isinstance(mistake, str):
            return (False, f"my_mistakes[{i}] must be string, got {type(mistake).__name__}")

    return (True, "")


# Standard relation types from RELATION_TYPES.md
STANDARD_RELATION_TYPES: Set[str] = {
    # Lexical relations
    'synonym', 'antonym', 'hypernym', 'hyponym', 'part_of', 'has_part',
    'derivationally_related', 'cognate', 'collocates_with', 'translation_of',
    # Conceptual/knowledge-graph relations
    'is_a', 'has_subtype', 'instance_of', 'has_instance',
    'prerequisite_of', 'has_prerequisite', 'cause_of', 'caused_by',
    'example_of', 'has_example', 'uses', 'used_by',
    'defines', 'defined_by', 'generalizes', 'specializes',
    # Comparative/associative relations
    'contrasts_with', 'complements', 'complemented_by', 'analogous_to', 'related'
}


def validate_typed_relations(typed_relations: Any, rem_id: str, all_rem_ids: Set[str]) -> Tuple[bool, str]:
    """Validate typed_relations field (optional)"""
    if not isinstance(typed_relations, list):
        return (False, f"'typed_relations' must be array, got {type(typed_relations).__name__}")

    for i, rel in enumerate(typed_relations):
        if not isinstance(rel, dict):
            return (False, f"typed_relations[{i}] must be object, got {type(rel).__name__}")

        # Check required fields
        if 'to' not in rel:
            return (False, f"typed_relations[{i}] missing 'to' field")
        if 'type' not in rel:
            return (False, f"typed_relations[{i}] missing 'type' field")

        # Validate 'to' field
        if not isinstance(rel['to'], str) or not rel['to'].strip():
            return (False, f"typed_relations[{i}]['to'] must be non-empty string")

        # Validate 'type' field
        rel_type = rel.get('type', '')
        if not isinstance(rel_type, str) or not rel_type.strip():
            return (False, f"typed_relations[{i}]['type'] must be non-empty string")

        # Check against standard relation types
        if rel_type not in STANDARD_RELATION_TYPES:
            return (False, f"typed_relations[{i}]['type']='{rel_type}' not in RELATION_TYPES.md standard. Valid types: {sorted(STANDARD_RELATION_TYPES)}")

        # Validate 'rationale' if present (optional but recommended)
        if 'rationale' in rel:
            if not isinstance(rel['rationale'], str):
                return (False, f"typed_relations[{i}]['rationale'] must be string")

        # Check for self-references
        if rel['to'] == rem_id:
            return (False, f"typed_relations[{i}]: Self-reference not allowed (to='{rem_id}')")

    return (True, "")


def validate_title(title: Any, rem_id: str) -> Tuple[bool, str]:
    """Validate title field"""
    if not isinstance(title, str):
        return (False, f"'title' must be string, got {type(title).__name__}")

    stripped = title.strip()
    if not stripped:
        return (False, "'title' is empty")

    # Title should not contain markdown formatting
    if stripped.startswith('#'):
        return (False, "'title' should not start with markdown header")

    return (True, "")


def validate_candidate_rems(rems: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate extracted Rems format (candidate_rems.json from Step 3)

    Returns: (is_valid, error_messages)
    """
    REQUIRED_FIELDS = ['rem_id', 'title', 'core_points', 'usage_scenario', 'my_mistakes']
    OPTIONAL_FIELDS = ['domain', 'isced', 'typed_relations']
    FORBIDDEN_FIELDS = [
        'content',      # Common mistake: full markdown content instead of structured sections
        'source',       # Auto-generated by save workflow
        'created',      # Auto-generated by save workflow
        'subdomain',    # Auto-generated from ISCED
        'output_path',  # Auto-generated by workflow_orchestrator
    ]

    errors = []
    warnings = []

    if not isinstance(rems, list):
        errors.append(f"❌ Root must be array, got {type(rems).__name__}")
        return (False, errors)

    if len(rems) == 0:
        errors.append("❌ Empty Rems array (nothing to extract)")
        return (False, errors)

    # Collect all rem_ids for cross-reference validation
    all_rem_ids = set()
    for rem in rems:
        if isinstance(rem, dict) and 'rem_id' in rem:
            all_rem_ids.add(rem['rem_id'])

    seen_ids = set()

    for idx, rem in enumerate(rems):
        if not isinstance(rem, dict):
            errors.append(f"❌ Rem {idx}: Must be object, got {type(rem).__name__}")
            continue

        rem_id = rem.get('rem_id', f'<unnamed-{idx}>')

        # Check forbidden fields (common mistakes)
        for forbidden in FORBIDDEN_FIELDS:
            if forbidden in rem:
                if forbidden == 'content':
                    errors.append(
                        f"❌ {rem_id}: Forbidden field '{forbidden}' found\n"
                        f"   ✅ Use: \"core_points\": [\"point1\", \"point2\", \"point3\"]\n"
                        f"   ❌ Not: \"content\": \"markdown string\""
                    )
                else:
                    errors.append(
                        f"❌ {rem_id}: Forbidden field '{forbidden}' (auto-generated by pipeline)"
                    )

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in rem:
                errors.append(f"❌ {rem_id}: Missing required field '{field}'")

        # Warn about unexpected fields
        expected_fields = set(REQUIRED_FIELDS + OPTIONAL_FIELDS + FORBIDDEN_FIELDS)
        for field in rem.keys():
            if field not in expected_fields:
                warnings.append(f"⚠️  {rem_id}: Unexpected field '{field}' (will be ignored)")

        # Validate rem_id format
        if 'rem_id' in rem:
            is_valid, error = validate_rem_id(rem['rem_id'])
            if not is_valid:
                errors.append(f"❌ {rem_id}: {error}")

            # Check duplicates
            if rem['rem_id'] in seen_ids:
                errors.append(f"❌ {rem_id}: Duplicate rem_id")
            seen_ids.add(rem['rem_id'])

        # Validate title
        if 'title' in rem:
            is_valid, error = validate_title(rem['title'], rem_id)
            if not is_valid:
                errors.append(f"❌ {rem_id}: {error}")

        # Validate core_points (Section 1: Core Memory Points)
        if 'core_points' in rem:
            is_valid, error = validate_core_points(rem['core_points'], rem_id)
            if not is_valid:
                errors.append(f"❌ {rem_id}: {error}")

        # Validate usage_scenario (Section 2: Usage Scenario)
        if 'usage_scenario' in rem:
            is_valid, error = validate_usage_scenario(rem['usage_scenario'], rem_id)
            if not is_valid:
                errors.append(f"❌ {rem_id}: {error}")

        # Validate my_mistakes (Section 3: My Mistakes)
        if 'my_mistakes' in rem:
            is_valid, error = validate_my_mistakes(rem['my_mistakes'], rem_id)
            if not is_valid:
                errors.append(f"❌ {rem_id}: {error}")

        # Validate typed_relations (Section 4: Related Rems - optional)
        if 'typed_relations' in rem:
            is_valid, error = validate_typed_relations(rem['typed_relations'], rem_id, all_rem_ids)
            if not is_valid:
                errors.append(f"❌ {rem_id}: {error}")

        # Validate domain (optional)
        if 'domain' in rem:
            if not isinstance(rem['domain'], str) or not rem['domain'].strip():
                errors.append(f"❌ {rem_id}: 'domain' must be non-empty string")

        # Validate isced (optional)
        if 'isced' in rem:
            if not isinstance(rem['isced'], str) or not rem['isced'].strip():
                errors.append(f"❌ {rem_id}: 'isced' must be non-empty string")

    # Print warnings to stderr if any
    if warnings:
        for warning in warnings:
            print(warning, file=sys.stderr)

    return (len(errors) == 0, errors)


def main():
    parser = argparse.ArgumentParser(
        description='Validate candidate Rems format (Step 3 of /save workflow)'
    )
    parser.add_argument(
        '--candidate-rems',
        required=True,
        help='Path to candidate_rems.json'
    )

    args = parser.parse_args()

    # Load candidate Rems
    try:
        with open(args.candidate_rems, 'r', encoding='utf-8') as f:
            rems = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {args.candidate_rems}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return 1

    # Validate
    is_valid, errors = validate_candidate_rems(rems)

    if is_valid:
        print(f"✅ Format validation passed ({len(rems)} Rems)", file=sys.stderr)
        return 0
    else:
        print("", file=sys.stderr)
        print("="*60, file=sys.stderr)
        print("❌ FORMAT VALIDATION FAILED", file=sys.stderr)
        print("="*60, file=sys.stderr)
        print("", file=sys.stderr)
        print(f"Found {len(errors)} error(s) in {len(rems)} Rems:\n", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        print("", file=sys.stderr)
        print("Fix errors in candidate_rems.json and retry", file=sys.stderr)
        print("", file=sys.stderr)
        print("📖 Required format (4 sections):", file=sys.stderr)
        print("   {", file=sys.stderr)
        print('     "rem_id": "kebab-case-id",', file=sys.stderr)
        print('     "title": "Human Readable Title",', file=sys.stderr)
        print('     "core_points": ["Point 1", "Point 2", "Point 3"],  // Section 1', file=sys.stderr)
        print('     "usage_scenario": "When/where/how to use",          // Section 2', file=sys.stderr)
        print('     "my_mistakes": ["❌ Error → ✅ Correction"],         // Section 3', file=sys.stderr)
        print('     "typed_relations": [...]                            // Section 4 (optional)', file=sys.stderr)
        print("   }", file=sys.stderr)
        print("", file=sys.stderr)
        print("📚 Format spec: docs/architecture/data-formats.md", file=sys.stderr)
        print("📚 Relation types: docs/architecture/standards/RELATION_TYPES.md", file=sys.stderr)
        print("="*60, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
