#!/usr/bin/env python3
"""
Validate Rem source field format

Checks:
1. Source field exists
2. Source matches pattern: chats/YYYY-MM/*.md
3. Source file actually exists (dead link detection)

Exit code 0 if all pass, 1 if any fail
"""

import os
import re
import sys
from pathlib import Path

def is_valid_source_format(source_value):
    """Check if source matches required pattern: chats/YYYY-MM/*.md"""
    pattern = r'^chats/\d{4}-\d{2}/[a-zA-Z0-9\-]+\.md$'
    return bool(re.match(pattern, source_value))

def extract_source_from_file(file_path):
    """Extract source field from Rem file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'^source:\s*(.+)$', content, re.MULTILINE)
            if match:
                return match.group(1).strip()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return None

def validate_rems(kb_path):
    """Validate all Rem source fields"""
    failures = []

    for root, dirs, files in os.walk(kb_path):
        # Skip templates and index directories
        if '_templates' in root or '_index' in root:
            continue

        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                source = extract_source_from_file(file_path)

                if source is None:
                    failures.append({
                        'file': file_path,
                        'reason': 'No source field found'
                    })
                elif not is_valid_source_format(source):
                    failures.append({
                        'file': file_path,
                        'reason': f'Invalid source format: {source}'
                    })
                else:
                    # Check if source file exists
                    if not os.path.exists(source):
                        failures.append({
                            'file': file_path,
                            'reason': f'Dead link - source file does not exist: {source}'
                        })

    return failures

def main():
    kb_path = 'knowledge-base'

    if not os.path.exists(kb_path):
        print(f"Error: {kb_path} directory not found")
        sys.exit(1)

    print("Validating Rem source fields...")
    failures = validate_rems(kb_path)

    if not failures:
        print("✓ All Rem source fields are valid!")
        sys.exit(0)
    else:
        print(f"\n✗ Found {len(failures)} validation failures:\n")
        for failure in failures:
            print(f"  - {failure['file']}")
            print(f"    Reason: {failure['reason']}\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
