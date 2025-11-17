#!/usr/bin/env python3
"""
Progress File Validator

Validates .progress.md files have required fields and proper structure.

Usage:
    python validate-progress.py <progress-file>
    python validate-progress.py --scan learning-materials/
"""

import sys
import argparse
from pathlib import Path
import yaml


REQUIRED_FIELDS = [
    'material_id',
    'title',
    'type',
    'domain',
    'status',
    'progress_percentage'
]

VALID_TYPES = ['book', 'pdf', 'video', 'article', 'course', 'epub', 'ppt', 'docx']
VALID_STATUSES = ['not-started', 'in-progress', 'completed']


def extract_frontmatter(content):
    """Extract YAML frontmatter from markdown file"""
    lines = content.split('\n')

    if not lines[0].strip() == '---':
        return None, "Missing frontmatter delimiter"

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break

    if end_idx is None:
        return None, "Frontmatter not closed"

    frontmatter = '\n'.join(lines[1:end_idx])
    return frontmatter, None


def validate_progress_file(filepath):
    """Validate a single progress file"""
    errors = []

    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    # Extract frontmatter
    frontmatter, error = extract_frontmatter(content)
    if error:
        return False, [error]

    # Parse YAML
    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError as e:
        return False, [f"Invalid YAML: {e}"]

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    # Validate field values
    if 'type' in data and data['type'] not in VALID_TYPES:
        errors.append(f"Invalid type: {data['type']} (must be one of {VALID_TYPES})")

    if 'status' in data and data['status'] not in VALID_STATUSES:
        errors.append(f"Invalid status: {data['status']} (must be one of {VALID_STATUSES})")

    if 'progress_percentage' in data:
        progress = data['progress_percentage']
        if not isinstance(progress, (int, float)) or progress < 0 or progress > 100:
            errors.append(f"Invalid progress_percentage: {progress} (must be 0-100)")

    # Check for required sections in body
    required_sections = ['Material Information', 'Current Position', 'Learned Concepts']
    for section in required_sections:
        if section not in content:
            errors.append(f"Missing section: ## {section}")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Validate progress files")
    parser.add_argument('path', nargs='?', help="Progress file or directory to scan")
    parser.add_argument('--scan', action='store_true', help="Scan directory recursively")

    args = parser.parse_args()

    if not args.path:
        print("Usage: python validate-progress.py <file-or-directory>")
        sys.exit(1)

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path not found: {path}")
        sys.exit(1)

    # Collect files to validate
    if path.is_dir() or args.scan:
        files = list(path.rglob('*.progress.md'))
        if not files:
            print(f"No .progress.md files found in {path}")
            sys.exit(0)
    else:
        if not path.name.endswith('.progress.md'):
            print(f"Error: Not a progress file: {path}")
            sys.exit(1)
        files = [path]

    # Validate each file
    print(f"Validating {len(files)} progress file(s)...\n")

    total = len(files)
    valid = 0
    invalid = 0

    for filepath in sorted(files):
        is_valid, errors = validate_progress_file(filepath)

        if is_valid:
            valid += 1
            print(f"✅ {filepath}")
        else:
            invalid += 1
            print(f"❌ {filepath}")
            for error in errors:
                print(f"   - {error}")
            print()

    # Summary
    print("=" * 60)
    print(f"Total: {total} | Valid: {valid} | Invalid: {invalid}")

    sys.exit(0 if invalid == 0 else 1)


if __name__ == '__main__':
    main()
