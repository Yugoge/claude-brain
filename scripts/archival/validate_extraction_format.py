#!/usr/bin/env python3
"""
Validate Rem Extraction Format (Step 3 of /save workflow)

Early validation to prevent wrong data format from propagating through pipeline.

Validates:
- Required fields: rem_id, title, core_points
- Forbidden fields: content (common mistake)
- core_points must be array, not string
- rem_id must be kebab-case

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
from typing import List, Dict, Tuple


def validate_rem_id(rem_id: str) -> Tuple[bool, str]:
    """Validate rem_id format (kebab-case)"""
    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', rem_id):
        return (False, f"rem_id must be kebab-case: '{rem_id}'")
    return (True, "")


def validate_core_points(core_points) -> Tuple[bool, str]:
    """Validate core_points field"""
    if not isinstance(core_points, list):
        return (False, f"'core_points' must be array, got {type(core_points).__name__}")

    if len(core_points) == 0:
        return (False, "'core_points' array is empty (need 1-3 points)")

    if len(core_points) > 3:
        return (False, f"'core_points' has {len(core_points)} items (max 3)")

    for i, point in enumerate(core_points):
        if not isinstance(point, str):
            return (False, f"core_points[{i}] must be string, got {type(point).__name__}")
        if not point.strip():
            return (False, f"core_points[{i}] is empty")

    return (True, "")


def validate_candidate_rems(rems: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate extracted Rems format

    Returns: (is_valid, error_messages)
    """
    REQUIRED_FIELDS = ['rem_id', 'title', 'core_points']
    FORBIDDEN_FIELDS = ['content']

    errors = []

    if not isinstance(rems, list):
        errors.append(f"❌ Root must be array, got {type(rems).__name__}")
        return (False, errors)

    if len(rems) == 0:
        errors.append("❌ Empty Rems array (nothing to extract)")
        return (False, errors)

    seen_ids = set()

    for idx, rem in enumerate(rems):
        if not isinstance(rem, dict):
            errors.append(f"❌ Rem {idx}: Must be object, got {type(rem).__name__}")
            continue

        rem_id = rem.get('rem_id', f'<unnamed-{idx}>')

        # Check forbidden fields (common mistakes)
        for forbidden in FORBIDDEN_FIELDS:
            if forbidden in rem:
                errors.append(
                    f"❌ {rem_id}: Forbidden field '{forbidden}' found\n"
                    f"   ✅ Use: \"core_points\": [\"point1\", \"point2\", \"point3\"]\n"
                    f"   ❌ Not: \"content\": \"markdown string\""
                )

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in rem:
                errors.append(f"❌ {rem_id}: Missing required field '{field}'")

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
            if not isinstance(rem['title'], str):
                errors.append(f"❌ {rem_id}: 'title' must be string")
            elif not rem['title'].strip():
                errors.append(f"❌ {rem_id}: 'title' is empty")

        # Validate core_points
        if 'core_points' in rem:
            is_valid, error = validate_core_points(rem['core_points'])
            if not is_valid:
                errors.append(f"❌ {rem_id}: {error}")

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
        for error in errors:
            print(error, file=sys.stderr)
        print("", file=sys.stderr)
        print("Fix errors in candidate_rems.json and retry", file=sys.stderr)
        print("Format spec: docs/architecture/data-formats.md", file=sys.stderr)
        print("="*60, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
