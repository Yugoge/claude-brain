#!/usr/bin/env python3
"""
Fix conversation header mislabeling in all archived conversations.

Problem: Two types of mislabeling:
1. Subagent JSON responses labeled as "### Assistant"
   → Should be "### Subagent → Assistant"
2. Main agent's teaching responses labeled as "### Subagent: {Name}"
   → Should be "### Assistant"

Correct conversation structure:
- User ←→ Assistant (user-facing dialogue)
- Assistant → Subagent (delegation prompt)
- Subagent → Assistant (JSON response back to main agent)
"""

import re
from pathlib import Path

def detect_json_response(content: str) -> bool:
    """
    Detect if content is a JSON response from subagent.

    Criteria:
    - Starts with { and ends with }
    - Contains JSON fields like "strategy", "rationale", "content"
    - Typically 100-500 lines of structured JSON
    """
    content = content.strip()
    if not (content.startswith('{') and content.endswith('}')):
        return False

    # Check for common subagent JSON fields
    json_indicators = [
        '"strategy"',
        '"rationale"',
        '"content"',
        '"confidence"',
        '"sources"',
        '"domain"',
        '"isced"',
        '"dewey"'
    ]

    return any(indicator in content for indicator in json_indicators)

def fix_conversation_headers(file_path: Path, dry_run=False) -> tuple[int, int]:
    """
    Fix mislabeled headers in conversation file.

    Returns:
        (fixes_count, total_headers)
    """
    content = file_path.read_text(encoding='utf-8')
    original = content

    # Split into sections by headers
    sections = re.split(r'^(###\s+.+)$', content, flags=re.MULTILINE)

    fixes = 0

    # Process sections (odd indices are headers, even indices are content)
    for i in range(1, len(sections), 2):
        header = sections[i]
        section_content = sections[i+1] if i+1 < len(sections) else ""

        # Fix 1: "### Assistant" followed by JSON → "### Subagent → Assistant"
        if header == "### Assistant" and detect_json_response(section_content):
            sections[i] = "### Subagent → Assistant"
            fixes += 1

        # Fix 2: "### Subagent: {Name}" → depends on content
        elif header.startswith("### Subagent: "):
            if detect_json_response(section_content):
                # JSON response → "### Subagent → Assistant"
                sections[i] = "### Subagent → Assistant"
                fixes += 1
            else:
                # Non-JSON (teaching dialogue) → "### Assistant"
                # This happens when main agent's response was mislabeled as subagent
                sections[i] = "### Assistant"
                fixes += 1

    # Rebuild content
    fixed_content = ''.join(sections)

    # Count total headers for verification
    total_headers = len(re.findall(
        r'^###\s+(User|Assistant|Subagent:\s*.+|Assistant\s*→\s*Subagent|Subagent\s*→\s*Assistant)',
        fixed_content,
        re.MULTILINE
    ))

    if fixes > 0 and not dry_run:
        file_path.write_text(fixed_content, encoding='utf-8')

    return fixes, total_headers

def main():
    """Fix all conversations in chats/ directory."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without modifying files')
    parser.add_argument('--file', type=Path, help='Fix single file (for testing)')
    args = parser.parse_args()

    chats_dir = Path(__file__).parent.parent.parent / "chats"

    if args.file:
        # Test single file
        fixes, headers = fix_conversation_headers(args.file, dry_run=args.dry_run)
        print(f"{'[DRY RUN] ' if args.dry_run else ''}✅ {args.file.name}: {fixes} fixes / {headers} headers")
        return 0

    # Process all files
    total_files = 0
    total_fixes = 0

    for md_file in chats_dir.rglob("*.md"):
        # Skip template files
        if '_template' in md_file.name:
            continue

        try:
            fixes, headers = fix_conversation_headers(md_file, dry_run=args.dry_run)
            if fixes > 0:
                total_files += 1
                total_fixes += fixes
                print(f"{'[DRY RUN] ' if args.dry_run else ''}✅ {md_file.relative_to(chats_dir)}: {fixes} fixes / {headers} headers")
        except Exception as e:
            print(f"❌ {md_file.name}: {e}")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}📊 Summary: {total_fixes} fixes in {total_files} files")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
