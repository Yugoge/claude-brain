#!/usr/bin/env python3
"""
Temporary validation script to check Rems and Chats format compliance.

Checks:
1. YAML frontmatter presence and required fields
2. Required sections (Rems Extracted, Conversation Source)
3. Hyperlinks in sections
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def parse_yaml_frontmatter(content: str) -> Tuple[Dict, str]:
    """Extract YAML frontmatter and remaining content."""
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not match:
        return {}, content

    yaml_text = match.group(1)
    body = match.group(2)

    # Simple YAML parsing (key: value)
    yaml_dict = {}
    for line in yaml_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            yaml_dict[key.strip()] = value.strip()

    return yaml_dict, body

def validate_rem(file_path: Path) -> List[str]:
    """Validate a Rem file format."""
    errors = []

    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return [f"Cannot read file: {e}"]

    # Check YAML frontmatter
    yaml_data, body = parse_yaml_frontmatter(content)

    if not yaml_data:
        errors.append("Missing YAML frontmatter")
        return errors

    # Required YAML fields for Rems
    required_fields = ['rem_id', 'subdomain', 'isced', 'created', 'source']
    for field in required_fields:
        if field not in yaml_data:
            errors.append(f"Missing YAML field: {field}")

    # Check required sections
    if '## Conversation Source' not in content and '## Source Conversation' not in content:
        errors.append("Missing '## Conversation Source' or '## Source Conversation' section")

    # Check for conversation link in source section
    source_section_match = re.search(
        r'## (?:Conversation Source|Source Conversation)\s+(.*?)(?:\n##|\Z)',
        content,
        re.DOTALL
    )
    if source_section_match:
        source_text = source_section_match.group(1)
        if not re.search(r'\[.*?\]\(.*?\.md\)', source_text):
            errors.append("No hyperlink found in Conversation Source section")

    return errors

def validate_chat(file_path: Path) -> List[str]:
    """Validate a Chat file format."""
    errors = []

    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return [f"Cannot read file: {e}"]

    # Check YAML frontmatter
    yaml_data, body = parse_yaml_frontmatter(content)

    if not yaml_data:
        errors.append("Missing YAML frontmatter")
        return errors

    # Required YAML fields for Chats
    required_fields = ['id', 'title', 'date', 'session_type', 'agent', 'domain']
    for field in required_fields:
        if field not in yaml_data:
            errors.append(f"Missing YAML field: {field}")

    # Check for Rems Extracted section
    if '## Rems Extracted' not in content and '## Extracted Rems' not in content:
        errors.append("Missing '## Rems Extracted' or '## Extracted Rems' section")
    else:
        # Check for hyperlinks in Rems Extracted section
        rems_section_match = re.search(
            r'## (?:Rems Extracted|Extracted Rems)\s+(.*?)(?:\n##|\Z)',
            content,
            re.DOTALL
        )
        if rems_section_match:
            rems_text = rems_section_match.group(1)
            # Look for markdown links
            links = re.findall(r'\[.*?\]\(.*?\.md\)', rems_text)
            if not links and 'rems_extracted' in yaml_data and yaml_data['rems_extracted'] != '[]':
                errors.append("Rems Extracted section exists but contains no hyperlinks")

    return errors

def main():
    root = Path("/home/user/knowledge-system")

    print("=" * 70)
    print("FORMAT VALIDATION REPORT")
    print("=" * 70)

    # Validate Rems
    print("\n📖 Validating Rems...")
    rem_files = list(root.glob("knowledge-base/**/*.md"))
    rem_files = [f for f in rem_files if '001-index.md' not in f.name]  # Skip index files

    rem_errors = {}
    for rem_file in rem_files:
        errors = validate_rem(rem_file)
        if errors:
            rem_errors[rem_file] = errors

    if rem_errors:
        print(f"❌ Found {len(rem_errors)} Rems with format issues:\n")
        for file_path, errors in list(rem_errors.items())[:10]:  # Show first 10
            rel_path = file_path.relative_to(root)
            print(f"  {rel_path}")
            for error in errors:
                print(f"    - {error}")
            print()

        if len(rem_errors) > 10:
            print(f"  ... and {len(rem_errors) - 10} more files with issues\n")
    else:
        print(f"✅ All {len(rem_files)} Rems are valid\n")

    # Validate Chats
    print("💬 Validating Chats...")
    chat_files = list(root.glob("chats/**/*.md"))

    chat_errors = {}
    for chat_file in chat_files:
        errors = validate_chat(chat_file)
        if errors:
            chat_errors[chat_file] = errors

    if chat_errors:
        print(f"❌ Found {len(chat_errors)} Chats with format issues:\n")
        for file_path, errors in list(chat_errors.items())[:10]:  # Show first 10
            rel_path = file_path.relative_to(root)
            print(f"  {rel_path}")
            for error in errors:
                print(f"    - {error}")
            print()

        if len(chat_errors) > 10:
            print(f"  ... and {len(chat_errors) - 10} more files with issues\n")
    else:
        print(f"✅ All {len(chat_files)} Chats are valid\n")

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Rems: {len(rem_files) - len(rem_errors)}/{len(rem_files)} valid")
    print(f"Chats: {len(chat_files) - len(chat_errors)}/{len(chat_files)} valid")

    if rem_errors or chat_errors:
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
