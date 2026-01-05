#!/usr/bin/env python3
"""
Fix Non-Standard Relation Types in Knowledge Base

Batch correction of existing non-standard relation types in knowledge base.
Corrections are based on semantic equivalence to standard types.

Usage:
    python scripts/fix-nonstandard-relation-types.py [--dry-run] [--report]

Options:
    --dry-run    Preview changes without writing to files
    --report     Output detailed change report to file

Exit codes:
    0 - Success (all non-standard types corrected)
    1 - Error during execution
    2 - Non-standard types found (dry-run mode)
"""

import json
import sys
import argparse
import re
from pathlib import Path
from collections import defaultdict

# Add scripts to path
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT / "scripts"))

from archival.relation_types import ALL_TYPES

# Correction mapping (non-standard -> standard)
CORRECTIONS = {
    'related': 'related_to',  # Common typo (65 instances)
    'quantitative-formula': 'defines',  # AI invented
    'provides_evidence_for': 'uses',  # AI invented
    'supported_by': 'used_by',  # AI invented
}


def load_backlinks():
    """Load backlinks.json"""
    backlinks_path = ROOT / 'knowledge-base/_index/backlinks.json'
    with open(backlinks_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_non_standard_relations(backlinks_data):
    """
    Find all non-standard relation types in backlinks.

    Returns:
        dict: {concept_id: [(target, type, corrected_type), ...]}
    """
    links = backlinks_data.get('links', {})
    non_standard = defaultdict(list)

    for concept_id, data in links.items():
        for rel in data.get('typed_links_to', []):
            rel_type = rel.get('type')
            target = rel.get('to')

            if rel_type and rel_type not in ALL_TYPES:
                corrected_type = CORRECTIONS.get(rel_type)
                if corrected_type:
                    non_standard[concept_id].append((target, rel_type, corrected_type))

    return non_standard


def fix_markdown_file(file_path, corrections):
    """
    Fix relation types in a single markdown file.

    Args:
        file_path: Path to Rem markdown file
        corrections: List of (target, old_type, new_type) tuples

    Returns:
        Number of corrections made
    """
    if not file_path.exists():
        print(f"  ⚠️  File not found: {file_path}", file=sys.stderr)
        return 0

    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    corrections_made = 0

    # Fix each relation
    for target, old_type, new_type in corrections:
        # Pattern: [[target]] (old_type) or [[target]](old_type)
        patterns = [
            (rf'\[\[{re.escape(target)}\]\]\s*\({re.escape(old_type)}\)',
             f'[[{target}]] ({new_type})'),
            (rf'\[\[{re.escape(target)}\]\]\({re.escape(old_type)}\)',
             f'[[{target}]]({new_type})'),
        ]

        for pattern, replacement in patterns:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                corrections_made += 1
                break

    # Write back if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    return corrections_made


def rebuild_backlinks():
    """Rebuild backlinks index after fixing markdown files"""
    import subprocess

    result = subprocess.run(
        ['python', 'scripts/knowledge-graph/rebuild-backlinks.py'],
        capture_output=True,
        text=True,
        cwd=ROOT
    )

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description='Fix non-standard relation types in knowledge base',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing files')
    parser.add_argument('--report', type=str, metavar='FILE',
                        help='Output detailed change report to file')

    args = parser.parse_args()

    try:
        print("🔍 Scanning knowledge base for non-standard relation types...\n", file=sys.stderr)

        # Load backlinks
        backlinks_data = load_backlinks()

        # Find non-standard relations
        non_standard = find_non_standard_relations(backlinks_data)

        if not non_standard:
            print("✅ No non-standard relation types found!", file=sys.stderr)
            return 0

        # Count total corrections needed
        total_corrections = sum(len(rels) for rels in non_standard.values())
        print(f"📊 Found {total_corrections} non-standard relations in {len(non_standard)} files\n",
              file=sys.stderr)

        # Group by type for summary
        type_summary = defaultdict(int)
        for rels in non_standard.values():
            for _, old_type, _ in rels:
                type_summary[old_type] += 1

        print("Type breakdown:", file=sys.stderr)
        for old_type, count in sorted(type_summary.items(), key=lambda x: -x[1]):
            new_type = CORRECTIONS.get(old_type, '???')
            print(f"  • {old_type:30s} → {new_type:20s} ({count} instances)", file=sys.stderr)

        if args.dry_run:
            print(f"\n🔍 DRY RUN MODE - No files will be modified\n", file=sys.stderr)
            print("Files that would be updated:", file=sys.stderr)

            for concept_id, rels in sorted(non_standard.items()):
                # Find file path
                file_path = None
                for path in (ROOT / 'knowledge-base').rglob(f'*{concept_id}.md'):
                    file_path = path
                    break

                if file_path:
                    print(f"  • {file_path.relative_to(ROOT)} ({len(rels)} corrections)",
                          file=sys.stderr)

            return 2  # Exit code 2 = non-standard types found

        # Apply fixes
        print(f"\n🔧 Applying corrections...\n", file=sys.stderr)

        total_fixed = 0
        files_updated = 0

        for concept_id, rels in non_standard.items():
            # Find markdown file
            file_path = None
            for path in (ROOT / 'knowledge-base').rglob(f'*{concept_id}.md'):
                file_path = path
                break

            if not file_path:
                print(f"  ⚠️  File not found for: {concept_id}", file=sys.stderr)
                continue

            # Fix file
            fixed = fix_markdown_file(file_path, rels)
            if fixed > 0:
                total_fixed += fixed
                files_updated += 1
                print(f"  ✓ {file_path.relative_to(ROOT)}: {fixed} corrections", file=sys.stderr)

        # Rebuild backlinks
        print(f"\n🔄 Rebuilding backlinks index...", file=sys.stderr)
        if rebuild_backlinks():
            print(f"  ✓ Backlinks rebuilt successfully", file=sys.stderr)
        else:
            print(f"  ⚠️  Failed to rebuild backlinks - run manually", file=sys.stderr)

        # Output report
        if args.report:
            report_data = {
                'summary': {
                    'total_corrections': total_fixed,
                    'files_updated': files_updated,
                    'type_breakdown': dict(type_summary)
                },
                'corrections': {
                    concept_id: [
                        {'target': target, 'old_type': old_type, 'new_type': new_type}
                        for target, old_type, new_type in rels
                    ]
                    for concept_id, rels in non_standard.items()
                }
            }

            report_path = Path(args.report)
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            print(f"\n📄 Report saved to: {report_path}", file=sys.stderr)

        print(f"\n✅ Complete: {total_fixed} relations corrected in {files_updated} files",
              file=sys.stderr)
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
