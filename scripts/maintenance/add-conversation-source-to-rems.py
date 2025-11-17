#!/usr/bin/env python3
"""
Add Conversation Source Section to All Rem Files

This script adds the missing "## Conversation Source" section to all Rem files
in the knowledge base, creating proper bidirectional navigation between Rems
and their source conversations.

The section is added after "## Related Rems" and before any other sections.

Usage:
    python scripts/maintenance/add-conversation-source-to-rems.py [--dry-run]

Options:
    --dry-run    Preview changes without writing files
"""

import re
import sys
import json
from pathlib import Path
from typing import Optional, Tuple


def load_chats_index() -> dict:
    """Load chats/index.json to get conversation titles."""
    index_path = Path(__file__).parent.parent.parent / "chats" / "index.json"

    if not index_path.exists():
        print(f"⚠️  Chats index not found: {index_path}", file=sys.stderr)
        return {"conversations": {}}

    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Failed to load chats index: {e}", file=sys.stderr)
        return {"conversations": {}}


def find_conversation_file(conversation_id: str, chats_dir: Path) -> Optional[Path]:
    """
    Find conversation file by ID.

    Searches in chats/YYYY-MM/ directories for files matching the conversation ID.
    """
    # Try to extract date from conversation ID
    # Format: {topic}-conversation-{YYYY-MM-DD} or {topic}-{YYYY-MM-DD}
    date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', conversation_id)

    if date_match:
        year = date_match.group(1)
        month = date_match.group(2)
        month_dir = chats_dir / f"{year}-{month}"

        if month_dir.exists():
            # Search for files containing the conversation ID
            for conv_file in month_dir.glob("*.md"):
                if conversation_id in conv_file.stem:
                    return conv_file

    # Fallback: search all month directories
    for month_dir in chats_dir.glob("20??-??"):
        if month_dir.is_dir():
            for conv_file in month_dir.glob("*.md"):
                if conversation_id in conv_file.stem:
                    return conv_file

    return None


def extract_frontmatter(content: str) -> Tuple[str, dict, str]:
    """
    Extract frontmatter from Rem file.

    Returns:
        (frontmatter_block, frontmatter_dict, body)
    """
    match = re.match(r'^(---\n)(.*?)(---\n)(.*)$', content, re.DOTALL)

    if not match:
        return None, {}, content

    frontmatter_block = match.group(1) + match.group(2) + match.group(3)
    frontmatter_yaml = match.group(2)
    body = match.group(4)

    # Parse frontmatter into dict
    frontmatter_dict = {}
    for line in frontmatter_yaml.strip().split('\n'):
        if ': ' in line:
            key, value = line.split(': ', 1)
            frontmatter_dict[key.strip()] = value.strip()

    return frontmatter_block, frontmatter_dict, body


def get_conversation_title(conversation_id: str, chats_index: dict, conv_file: Optional[Path]) -> str:
    """
    Get conversation title from index or file.

    Priority:
    1. chats/index.json
    2. Conversation file frontmatter
    3. Formatted conversation ID
    """
    # Try index first
    if conversation_id in chats_index.get("conversations", {}):
        conv_data = chats_index["conversations"][conversation_id]
        if "title" in conv_data:
            return conv_data["title"]

    # Try reading conversation file
    if conv_file and conv_file.exists():
        try:
            content = conv_file.read_text(encoding='utf-8')
            fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
            if fm_match:
                for line in fm_match.group(1).split('\n'):
                    if line.startswith('title:'):
                        title = line.split(':', 1)[1].strip()
                        # Remove quotes if present
                        title = title.strip('"').strip("'")
                        return title
        except Exception:
            pass

    # Fallback: Format conversation ID nicely
    # Remove date suffix and convert to title case
    title = re.sub(r'-\d{4}-\d{2}-\d{2}$', '', conversation_id)
    title = title.replace('-', ' ').title()
    return f"{title} Conversation"


def calculate_relative_path(rem_file: Path, conv_file: Path) -> str:
    """Calculate relative path from Rem file to conversation file."""
    import os
    rem_dir = rem_file.parent
    rel_path = os.path.relpath(conv_file, rem_dir)
    # Normalize to forward slashes (cross-platform)
    return rel_path.replace('\\', '/')


def has_conversation_source_section(body: str) -> bool:
    """Check if body already has Conversation Source section."""
    return bool(re.search(r'^## Conversation Source\s*$', body, re.MULTILINE))


