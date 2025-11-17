#!/usr/bin/env python3
"""
Update existing Rem file with clarification
Appends clarification to target section
"""
import sys
import argparse
from pathlib import Path

def find_rem_file(rem_id):
    """Find Rem file by ID using glob."""
    matches = list(Path('knowledge-base').rglob(f'{rem_id}.md'))
    if len(matches) == 0:
        print(f"Error: Rem {rem_id} not found", file=sys.stderr)
        return None
    if len(matches) > 1:
        print(f"Error: Multiple matches for {rem_id}", file=sys.stderr)
        return None
    return matches[0]

def update_clarification(rem_file, clarification, target_section):
    """Append clarification to target section."""
    content = rem_file.read_text()

    # Try English section names first
    section_alternatives = {
        'Core Memory Points': ['## Core Memory Points', '## Core Points'],
        'Usage Scenario': ['## Usage Scenario', '## Usage'],
        'My Mistakes': ['## My Mistakes', '## Mistakes']
    }

    found_section = None
    for section_name, alternatives in section_alternatives.items():
        if target_section in section_name:
            for alt in alternatives:
                if alt in content:
                    found_section = alt
                    break

    if not found_section:
        print(f"Error: Section {target_section} not found", file=sys.stderr)
        return False

    # Append clarification
    new_content = content.replace(
        found_section,
        f"{found_section}\n\n{clarification}"
    )

    rem_file.write_text(new_content)
    print(f"✅ Updated {rem_file.name}")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('rem_id', help='Rem ID to update')
    parser.add_argument('clarification', help='Clarification text')
    parser.add_argument('--section', default='Core Memory Points',
                       help='Target section')
    args = parser.parse_args()

    rem_file = find_rem_file(args.rem_id)
    if not rem_file:
        sys.exit(1)

    if update_clarification(rem_file, args.clarification, args.section):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
