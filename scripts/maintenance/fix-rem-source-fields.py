#!/usr/bin/env python3
"""
Fix Incorrect Rem Source Fields

This script fixes Rem files where the source field points to non-existent
conversation IDs by matching them with actual conversation files based on
the rems_extracted field in conversations.

Usage:
    python scripts/maintenance/fix-rem-source-fields.py [--dry-run]
"""

import re
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional


def load_chats_index() -> dict:
    """Load chats/index.json."""
    index_path = Path(__file__).parent.parent.parent / "chats" / "index.json"

    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    return {"conversations": {}}


def find_all_conversations(chats_dir: Path) -> List[Path]:
    """Find all conversation markdown files."""
    conversations = []

    for month_dir in chats_dir.glob("20??-??"):
        if month_dir.is_dir():
            for conv_file in month_dir.glob("*.md"):
                if not conv_file.name.startswith('_'):
                    conversations.append(conv_file)

    return conversations


def extract_rems_from_conversation(conv_file: Path) -> tuple:
    """
    Extract rems_extracted list from conversation frontmatter.

    Returns:
        (conversation_id, list_of_rem_ids)
    """
    try:
        content = conv_file.read_text(encoding='utf-8')
        fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)

        if not fm_match:
            return None, []

        frontmatter = fm_match.group(1)
        conversation_id = None
        rems_extracted = []

        for line in frontmatter.split('\n'):
            if line.startswith('id:'):
                conversation_id = line.split(':', 1)[1].strip()
            elif line.startswith('rems_extracted:'):
                # Parse list: [item1, item2, item3]
                rems_text = line.split(':', 1)[1].strip()
                if rems_text.startswith('[') and rems_text.endswith(']'):
                    rems_text = rems_text[1:-1]  # Remove [ ]
                    if rems_text:
                        rems_extracted = [r.strip() for r in rems_text.split(',')]

        return conversation_id, rems_extracted

    except Exception as e:
        print(f"⚠️  Error reading {conv_file.name}: {e}", file=sys.stderr)
        return None, []


def build_rem_to_conversation_map(chats_dir: Path) -> Dict[str, str]:
    """
    Build mapping from rem_id to conversation_id.

    Returns:
        {rem_id: conversation_id}
    """
    rem_map = {}
    conversations = find_all_conversations(chats_dir)

    for conv_file in conversations:
        conv_id, rems = extract_rems_from_conversation(conv_file)

        if not conv_id:
            continue

        for rem_id in rems:
            if rem_id:
                rem_map[rem_id] = conv_id

    return rem_map


def fix_rem_source(rem_file: Path, correct_conversation_id: str, dry_run: bool = False) -> bool:
    """
    Fix source field in Rem frontmatter.

    Returns:
        True if file was changed, False otherwise
    """
    try:
        content = rem_file.read_text(encoding='utf-8')

        # Extract frontmatter
        fm_match = re.match(r'^(---\n)(.*?)(---\n)(.*)$', content, re.DOTALL)

        if not fm_match:
            return False

        fm_start = fm_match.group(1)
        frontmatter = fm_match.group(2)
        fm_end = fm_match.group(3)
        body = fm_match.group(4)

        # Check current source
        source_match = re.search(r'^source:\s*(.+?)$', frontmatter, re.MULTILINE)

        if not source_match:
            return False

        old_source = source_match.group(1).strip()

        # Update source field
        new_source = correct_conversation_id
        updated_frontmatter = re.sub(
            r'^source:\s*.+$',
            f'source: {new_source}',
            frontmatter,
            flags=re.MULTILINE
        )

        if updated_frontmatter == frontmatter:
            return False

        # Reconstruct file
        updated_content = fm_start + updated_frontmatter + fm_end + body

        if dry_run:
            print(f"📝 Would update: {rem_file.name}")
            print(f"   Old source: {old_source}")
            print(f"   New source: {new_source}")
        else:
            rem_file.write_text(updated_content, encoding='utf-8')
            print(f"✅ Updated: {rem_file.name}")
            print(f"   {old_source} → {new_source}")

        return True

    except Exception as e:
        print(f"❌ Error processing {rem_file.name}: {e}")
        return False


def find_rem_files(kb_dir: Path) -> List[Path]:
    """Find all Rem files."""
    rem_files = []

    for file_path in kb_dir.rglob("*.md"):
        if any(part in file_path.parts for part in ['_templates', '_taxonomy', '_index']):
            continue
        if file_path.name.endswith('index.md'):
            continue

        rem_files.append(file_path)

    return sorted(rem_files)


def extract_rem_id(rem_file: Path) -> Optional[str]:
    """Extract rem_id from Rem frontmatter."""
    try:
        content = rem_file.read_text(encoding='utf-8')
        fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)

        if fm_match:
            for line in fm_match.group(1).split('\n'):
                if line.startswith('rem_id:'):
                    return line.split(':', 1)[1].strip()
    except Exception:
        pass

    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix incorrect Rem source fields"
    )
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview changes without writing files")

    args = parser.parse_args()

    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    kb_dir = project_root / "knowledge-base"
    chats_dir = project_root / "chats"

    if not kb_dir.exists():
        print(f"❌ Knowledge base not found: {kb_dir}")
        sys.exit(1)

    if not chats_dir.exists():
        print(f"❌ Chats directory not found: {chats_dir}")
        sys.exit(1)

    print("🔍 Building rem_id → conversation_id map...")
    rem_to_conv_map = build_rem_to_conversation_map(chats_dir)
    print(f"   Found {len(rem_to_conv_map)} Rem→Conversation mappings")

    print("\n🔍 Finding all Rem files...")
    rem_files = find_rem_files(kb_dir)
    print(f"   Found {len(rem_files)} Rem files")

    if args.dry_run:
        print("\n🔄 DRY RUN MODE - No files will be modified\n")
    else:
        print("\n⚠️  WRITE MODE - Files will be modified\n")

    # Process files
    changed_count = 0
    not_found_count = 0

    for rem_file in rem_files:
        rem_id = extract_rem_id(rem_file)

        if not rem_id:
            continue

        # Check if we have a mapping for this rem_id
        if rem_id in rem_to_conv_map:
            correct_conversation_id = rem_to_conv_map[rem_id]

            if fix_rem_source(rem_file, correct_conversation_id, dry_run=args.dry_run):
                changed_count += 1
        else:
            not_found_count += 1
            if args.dry_run:
                print(f"⚠️  No conversation mapping for rem_id: {rem_id} ({rem_file.name})")

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total Rem files: {len(rem_files)}")
    print(f"   Fixed source fields: {changed_count}")
    print(f"   No mapping found: {not_found_count}")
    print(f"   Unchanged: {len(rem_files) - changed_count - not_found_count}")

    if args.dry_run and changed_count > 0:
        print(f"\n💡 Run without --dry-run to apply changes")
    elif not args.dry_run and changed_count > 0:
        print(f"\n✅ Source fields fixed!")


if __name__ == "__main__":
    main()
