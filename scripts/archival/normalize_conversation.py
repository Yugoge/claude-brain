#!/usr/bin/env python3
"""
Normalize Conversation File - Convert chat_archiver output to standard format

This script:
1. Updates front matter with actual metadata (from active context)
2. Renames file from claude-{date}-{time}-{slug}.md to {topic}-conversation-{date}.md
3. Updates document structure to match /save standard format

Usage:
    python scripts/archival/normalize_conversation.py <file_path> \
        --id "topic-id" \
        --title "Topic Title" \
        --session-type "learn" \
        --agent "analyst" \
        --domain "programming" \
        --concepts '["concept-1", "concept-2"]' \
        --tags '["tag1", "tag2"]' \
        --summary "Brief summary of conversation"
"""

import re
import sys
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime


def slugify(text: str, max_length: int = 50) -> str:
    """
    Convert title to URL-friendly slug with improved non-ASCII handling.

    Handles:
    - French accents: é → e, à → a, etc.
    - Chinese characters: convert to pinyin (jingji-zengzhang)
    - Special characters: punctuation removed
    - Fallback: use metadata ID if all characters are non-ASCII

    Args:
        text: Title to slugify
        max_length: Maximum slug length (default: 50)

    Returns:
        URL-friendly slug
    """
    original_text = text
    slug = text.lower()

    # Remove content in parentheses
    slug = re.sub(r'\([^)]*\)', '', slug)

    # Replace special chars with spaces
    slug = re.sub(r'[:\'"?!.,;、。：；！？]', ' ', slug)

    # Try Chinese to Pinyin conversion (if pypinyin available)
    try:
        from pypinyin import lazy_pinyin
        # Check if text has Chinese characters
        if re.search(r'[\u4e00-\u9fff]', slug):
            # Convert Chinese to pinyin
            pinyin_parts = lazy_pinyin(slug)
            slug = '-'.join(pinyin_parts)
    except ImportError:
        # pypinyin not available, use transliteration fallback
        pass

    # Normalize unicode (NFD) and remove combining marks for accents
    # This converts é → e, à → a, ñ → n, etc.
    slug = unicodedata.normalize('NFD', slug)
    slug = ''.join(char for char in slug if unicodedata.category(char) != 'Mn')

    # Replace whitespace with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)

    # Keep only alphanumeric and hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)

    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Trim hyphens
    slug = slug.strip('-')

    # If slug is empty or too short (all non-ASCII removed), use fallback
    if len(slug) < 3:
        # Extract first few words of original title for fallback
        words = re.findall(r'\w+', original_text, re.UNICODE)
        if words:
            # Use first meaningful word
            slug = '-'.join(words[:3]).lower()
            # Try again with unicode normalization
            slug = unicodedata.normalize('NFD', slug)
            slug = ''.join(char for char in slug if unicodedata.category(char) != 'Mn')
            slug = re.sub(r'[^a-z0-9-]', '', slug)
            slug = re.sub(r'-+', '-', slug).strip('-')

        # Still empty? Use generic fallback
        if len(slug) < 3:
            slug = 'conversation'

    # Limit length
    return slug[:max_length].rstrip('-')


def update_frontmatter(content: str, metadata: dict) -> str:
    """Update YAML front matter with new metadata"""

    # Extract current front matter
    fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not fm_match:
        raise ValueError("No YAML front matter found")

    # Build new front matter
    concepts_str = ', '.join(metadata['concepts']) if metadata['concepts'] else ''
    tags_str = ', '.join(metadata['tags']) if metadata['tags'] else ''

    new_fm = f"""---
id: {metadata['id']}
title: "{metadata['title']}"
date: {metadata['date']}
session_type: {metadata['session_type']}
agent: {metadata['agent']}
domain: {metadata['domain']}
rems_extracted: []
turns: {metadata['turns']}
tags: [{tags_str}]
archived_by: save-command
archived_at: {metadata['date']}
---
"""

    # Replace front matter
    return re.sub(r'^---\n.*?\n---\n', new_fm, content, count=1, flags=re.DOTALL)


