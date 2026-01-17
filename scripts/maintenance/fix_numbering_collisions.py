#!/usr/bin/env python3
"""
Fix numbering collisions in knowledge base by renumbering files with duplicate prefixes.
"""

import os
import re
import shutil
from pathlib import Path
from collections import defaultdict
import json

def find_collisions(base_path):
    """Find all files with duplicate number prefixes."""
    collisions = defaultdict(list)

    for path in Path(base_path).rglob("*.md"):
        if path.name in ["index.md", "backlinks.json"]:
            continue

        # Extract number prefix (first part before dash)
        match = re.match(r'^(\d+)-', path.name)
        if match:
            number = match.group(1)
            parent = str(path.parent.relative_to(base_path))
            collisions[parent].append((number, str(path)))

    # Filter to only directories with collisions
    collision_groups = {}
    for directory, files in collisions.items():
        number_counts = defaultdict(list)
        for number, filepath in files:
            number_counts[number].append(filepath)

        # Find actual collisions (more than one file with same number)
        for number, filepaths in number_counts.items():
            if len(filepaths) > 1:
                if directory not in collision_groups:
                    collision_groups[directory] = {}
                collision_groups[directory][number] = filepaths

    return collision_groups

def get_next_available_number(directory, start_from=1, existing_numbers=None):
    """Find the next available number in a directory."""
    if existing_numbers is None:
        existing_numbers = set()
        for path in Path(directory).glob("*.md"):
            if path.name != "index.md":
                match = re.match(r'^(\d+)-', path.name)
                if match:
                    existing_numbers.add(int(match.group(1)))

    number = start_from
    while number in existing_numbers:
        number += 1
    return number, existing_numbers

def create_renaming_plan(collision_groups):
    """Create a plan for renaming all collision files."""
    rename_map = {}

    for directory, number_groups in collision_groups.items():
        dir_path = Path("/root/knowledge-system/knowledge-base") / directory

        # Get all existing numbers in this directory
        existing_numbers = set()
        for path in dir_path.glob("*.md"):
            if path.name != "index.md":
                match = re.match(r'^(\d+)-', path.name)
                if match:
                    existing_numbers.add(int(match.group(1)))

        for number, filepaths in sorted(number_groups.items()):
            # Keep the first file, rename the rest
            for i, filepath in enumerate(sorted(filepaths)):
                if i == 0:
                    continue  # Keep first file as is

                old_path = Path(filepath)
                old_name = old_path.name

                # Find next available number
                next_num, existing_numbers = get_next_available_number(
                    old_path.parent,
                    int(number) + 1,
                    existing_numbers
                )
                existing_numbers.add(next_num)

                # Create new name with new number
                new_name = re.sub(r'^\d+-', f'{next_num:03d}-', old_name)
                new_path = old_path.parent / new_name

                rename_map[str(old_path)] = str(new_path)
                rename_map[old_name] = new_name  # Also store just filename mapping

    return rename_map

def execute_renaming(rename_map):
    """Execute the renaming plan."""
    renamed = []
    errors = []

    for old_path, new_path in rename_map.items():
        if '/' not in old_path:
            continue  # Skip filename-only entries

        try:
            old = Path(old_path)
            new = Path(new_path)

            if old.exists():
                print(f"Renaming: {old.name} -> {new.name}")
                shutil.move(str(old), str(new))
                renamed.append((str(old), str(new)))
            else:
                errors.append(f"File not found: {old}")
        except Exception as e:
            errors.append(f"Error renaming {old_path}: {e}")

    return renamed, errors

def update_references(rename_map, base_path):
    """Update all references to renamed files."""
    updates = 0

    # Create a mapping of just filenames for easier lookup
    filename_map = {k: v for k, v in rename_map.items() if '/' not in k}

    for path in Path(base_path).rglob("*.md"):
        if path.name == "index.md":
            continue

        try:
            content = path.read_text()
            original_content = content

            # Update references to renamed files
            for old_name, new_name in filename_map.items():
                # Match various reference patterns
                patterns = [
                    (f'\\[([^\\]]*)\\]\\({re.escape(old_name)}\\)', f'[\\1]({new_name})'),  # [text](file.md)
                    (f'\\[\\[{re.escape(old_name[:-3])}\\]\\]', f'[[{new_name[:-3]}]]'),  # [[file]]
                    (re.escape(old_name), new_name)  # Direct references
                ]

                for pattern, replacement in patterns:
                    content = re.sub(pattern, replacement, content)

            if content != original_content:
                path.write_text(content)
                updates += 1
                print(f"Updated references in: {path.name}")
        except Exception as e:
            print(f"Error updating {path}: {e}")

    return updates

def main():
    base_path = "/root/knowledge-system/knowledge-base"

    print("Step 1: Finding all numbering collisions...")
    collision_groups = find_collisions(base_path)

    total_collisions = sum(len(files) for dir_groups in collision_groups.values() for files in dir_groups.values())
    print(f"Found {len(collision_groups)} directories with collisions, {total_collisions} total collision files")

    # Show summary
    print("\nCollision Summary:")
    for directory, number_groups in sorted(collision_groups.items()):
        print(f"\n{directory}:")
        for number, files in sorted(number_groups.items()):
            print(f"  {number}: {len(files)} files")
            for f in files[:3]:  # Show first 3
                print(f"    - {Path(f).name}")
            if len(files) > 3:
                print(f"    ... and {len(files)-3} more")

    print("\nStep 2: Creating renaming plan...")
    rename_map = create_renaming_plan(collision_groups)

    print(f"\nPlanning to rename {len([k for k in rename_map if '/' in k])} files")

    # Save rename map for reference
    with open('/tmp/rename_map.json', 'w') as f:
        json.dump(rename_map, f, indent=2)
    print("Rename map saved to /tmp/rename_map.json")

    print("\nStep 3: Executing renaming...")
    renamed, errors = execute_renaming(rename_map)

    print(f"Successfully renamed {len(renamed)} files")
    if errors:
        print(f"Errors encountered: {len(errors)}")
        for error in errors[:5]:
            print(f"  - {error}")

    print("\nStep 4: Updating references...")
    updates = update_references(rename_map, base_path)
    print(f"Updated references in {updates} files")

    print("\nStep 5: Verifying no collisions remain...")
    remaining_collisions = find_collisions(base_path)

    if remaining_collisions:
        print(f"WARNING: {len(remaining_collisions)} directories still have collisions!")
        for directory, number_groups in sorted(remaining_collisions.items())[:5]:
            print(f"  {directory}: {list(number_groups.keys())}")
    else:
        print("SUCCESS: No numbering collisions remain!")

    # Generate report
    report = {
        "collision_groups_found": len(collision_groups),
        "total_collision_files": total_collisions,
        "files_renamed": len(renamed),
        "references_updated": updates,
        "errors": errors,
        "remaining_collisions": len(remaining_collisions)
    }

    with open('/tmp/numbering_fix_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*50)
    print("FINAL REPORT:")
    print(f"  Collision groups found: {report['collision_groups_found']}")
    print(f"  Files renamed: {report['files_renamed']}")
    print(f"  References updated: {report['references_updated']}")
    print(f"  Errors: {len(report['errors'])}")
    print(f"  Remaining collisions: {report['remaining_collisions']}")
    print("\nFull report saved to /tmp/numbering_fix_report.json")

    return report

if __name__ == "__main__":
    main()