#!/usr/bin/env python3
"""
Fix broken source paths in Rem files

This script:
1. Scans all Rem files for broken source links
2. Attempts to find the correct conversation file using fuzzy matching
3. Updates the source field in frontmatter
4. Generates a report of fixed and unfixable paths

Usage:
    python scripts/utilities/fix-broken-source-paths.py [--dry-run] [--verbose]
"""

import os
import re
import sys
import argparse
from pathlib import Path
from difflib import SequenceMatcher

def similarity(a, b):
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, a, b).ratio()

def find_all_conversation_files():
    """Get all conversation files in chats directory"""
    conversations = []
    for root, dirs, files in os.walk('chats'):
        for file in files:
            if file.endswith('.md'):
                path = os.path.join(root, file)
                conversations.append(path)
    return conversations

def find_best_match(broken_path, all_conversations):
    """Find the best matching conversation file using fuzzy matching"""
    broken_filename = os.path.basename(broken_path)
    broken_date = re.search(r'(\d{4}-\d{2}-\d{2})', broken_path)

    candidates = []

    for conv_path in all_conversations:
        conv_filename = os.path.basename(conv_path)

        # Must have matching date if date exists
        conv_date = re.search(r'(\d{4}-\d{2}-\d{2})', conv_path)
        if broken_date and conv_date:
            if broken_date.group(1) != conv_date.group(1):
                continue

        # Calculate similarity score
        score = similarity(broken_filename, conv_filename)
        candidates.append((conv_path, score))

    if not candidates:
        return None

    # Sort by similarity score (descending)
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Return best match if score is high enough (>= 0.6)
    if candidates[0][1] >= 0.6:
        return candidates[0][0]

    return None

def extract_frontmatter_field(content, field_name):
    """Extract a field from YAML frontmatter"""
    pattern = rf'^{field_name}:\s*(.+)$'
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None

def update_source_field(rem_file_path, old_source, new_source, dry_run=False, verbose=False):
    """Update source field in Rem file frontmatter"""
    try:
        with open(rem_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace source field
        pattern = rf'^(source:\s*){re.escape(old_source)}$'
        new_content = re.sub(pattern, rf'\1{new_source}', content, count=1, flags=re.MULTILINE)

        if new_content == content:
            if verbose:
                print(f"  ⚠️  Warning: Source field not found or not replaced in {rem_file_path}")
            return False

        if not dry_run:
            with open(rem_file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            if verbose:
                print(f"  ✅ Fixed: {rem_file_path}")
                print(f"      Old: {old_source}")
                print(f"      New: {new_source}")
        else:
            if verbose:
                print(f"  [DRY RUN] Would fix: {rem_file_path}")
                print(f"      Old: {old_source}")
                print(f"      New: {new_source}")

        return True

    except Exception as e:
        print(f"  ❌ Error updating {rem_file_path}: {e}")
        return False

def fix_broken_sources(kb_path='knowledge-base', dry_run=False, verbose=False):
    """Fix all broken source paths in knowledge base"""
    all_conversations = find_all_conversation_files()

    fixed = 0
    unfixable = []
    skipped = 0

    for root, dirs, files in os.walk(kb_path):
        # Skip templates and taxonomy
        if '_templates' in root or '_taxonomy' in root:
            continue

        for file in files:
            if file.endswith('.md') and not file.startswith('index'):
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    source = extract_frontmatter_field(content, 'source')
                    if not source:
                        continue

                    # Check if source file exists
                    if os.path.exists(source):
                        skipped += 1
                        continue

                    # Try to find best match
                    best_match = find_best_match(source, all_conversations)

                    if best_match:
                        success = update_source_field(file_path, source, best_match, dry_run, verbose)
                        if success:
                            fixed += 1
                    else:
                        unfixable.append({
                            'file': file_path,
                            'broken_source': source
                        })
                        if verbose:
                            print(f"  ❌ Could not find match for: {source} (in {file_path})")

                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

    return fixed, unfixable, skipped

def main():
    parser = argparse.ArgumentParser(description='Fix broken source paths in Rem files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')

    args = parser.parse_args()

    print("🔍 Scanning for broken source paths...\n")

    fixed, unfixable, skipped = fix_broken_sources(
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    print(f"\n📊 Summary:")
    print(f"  ✅ Fixed: {fixed}")
    print(f"  ⏭️  Skipped (already valid): {skipped}")
    print(f"  ❌ Unfixable: {len(unfixable)}")

    if unfixable:
        print(f"\n⚠️  Unfixable broken sources ({len(unfixable)}):")
        for item in unfixable[:10]:  # Show first 10
            print(f"  - {item['file']}")
            print(f"    Broken source: {item['broken_source']}")
        if len(unfixable) > 10:
            print(f"  ... and {len(unfixable) - 10} more")

    if args.dry_run:
        print("\n💡 This was a dry run. Use without --dry-run to apply changes.")
    else:
        print(f"\n✅ Done! {fixed} source paths fixed.")

if __name__ == '__main__':
    main()
