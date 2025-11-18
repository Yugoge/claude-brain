#!/usr/bin/env python3
"""
Fix invalid source fields in Rems.

Maps conversation IDs to full file paths.
"""

import re
from pathlib import Path
import glob

# Mapping of conversation IDs to full file paths
CONVERSATION_MAPPING = {
    'french-review-session-2025-10-28': 'chats/2025-10/french-review-session-grammar-and-expressions-conversation-2025-10-28.md',
    'french-1453-vocab-20251030': 'chats/2025-10/french-1453-vocab-20251030-conversation-2025-10-30.md',
    'french-grammar-session-2025-11-03': 'chats/2025-11/french-grammar-session-2025-11-03.md',
    'ask-conversation-2025-11-02': 'chats/2025-11/desire-driven-growth-2025-11-02.md',
    'fx-forward-primary-depo-rate-2025-11-03': 'chats/2025-11/fx-forward-primary-depo-rate-and-interest-rate-par-conversation-2025-11-03.md',
    'fx-delta-currency-conventions-2025-11-03': 'chats/2025-11/fx-delta-calculation-decision-logic-for-central-di-conversation-2025-11-03.md',
    'csharp-learning-ba-20251028': 'chats/2025-10/c-learning-ba-s-first-c-sample-test-conversation-2025-10-28.md',
    'csharp-review-early-exit-2025-10-30': 'chats/2025-10/c-programming-review-session-conversation-2025-10-30.md',
}

def fix_source_field(file_path: Path):
    """Fix source field in Rem file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match frontmatter
    match = re.match(r'^(---\n)(.*?)(---\n)', content, re.DOTALL)
    if not match:
        return False, "No frontmatter"

    frontmatter = match.group(2)

    # Find source field
    source_match = re.search(r'^source:\s*(.+?)$', frontmatter, re.MULTILINE)
    if not source_match:
        return False, "No source field"

    current_source = source_match.group(1).strip()

    # Check if it's already a valid .md path
    if current_source.endswith('.md'):
        return False, "Already valid"

    # Try to map to conversation file
    if current_source in CONVERSATION_MAPPING:
        new_source = CONVERSATION_MAPPING[current_source]
        new_frontmatter = re.sub(
            r'^source:\s*.+?$',
            f'source: {new_source}',
            frontmatter,
            flags=re.MULTILINE
        )
        new_content = match.group(1) + new_frontmatter + match.group(3) + content[match.end():]

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True, f"{current_source} → {new_source}"
    else:
        return False, f"Unknown conversation ID: {current_source}"

def main():
    root_dir = Path('.').resolve()
    kb_dir = root_dir / 'knowledge-base'

    print("🔗 Fixing invalid source fields...")
    print("=" * 70)

    fixed_count = 0
    skip_count = 0
    error_count = 0

    for md_file in kb_dir.rglob('*.md'):
        if '_templates' in str(md_file) or 'index' in md_file.name:
            continue

        result, message = fix_source_field(md_file)

        if result:
            print(f"  ✓ {md_file.name}: {message}")
            fixed_count += 1
        elif "Unknown conversation ID" in message:
            print(f"  ⚠️  {md_file.name}: {message}")
            error_count += 1
        elif message not in ["No frontmatter", "No source field", "Already valid"]:
            pass  # Skip silently

    print("=" * 70)
    print(f"✅ Fixed {fixed_count} files")
    if skip_count:
        print(f"⏭️  Skipped {skip_count} files (already valid)")
    if error_count:
        print(f"⚠️  {error_count} files have unknown conversation IDs (need manual mapping)")

if __name__ == '__main__':
    main()
