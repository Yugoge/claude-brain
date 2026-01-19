#!/usr/bin/env python3
"""
Migrate Rem files to dual-source format (YAML + Markdown body).

Standard Format:
- YAML source: Project root relative ("chats/2025-11/file.md")
- Markdown body: Rem location relative ("../../../../chats/2025-11/file.md")

Usage:
    python migrate-conversation-sources.py [--dry-run] [--domain <path>]

Exit Codes:
    0 = Success
    1 = Errors encountered
"""

import sys
import re
from pathlib import Path
from typing import Tuple, Optional

PROJECT_ROOT = Path("/root/knowledge-system")


def extract_frontmatter(content: str) -> Tuple[Optional[dict], str]:
    """Extract YAML frontmatter and body from Rem content."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if not match:
        return None, content

    frontmatter_text = match.group(1)
    body = match.group(2)

    # Parse YAML manually (simple key: value parsing)
    frontmatter = {}
    for line in frontmatter_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            frontmatter[key.strip()] = value.strip()

    return frontmatter, body


def calculate_markdown_link(rem_path: Path, conversation_path: str) -> str:
    """
    Calculate Markdown link from Rem location to conversation file.

    Args:
        rem_path: Path to Rem file
        conversation_path: Project root relative path (e.g., "chats/2025-11/file.md")

    Returns:
        Rem location relative path (e.g., "../../../../chats/2025-11/file.md")

    Example:
        Rem: knowledge-base/04/.../0412/001-file.md
        Parts from PROJECT_ROOT: ['knowledge-base', '04...', '041...', '0412', '001-file.md']
        Depth (excluding filename): 4
        Result: ../../../../chats/...
    """
    # Calculate depth from project root (not from knowledge-base!)
    try:
        rel_path = rem_path.relative_to(PROJECT_ROOT)
        depth = len(rel_path.parts) - 1  # Exclude filename itself
    except ValueError:
        # Fallback: count directory separators
        depth = str(rem_path).count('/')

    markdown_prefix = "../" * depth
    return f"{markdown_prefix}{conversation_path}"


def extract_conversation_title(conversation_path: Path) -> str:
    """Extract title from conversation file or generate from filename."""
    if not conversation_path.exists():
        # Generate title from filename
        return conversation_path.stem.replace('-', ' ').title()

    try:
        with open(conversation_path, 'r', encoding='utf-8') as f:
            content = f.read(2000)  # Read first 2000 chars

        # Try to extract title from frontmatter
        match = re.search(r'title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
        if match:
            return match.group(1)

        # Fallback: use filename
        return conversation_path.stem.replace('-', ' ').title()

    except Exception:
        return conversation_path.stem.replace('-', ' ').title()


def migrate_rem(rem_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Migrate single Rem to dual-source format.

    Returns:
        (success, message)
    """
    try:
        content = rem_path.read_text(encoding='utf-8')
    except Exception as e:
        return False, f"Cannot read: {e}"

    frontmatter, body = extract_frontmatter(content)
    if not frontmatter:
        return False, "No frontmatter found"

    source = frontmatter.get('source', '').strip()
    if not source:
        return False, "No source field in frontmatter"

    # Determine current format and convert if needed
    yaml_source = source
    if source.startswith("../"):
        # Legacy format: Convert to project root relative
        # Remove ../ prefix and normalize
        yaml_source = source.lstrip('../')
        if not yaml_source.startswith('chats/'):
            yaml_source = f"chats/{yaml_source.split('chats/', 1)[-1]}"

    # Calculate Markdown link
    markdown_link = calculate_markdown_link(rem_path, yaml_source)

    # Check if conversation file exists
    conversation_path = PROJECT_ROOT / yaml_source
    conversation_exists = conversation_path.exists()

    # Extract conversation title
    if conversation_exists:
        conversation_title = extract_conversation_title(conversation_path)
    else:
        conversation_title = yaml_source.split('/')[-1].replace('.md', '')

    # Check if body already has Conversation Source
    has_conversation_source = "## Conversation Source" in body

    # Build new content
    new_frontmatter = dict(frontmatter)
    new_frontmatter['source'] = yaml_source

    frontmatter_lines = ["---"]
    for key, value in new_frontmatter.items():
        frontmatter_lines.append(f"{key}: {value}")
    frontmatter_lines.append("---")

    # Add or update Conversation Source in body
    if has_conversation_source:
        # Replace existing Conversation Source section
        body = re.sub(
            r'## Conversation Source\s*\n\s*.*?(?=\n##|\Z)',
            f"## Conversation Source\n\n→ See: [{conversation_title}]({markdown_link})\n",
            body,
            flags=re.DOTALL
        )
    else:
        # Add Conversation Source section before any existing ## sections or at end
        if '\n## ' in body:
            # Insert before first ## section
            parts = body.split('\n## ', 1)
            body = f"{parts[0].rstrip()}\n\n## Conversation Source\n\n→ See: [{conversation_title}]({markdown_link})\n\n## {parts[1]}"
        else:
            # Append to end
            body = f"{body.rstrip()}\n\n## Conversation Source\n\n→ See: [{conversation_title}]({markdown_link})\n"

    new_content = '\n'.join(frontmatter_lines) + '\n' + body

    # Write changes
    if not dry_run:
        rem_path.write_text(new_content, encoding='utf-8')

    status = "✓" if conversation_exists else "⚠"
    return True, f"{status} YAML: {yaml_source}, Link: {markdown_link}"


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate Rem conversation sources to dual format")
    parser.add_argument('--dry-run', action='store_true', help="Preview changes without applying")
    parser.add_argument('--domain', type=str, help="Limit to specific domain path")
    args = parser.parse_args()

    # Find all Rem files
    kb_path = PROJECT_ROOT / "knowledge-base"
    if args.domain:
        search_path = kb_path / args.domain
    else:
        search_path = kb_path

    rem_files = list(search_path.rglob("*.md"))
    # Exclude INDEX.md and README.md
    rem_files = [f for f in rem_files if f.name not in ['INDEX.md', 'README.md', '_templates']]

    print(f"Found {len(rem_files)} Rem files to process")
    if args.dry_run:
        print("DRY RUN MODE - No changes will be written\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    for rem_file in rem_files:
        try:
            rel_path = rem_file.relative_to(PROJECT_ROOT)
        except ValueError:
            rel_path = rem_file

        success, message = migrate_rem(rem_file, dry_run=args.dry_run)

        if success:
            success_count += 1
            print(f"✓ {rel_path}: {message}")
        else:
            if "No source field" in message:
                skip_count += 1
            else:
                error_count += 1
                print(f"✗ {rel_path}: {message}")

    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Migrated: {success_count}")
    print(f"  Skipped (no source): {skip_count}")
    print(f"  Errors: {error_count}")

    if args.dry_run:
        print(f"\nDRY RUN - Run without --dry-run to apply changes")

    sys.exit(1 if error_count > 0 else 0)


if __name__ == "__main__":
    main()
