#!/usr/bin/env python3
"""
YAML Frontmatter Validator for Chat Archive Files

Detects and fixes unquoted colons and special characters in YAML frontmatter
that break parsing.

Usage:
    python validate-yaml-frontmatter.py [--fix] [--path DIRECTORY]

Options:
    --fix      Automatically fix detected errors
    --path     Directory to scan (default: chats/)
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import yaml


def extract_frontmatter(content: str) -> Tuple[str, str, str]:
    """
    Extract YAML frontmatter from markdown file.

    Returns:
        Tuple of (frontmatter, body, full_content)
    """
    lines = content.split('\n')

    if not lines[0].strip() == '---':
        return "", content, content

    # Find closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break

    if end_idx is None:
        return "", content, content

    frontmatter = '\n'.join(lines[1:end_idx])
    body = '\n'.join(lines[end_idx+1:])

    return frontmatter, body, content


def needs_quoting(value: str) -> bool:
    """
    Check if a YAML value needs quoting.

    Requires quotes if contains:
    - Unquoted colon (:)
    - Leading/trailing quotes that aren't properly escaped
    - Special YAML characters in problematic positions
    """
    if not value:
        return False

    # Already properly quoted
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        return False

    # Check for unquoted colons (but not in URLs like https://)
    if ':' in value and not re.match(r'^https?://', value):
        return True

    # Check for special YAML characters
    special_chars = ['#', '@', '`', '|', '>', '[', ']', '{', '}', '&', '*', '!']
    if any(char in value for char in special_chars):
        return True

    return False


def quote_value(value: str) -> str:
    """Add double quotes around a value, escaping internal quotes."""
    # Escape existing double quotes
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def fix_yaml_line(line: str) -> Tuple[str, bool]:
    """
    Fix a single YAML line if it has unquoted values.

    Returns:
        Tuple of (fixed_line, was_modified)
    """
    # Match key: value pattern
    match = re.match(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*(.+)$', line)

    if not match:
        return line, False

    indent, key, value = match.groups()
    value = value.rstrip()

    # Skip if value is array/dict notation
    if value.startswith('[') or value.startswith('{'):
        return line, False

    if needs_quoting(value):
        fixed_value = quote_value(value)
        fixed_line = f"{indent}{key}: {fixed_value}"
        return fixed_line, True

    return line, False


def validate_yaml(frontmatter: str) -> Tuple[bool, List[str]]:
    """
    Validate YAML frontmatter.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    try:
        yaml.safe_load(frontmatter)
        return True, []
    except yaml.YAMLError as e:
        errors.append(str(e))
        return False, errors


def fix_frontmatter(frontmatter: str) -> Tuple[str, List[str]]:
    """
    Fix YAML frontmatter by quoting problematic values.

    Returns:
        Tuple of (fixed_frontmatter, changes_made)
    """
    lines = frontmatter.split('\n')
    fixed_lines = []
    changes = []

    for i, line in enumerate(lines):
        fixed_line, was_modified = fix_yaml_line(line)
        fixed_lines.append(fixed_line)

        if was_modified:
            changes.append(f"Line {i+1}: {line.strip()} → {fixed_line.strip()}")

    return '\n'.join(fixed_lines), changes


def process_file(filepath: Path, fix: bool = False) -> Dict:
    """
    Process a single markdown file.

    Returns:
        Dict with validation results and changes
    """
    result = {
        'path': str(filepath),
        'valid': True,
        'errors': [],
        'changes': [],
        'fixed': False
    }

    try:
        content = filepath.read_text(encoding='utf-8')
        frontmatter, body, _ = extract_frontmatter(content)

        if not frontmatter:
            result['valid'] = True
            result['errors'] = ['No YAML frontmatter found']
            return result

        # Validate original
        is_valid, errors = validate_yaml(frontmatter)
        result['valid'] = is_valid
        result['errors'] = errors

        if not is_valid and fix:
            # Attempt to fix
            fixed_frontmatter, changes = fix_frontmatter(frontmatter)

            # Validate fixed version
            is_fixed_valid, _ = validate_yaml(fixed_frontmatter)

            if is_fixed_valid:
                # Write back
                new_content = f"---\n{fixed_frontmatter}\n---\n{body}"
                filepath.write_text(new_content, encoding='utf-8')
                result['fixed'] = True
                result['changes'] = changes
            else:
                result['errors'].append("Auto-fix failed - manual intervention required")

    except Exception as e:
        result['valid'] = False
        result['errors'] = [f"Exception: {str(e)}"]

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Validate and fix YAML frontmatter in markdown files"
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help="Automatically fix detected errors"
    )
    parser.add_argument(
        '--path',
        type=str,
        default='chats/',
        help="Directory to scan (default: chats/)"
    )

    args = parser.parse_args()

    base_path = Path(args.path)

    if not base_path.exists():
        print(f"Error: Directory '{base_path}' does not exist")
        sys.exit(1)

    # Find all markdown files
    md_files = list(base_path.rglob('*.md'))

    if not md_files:
        print(f"No markdown files found in '{base_path}'")
        sys.exit(0)

    print(f"Scanning {len(md_files)} markdown files...")
    print()

    results = []
    errors_found = 0
    files_fixed = 0

    for filepath in sorted(md_files):
        result = process_file(filepath, fix=args.fix)
        results.append(result)

        if not result['valid']:
            errors_found += 1
            print(f"❌ {result['path']}")
            for error in result['errors']:
                print(f"   {error}")

            if result['fixed']:
                files_fixed += 1
                print(f"   ✅ FIXED")
                for change in result['changes']:
                    print(f"      {change}")
            print()

    # Summary
    print("=" * 60)
    print(f"Total files scanned: {len(md_files)}")
    print(f"Files with errors: {errors_found}")

    if args.fix:
        print(f"Files fixed: {files_fixed}")
        if errors_found > files_fixed:
            print(f"Files requiring manual fix: {errors_found - files_fixed}")
    else:
        print()
        print("Run with --fix to automatically repair detected errors")

    sys.exit(0 if errors_found == 0 else 1)


if __name__ == '__main__':
    main()
