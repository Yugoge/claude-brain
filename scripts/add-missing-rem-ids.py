#!/usr/bin/env python3
"""
Add missing rem_id fields to energy-derivatives Rems.

Generates rem_id based on filename pattern.
"""

import re
from pathlib import Path

# Files missing rem_id and their correct IDs (based on filename)
REM_ID_MAPPING = {
    '001-energy-derivatives-epad-structure.md': 'energy-derivatives-epad-structure',
    '002-energy-derivatives-se3-bidding-zone.md': 'energy-derivatives-se3-bidding-zone',
    '003-energy-derivatives-delta-mwh.md': 'energy-derivatives-delta-mwh',
    '004-energy-derivatives-rdq.md': 'energy-derivatives-rdq',
    '005-energy-derivatives-jkm-settlement.md': 'energy-derivatives-jkm-settlement',
    '006-energy-derivatives-fixing-methods.md': 'energy-derivatives-fixing-methods',
}

def add_rem_id(file_path: Path, rem_id: str):
    """Add rem_id field to frontmatter."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match frontmatter
    match = re.match(r'^(---\n)(.*?)(---\n)', content, re.DOTALL)
    if not match:
        return False, "No frontmatter"

    frontmatter = match.group(2)

    # Check if rem_id already exists
    if re.search(r'^rem_id:', frontmatter, re.MULTILINE):
        return False, "Already has rem_id"

    # Add rem_id as first field
    new_frontmatter = f'rem_id: {rem_id}\n' + frontmatter
    new_content = match.group(1) + new_frontmatter + match.group(3) + content[match.end():]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True, f"Added rem_id: {rem_id}"

def main():
    root_dir = Path('.').resolve()
    finance_dir = root_dir / 'knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance'

    print("🆔 Adding missing rem_id fields...")
    print("=" * 70)

    fixed_count = 0
    for filename, rem_id in REM_ID_MAPPING.items():
        file_path = finance_dir / filename
        if file_path.exists():
            result, message = add_rem_id(file_path, rem_id)
            if result:
                print(f"  ✓ {filename}: {message}")
                fixed_count += 1
            else:
                print(f"  ⏭️  {filename}: {message}")
        else:
            print(f"  ⚠️  File not found: {filename}")

    print("=" * 70)
    print(f"✅ Added rem_id to {fixed_count} files")

if __name__ == '__main__':
    main()