def update_document_structure(content: str, metadata: dict) -> str:
    """Update document structure to match /save standard"""

    # Update title (first h1)
    content = re.sub(
        r'^# Conversation - \d{4}-\d{2}-\d{2}',
        f'# {metadata["title"]}',
        content,
        count=1,
        flags=re.MULTILINE
    )

    # Remove ALL placeholder/duplicate metadata sections (everything between title and ## Summary)
    # This handles multiple Date/Agent/Domain lines and Metadata sections
    # Pattern: After title, remove everything until ## Summary (excluding ## Summary itself)
    content = re.sub(
        r'(# .*?\n)\n.*?(?=## Summary)',
        r'\1\n',
        content,
        count=1,
        flags=re.DOTALL
    )

    # Build clean metadata section
    metadata_section = f"""**Date**: {metadata['date']}
**Agent**: {metadata['agent']}
**Domain**: {metadata['domain']}

## Metadata

- **Concepts Extracted**: {', '.join([f"[[{c}]]" for c in metadata['concepts']])}
- **Total Turns**: {metadata['turns']}
- **Tags**: {', '.join(metadata['tags'])}

"""

    # Insert metadata after title (before ## Summary)
    content = re.sub(
        r'(# .*?\n)\n(## Summary)',
        rf'\1\n{metadata_section}\2',
        content,
        count=1,
        flags=re.DOTALL
    )

    # Update summary placeholder
    if metadata.get('summary'):
        content = re.sub(
            r'\*\(Summary will be generated by /save from active context\)\*',
            metadata['summary'],
            content
        )

    # Remove placeholder "## Rems Extracted" section (will be added by update-conversation-rems.py)
    content = re.sub(
        r'## Rems Extracted\n\nThis conversation led to the creation of these knowledge Rems:\n\n\*\(Rems will be listed by /save command\)\*\n\n',
        '',
        content,
        flags=re.DOTALL
    )

    return content


def normalize_conversation(file_path: Path, metadata: dict) -> Path:
    """
    Normalize conversation file to standard format

    Args:
        file_path: Path to conversation file
        metadata: Dictionary with id, title, session_type, agent, domain, concepts, tags, summary, turns

    Returns:
        New file path after renaming
    """
    # Read current content
    content = file_path.read_text(encoding='utf-8')

    # Update front matter
    content = update_frontmatter(content, metadata)

    # Update document structure
    content = update_document_structure(content, metadata)

    # Write back to file
    file_path.write_text(content, encoding='utf-8')

    # Generate new filename based on ID (not title)
    # ID should be a descriptive English slug provided by /save command
    # This allows titles to be in any language (Chinese, French, etc.)
    conversation_id = metadata['id']

    # If ID doesn't end with date, use it as-is for filename
    # Otherwise, append date only if not already in ID
    if metadata['date'] not in conversation_id:
        new_filename = f"{conversation_id}-conversation-{metadata['date']}.md"
    else:
        new_filename = f"{conversation_id}.md"

    new_path = file_path.parent / new_filename

    # Handle collision
    if new_path.exists() and new_path != file_path:
        counter = 2
        # Extract base name without .md extension
        base_name = new_filename.rsplit('.md', 1)[0]
        while new_path.exists():
            new_filename = f"{base_name}-{counter}.md"
            new_path = file_path.parent / new_filename
            counter += 1

    # Rename file
    if new_path != file_path:
        file_path.rename(new_path)
        print(f"✅ Renamed: {file_path.name} → {new_path.name}")

    return new_path


def main():
    parser = argparse.ArgumentParser(description="Normalize conversation file to standard format")
    parser.add_argument("file_path", type=Path, help="Path to conversation file")
    parser.add_argument("--id", required=True, help="Conversation ID (slug format)")
    parser.add_argument("--title", required=True, help="Conversation title")
    parser.add_argument("--session-type", required=True, choices=['learn', 'ask', 'review'], help="Session type")
    parser.add_argument("--agent", required=True, help="Agent name (e.g., analyst, main)")
    parser.add_argument("--domain", required=True, help="Domain (e.g., programming, finance, language)")
    parser.add_argument("--concepts", default='[]', help="JSON array of concept IDs")
    parser.add_argument("--tags", default='[]', help="JSON array of tags")
    parser.add_argument("--summary", default='', help="Conversation summary")
    parser.add_argument("--turns", type=int, help="Number of conversation turns (auto-detect if not provided)")

    args = parser.parse_args()

    # Validate file exists
    if not args.file_path.exists():
        print(f"❌ File not found: {args.file_path}", file=sys.stderr)
        sys.exit(1)

    # Parse JSON arrays
    import json
    concepts = json.loads(args.concepts)
    tags = json.loads(args.tags)

    # Auto-detect turns if not provided
    turns = args.turns
    if not turns:
        content = args.file_path.read_text(encoding='utf-8')
        # Count only User and Assistant turns, excluding Subagent messages
        turns = len(re.findall(r'^### (User|Assistant)$', content, re.MULTILINE))

    # Extract date from filename or front matter
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', args.file_path.name)
    if date_match:
        date = date_match.group(1)
    else:
        date = datetime.now().strftime('%Y-%m-%d')

    # Build metadata
    metadata = {
        'id': args.id,
        'title': args.title,
        'date': date,
        'session_type': args.session_type,
        'agent': args.agent,
        'domain': args.domain,
        'concepts': concepts,
        'tags': tags,
        'summary': args.summary,
        'turns': turns
    }

    # Normalize
    new_path = normalize_conversation(args.file_path, metadata)

    print(f"✅ Normalized conversation file: {new_path}", file=sys.stderr)
    print(str(new_path))  # Output path to stdout for programmatic consumption
    return 0


if __name__ == "__main__":
    main()
