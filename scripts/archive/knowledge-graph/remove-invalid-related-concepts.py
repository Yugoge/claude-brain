#!/usr/bin/env python3
"""
Remove Invalid Related Concepts Sections

This script removes "## Related Concepts" sections from all rems that were
incorrectly added with references to non-existent concepts.

The original design uses `related:` in YAML frontmatter, which is populated
by the /save command with references to concepts extracted in the SAME session
or verified existing concepts only.

Usage:
    python scripts/remove-invalid-related-concepts.py [--dry-run]
"""

import re
import sys
from pathlib import Path

def remove_related_concepts_section(content: str) -> tuple[str, bool]:
    """
    Remove "## Related Concepts" section from rem content.

    Returns:
        (modified_content, was_modified)
    """
    # Pattern to match "## Related Concepts" section until next ## header or end
    pattern = r'\n## Related Concepts\n\n.*?(?=\n## |\n---\n|\Z)'

    modified = re.sub(pattern, '', content, flags=re.DOTALL)

    return modified, modified != content

def process_rem_file(file_path: Path, dry_run: bool = False) -> bool:
    """
    Process a single rem file to remove Related Concepts section.

    Returns:
        True if file was modified
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        modified_content, was_modified = remove_related_concepts_section(content)

        if was_modified:
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)
        return False

def main():
    dry_run = '--dry-run' in sys.argv

    kb_dir = Path('/root/knowledge-system/knowledge-base')

    # Find all markdown files (excluding templates, indexes, backups)
    rem_files = []
    for md_file in kb_dir.rglob('*.md'):
        # Skip special directories
        if any(part.startswith('_') or 'backup' in part.lower()
               for part in md_file.parts):
            continue
        rem_files.append(md_file)

    print(f"Found {len(rem_files)} rem files to process")
    if dry_run:
        print("DRY RUN - No files will be modified")
    print()

    modified_count = 0

    for file_path in sorted(rem_files):
        if process_rem_file(file_path, dry_run):
            print(f"{'[DRY RUN] Would modify' if dry_run else '✓ Modified'}: {file_path.relative_to(kb_dir)}")
            modified_count += 1

    print()
    print(f"{'Would modify' if dry_run else 'Modified'} {modified_count}/{len(rem_files)} files")

    if dry_run:
        print("\nRun without --dry-run to apply changes")

if __name__ == '__main__':
    main()
