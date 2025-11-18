#!/usr/bin/env python3
"""
Batch fix script for archive validation issues

Fixes all critical and high-priority issues found by validation.
"""

import sys
import re
from pathlib import Path
from datetime import datetime

class ArchiveFixer:
    def __init__(self, root_dir: Path, dry_run: bool = False):
        self.root_dir = root_dir
        self.dry_run = dry_run
        self.fixes_applied = []

    def fix_duplicate_sections(self, file_path: Path):
        """Remove duplicate 'Rems Extracted' sections, keep only first occurrence."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find all "## Rems Extracted" sections
        pattern = r'^## Rems Extracted\n((?:(?!^##).*\n)*)'
        matches = list(re.finditer(pattern, content, re.MULTILINE))

        if len(matches) <= 1:
            return False  # No duplicates

        print(f"  Found {len(matches)} duplicate sections in {file_path.name}")

        # Keep only the first occurrence, remove the rest
        # Work backwards to preserve indices
        for match in reversed(matches[1:]):
            start, end = match.span()
            content = content[:start] + content[end:]
            print(f"    Removed duplicate at position {start}")

        if not self.dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        self.fixes_applied.append(f"Removed {len(matches)-1} duplicate sections in {file_path.name}")
        return True

    def fix_section_name(self, file_path: Path, old_name: str, new_name: str):
        """Replace section name (e.g., ## Core Points → ## Core Memory Points)."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        pattern = f'^## {re.escape(old_name)}$'
        if not re.search(pattern, content, re.MULTILINE):
            return False

        new_content = re.sub(pattern, f'## {new_name}', content, flags=re.MULTILINE)

        if not self.dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        self.fixes_applied.append(f"Renamed '{old_name}' → '{new_name}' in {file_path.name}")
        return True

    def add_frontmatter_field(self, file_path: Path, field_name: str, field_value):
        """Add missing frontmatter field."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Match frontmatter
        match = re.match(r'^(---\n)(.*?)(---\n)', content, re.DOTALL)
        if not match:
            print(f"  ⚠️  No frontmatter found in {file_path.name}")
            return False

        frontmatter = match.group(2)

        # Check if field already exists
        if re.search(f'^{field_name}:', frontmatter, re.MULTILINE):
            return False  # Already exists

        # Add field at the end of frontmatter
        new_frontmatter = frontmatter.rstrip('\n') + f'\n{field_name}: {field_value}\n'
        new_content = match.group(1) + new_frontmatter + match.group(3) + content[match.end():]

        if not self.dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        self.fixes_applied.append(f"Added {field_name}: {field_value} to {file_path.name}")
        return True

    def update_frontmatter_field(self, file_path: Path, field_name: str, new_value: str):
        """Update existing frontmatter field value."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Match frontmatter
        match = re.match(r'^(---\n)(.*?)(---\n)', content, re.DOTALL)
        if not match:
            return False

        frontmatter = match.group(2)

        # Update field
        pattern = f'^({field_name}:)(.*)$'
        if not re.search(pattern, frontmatter, re.MULTILINE):
            return False  # Field doesn't exist

        new_frontmatter = re.sub(pattern, f'\\1 {new_value}', frontmatter, flags=re.MULTILINE)
        new_content = match.group(1) + new_frontmatter + match.group(3) + content[match.end():]

        if not self.dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        self.fixes_applied.append(f"Updated {field_name} in {file_path.name}")
        return True

    def quote_yaml_value(self, file_path: Path, field_name: str):
        """Add quotes around a YAML field value."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Match frontmatter
        match = re.match(r'^(---\n)(.*?)(---\n)', content, re.DOTALL)
        if not match:
            return False

        frontmatter = match.group(2)

        # Quote the field value
        pattern = f'^({field_name}:)\\s*(.+?)\\s*$'
        def quote_replace(m):
            value = m.group(2).strip()
            # If already quoted, skip
            if value.startswith('"') and value.endswith('"'):
                return m.group(0)
            # Escape internal quotes
            value = value.replace('"', '\\"')
            return f'{m.group(1)} "{value}"'

        new_frontmatter = re.sub(pattern, quote_replace, frontmatter, flags=re.MULTILINE)

        if new_frontmatter == frontmatter:
            return False

        new_content = match.group(1) + new_frontmatter + match.group(3) + content[match.end():]

        if not self.dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

        self.fixes_applied.append(f"Quoted {field_name} value in {file_path.name}")
        return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Batch fix archive validation issues')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--root', type=str, default='.', help='Root directory')

    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    fixer = ArchiveFixer(root_dir, dry_run=args.dry_run)

    print("🔧 Archive Issue Fixer")
    print("=" * 70)
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No files will be modified\n")

    # Fix 1: Remove duplicate "Rems Extracted" sections
    print("\n1️⃣  Fixing duplicate 'Rems Extracted' sections...")
    duplicate_files = [
        'chats/2025-11/bloomberg-ovdv-black-scholes-deep-dive-volatility-conversation-2025-11-04.md',
        'chats/2025-11/desire-driven-growth-2025-11-02.md',
        'chats/2025-11/epad-vs-jkm-european-power-and-asian-lng-derivativ-conversation-2025-11-05.md',
        'chats/2025-11/french-grammar-session-2025-11-03.md',
        'chats/2025-11/nds-fx-options-payment-currency-conventions-conversation-2025-11-03.md'
    ]

    for file_rel in duplicate_files:
        file_path = root_dir / file_rel
        if file_path.exists():
            fixer.fix_duplicate_sections(file_path)

    # Fix 2: Standardize section names
    print("\n2️⃣  Standardizing section names (Core Points → Core Memory Points)...")
    kb_dir = root_dir / 'knowledge-base'
    for md_file in kb_dir.rglob('*.md'):
        if '_templates' in str(md_file) or 'index' in md_file.name:
            continue
        if fixer.fix_section_name(md_file, 'Core Points', 'Core Memory Points'):
            print(f"  ✓ Fixed {md_file.relative_to(root_dir)}")

    # Fix 3: Quote YAML title in problematic file
    print("\n3️⃣  Fixing YAML parse error...")
    problem_file = root_dir / 'knowledge-base/02-arts-and-humanities/023-languages/0231-language-acquisition/003-english-ple-syllable-position-variation.md'
    if problem_file.exists():
        if fixer.quote_yaml_value(problem_file, 'title'):
            print(f"  ✓ Quoted title in {problem_file.name}")

    # Summary
    print("\n" + "=" * 70)
    print(f"✅ Applied {len(fixer.fixes_applied)} fixes")
    if args.dry_run:
        print("⚠️  DRY RUN - No files were actually modified")
        print("\nRun without --dry-run to apply changes:")
        print("  python scripts/fix-archive-issues.py")
    else:
        print("\n📋 Fixes applied:")
        for fix in fixer.fixes_applied:
            print(f"  • {fix}")


if __name__ == '__main__':
    main()
