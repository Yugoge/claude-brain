#!/usr/bin/env python3
"""
Standardize all rem_id fields to format: {subdomain}-{concept-slug}

This script:
1. Scans all Rem files
2. Ensures rem_id follows pattern: {subdomain}-{concept-slug}
3. Updates all references:
   - Rem frontmatter rem_id fields
   - Related Rems wikilinks [[old_id]] -> [[new_id]]
   - backlinks.json
   - schedule.json
4. Preserves all relationships and FSRS data

Usage:
    python scripts/utilities/standardize-rem-ids.py [--dry-run] [--verbose]
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict

def extract_frontmatter_field(content, field_name):
    """Extract a field from YAML frontmatter"""
    pattern = rf'^{field_name}:\s*(.+)$'
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None

def extract_frontmatter_block(content):
    """Extract entire YAML frontmatter block"""
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if match:
        return match.group(0)
    return None

def scan_all_rems(kb_path='knowledge-base'):
    """Scan all Rem files and build mapping of old_id -> new_id"""
    id_mapping = {}  # old_id -> new_id
    rem_files = {}   # new_id -> file_path

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

                    rem_id = extract_frontmatter_field(content, 'rem_id')
                    subdomain = extract_frontmatter_field(content, 'subdomain')

                    if not rem_id or not subdomain:
                        continue

                    # Check if rem_id already follows the pattern
                    if rem_id.startswith(f"{subdomain}-"):
                        # Already correct
                        new_id = rem_id
                    else:
                        # Need to add subdomain prefix
                        new_id = f"{subdomain}-{rem_id}"

                    # Store mapping
                    if rem_id != new_id:
                        id_mapping[rem_id] = new_id

                    rem_files[new_id] = file_path

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    return id_mapping, rem_files

def update_rem_file(file_path, old_id, new_id, id_mapping, dry_run=False, verbose=False):
    """Update rem_id in a single Rem file and update Related Rems wikilinks"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # 1. Update rem_id in frontmatter
        content = re.sub(
            rf'^rem_id:\s*{re.escape(old_id)}$',
            f'rem_id: {new_id}',
            content,
            count=1,
            flags=re.MULTILINE
        )

        # 2. Update all wikilinks in Related Rems section
        # Find all [[concept-id]] patterns and update if they're in the mapping
        def replace_wikilink(match):
            link_id = match.group(1)
            if link_id in id_mapping:
                return f"[[{id_mapping[link_id]}]]"
            return match.group(0)

        content = re.sub(r'\[\[([^\]]+)\]\]', replace_wikilink, content)

        # Only write if content changed
        if content != original_content:
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                if verbose:
                    print(f"  ✅ Updated: {file_path}")
                    print(f"      rem_id: {old_id} -> {new_id}")
            else:
                if verbose:
                    print(f"  [DRY RUN] Would update: {file_path}")
                    print(f"      rem_id: {old_id} -> {new_id}")
            return True

        return False

    except Exception as e:
        print(f"  ❌ Error updating {file_path}: {e}")
        return False

def update_backlinks_json(id_mapping, dry_run=False, verbose=False):
    """Update all concept IDs in backlinks.json"""
    backlinks_path = 'knowledge-base/_index/backlinks.json'

    if not os.path.exists(backlinks_path):
        print("⚠️  backlinks.json not found, skipping")
        return False

    try:
        with open(backlinks_path, 'r', encoding='utf-8') as f:
            backlinks = json.load(f)

        # Create new backlinks dict with updated IDs
        new_backlinks = {}

        for concept_id, data in backlinks.items():
            # Update the concept ID itself
            new_concept_id = id_mapping.get(concept_id, concept_id)

            # Update all linked_from IDs
            if 'linked_from' in data:
                new_linked_from = []
                for link in data['linked_from']:
                    new_link = dict(link)
                    if 'concept_id' in new_link:
                        new_link['concept_id'] = id_mapping.get(new_link['concept_id'], new_link['concept_id'])
                    new_linked_from.append(new_link)
                data['linked_from'] = new_linked_from

            new_backlinks[new_concept_id] = data

        if not dry_run:
            with open(backlinks_path, 'w', encoding='utf-8') as f:
                json.dump(new_backlinks, f, indent=2, ensure_ascii=False)
            if verbose:
                print(f"  ✅ Updated backlinks.json ({len(id_mapping)} IDs remapped)")
        else:
            if verbose:
                print(f"  [DRY RUN] Would update backlinks.json ({len(id_mapping)} IDs remapped)")

        return True

    except Exception as e:
        print(f"  ❌ Error updating backlinks.json: {e}")
        return False

