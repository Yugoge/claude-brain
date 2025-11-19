#!/usr/bin/env python3
"""
Add Typed Relations to Rem Files

Reads enriched Rems JSON and appends typed relations to the
"## Related Rems" section of each Rem file.

Usage:
    python scripts/archival/add_typed_relations.py --enriched-rems <file>

Examples:
    # Add relations from enriched_rems.json
    python scripts/archival/add_typed_relations.py --enriched-rems enriched_rems.json

    # Dry run (preview changes)
    python scripts/archival/add_typed_relations.py --enriched-rems enriched_rems.json --dry-run
"""

import json
import argparse
import sys
import re
from pathlib import Path

# Project root
ROOT = Path(__file__).parent.parent.parent


def read_rem_file(file_path: Path) -> str:
    """Read Rem file content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_rem_file(file_path: Path, content: str):
    """Write Rem file content."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def find_related_rems_section(content: str) -> tuple:
    """
    Find the "## Related Rems" section in content.

    Returns:
        (start_pos, end_pos) where:
        - start_pos: index of "## Related Rems" line
        - end_pos: index of next "##" section or end of file

    Returns (None, None) if section not found.
    """
    # Find "## Related Rems" section
    match = re.search(r'^## Related Rems\s*$', content, re.MULTILINE)
    if not match:
        return None, None

    start_pos = match.start()

    # Find next ## section or end of file
    remaining = content[match.end():]
    next_section = re.search(r'^## ', remaining, re.MULTILINE)

    if next_section:
        end_pos = match.end() + next_section.start()
    else:
        end_pos = len(content)

    return start_pos, end_pos


def extract_existing_links(section_content: str) -> set:
    """
    Extract existing wikilinks from Related Rems section.

    Returns set of concept IDs already linked.
    """
    # Match both [[id]] and [Title](path.md) formats
    wikilinks = re.findall(r'\[\[([^\]]+)\]\]', section_content)
    markdown_links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', section_content)

    existing = set(wikilinks)

    # Extract IDs from markdown links (filename without extension)
    for title, path in markdown_links:
        # Extract filename from path
        filename = Path(path).stem
        # Remove numeric prefix if present (e.g., "013-french-vocabulary" -> "french-vocabulary")
        clean_id = re.sub(r'^\d+-', '', filename)
        existing.add(clean_id)

    return existing


def format_typed_relation(to_id: str, rel_type: str) -> str:
    """
    Format a typed relation as a wikilink with relation metadata.

    Returns: "- [[to_id]] {rel: rel_type}"
    """
    return f"- [[{to_id}]] {{rel: {rel_type}}}"


def add_relations_to_rem(file_path: Path, typed_relations: list, dry_run: bool = False) -> dict:
    """
    Add typed relations to a Rem file.

    Returns:
        dict with keys: added, skipped, error
    """
    result = {
        "added": [],
        "skipped": [],
        "error": None
    }

    try:
        content = read_rem_file(file_path)

        # Find Related Rems section
        start_pos, end_pos = find_related_rems_section(content)

        if start_pos is None:
            result["error"] = "No '## Related Rems' section found"
            return result

        # Extract existing links
        section_content = content[start_pos:end_pos]
        existing_links = extract_existing_links(section_content)

        # Prepare new relations to add
        new_relations = []
        for rel in typed_relations:
            to_id = rel['to']
            rel_type = rel['type']

            # Check if already linked (by concept ID)
            if to_id in existing_links:
                result["skipped"].append({
                    "to": to_id,
                    "type": rel_type,
                    "reason": "Already linked"
                })
                continue

            new_relations.append(format_typed_relation(to_id, rel_type))
            result["added"].append({
                "to": to_id,
                "type": rel_type
            })

        # If no new relations, return
        if not new_relations:
            return result

        # Insert new relations at end of Related Rems section
        # Find the last non-empty line in the section
        section_lines = section_content.split('\n')

        # Find insertion point (after last non-empty line)
        insertion_point = end_pos
        for i in range(len(section_lines) - 1, -1, -1):
            if section_lines[i].strip():
                # Found last non-empty line
                # Calculate position in original content
                offset = start_pos + sum(len(l) + 1 for l in section_lines[:i+1])
                insertion_point = offset
                break

        # Build new content
        new_content = (
            content[:insertion_point] +
            '\n' + '\n'.join(new_relations) + '\n' +
            content[insertion_point:]
        )

        # Write file
        if not dry_run:
            write_rem_file(file_path, new_content)

        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def main():
    parser = argparse.ArgumentParser(
        description='Add typed relations to Rem files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--enriched-rems',
        required=True,
        help='Path to enriched_rems.json file'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing files'
    )

    args = parser.parse_args()

    # Load enriched Rems
    enriched_path = Path(args.enriched_rems)
    if not enriched_path.exists():
        print(f"❌ File not found: {enriched_path}", file=sys.stderr)
        return 1

    with open(enriched_path, 'r', encoding='utf-8') as f:
        enriched_rems = json.load(f)

    print(f"✓ Loaded {len(enriched_rems)} enriched Rems")

    # Filter Rems with typed_relations
    rems_with_relations = [
        rem for rem in enriched_rems
        if rem.get('typed_relations')
    ]

    print(f"✓ Found {len(rems_with_relations)} Rems with typed relations")

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be modified\n")

    # Process each Rem
    total_added = 0
    total_skipped = 0
    errors = []

    for rem in rems_with_relations:
        rem_id = rem['id']
        file_path = ROOT / rem['file_path']
        typed_relations = rem['typed_relations']

        if not file_path.exists():
            errors.append(f"File not found: {file_path}")
            continue

        result = add_relations_to_rem(file_path, typed_relations, args.dry_run)

        if result['error']:
            errors.append(f"[[{rem_id}]]: {result['error']}")
            continue

        added_count = len(result['added'])
        skipped_count = len(result['skipped'])

        if added_count > 0:
            status = "📝 [DRY RUN]" if args.dry_run else "✅"
            print(f"{status} [[{rem_id}]]: Added {added_count} relation(s)")
            for rel in result['added']:
                print(f"    + [[{rel['to']}]] {{rel: {rel['type']}}}")

        if skipped_count > 0:
            print(f"⏭️  [[{rem_id}]]: Skipped {skipped_count} (already exists)")

        total_added += added_count
        total_skipped += skipped_count

    # Summary
    print("\n" + "=" * 80)
    print(f"📊 Summary:")
    print(f"   - Rems processed: {len(rems_with_relations)}")
    print(f"   - Relations added: {total_added}")
    print(f"   - Relations skipped: {total_skipped}")

    if errors:
        print(f"\n⚠️  Errors ({len(errors)}):")
        for error in errors:
            print(f"   - {error}")

    if args.dry_run:
        print("\n💡 Run without --dry-run to apply changes")
        return 0

    if total_added > 0:
        print("\n✅ Typed relations added successfully!")
        print("📋 Next steps:")
        print("   1. Run: python scripts/knowledge-graph/rebuild-backlinks.py")
        print("   2. Run: python scripts/knowledge-graph/normalize-links.py --mode replace")
    else:
        print("\n✅ No new relations to add (all existing)")

    return 0


if __name__ == '__main__':
    sys.exit(main())