def add_conversation_source_section(
    body: str,
    conversation_title: str,
    relative_path: str
) -> str:
    """
    Add "## Conversation Source" section after "## Related Rems".

    If "## Related Rems" exists, insert after it.
    Otherwise, append at end of file.
    """
    section = f"""## Conversation Source

→ See: [{conversation_title}]({relative_path})
"""

    # Try to find "## Related Rems" section
    related_rems_pattern = r'(## Related Rems\s*\n(?:.*?\n)*?)(?=## |\Z)'
    match = re.search(related_rems_pattern, body, re.MULTILINE | re.DOTALL)

    if match:
        # Insert after ## Related Rems section
        insert_pos = match.end()
        updated_body = body[:insert_pos] + '\n' + section + body[insert_pos:]
    else:
        # Append at end of file
        # Ensure there's a blank line before the new section
        if not body.endswith('\n\n'):
            if body.endswith('\n'):
                body += '\n'
            else:
                body += '\n\n'
        updated_body = body + section

    return updated_body


def process_rem_file(
    rem_file: Path,
    chats_dir: Path,
    chats_index: dict,
    dry_run: bool = False
) -> bool:
    """
    Process a single Rem file to add Conversation Source section.

    Returns:
        True if file was changed, False otherwise
    """
    try:
        content = rem_file.read_text(encoding='utf-8')

        # Extract frontmatter
        frontmatter_block, frontmatter_dict, body = extract_frontmatter(content)

        if not frontmatter_dict:
            print(f"⚠️  No frontmatter: {rem_file.name}")
            return False

        # Check if already has Conversation Source section
        if has_conversation_source_section(body):
            return False

        # Get source conversation ID
        source = frontmatter_dict.get('source', '')

        if not source:
            print(f"⚠️  No source field: {rem_file.name}")
            return False

        # Extract conversation ID (remove .md extension if present)
        conversation_id = source.replace('.md', '').replace('chats/', '')
        # Remove any YYYY-MM/ prefix
        conversation_id = re.sub(r'^\d{4}-\d{2}/', '', conversation_id)

        # Find conversation file
        conv_file = find_conversation_file(conversation_id, chats_dir)

        if not conv_file:
            print(f"⚠️  Conversation file not found for source '{source}': {rem_file.name}")
            # Still add section with generic title
            conversation_title = get_conversation_title(conversation_id, chats_index, None)
            # Use source path as-is for relative path calculation
            relative_path = f"../../../../chats/{source}"
        else:
            conversation_title = get_conversation_title(conversation_id, chats_index, conv_file)
            relative_path = calculate_relative_path(rem_file, conv_file)

        # Add Conversation Source section
        updated_body = add_conversation_source_section(body, conversation_title, relative_path)

        # Reconstruct file
        updated_content = frontmatter_block + updated_body

        if dry_run:
            print(f"📝 Would update: {rem_file.name}")
            print(f"   Source: {source}")
            print(f"   Title: {conversation_title}")
            print(f"   Path: {relative_path}")
        else:
            # Write updated content
            rem_file.write_text(updated_content, encoding='utf-8')
            print(f"✅ Updated: {rem_file.name}")

        return True

    except Exception as e:
        print(f"❌ Error processing {rem_file.name}: {e}")
        return False


def find_rem_files(kb_dir: Path) -> list:
    """Find all Rem files in knowledge base."""
    rem_files = []

    for file_path in kb_dir.rglob("*.md"):
        # Exclude templates, taxonomy, and index files
        if any(part in file_path.parts for part in ['_templates', '_taxonomy', '_index']):
            continue
        if file_path.name.endswith('index.md'):
            continue

        rem_files.append(file_path)

    return sorted(rem_files)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Add Conversation Source section to all Rem files"
    )
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview changes without writing files")

    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    kb_dir = project_root / "knowledge-base"
    chats_dir = project_root / "chats"

    if not kb_dir.exists():
        print(f"❌ Knowledge base directory not found: {kb_dir}")
        sys.exit(1)

    if not chats_dir.exists():
        print(f"❌ Chats directory not found: {chats_dir}")
        sys.exit(1)

    # Load chats index
    chats_index = load_chats_index()

    # Find all Rem files
    rem_files = find_rem_files(kb_dir)

    if not rem_files:
        print("❌ No Rem files found")
        sys.exit(1)

    print(f"🔍 Found {len(rem_files)} Rem files")

    if args.dry_run:
        print("🔄 DRY RUN MODE - No files will be modified\n")
    else:
        print("⚠️  WRITE MODE - Files will be modified\n")

    # Process files
    changed_count = 0

    for rem_file in rem_files:
        if process_rem_file(rem_file, chats_dir, chats_index, dry_run=args.dry_run):
            changed_count += 1

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total Rem files: {len(rem_files)}")
    print(f"   Changed: {changed_count}")
    print(f"   Unchanged: {len(rem_files) - changed_count}")

    if args.dry_run and changed_count > 0:
        print(f"\n💡 Run without --dry-run to apply changes")
    elif not args.dry_run and changed_count > 0:
        print(f"\n✅ Repair complete!")


if __name__ == "__main__":
    main()
