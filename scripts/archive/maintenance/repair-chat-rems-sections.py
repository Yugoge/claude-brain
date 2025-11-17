#!/usr/bin/env python3
"""
Repair Chat Rems Sections - Batch fix for conversation files

Fixes all chat files to have proper "## Rems Extracted" sections:
1. Unifies section name to "## Rems Extracted" (not "Extracted Concepts")
2. Replaces placeholder text with actual markdown links
3. Converts wikilinks to clickable markdown relative paths
4. Positions section correctly (after Date/Agent/Domain, before ## Metadata)

Usage:
    # Dry-run (preview changes)
    python repair-chat-rems-sections.py --input chats/ --dry-run

    # Execute repairs
    python repair-chat-rems-sections.py --input chats/ --execute
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

# Import functions from update_conversation_rems.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "update_conversation_rems",
    scripts_dir / "archival" / "update-conversation-rems.py"
)
update_conv_rems = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_conv_rems)

build_rem_metadata = update_conv_rems.build_rem_metadata
generate_rems_section = update_conv_rems.generate_rems_section
calculate_relative_path = update_conv_rems.calculate_relative_path
extract_rem_title = update_conv_rems.extract_rem_title


def find_rem_file_by_id(rem_id: str, kb_root: Path) -> Optional[Path]:
    """
    Find Rem file by ID in knowledge base.

    Handles two formats:
    1. Full rem_id with subdomain: equity-derivatives-theta-decay
    2. Partial rem_id without subdomain: theta-decay

    Searches for files matching pattern: *{rem_id}.md
    """
    # Try exact match first (with numeric prefix support)
    pattern = f"**/*{rem_id}.md"
    matches = list(kb_root.glob(pattern))

    # Filter to exact matches (filename ends with rem_id, ignoring numeric prefix)
    exact_matches = []
    for match in matches:
        filename = match.stem
        # Remove numeric prefix if exists (e.g., "001-")
        filename_clean = re.sub(r'^\d+-', '', filename)

        # Exact match: full rem_id matches
        if filename_clean == rem_id:
            exact_matches.append(match)
        # Partial match: rem_id is suffix after subdomain (e.g., "theta-decay" matches "equity-derivatives-theta-decay")
        elif filename_clean.endswith(f"-{rem_id}"):
            exact_matches.append(match)

    if len(exact_matches) == 1:
        return exact_matches[0]
    elif len(exact_matches) > 1:
        # Prefer exact match over partial match
        for match in exact_matches:
            filename_clean = re.sub(r'^\d+-', '', match.stem)
            if filename_clean == rem_id:
                return match
        # If no exact match, return first partial match
        return exact_matches[0]
    else:
        # Last resort: search by pattern in entire filename
        pattern_loose = f"**/*{rem_id}*.md"
        loose_matches = list(kb_root.glob(pattern_loose))
        if loose_matches:
            # Filter out index files
            filtered = [m for m in loose_matches if not m.stem.endswith('-index') and 'index.md' not in str(m)]
            if filtered:
                return filtered[0]

        print(f"⚠️  No Rem file found for ID: {rem_id}", file=sys.stderr)
        return None


def extract_rems_from_frontmatter(content: str) -> List[str]:
    """Extract rem IDs from YAML frontmatter"""
    fm_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not fm_match:
        return []

    frontmatter = fm_match.group(1)

    # Try concepts_extracted field first (older format)
    concepts_match = re.search(r'concepts_extracted:\s*\[(.*?)\]', frontmatter, re.DOTALL)
    if concepts_match:
        concepts_str = concepts_match.group(1)
        rem_ids = [c.strip().strip('"\'') for c in concepts_str.split(',') if c.strip()]
        return rem_ids

    # Try rems_extracted field (newer format)
    rems_match = re.search(r'rems_extracted:\s*\[(.*?)\]', frontmatter, re.DOTALL)
    if rems_match:
        rems_str = rems_match.group(1)
        rem_ids = [r.strip().strip('"\'') for r in rems_str.split(',') if r.strip()]
        return rem_ids

    return []


def remove_old_rems_section(body: str) -> str:
    """
    Remove old "## Rems Extracted" or "## Extracted Concepts" section.

    Handles both:
    - Old placeholder: "## Rems Extracted\n\n*(Rems will be listed...)*"
    - Old wikilinks: "## Extracted Concepts\n\n- [[concept]]..."
    """
    # Pattern 1: Remove "## Rems Extracted" + placeholder
    pattern1 = r'## Rems Extracted\n\n\*\(.*?\)\*\n\n'
    body = re.sub(pattern1, '', body, flags=re.DOTALL)

    # Pattern 2: Remove "## Extracted Concepts" + anything until next ##
    pattern2 = r'## Extracted Concepts\n\n.*?(?=\n## )'
    body = re.sub(pattern2, '', body, flags=re.DOTALL)

    # Pattern 3: Remove "## Rems Extracted" + bullet list until next ##
    pattern3 = r'## Rems Extracted\n\nThis conversation led.*?(?=\n## )'
    body = re.sub(pattern3, '', body, flags=re.DOTALL)

    return body


def remove_metadata_wikilinks(body: str) -> str:
    """
    Remove wikilinks from ## Metadata section.

    Changes:
        - **Rems Extracted**: [[rem-1]], [[rem-2]]
    To:
        - **Rems Extracted**: rem-1, rem-2
    """
    # Find ## Metadata section
    metadata_match = re.search(r'(## Metadata.*?)(?=\n## |\Z)', body, re.DOTALL)
    if not metadata_match:
        return body

    metadata_section = metadata_match.group(1)

    # Remove wikilinks: [[rem-id]] -> rem-id
    cleaned_section = re.sub(r'\[\[([^\]]+)\]\]', r'\1', metadata_section)

    # Replace in body
    body = body.replace(metadata_section, cleaned_section)

    return body


def insert_rems_section(body: str, rems_section: str) -> str:
    """
    Insert "## Rems Extracted" section after Date/Agent/Domain, before ## Metadata.

    Target position:
        **Date**: ...
        **Agent**: ...
        **Domain**: ...

        ## Rems Extracted  ← Insert HERE
        ...

        ## Metadata
    """
    if not rems_section:
        return body

    # Pattern: Match Date/Agent/Domain block, capture until next ##
    pattern = r'(\*\*Date\*\*:.*?\*\*Agent\*\*:.*?\*\*Domain\*\*:.*?\n)\n(## )'

    replacement = rf'\1\n{rems_section}\n\n\2'

    updated_body = re.sub(pattern, replacement, body, count=1, flags=re.DOTALL)

    return updated_body


def repair_chat_file(chat_file: Path, kb_root: Path, dry_run: bool = True) -> Dict:
    """
    Repair a single chat file.

    Returns dict with status and changes.
    """
    result = {
        'file': str(chat_file.relative_to(chat_file.parent.parent.parent)),
        'status': 'unchanged',
        'changes': [],
        'errors': []
    }

    try:
        # Read file
        with open(chat_file, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Extract Rem IDs from frontmatter
        rem_ids = extract_rems_from_frontmatter(original_content)

        if not rem_ids:
            result['status'] = 'skipped'
            result['changes'].append('No Rems extracted')
            return result

        # Find Rem files
        rem_files = []
        for rem_id in rem_ids:
            rem_file = find_rem_file_by_id(rem_id, kb_root)
            if rem_file:
                rem_files.append(str(rem_file))
            else:
                result['errors'].append(f"Rem file not found: {rem_id}")

        if not rem_files:
            result['status'] = 'error'
            result['errors'].append('No Rem files found')
            return result

        # Build Rem metadata
        rem_metadata = build_rem_metadata(str(chat_file), rem_files)

        # Generate new Rems section
        new_rems_section = generate_rems_section(rem_metadata)

        # Extract frontmatter and body
        fm_match = re.match(r'^(---\n.*?\n---\n)(.*)$', original_content, re.DOTALL)
        if not fm_match:
            result['status'] = 'error'
            result['errors'].append('No frontmatter found')
            return result

        frontmatter = fm_match.group(1)
        body = fm_match.group(2)

        # Apply fixes
        modified_body = body

        # 1. Remove old Rems/Extracted Concepts sections
        modified_body = remove_old_rems_section(modified_body)
        result['changes'].append('Removed old Rems section')

        # 2. Remove wikilinks from Metadata section
        modified_body = remove_metadata_wikilinks(modified_body)
        result['changes'].append('Cleaned Metadata section wikilinks')

        # 3. Insert new Rems section
        modified_body = insert_rems_section(modified_body, new_rems_section)
        result['changes'].append(f'Inserted new Rems section ({len(rem_metadata)} Rems)')

        # Reconstruct content
        new_content = frontmatter + modified_body

        # Check if actually changed
        if new_content == original_content:
            result['status'] = 'unchanged'
            result['changes'] = ['No changes needed']
            return result

        # Write if not dry-run
        if not dry_run:
            with open(chat_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            result['status'] = 'repaired'
        else:
            result['status'] = 'would_repair'

    except Exception as e:
        result['status'] = 'error'
        result['errors'].append(str(e))

    return result


def main():
    parser = argparse.ArgumentParser(description='Repair chat Rems sections')
    parser.add_argument('--input', required=True, help='Input directory (chats/)')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    parser.add_argument('--execute', action='store_true', help='Execute repairs')

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("❌ Must specify either --dry-run or --execute")
        sys.exit(1)

    dry_run = args.dry_run

    # Paths
    chat_dir = Path(args.input)
    kb_root = Path(__file__).parent.parent.parent / "knowledge-base"

    if not chat_dir.exists():
        print(f"❌ Chat directory not found: {chat_dir}")
        sys.exit(1)

    # Find all chat files (exclude templates)
    chat_files = [f for f in chat_dir.rglob("*.md") if "_templates" not in str(f)]

    print(f"{'🔍 DRY-RUN MODE' if dry_run else '🚀 EXECUTE MODE'}")
    print(f"Found {len(chat_files)} chat files\n")

    # Repair each file
    results = []
    for chat_file in sorted(chat_files):
        result = repair_chat_file(chat_file, kb_root, dry_run=dry_run)
        results.append(result)

        # Print progress
        status_emoji = {
            'repaired': '✅',
            'would_repair': '🔧',
            'unchanged': '⏭️',
            'skipped': '⏭️',
            'error': '❌'
        }
        emoji = status_emoji.get(result['status'], '❓')

        print(f"{emoji} {result['file']}")
        if result['changes']:
            for change in result['changes']:
                print(f"    • {change}")
        if result['errors']:
            for error in result['errors']:
                print(f"    ⚠️  {error}")

    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)

    status_counts = {}
    for result in results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    for status, count in sorted(status_counts.items()):
        print(f"{status.upper()}: {count}")

    if dry_run:
        print("\n💡 Run with --execute to apply changes")


if __name__ == "__main__":
    main()
