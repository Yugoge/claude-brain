#!/usr/bin/env python3
"""
Create Rem File - Generate standardized knowledge Rem with all required sections

This script creates a complete Rem file following the ultra-minimal template (100-120 tokens)
with all required sections including Conversation Source bidirectional link.

Usage:
    python create-rem-file.py \\
        --rem-id "concept-slug" \\
        --title "Concept Title" \\
        --isced "02-arts-and-humanities/023-languages/0231-language-acquisition" \\
        --subdomain "english" \\
        --core-points '["Point 1", "Point 2", "Point 3"]' \\
        --usage-scenario "When to use this concept..." \\
        --mistakes '["❌ Wrong → ✅ Right", ...]' \\
        --related-rems '["rem-id-1", "rem-id-2"]' \\
        --conversation-file "chats/2025-11/conversation.md" \\
        --conversation-title "Conversation Title" \\
        --output-path "knowledge-base/.../003-concept-slug.md"

Example:
    python create-rem-file.py \\
        --rem-id "english-schwa-reduction" \\
        --title "Schwa Reduction in Unstressed Syllables" \\
        --isced "02-arts-and-humanities/023-languages/0231-language-acquisition" \\
        --subdomain "english" \\
        --core-points '["Schwa /ə/ is most common vowel", "Appears only in unstressed syllables"]' \\
        --usage-scenario "Identify stress first, then expect vowel reduction" \\
        --mistakes '["❌ Pronounce all vowels fully → ✅ Reduce unstressed"]' \\
        --conversation-file "chats/2025-11/english-pronunciation.md" \\
        --conversation-title "English Pronunciation Session" \\
        --output-path "knowledge-base/.../004-english-schwa-reduction.md"
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import os


def calculate_relative_path(from_file: str, to_file: str) -> str:
    """Calculate relative path from Rem to conversation file"""
    from_dir = Path(from_file).parent
    rel_path = os.path.relpath(to_file, from_dir)
    # Normalize to forward slashes
    return rel_path.replace('\\', '/')


def format_related_rems(related_rems: list) -> str:
    """
    Format related Rems section.

    If empty, return placeholder for backlinks rebuild.
    Otherwise, format as wikilinks with {rel: type} if provided.
    """
    if not related_rems:
        return "*(Will be populated by backlinks rebuild)*"

    lines = []
    for rem in related_rems:
        if isinstance(rem, dict):
            # Format: {"rem_id": "rem-id", "rel": "synonym"} or legacy {"id": "rem-id", "rel": "synonym"}
            rem_id = rem.get('rem_id') or rem.get('id', '')
            rel_type = rem.get('rel', 'related')
            lines.append(f"- [[{rem_id}]] {{rel: {rel_type}}}")
        elif isinstance(rem, str):
            # Check if already in wikilink format
            if rem.strip().startswith('[[') and ']]' in rem:
                # Already formatted, use as-is
                lines.append(f"- {rem}")
            else:
                # Plain rem-id, add brackets
                lines.append(f"- [[{rem}]]")

    return "\n".join(lines)


def generate_rem_content(args) -> str:
    """Generate complete Rem file content"""

    # Parse JSON arrays
    core_points = json.loads(args.core_points)
    mistakes = json.loads(args.mistakes) if args.mistakes else []
    related_rems = json.loads(args.related_rems) if args.related_rems else []

    # Calculate relative path to conversation
    source_rel_path = calculate_relative_path(args.output_path, args.conversation_file)

    # Current date
    created_date = datetime.now().strftime('%Y-%m-%d')

    # Format core points (max 3)
    core_points_text = "\n".join([f"- {point}" for point in core_points[:3]])

    # Format mistakes
    mistakes_text = "\n".join([f"- {mistake}" for mistake in mistakes])

    # Format related Rems
    related_text = format_related_rems(related_rems)

    # Build frontmatter
    frontmatter = f"""---
rem_id: {args.rem_id}
title: {args.title}
isced: {args.isced}
subdomain: {args.subdomain}
created: {created_date}
source: {source_rel_path}
---"""

    # Build body
    body = f"""
# {args.title}

## Core Memory Points

{core_points_text}

## Usage Scenario

{args.usage_scenario}
"""

    # Add My Mistakes if provided
    if mistakes:
        body += f"""
## My Mistakes

{mistakes_text}
"""

    # Add Related Rems
    body += f"""
## Related Rems

{related_text}

## Conversation Source

→ See: [{args.conversation_title}]({source_rel_path})
"""

    return frontmatter + body


def main():
    parser = argparse.ArgumentParser(description="Create standardized Rem file")
    parser.add_argument("--rem-id", required=True, help="Rem ID (slug format)")
    parser.add_argument("--title", required=True, help="Rem title")
    parser.add_argument("--isced", required=True, help="ISCED path (e.g., 02-arts-and-humanities/023-languages/0231-language-acquisition)")
    parser.add_argument("--subdomain", required=True, help="Subdomain (e.g., english, french, finance)")
    parser.add_argument("--core-points", required=True, help="JSON array of 1-3 core points")
    parser.add_argument("--usage-scenario", required=True, help="Usage scenario text (1-2 sentences)")
    parser.add_argument("--mistakes", default='[]', help="JSON array of mistakes (optional)")
    parser.add_argument("--related-rems", default='[]', help="JSON array of related Rem IDs or objects with {id, rel} (optional)")
    parser.add_argument("--conversation-file", required=True, help="Path to conversation file (absolute or relative to project root)")
    parser.add_argument("--conversation-title", required=True, help="Conversation title for link text")
    parser.add_argument("--output-path", required=True, help="Output file path (absolute)")

    args = parser.parse_args()

    # Generate content
    content = generate_rem_content(args)

    # Ensure parent directory exists
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    output_path.write_text(content, encoding='utf-8')

    print(f"✅ Created: {output_path}")
    print(f"   Rem ID: {args.rem_id}")
    print(f"   Tokens: ~{len(content.split())} words")

    return str(output_path)


if __name__ == "__main__":
    main()
