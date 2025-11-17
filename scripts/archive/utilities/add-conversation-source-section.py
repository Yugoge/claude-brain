#!/usr/bin/env python3
"""
Add Conversation Source section to all Rem files

This script:
1. Scans all Rem files in knowledge-base/
2. Extracts the source field from frontmatter
3. Reads conversation title from the source file
4. Adds a "## Conversation Source" section at the end
5. Creates a clickable markdown link to the conversation

Usage:
    python scripts/utilities/add-conversation-source-section.py [--dry-run] [--verbose]
"""

import os
import re
import sys
import argparse
from pathlib import Path

def extract_frontmatter_field(content, field_name):
    """Extract a field from YAML frontmatter"""
    pattern = rf'^{field_name}:\s*(.+)$'
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None

def extract_conversation_title(conversation_path):
    """Extract title from conversation file frontmatter"""
    try:
        with open(conversation_path, 'r', encoding='utf-8') as f:
            content = f.read()
            title = extract_frontmatter_field(content, 'title')
            if title:
                return title
            # Fallback: use filename
            return Path(conversation_path).stem.replace('-', ' ').title()
    except Exception as e:
        print(f"Warning: Could not read conversation file {conversation_path}: {e}")
        return None

def has_conversation_source_section(content):
    """Check if file already has Conversation Source section"""
    return bool(re.search(r'^##\s+Conversation\s+Source', content, re.MULTILINE | re.IGNORECASE))

def calculate_relative_path(rem_file_path, conversation_path):
    """Calculate relative path from rem to conversation"""
    rem_dir = os.path.dirname(rem_file_path)
    rel_path = os.path.relpath(conversation_path, rem_dir)
    return rel_path

def add_conversation_source_section(rem_file_path, dry_run=False, verbose=False):
    """Add Conversation Source section to a Rem file"""
    try:
        with open(rem_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if section already exists
        if has_conversation_source_section(content):
            if verbose:
                print(f"  ⏭️  Skipped (already has section): {rem_file_path}")
            return False

        # Extract source field
        source = extract_frontmatter_field(content, 'source')
        if not source:
            if verbose:
                print(f"  ⚠️  Warning: No source field found in {rem_file_path}")
            return False

        # Validate source file exists
        if not os.path.exists(source):
            if verbose:
                print(f"  ⚠️  Warning: Source file not found: {source} (in {rem_file_path})")
            return False

        # Get conversation title
        conversation_title = extract_conversation_title(source)
        if not conversation_title:
            conversation_title = "Conversation"

        # Calculate relative path from rem to conversation
        rel_path = calculate_relative_path(rem_file_path, source)

        # Create the section
        section = f"\n## Conversation Source\n\n→ See: [{conversation_title}]({rel_path})\n"

        # Add section at the end (ensure proper spacing)
        content = content.rstrip() + "\n" + section

        if not dry_run:
            with open(rem_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            if verbose:
                print(f"  ✅ Added section: {rem_file_path}")
        else:
            if verbose:
                print(f"  [DRY RUN] Would add section to: {rem_file_path}")

        return True

    except Exception as e:
        print(f"  ❌ Error processing {rem_file_path}: {e}")
        return False

def process_knowledge_base(kb_path='knowledge-base', dry_run=False, verbose=False):
    """Process all Rem files in knowledge base"""
    processed = 0
    updated = 0
    skipped = 0
    errors = 0

    for root, dirs, files in os.walk(kb_path):
        # Skip templates and taxonomy
        if '_templates' in root or '_taxonomy' in root or 'index.md' in files:
            continue

        for file in files:
            if file.endswith('.md') and not file.startswith('index'):
                file_path = os.path.join(root, file)
                processed += 1

                try:
                    result = add_conversation_source_section(file_path, dry_run, verbose)
                    if result:
                        updated += 1
                    else:
                        skipped += 1
                except Exception as e:
                    print(f"Error: {e}")
                    errors += 1

    return processed, updated, skipped, errors

def main():
    parser = argparse.ArgumentParser(description='Add Conversation Source section to all Rem files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')

    args = parser.parse_args()

    print("🔍 Scanning knowledge base for Rem files...\n")

    processed, updated, skipped, errors = process_knowledge_base(
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    print(f"\n📊 Summary:")
    print(f"  Total Rems processed: {processed}")
    print(f"  ✅ Updated: {updated}")
    print(f"  ⏭️  Skipped (already had section): {skipped}")
    print(f"  ❌ Errors: {errors}")

    if args.dry_run:
        print("\n💡 This was a dry run. Use without --dry-run to apply changes.")
    else:
        print(f"\n✅ Done! {updated} Rem files now have Conversation Source sections.")

if __name__ == '__main__':
    main()
