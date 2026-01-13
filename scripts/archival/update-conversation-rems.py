#!/usr/bin/env python3
"""
Update Conversation Rems - Add Dual-Format Rem Links to Archived Conversation

Updates conversation files with Rem backlinks in TWO formats:
1. YAML frontmatter: List of Rem IDs (for machine parsing)
2. Document body: Clickable Markdown links (for human navigation)

The "## Rems Extracted" section is placed at the TOP of the conversation,
right after the title and metadata, making it immediately visible without scrolling.

Usage:
    source venv/bin/activate && source venv/bin/activate && python update-conversation-rems.py <conversation_file> <rem_file_1> [rem_file_2 ...]

Example:
    source venv/bin/activate && source venv/bin/activate && python update-conversation-rems.py \
        chats/2025-11/conversation.md \
        knowledge-base/04-business.../001-concept.md \
        knowledge-base/04-business.../002-concept.md
"""

import sys
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional


def load_backlinks_index() -> Dict:
    """Load backlinks.json to get Rem metadata"""
    backlinks_path = Path(__file__).parent.parent.parent / "knowledge-base" / "_index" / "backlinks.json"

    if not backlinks_path.exists():
        print(f"⚠️  Backlinks index not found at: {backlinks_path}", file=sys.stderr)
        return {"links": {}}

    try:
        with open(backlinks_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Failed to load backlinks.json: {e}", file=sys.stderr)
        return {"links": {}}


def extract_rem_id_from_path(rem_path: str) -> Optional[str]:
    """
    Extract Rem ID from file path.

    Examples:
        knowledge-base/.../001-concept-name.md → concept-name
        knowledge-base/.../french-verb-vouloir.md → french-verb-vouloir
    """
    filename = Path(rem_path).stem

    # Remove numeric prefix (e.g., "001-", "023-")
    match = re.match(r'^\d+-(.+)$', filename)
    if match:
        return match.group(1)

    return filename


def extract_rem_title(rem_path: str) -> str:
    """
    Extract Rem title from file content.

    Priority:
    1. First h1 heading (# Title)
    2. `rem_id` from frontmatter (formatted nicely)
    3. Filename without numeric prefix

    Returns human-readable title.
    """
    try:
        with open(rem_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Try to find h1 heading
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
            # Remove wikilink syntax if present
            title = re.sub(r'\[\[([^\]]+)\]\]', r'\1', title)
            return title

        # Try to extract rem_id from frontmatter
        fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            rem_id_match = re.search(r'^rem_id:\s*(.+)$', fm_text, re.MULTILINE)
            if rem_id_match:
                rem_id = rem_id_match.group(1).strip()
                # Format rem_id: optimal-aspiration-window → Optimal Aspiration Window
                title = rem_id.replace('-', ' ').title()
                return title

    except Exception as e:
        print(f"⚠️  Could not read Rem title from {rem_path}: {e}", file=sys.stderr)

    # Final fallback: use filename without numeric prefix, formatted nicely
    filename = Path(rem_path).stem
    # Remove numeric prefix (e.g., "001-")
    filename = re.sub(r'^\d+-', '', filename)
    # Format: some-concept-name → Some Concept Name
    return filename.replace('-', ' ').title()


def calculate_relative_path(conversation_file: str, rem_file: str) -> str:
    """Calculate relative path from conversation to Rem file"""
    conv_dir = Path(conversation_file).parent
    rel_path = os.path.relpath(rem_file, conv_dir)
    # Normalize to forward slashes (cross-platform)
    return rel_path.replace('\\', '/')


def build_rem_metadata(conversation_file: str, rem_files: List[str]) -> List[Dict]:
    """
    Build metadata for each Rem file.

    Returns:
        List of dicts with keys: id, title, path
    """
    rem_metadata = []

    for rem_file in rem_files:
        rem_id = extract_rem_id_from_path(rem_file)
        rem_title = extract_rem_title(rem_file)
        rel_path = calculate_relative_path(conversation_file, rem_file)

        rem_metadata.append({
            'id': rem_id,
            'title': rem_title,
            'path': rel_path
        })

    return rem_metadata


def update_yaml_frontmatter(frontmatter: str, rem_ids: List[str]) -> str:
    """
    Update YAML frontmatter with Rem IDs (not full paths).

    Replaces old format (paths) or empty array with new format (IDs).

    Before:
        rems_extracted: []
        OR
        rems_extracted:
          - ../../../knowledge-base/.../file.md

    After:
        rems_extracted:
          - rem-id-1
          - rem-id-2
    """
    # Build new YAML section
    new_rems_yaml = "rems_extracted:\n"
    for rem_id in rem_ids:
        new_rems_yaml += f"  - {rem_id}\n"
    new_rems_yaml = new_rems_yaml.rstrip('\n')

    # Try to replace existing rems_extracted (empty array)
    if 'rems_extracted: []' in frontmatter:
        return frontmatter.replace('rems_extracted: []', new_rems_yaml)

    # Try to replace existing rems_extracted (multi-line with paths)
    # Pattern: rems_extracted:\n  - path\n  - path\n...
    pattern = r'rems_extracted:\n(?:  - .+\n)+'
    if re.search(pattern, frontmatter):
        return re.sub(pattern, new_rems_yaml + '\n', frontmatter, count=1)

    # Fallback: Append to frontmatter
    print(f"⚠️  'rems_extracted' not found, appending to frontmatter", file=sys.stderr)
    return frontmatter + '\n' + new_rems_yaml


def generate_rems_section(rem_metadata: List[Dict]) -> str:
    """
    Generate the "## Rems Extracted" section with clickable Markdown links.

    Format:
        ## Rems Extracted

        - **Rem Title 1** - [[rem-id-1]](../path/to/rem-1.md)
        - **Rem Title 2** - [[rem-id-2]](../path/to/rem-2.md)
    """
    if not rem_metadata:
        return ""

    lines = ["## Rems Extracted", ""]

    for rem in rem_metadata:
        # Format: - **Title** - [[id]](path)
        line = f"- **{rem['title']}** - [[{rem['id']}]]({rem['path']})"
        lines.append(line)

    return "\n".join(lines)


def insert_rems_section_after_title(body: str, rems_section: str) -> str:
    """
    Insert "## Rems Extracted" section right after title and Date/Agent/Domain metadata,
    BEFORE the "## Metadata" section.

    If section already exists, replace it instead of inserting.

    Target position:
        # Title

        **Date**: ...
        **Agent**: ...
        **Domain**: ...

        ## Rems Extracted  ← Insert HERE (or replace if exists)
        - ...

        ## Metadata
        - **Concepts Extracted**: ...
    """
    if not rems_section:
        return body

    # First check if "## Rems Extracted" already exists and remove ALL instances
    # This handles multiple formats:
    # 1. Section with links: ## Rems Extracted\n\n- **Title** - [[id]](path)\n\n
    # 2. Placeholder: ## Rems Extracted\n\nThis conversation...\n\n*(Rems will be listed...)*\n\n
    # 3. Empty section: ## Rems Extracted\n\n

    # Remove format 1: ## Rems Extracted with actual links
    existing_links_pattern = r'## Rems Extracted\n\n(?:- .+\n)+\n'
    body = re.sub(existing_links_pattern, '', body, flags=re.DOTALL)

    # Remove format 2: ## Rems Extracted with placeholder
    existing_placeholder_pattern = r'## Rems Extracted\n\nThis conversation led to the creation of these knowledge Rems:\n\n\*\(Rems will be listed by /save command\)\*\n\n'
    body = re.sub(existing_placeholder_pattern, '', body, flags=re.DOTALL)

    # Remove format 3: Empty ## Rems Extracted
    existing_empty_pattern = r'## Rems Extracted\n\n'
    body = re.sub(existing_empty_pattern, '', body, flags=re.DOTALL)

    # Now insert at correct position
    # Match: # Title ... **Domain**: ... (capture everything up to next ##)
    pattern = r'(# .+?\n\n\*\*Date\*\*:.*?\n\*\*Agent\*\*:.*?\n\*\*Domain\*\*:.*?\n)\n(## )'

    replacement = rf'\1\n{rems_section}\n\n\2'

    updated_body = re.sub(pattern, replacement, body, count=1, flags=re.DOTALL)

    # If pattern didn't match (e.g., different structure), try fallback
    if updated_body == body:
        # Fallback: Insert after first h1, before first ##
        pattern_fallback = r'(# .+?\n\n)(## )'
        replacement_fallback = rf'\1{rems_section}\n\n\2'
        updated_body = re.sub(pattern_fallback, replacement_fallback, body, count=1, flags=re.DOTALL)

    return updated_body


def update_conversation_file(conversation_file: str, rem_metadata: List[Dict]):
    """
    Update conversation file with dual-format Rem backlinks:
    1. YAML frontmatter: Rem IDs
    2. Document body: Clickable Markdown links (at top)
    """
    conv_path = Path(conversation_file)

    if not conv_path.exists():
        print(f"❌ Conversation file not found: {conversation_file}", file=sys.stderr)
        sys.exit(1)

    # Read file
    with open(conv_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract frontmatter and body
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not frontmatter_match:
        print(f"❌ No frontmatter found in: {conversation_file}", file=sys.stderr)
        sys.exit(1)

    frontmatter = frontmatter_match.group(1)
    body = frontmatter_match.group(2)

    # Step 1: Update YAML frontmatter with Rem IDs
    rem_ids = [rem['id'] for rem in rem_metadata]
    updated_frontmatter = update_yaml_frontmatter(frontmatter, rem_ids)

    # Step 2: Generate "## Rems Extracted" section
    rems_section = generate_rems_section(rem_metadata)

    # Step 3: Insert section at top of body (after title, before ## Metadata)
    updated_body = insert_rems_section_after_title(body, rems_section)

    # Reconstruct file
    updated_content = f"---\n{updated_frontmatter}\n---\n{updated_body}"

    # Write back
    with open(conv_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print(f"✅ Updated: {conversation_file}")
    print(f"   YAML: Added {len(rem_ids)} Rem IDs")
    print(f"   Body: Added '## Rems Extracted' section at top")


def main():
    if len(sys.argv) < 3:
        print("Usage: python update-conversation-rems.py <conversation_file> <rem_file_1> [rem_file_2 ...]")
        sys.exit(1)

    conversation_file = sys.argv[1]
    rem_files = sys.argv[2:]

    # Build metadata for all Rem files
    rem_metadata = build_rem_metadata(conversation_file, rem_files)

    # Update conversation with dual-format backlinks
    update_conversation_file(conversation_file, rem_metadata)


if __name__ == "__main__":
    main()
