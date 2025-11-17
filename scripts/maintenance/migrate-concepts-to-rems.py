#!/usr/bin/env python3
"""
Migrate Conversation Frontmatter: concepts_extracted → rems_extracted

This script batch-updates all conversation files to use the standardized
'rems_extracted' field instead of the legacy 'concepts_extracted' field.

Usage:
    python scripts/maintenance/migrate-concepts-to-rems.py [--dry-run]

Options:
    --dry-run    Preview changes without writing files
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def find_conversation_files(chats_dir: Path) -> List[Path]:
    """Find all conversation markdown files (excluding templates)."""
    conversation_files = []

    for pattern in ['2025-*/*.md', '2024-*/*.md', '2026-*/*.md']:
        conversation_files.extend(chats_dir.glob(pattern))

    return sorted(conversation_files)


def extract_frontmatter(content: str) -> Tuple[str, str, str]:
    """
    Extract frontmatter from markdown content.

    Returns:
        (full_frontmatter_block, frontmatter_yaml, body)
    """
    match = re.match(r'^(---\n)(.*?)(---\n)(.*)$', content, re.DOTALL)
    if match:
        return match.group(1) + match.group(2) + match.group(3), match.group(2), match.group(4)
    return None, None, content


def migrate_frontmatter(frontmatter_yaml: str) -> Tuple[str, bool]:
    """
    Migrate frontmatter from concepts_extracted to rems_extracted.

    Returns:
        (updated_frontmatter_yaml, was_changed)
    """
    # Check if already using rems_extracted
    if re.search(r'^rems_extracted:', frontmatter_yaml, re.MULTILINE):
        return frontmatter_yaml, False

    # Find concepts_extracted field
    concepts_match = re.search(r'^concepts_extracted:\s*(.+?)$', frontmatter_yaml, re.MULTILINE)

    if not concepts_match:
        # No concepts_extracted field found
        return frontmatter_yaml, False

    concepts_value = concepts_match.group(1)

    # Replace concepts_extracted with rems_extracted
    updated_frontmatter = re.sub(
        r'^concepts_extracted:',
        'rems_extracted:',
        frontmatter_yaml,
        flags=re.MULTILINE
    )

    return updated_frontmatter, True


def migrate_conversation_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Migrate a single conversation file.

    Returns:
        True if file was changed, False otherwise
    """
    try:
        content = file_path.read_text(encoding='utf-8')

        # Extract frontmatter
        frontmatter_block, frontmatter_yaml, body = extract_frontmatter(content)

        if not frontmatter_yaml:
            print(f"⚠️  No frontmatter found: {file_path.name}")
            return False

        # Migrate frontmatter
        updated_yaml, was_changed = migrate_frontmatter(frontmatter_yaml)

        if not was_changed:
            return False

        # Reconstruct file
        updated_content = f"---\n{updated_yaml}---\n{body}"

        if dry_run:
            print(f"📝 Would update: {file_path.name}")
            # Show diff
            old_line = re.search(r'^concepts_extracted:.*$', frontmatter_yaml, re.MULTILINE).group(0)
            new_line = re.search(r'^rems_extracted:.*$', updated_yaml, re.MULTILINE).group(0)
            print(f"   - {old_line}")
            print(f"   + {new_line}")
        else:
            # Write updated content
            file_path.write_text(updated_content, encoding='utf-8')
            print(f"✅ Updated: {file_path.name}")

        return True

    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate conversation frontmatter: concepts_extracted → rems_extracted"
    )
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview changes without writing files")

    args = parser.parse_args()

    # Find all conversation files
    project_root = Path(__file__).parent.parent.parent
    chats_dir = project_root / "chats"

    if not chats_dir.exists():
        print(f"❌ Chats directory not found: {chats_dir}")
        sys.exit(1)

    conversation_files = find_conversation_files(chats_dir)

    if not conversation_files:
        print("❌ No conversation files found")
        sys.exit(1)

    print(f"🔍 Found {len(conversation_files)} conversation files")

    if args.dry_run:
        print("🔄 DRY RUN MODE - No files will be modified\n")
    else:
        print("⚠️  WRITE MODE - Files will be modified\n")

    # Process files
    changed_count = 0

    for file_path in conversation_files:
        if migrate_conversation_file(file_path, dry_run=args.dry_run):
            changed_count += 1

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total files: {len(conversation_files)}")
    print(f"   Changed: {changed_count}")
    print(f"   Unchanged: {len(conversation_files) - changed_count}")

    if args.dry_run and changed_count > 0:
        print(f"\n💡 Run without --dry-run to apply changes")
    elif not args.dry_run and changed_count > 0:
        print(f"\n✅ Migration complete!")


if __name__ == "__main__":
    main()
