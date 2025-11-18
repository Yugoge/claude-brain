#!/usr/bin/env python3
"""
Add missing sections to Rem files.

Generates titles from filenames and adds placeholder sections.
"""

import re
from pathlib import Path
from typing import Optional

def filename_to_title(filename: str) -> str:
    """Convert filename to readable title.

    Example: 018-french-verb-aller-prepositions.md
    -> French Verb Aller - Prepositions
    """
    # Remove number prefix and extension
    name = re.sub(r'^\d+-', '', filename)
    name = name.replace('.md', '')

    # Split by hyphens
    parts = name.split('-')

    # Capitalize parts
    title_parts = [part.capitalize() for part in parts]

    # Join with spaces
    return ' '.join(title_parts)

def add_title(file_path: Path, content: str) -> str:
    """Add title heading if missing."""
    # Check if title already exists
    if re.match(r'^#\s+.+', content, re.MULTILINE):
        return content

    # Generate title from filename
    title = filename_to_title(file_path.name)

    # Find where to insert (after frontmatter)
    match = re.match(r'^(---\n.*?\n---\n)', content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        rest = content[match.end():]
        return frontmatter + f'\n# {title}\n' + rest
    else:
        return f'# {title}\n\n' + content

def add_section(content: str, section_name: str, placeholder: str) -> str:
    """Add section if missing."""
    pattern = f'^## {re.escape(section_name)}$'
    if re.search(pattern, content, re.MULTILINE):
        return content  # Section already exists

    # Find where to insert
    if section_name == 'Core Memory Points':
        # Insert after title
        match = re.search(r'^(# .+\n)', content, re.MULTILINE)
        if match:
            pos = match.end()
            return content[:pos] + f'\n## {section_name}\n\n{placeholder}\n' + content[pos:]

    elif section_name == 'My Mistakes':
        # Insert before Related Rems or at end
        related_match = re.search(r'^## Related Rems', content, re.MULTILINE)
        if related_match:
            pos = related_match.start()
            return content[:pos] + f'## {section_name}\n\n{placeholder}\n\n' + content[pos:]

    elif section_name == 'Conversation Source':
        # Add at end
        return content.rstrip() + f'\n\n## {section_name}\n\n{placeholder}\n'

    return content

def fix_rem_file(file_path: Path, add_placeholders: bool = True):
    """Fix a single Rem file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes = []

    # Add title if missing
    new_content = add_title(file_path, content)
    if new_content != content:
        changes.append("Added title")
        content = new_content

    # Add Core Memory Points if missing
    if add_placeholders:
        placeholder = "1. **[Key concept]** - [Brief explanation]\n2. **[Key concept]** - [Brief explanation]\n3. **[Key concept]** - [Brief explanation]"
        new_content = add_section(content, 'Core Memory Points', placeholder)
        if new_content != content:
            changes.append("Added Core Memory Points")
            content = new_content

    # Add My Mistakes if missing
    if add_placeholders:
        placeholder = "- ❌ [Common mistake] → ✅ [Correct understanding]"
        new_content = add_section(content, 'My Mistakes', placeholder)
        if new_content != content:
            changes.append("Added My Mistakes")
            content = new_content

    # Add Conversation Source if missing
    # Try to get from source field in frontmatter
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        source_match = re.search(r'^source:\s*(.+?)$', fm, re.MULTILINE)
        if source_match:
            source_path = source_match.group(1).strip()
            # Generate conversation title from path
            if source_path.endswith('.md'):
                conv_name = Path(source_path).stem
                conv_title = filename_to_title(conv_name + '.md')
                placeholder = f"→ See: [{conv_title}]({source_path})"
            else:
                placeholder = f"→ See: [Conversation]({source_path})"

            new_content = add_section(content, 'Conversation Source', placeholder)
            if new_content != content:
                changes.append("Added Conversation Source")
                content = new_content

    # Write if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, changes

    return False, []

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Add missing sections to Rem files')
    parser.add_argument('files', nargs='*', help='Specific files to fix (optional)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--no-placeholders', action='store_true', help='Only add titles, not placeholder content')

    args = parser.parse_args()

    root_dir = Path('.').resolve()

    # List of files to fix based on validation results
    target_files = [
        # French Rems
        'knowledge-base/02-arts-and-humanities/023-languages/0231-language-acquisition/018-french-verb-aller-prepositions.md',
        'knowledge-base/02-arts-and-humanities/023-languages/0231-language-acquisition/019-french-tout-agreement-a2.md',
        'knowledge-base/02-arts-and-humanities/023-languages/0231-language-acquisition/020-french-lorsque-vs-quand.md',
        'knowledge-base/02-arts-and-humanities/023-languages/0231-language-acquisition/021-french-negation-ne-jamais.md',
        # Finance Rems
        'knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/001-fx-derivatives-interest-rate-parity-forward-pricing.md',
        'knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/002-risk-management-xccy-curve-rebuild-spot-shock.md',
        'knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/003-fx-derivatives-tradability-interest-vs-inflation-pricing.md',
        'knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/006-fixed-income-fx-swap-vs-basis-swap-structure.md',
        'knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/007-fixed-income-xccy-interpolation-methodology.md',
    ]

    if args.files:
        target_files = args.files

    print("🔧 Adding Missing Sections to Rems")
    print("=" * 70)
    if args.dry_run:
        print("⚠️  DRY RUN MODE\n")

    fixed_count = 0
    for file_rel in target_files:
        file_path = root_dir / file_rel
        if not file_path.exists():
            print(f"  ⚠️  Not found: {file_rel}")
            continue

        if args.dry_run:
            print(f"  Would fix: {file_path.name}")
        else:
            changed, changes = fix_rem_file(file_path, add_placeholders=not args.no_placeholders)
            if changed:
                print(f"  ✓ Fixed {file_path.name}")
                for change in changes:
                    print(f"      - {change}")
                fixed_count += 1
            else:
                print(f"  ⏭️  No changes needed: {file_path.name}")

    print("=" * 70)
    if args.dry_run:
        print(f"Would fix {len(target_files)} files")
    else:
        print(f"✅ Fixed {fixed_count} files")

if __name__ == '__main__':
    main()
