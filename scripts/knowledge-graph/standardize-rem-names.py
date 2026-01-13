#!/usr/bin/env python3
"""
Standardize Rem naming conventions by renaming files and updating all references.

Usage:
    source venv/bin/activate && source venv/bin/activate && python3 scripts/standardize-rem-names.py --domain language/french [--dry-run] [--verbose]
"""

import argparse
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
KB_DIR = ROOT / "knowledge-base"
SCHEDULE_FILE = ROOT / ".review" / "schedule.json"
CHATS_DIR = ROOT / "chats"

# Domain-specific rename maps
# Format: 'old_rem_id': 'new_rem_id'
# Note: For files in subdirectories, the file path will be constructed from the rem_id
# Example: 'sentir-to-smell-to-feel' will search for files named 'sentir-to-smell-to-feel.md'
# or 'sentir-to-smell-to-feel.rem.md' in any subdirectory
RENAME_MAPS = {
    'language/french': {
        'vouloir-verb': 'french-verb-vouloir',
        'avoir-faim-expression': 'french-expression-avoir-faim',
        'il-fait-weather-pattern': 'french-pattern-il-fait',
        'daily-verbs-high-freq': 'french-verbs-high-frequency',
        'family-members-vocab': 'french-vocabulary-family',
        'sentir-to-smell-to-feel': 'french-verb-sentir',
        'le-savon-the-soap': 'french-vocabulary-savon'
    }
}


def find_all_references(old_name, kb_dir, chats_dir):
    """Find all files referencing old_name."""
    refs = []
    pattern = re.compile(rf'\[\[{re.escape(old_name)}\]\]')

    # Search in knowledge base
    for md_file in kb_dir.rglob('*.md'):
        if md_file.name.startswith('_'):
            continue
        try:
            content = md_file.read_text(encoding='utf-8')
            if pattern.search(content):
                refs.append(md_file)
        except Exception:
            pass

    # Search in chat archives
    for md_file in chats_dir.rglob('*.md'):
        try:
            content = md_file.read_text(encoding='utf-8')
            if pattern.search(content):
                refs.append(md_file)
        except Exception:
            pass

    return refs


def update_file_references(file_path, old_name, new_name, dry_run=False):
    """Update all references in a file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        old_pattern = f'[[{old_name}]]'
        new_pattern = f'[[{new_name}]]'

        if old_pattern in content:
            if not dry_run:
                updated = content.replace(old_pattern, new_pattern)
                file_path.write_text(updated, encoding='utf-8')
            return True
    except Exception as e:
        print(f"  ❌ Error updating {file_path}: {e}")
    return False


def update_fsrs_schedule(old_name, new_name, dry_run=False):
    """Update FSRS schedule with renamed Rem ID."""
    if not SCHEDULE_FILE.exists():
        return False

    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            schedule = json.load(f)

        if old_name in schedule.get('concepts', {}):
            if not dry_run:
                # Rename key and update rem_id field
                schedule['concepts'][new_name] = schedule['concepts'].pop(old_name)
                schedule['concepts'][new_name]['rem_id'] = new_name

                # Backup original
                backup_file = SCHEDULE_FILE.with_suffix('.json.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
                shutil.copy2(SCHEDULE_FILE, backup_file)

                with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(schedule, f, indent=2, ensure_ascii=False)
            return True
    except Exception as e:
        print(f"  ❌ Error updating FSRS schedule: {e}")
    return False


def standardize_domain(domain, dry_run=False, verbose=False):
    """Standardize all Rems in a domain."""
    rename_map = RENAME_MAPS.get(domain)
    if not rename_map:
        print(f"❌ No rename map defined for domain: {domain}")
        return

    domain_path = KB_DIR / domain.replace('/', Path('/').as_posix())
    if not domain_path.exists():
        print(f"❌ Domain path not found: {domain_path}")
        return

    print(f"📋 Proposed Renames ({len(rename_map)} files):\n")

    # Preview changes
    stats = {
        'files_renamed': 0,
        'references_updated': 0,
        'fsrs_updated': 0,
        'chats_updated': 0
    }

    for old_name, new_name in rename_map.items():
        # Search for files matching old_name (could be in subdirectories)
        # Try both .md and .rem.md extensions
        old_file_candidates = list(domain_path.rglob(f"{old_name}.md")) + \
                            list(domain_path.rglob(f"{old_name}.rem.md"))

        if not old_file_candidates:
            print(f"  ⏭️  {old_name} - file not found, skipping")
            continue

        if len(old_file_candidates) > 1:
            print(f"  ❌ {old_name} - multiple files found, skipping")
            continue

        old_file = old_file_candidates[0]

        # Determine target location (same directory as old file)
        new_file = old_file.parent / f"{new_name}.md"

        if new_file.exists():
            print(f"  ❌ {old_name} → {new_name} - target already exists!")
            continue

        # Find references
        refs = find_all_references(old_name, KB_DIR, CHATS_DIR)
        kb_refs = [r for r in refs if str(r).startswith(str(KB_DIR))]
        chat_refs = [r for r in refs if str(r).startswith(str(CHATS_DIR))]

        print(f"{stats['files_renamed'] + 1}. {old_name} → {new_name}")
        print(f"   - File: {old_file.relative_to(KB_DIR)}")
        print(f"   - Target: {new_file.relative_to(KB_DIR)}")
        print(f"   - Referenced by: {len(kb_refs)} Rems, {len(chat_refs)} conversations")

        # Check FSRS schedule
        has_fsrs = False
        if SCHEDULE_FILE.exists():
            try:
                with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
                    schedule = json.load(f)
                has_fsrs = old_name in schedule.get('concepts', {})
            except Exception:
                pass
        print(f"   - FSRS entry: {'Yes' if has_fsrs else 'No'}")

        if verbose:
            if kb_refs:
                print(f"     KB refs: {', '.join(r.stem for r in kb_refs[:3])}")
            if chat_refs:
                print(f"     Chat refs: {', '.join(r.stem for r in chat_refs[:3])}")

        # Execute rename
        if not dry_run:
            # 1. Rename file
            old_file.rename(new_file)
            stats['files_renamed'] += 1

            # 2. Update references in other files
            for ref_file in refs:
                if update_file_references(ref_file, old_name, new_name):
                    if str(ref_file).startswith(str(KB_DIR)):
                        stats['references_updated'] += 1
                    else:
                        stats['chats_updated'] += 1

            # 3. Update FSRS schedule
            if update_fsrs_schedule(old_name, new_name):
                stats['fsrs_updated'] += 1

    print("\n" + "=" * 63)

    if dry_run:
        print("🔍 DRY RUN - No changes made")
    else:
        print("✅ Batch Rename Completed\n")
        print(f"📝 Renamed Files: {stats['files_renamed']}")
        print(f"🔗 Updated References:")
        print(f"  - {stats['references_updated']} wikilinks in Rems")
        print(f"  - {stats['chats_updated']} references in conversations")
        print(f"  - {stats['fsrs_updated']} FSRS schedule entries")
        print(f"\n📊 Next: Run 'python3 scripts/rebuild-backlinks.py' to update index")


def main():
    parser = argparse.ArgumentParser(description='Standardize Rem naming conventions')
    parser.add_argument('--domain', required=True, help='Domain to process (e.g., language/french)')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without executing')
    parser.add_argument('--verbose', action='store_true', help='Show detailed reference information')

    args = parser.parse_args()

    standardize_domain(args.domain, dry_run=args.dry_run, verbose=args.verbose)


if __name__ == '__main__':
    main()
