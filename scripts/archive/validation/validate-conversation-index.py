#!/usr/bin/env python3
"""
Conversation Index Validation Script

Validates chats/index.json schema and content.

Usage:
    python3 scripts/validate-conversation-index.py [--fix]

Options:
    --fix: Automatically fix minor issues (rename statistics → metadata)

Exit codes:
    0 - Validation passed
    1 - Validation failed
    2 - Fixed issues (with --fix)
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime


def validate_index(file_path, fix=False):
    """Validate conversation index structure and content."""
    index_file = Path(file_path)

    # Check file exists
    if not index_file.exists():
        print(f"❌ Error: {file_path} not found")
        return False

    # Load and parse JSON
    try:
        with open(index_file) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON - {e}")
        return False

    issues_fixed = False

    # Check for legacy 'statistics' field
    if "statistics" in data and "metadata" not in data:
        print("⚠️  Warning: Legacy 'statistics' field detected")
        if fix:
            print("   Migrating 'statistics' → 'metadata'...")
            data["metadata"] = data.pop("statistics")
            issues_fixed = True
        else:
            print("   Run with --fix to automatically migrate")
            return False

    # Required fields
    required_fields = ["version", "conversations", "metadata"]
    for field in required_fields:
        if field not in data:
            print(f"❌ Error: Missing required field '{field}'")
            return False

    # Version format (semver)
    if not re.match(r'^\d+\.\d+\.\d+$', data["version"]):
        print(f"❌ Error: Invalid version format (must be semver: X.Y.Z)")
        return False

    # Metadata sub-fields
    required_metadata = [
        "last_updated",
        "total_conversations",
        "total_turns",
        "total_concepts_extracted",
        "by_domain",
        "by_agent",
        "by_month"
    ]
    for field in required_metadata:
        if field not in data["metadata"]:
            print(f"❌ Error: Missing metadata field '{field}'")
            return False

    # Validate conversations structure
    if not isinstance(data["conversations"], dict):
        print("❌ Error: 'conversations' must be object/dict")
        return False

    # Write fixed data if changes made
    if issues_fixed:
        # Backup original
        backup_path = index_file.parent / f"{index_file.name}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        import shutil
        shutil.copy2(index_file, backup_path)
        print(f"   Backup created: {backup_path}")

        # Write fixed version
        with open(index_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"   Fixed index written: {index_file}")
        return "fixed"

    print("✅ Conversation index validation passed")
    print(f"   Version: {data['version']}")
    print(f"   Conversations: {data['metadata']['total_conversations']}")
    print(f"   Schema: metadata (correct)")
    return True


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Validate conversation index schema')
    parser.add_argument('--fix', action='store_true', help='Auto-fix minor issues')
    args = parser.parse_args()

    result = validate_index('chats/index.json', fix=args.fix)

    if result is True:
        sys.exit(0)
    elif result == "fixed":
        sys.exit(2)
    else:
        sys.exit(1)
