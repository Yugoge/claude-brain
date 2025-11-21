#!/usr/bin/env python3
"""
Systematic format issue fixes.

Fixes:
1. Economics Rems source hyperlinks (5 files)
2. Chat files missing session_type and Rems Extracted section (3 files)
"""

import re
import sys
from pathlib import Path

def fix_economics_rem_source(file_path: Path) -> bool:
    """Fix source hyperlink in economics Rem files."""
    content = file_path.read_text(encoding='utf-8')

    # Pattern: "→ See: [Ask Conversation Conversation](../../../../chats/ask-conversation-2025-11-02)"
    # Should be: "→ See: [Desire-Driven Economic Growth](../../../../chats/2025-11/desire-driven-growth-2025-11-02.md)"

    # Extract source path from YAML
    yaml_match = re.search(r'source:\s*(.+)\.md', content)
    if not yaml_match:
        print(f"  ⚠️  No source found in YAML for {file_path.name}")
        return False

    source_path = yaml_match.group(1) + '.md'

    # Check if source file exists
    root = Path("/home/user/knowledge-system")
    full_source_path = root / source_path

    if not full_source_path.exists():
        print(f"  ⚠️  Source file not found: {source_path}")
        return False

    # Get title from source file
    try:
        source_content = full_source_path.read_text(encoding='utf-8')
        title_match = re.search(r'^title:\s*"(.+)"', source_content, re.MULTILINE)
        if title_match:
            title = title_match.group(1)
        else:
            # Fallback: use filename
            title = full_source_path.stem.replace('-', ' ').title()
    except:
        title = "Conversation"

    # Calculate relative path from Rem to source
    try:
        rel_path = Path('../../../..') / source_path
    except:
        rel_path = source_path

    # Fix the source section
    new_source_line = f"→ See: [{title}]({rel_path})"

    # Replace the broken link
    content = re.sub(
        r'→ See: \[.*?\]\(.*?chats/.*?\)',
        new_source_line,
        content
    )

    # Write back
    file_path.write_text(content, encoding='utf-8')
    print(f"  ✓ Fixed: {file_path.name}")
    return True

def fix_chat_session_type(file_path: Path) -> bool:
    """Add missing session_type to chat file."""
    content = file_path.read_text(encoding='utf-8')

    # Check if session_type already exists
    if re.search(r'^session_type:', content, re.MULTILINE):
        return False

    # Add session_type: ask after domain line
    content = re.sub(
        r'(domain:\s+\w+)\n',
        r'\1\nsession_type: ask\n',
        content
    )

    file_path.write_text(content, encoding='utf-8')
    print(f"  ✓ Added session_type: {file_path.name}")
    return True

def fix_chat_rems_extracted(file_path: Path) -> bool:
    """Add ## Rems Extracted section if missing."""
    content = file_path.read_text(encoding='utf-8')

    # Check if section exists
    if '## Rems Extracted' in content or '## Extracted Rems' in content:
        return False

    # Extract concepts from Metadata section
    concepts_match = re.search(
        r'- \*\*Concepts Extracted\*\*:\s*(.+)',
        content
    )

    if concepts_match:
        concepts_text = concepts_match.group(1)
        # Parse [[concept]] wikilinks
        concepts = re.findall(r'\[\[(.+?)\]\]', concepts_text)

        # Build Rems Extracted section
        rems_section = "\n## Rems Extracted\n\n"
        if concepts:
            for concept in concepts:
                # Try to find the actual Rem file
                concept_slug = concept.replace('-', '')
                rems_section += f"- **{concept.title()}** - (Link TBD)\n"
        else:
            rems_section += "*(No Rems extracted during conversation)*\n"

        # Insert after Summary section
        content = re.sub(
            r'(## Summary\n\n.*?\n)\n(## Full Conversation)',
            rf'\1{rems_section}\n\2',
            content,
            flags=re.DOTALL
        )

        file_path.write_text(content, encoding='utf-8')
        print(f"  ✓ Added Rems Extracted section: {file_path.name}")
        return True

    return False

def main():
    root = Path("/home/user/knowledge-system")

    print("=" * 70)
    print("FORMAT ISSUE FIXES")
    print("=" * 70)

    # Fix 1: Economics Rems source hyperlinks
    print("\n[1] Fixing economics Rems source hyperlinks...")
    economics_rems = [
        "knowledge-base/03-social-sciences-journalism-and-information/031-social-and-behavioural-sciences/0311-economics/001-development-economics-east-asia-latin-america-savings-institutional.md",
        "knowledge-base/03-social-sciences-journalism-and-information/031-social-and-behavioural-sciences/0311-economics/002-development-economics-relative-deprivation-economic-development.md",
        "knowledge-base/03-social-sciences-journalism-and-information/031-social-and-behavioural-sciences/0311-economics/003-development-economics-gerschenkron-backward-advantage.md",
        "knowledge-base/03-social-sciences-journalism-and-information/031-social-and-behavioural-sciences/0311-economics/004-development-economics-desire-driven-growth-necessary-conditions.md",
        "knowledge-base/03-social-sciences-journalism-and-information/031-social-and-behavioural-sciences/0311-economics/005-development-economics-optimal-aspiration-window-genicot-ray.md",
    ]

    fixed_count = 0
    for rem_path in economics_rems:
        if fix_economics_rem_source(root / rem_path):
            fixed_count += 1

    print(f"  Fixed {fixed_count}/5 economics Rems")

    # Fix 2: Chat session_type
    print("\n[2] Fixing chat session_type...")
    chat_file = root / "chats/2025-11/claude-2025-11-21-150340-derivatives-contract-listing-and-specification-rel.md"
    if chat_file.exists():
        fix_chat_session_type(chat_file)

    # Fix 3: Chat Rems Extracted sections
    print("\n[3] Adding Rems Extracted sections...")
    chat_files = [
        root / "chats/2025-11/eur3m-curve-calibration-2025-11-17.md",
        root / "chats/2025-11/scenario-analysis-rebuild-mechanisms-2025-11-10-conversation-2025-11-06.md",
    ]

    for chat_file in chat_files:
        if chat_file.exists():
            fix_chat_rems_extracted(chat_file)

    print("\n" + "=" * 70)
    print("FIXES COMPLETE")
    print("=" * 70)

    return 0

if __name__ == '__main__':
    sys.exit(main())