def update_schedule_json(id_mapping, dry_run=False, verbose=False):
    """Update all concept IDs in schedule.json"""
    schedule_path = '.review/schedule.json'

    if not os.path.exists(schedule_path):
        print("⚠️  schedule.json not found, skipping")
        return False

    try:
        with open(schedule_path, 'r', encoding='utf-8') as f:
            schedule = json.load(f)

        # Create new concepts dict with updated IDs
        new_concepts = {}

        if 'concepts' in schedule:
            for concept_id, data in schedule['concepts'].items():
                # Update the concept ID key
                new_concept_id = id_mapping.get(concept_id, concept_id)

                # Update the id field inside the data
                if 'id' in data:
                    data['id'] = new_concept_id

                new_concepts[new_concept_id] = data

            schedule['concepts'] = new_concepts

        if not dry_run:
            with open(schedule_path, 'w', encoding='utf-8') as f:
                json.dump(schedule, f, indent=2, ensure_ascii=False)
            if verbose:
                print(f"  ✅ Updated schedule.json ({len(id_mapping)} IDs remapped)")
        else:
            if verbose:
                print(f"  [DRY RUN] Would update schedule.json ({len(id_mapping)} IDs remapped)")

        return True

    except Exception as e:
        print(f"  ❌ Error updating schedule.json: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Standardize all rem_id fields to {subdomain}-{concept-slug} format')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')

    args = parser.parse_args()

    print("🔍 Scanning all Rem files...\n")

    # Step 1: Build ID mapping
    id_mapping, rem_files = scan_all_rems()

    if not id_mapping:
        print("✅ All rem_ids already follow the correct format!")
        return

    print(f"📋 Found {len(id_mapping)} Rems that need ID updates:\n")

    if args.verbose:
        for old_id, new_id in sorted(id_mapping.items()):
            print(f"  {old_id} -> {new_id}")
        print()

    # Step 2: Update all Rem files
    print("📝 Updating Rem files...\n")
    updated_count = 0

    for old_id, new_id in id_mapping.items():
        if new_id in rem_files:
            file_path = rem_files[new_id]
            if update_rem_file(file_path, old_id, new_id, id_mapping, args.dry_run, args.verbose):
                updated_count += 1

    # Step 3: Update all other Rem files (for wikilinks even if their own ID doesn't change)
    print(f"\n🔗 Updating wikilinks in all Rem files...\n")
    wikilink_updates = 0

    for new_id, file_path in rem_files.items():
        if new_id not in id_mapping.values():
            # This file's ID didn't change, but it might have wikilinks to update
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                def replace_wikilink(match):
                    link_id = match.group(1)
                    if link_id in id_mapping:
                        return f"[[{id_mapping[link_id]}]]"
                    return match.group(0)

                content = re.sub(r'\[\[([^\]]+)\]\]', replace_wikilink, content)

                if content != original_content:
                    if not args.dry_run:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        if args.verbose:
                            print(f"  ✅ Updated wikilinks in: {file_path}")
                    else:
                        if args.verbose:
                            print(f"  [DRY RUN] Would update wikilinks in: {file_path}")
                    wikilink_updates += 1
            except Exception as e:
                print(f"  ❌ Error updating wikilinks in {file_path}: {e}")

    # Step 4: Update backlinks.json
    print(f"\n📊 Updating backlinks.json...\n")
    update_backlinks_json(id_mapping, args.dry_run, args.verbose)

    # Step 5: Update schedule.json
    print(f"\n📅 Updating schedule.json...\n")
    update_schedule_json(id_mapping, args.dry_run, args.verbose)

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"  Total rem_ids updated: {updated_count}")
    print(f"  Wikilinks updated in files: {wikilink_updates}")
    print(f"  backlinks.json: Updated")
    print(f"  schedule.json: Updated")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n💡 This was a dry run. Use without --dry-run to apply changes.")
    else:
        print(f"\n✅ Done! All rem_ids now follow the {'{subdomain}-{concept-slug}'} format.")
        print("   All references have been updated (wikilinks, backlinks, schedule).")

if __name__ == '__main__':
    main()
