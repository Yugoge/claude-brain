#!/usr/bin/env python3
"""
Validate Rem format compliance

Checks:
1. All Rems have exactly 6 frontmatter fields (or more if optional fields exist)
2. No non-standard fields exist
3. All required fields are present

Exit code 0 if all pass, 1 if any fail
"""

import os
import re
import sys
from pathlib import Path

# Required fields (6 standard fields)
REQUIRED_FIELDS = {
    'rem_id', 'title', 'domain', 'tags', 'created', 'source'
}

# Optional fields (content-level, can appear in frontmatter if present in content)
OPTIONAL_FIELDS = {
    'mistake', 'usage'  # These are OK if they appear
}

# Forbidden non-standard fields
FORBIDDEN_FIELDS = {
    'learned_in_session', 'mastery', 'learning_audit', 'related', 'taxonomy', 'review'
}

def parse_frontmatter_fields(content):
    """Extract field names from YAML frontmatter"""
    match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        fields = set(re.findall(r'^([a-z_]+):', frontmatter, re.MULTILINE))
        return fields
    return set()

def validate_rem_file(file_path):
    """Validate a single Rem file"""
    failures = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        fields = parse_frontmatter_fields(content)

        if not fields:
            return [f"No frontmatter found"]

        # Check required fields
        missing_fields = REQUIRED_FIELDS - fields
        if missing_fields:
            failures.append(f"Missing required fields: {', '.join(missing_fields)}")

        # Check for forbidden fields
        forbidden_found = fields & FORBIDDEN_FIELDS
        if forbidden_found:
            failures.append(f"Found forbidden fields: {', '.join(forbidden_found)}")

        # Check for unknown fields (not required, optional, or forbidden)
        known_fields = REQUIRED_FIELDS | OPTIONAL_FIELDS | FORBIDDEN_FIELDS
        unknown_fields = fields - known_fields
        if unknown_fields:
            failures.append(f"Found unknown fields: {', '.join(unknown_fields)}")

    except Exception as e:
        failures.append(f"Error reading file: {e}")

    return failures

def main():
    kb_path = 'knowledge-base'

    if not os.path.exists(kb_path):
        print(f"Error: {kb_path} directory not found")
        sys.exit(1)

    print("Validating Rem format compliance...\n")

    all_failures = {}

    for root, dirs, files in os.walk(kb_path):
        # Skip templates and index directories
        if '_templates' in root or '_index' in root:
            continue

        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                failures = validate_rem_file(file_path)

                if failures:
                    all_failures[file_path] = failures

    if not all_failures:
        print("✓ All Rems have valid format!")
        print(f"  - All required fields present: {', '.join(REQUIRED_FIELDS)}")
        print(f"  - No forbidden fields found")
        sys.exit(0)
    else:
        print(f"✗ Found {len(all_failures)} Rems with format issues:\n")
        for file_path, failures in all_failures.items():
            print(f"  - {file_path}")
            for failure in failures:
                print(f"    ✗ {failure}")
            print()
        sys.exit(1)

if __name__ == '__main__':
    main()
