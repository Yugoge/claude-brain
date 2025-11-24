#!/usr/bin/env python3
"""
Validate enriched_rems.json before passing to save_post_processor.py

Usage:
    python scripts/validation/validate-enriched-rems.py <enriched_rems.json>

Exit codes:
    0 = Valid
    1 = Validation failed (missing required fields)
"""

import json
import sys
from pathlib import Path

REQUIRED_SESSION_METADATA_FIELDS = [
    "id",
    "title",
    "summary",
    "archived_file",
    "session_type",
    "domain",
    "subdomain",
    "isced_path",
    "agent",
    "tags"
]

REQUIRED_REM_FIELDS = [
    "rem_id",
    "title",
    "core_points",
    "usage_scenario",
    "my_mistakes",
    "typed_relations",
    "output_path"
]

def validate_enriched_rems(file_path):
    """
    Validate enriched_rems.json structure and required fields.

    Returns: (is_valid, errors)
    """
    errors = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, [f"File not found: {file_path}"]
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    # Check top-level structure
    if "session_metadata" not in data:
        errors.append("Missing required key: 'session_metadata'")
        return False, errors

    if "rems" not in data:
        errors.append("Missing required key: 'rems'")
        return False, errors

    if "rems_to_update" not in data:
        errors.append("Missing required key: 'rems_to_update'")

    # Validate session_metadata
    metadata = data["session_metadata"]
    for field in REQUIRED_SESSION_METADATA_FIELDS:
        if field not in metadata:
            errors.append(f"session_metadata missing required field: '{field}'")
        elif metadata[field] is None and field != "tags":
            errors.append(f"session_metadata.{field} is null (must have value)")

    # Validate session_type enum
    if "session_type" in metadata:
        valid_types = ["learn", "ask", "review"]
        if metadata["session_type"] not in valid_types:
            errors.append(f"session_metadata.session_type must be one of {valid_types}, got: {metadata['session_type']}")

    # Validate Rems array
    rems = data.get("rems", [])
    if not isinstance(rems, list):
        errors.append("'rems' must be an array")
        return False, errors

    if len(rems) == 0:
        errors.append("'rems' array is empty (must have at least 1 Rem)")

    for i, rem in enumerate(rems):
        for field in REQUIRED_REM_FIELDS:
            if field not in rem:
                errors.append(f"rems[{i}] ('{rem.get('rem_id', 'unknown')}') missing required field: '{field}'")

        # Validate core_points is non-empty array
        if "core_points" in rem and not isinstance(rem["core_points"], list):
            errors.append(f"rems[{i}].core_points must be an array")
        elif "core_points" in rem and len(rem["core_points"]) == 0:
            errors.append(f"rems[{i}].core_points is empty (must have at least 1 point)")

        # Validate typed_relations is array (can be empty)
        if "typed_relations" in rem and not isinstance(rem["typed_relations"], list):
            errors.append(f"rems[{i}].typed_relations must be an array")

        # Validate output_path is non-empty
        if "output_path" in rem and not rem["output_path"]:
            errors.append(f"rems[{i}].output_path is empty (must have value)")

    # Validate rems_to_update array (can be empty for learn/ask sessions)
    rems_to_update = data.get("rems_to_update", [])
    if not isinstance(rems_to_update, list):
        errors.append("'rems_to_update' must be an array")

    return (len(errors) == 0, errors)


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate-enriched-rems.py <enriched_rems.json>", file=sys.stderr)
        return 1

    file_path = sys.argv[1]
    is_valid, errors = validate_enriched_rems(file_path)

    if is_valid:
        print(f"✅ Validation passed: {file_path}", file=sys.stderr)
        return 0
    else:
        print(f"❌ Validation failed: {file_path}", file=sys.stderr)
        print(f"\nFound {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  • {error}", file=sys.stderr)

        print("\n💡 Tip: Ensure main agent constructs complete session_metadata (see .claude/commands/save.md Step 9)", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
