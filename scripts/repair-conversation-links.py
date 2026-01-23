#!/usr/bin/env python3
"""
Repair broken conversation links in Rems.

Root cause (commit 4f4ba1b): Path resolution issues stripped too much from relative paths.
This script detects and fixes all broken conversation links in parallel.
"""

import argparse
import json
import sys
import yaml
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime

# Add scripts directory to path for imports
sys.path.append(str(Path(__file__).parent))

def load_rem(rem_path: Path) -> Dict:
    """Load a Rem file and extract its metadata."""
    try:
        with open(rem_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract YAML frontmatter
        if content.startswith('---'):
            yaml_end = content.find('---', 3)
            if yaml_end > 0:
                yaml_content = content[3:yaml_end].strip()
                metadata = yaml.safe_load(yaml_content) or {}
                return {
                    'path': rem_path,
                    'metadata': metadata,
                    'content': content[yaml_end+3:].strip(),
                    'full_content': content
                }
    except Exception as e:
        print(f"Error loading {rem_path}: {e}")

    return None


def resolve_conversation_path(rem_path: Path, conversation_source: str) -> Path:
    """Resolve the conversation path from Rem metadata."""
    if not conversation_source:
        return None

    # Handle absolute paths
    if conversation_source.startswith('/'):
        return Path(conversation_source)

    # Handle relative paths (../../../../chats/...)
    if conversation_source.startswith('..'):
        # Navigate from the Rem's directory
        base = rem_path.parent
        parts = conversation_source.split('/')

        for part in parts:
            if part == '..':
                base = base.parent
            elif part and part != '.':
                base = base / part

        return base

    # Handle simple paths (chats/...)
    return Path.cwd() / conversation_source


def find_correct_conversation(rem_data: Dict, chats_dir: Path) -> Optional[str]:
    """Find the correct conversation for a Rem based on content matching."""
    rem_title = rem_data['metadata'].get('title', '')
    rem_created = rem_data['metadata'].get('created', '')
    rem_subdomain = rem_data['metadata'].get('subdomain', '')

    # Search strategy:
    # 1. Look for conversations on the same date
    # 2. Match by title keywords
    # 3. Match by subdomain

    best_match = None
    best_score = 0

    # Parse date from rem_created (YYYY-MM-DD format)
    year_month = None
    if rem_created:
        try:
            date_parts = rem_created.split('-')
            if len(date_parts) >= 2:
                year_month = f"{date_parts[0]}-{date_parts[1]}"
        except:
            pass

    # Search in the appropriate month directory
    search_dirs = []
    if year_month:
        month_dir = chats_dir / year_month
        if month_dir.exists():
            search_dirs.append(month_dir)

    # Also search recent months as fallback
    for month_dir in sorted(chats_dir.glob("*-*"), reverse=True)[:3]:
        if month_dir not in search_dirs:
            search_dirs.append(month_dir)

    for search_dir in search_dirs:
        for conv_file in search_dir.glob("*.md"):
            score = 0

            # Check filename for keyword matches
            conv_name = conv_file.stem.lower()
            title_lower = rem_title.lower()

            # Check for subdomain match
            if rem_subdomain and rem_subdomain.lower() in conv_name:
                score += 10

            # Check for title keywords
            title_words = re.findall(r'\w+', title_lower)
            for word in title_words:
                if len(word) > 3 and word in conv_name:
                    score += 5

            # Check date match
            if rem_created and rem_created in conv_file.stem:
                score += 20

            # If we have a good match, check content
            if score > 10:
                try:
                    with open(conv_file, 'r', encoding='utf-8') as f:
                        conv_content = f.read()[:5000].lower()  # Check first 5000 chars

                    # Check if rem title appears in conversation
                    if title_lower in conv_content:
                        score += 15

                    # Check for specific keywords from rem content
                    rem_text = rem_data['content'][:500].lower()
                    important_words = re.findall(r'\b[a-z]{4,}\b', rem_text)[:10]
                    matches = sum(1 for word in important_words if word in conv_content)
                    score += matches * 2

                except:
                    pass

            if score > best_score:
                best_score = score
                best_match = conv_file

    # Only return if we have a confident match
    if best_score >= 20:
        # Convert to relative path from rem location
        rem_path = rem_data['path']
        rel_path = Path('..') / '..' / '..' / '..' / best_match.relative_to(Path.cwd())
        return str(rel_path).replace('\\', '/')

    return None


def repair_rem(rem_path: Path, dry_run: bool = False) -> Dict:
    """Repair a single Rem's conversation link."""
    result = {
        'rem': str(rem_path),
        'status': 'unchanged',
        'original_source': None,
        'new_source': None,
        'error': None
    }

    # Load the Rem
    rem_data = load_rem(rem_path)
    if not rem_data:
        result['status'] = 'error'
        result['error'] = 'Failed to load Rem'
        return result

    # Get conversation source
    conversation_source = rem_data['metadata'].get('source', '')
    result['original_source'] = conversation_source

    if not conversation_source:
        result['status'] = 'no_source'
        return result

    # Check if it's the template
    if 'YYYY-MM' in conversation_source:
        result['status'] = 'template'
        return result

    # Resolve the path
    resolved_path = resolve_conversation_path(rem_path, conversation_source)

    # Check if the file exists
    if resolved_path and resolved_path.exists():
        result['status'] = 'valid'
        return result

    # File doesn't exist - try to find the correct one
    chats_dir = Path.cwd() / 'chats'
    correct_source = find_correct_conversation(rem_data, chats_dir)

    if correct_source:
        result['new_source'] = correct_source
        result['status'] = 'fixed'

        if not dry_run:
            # Update the Rem file
            try:
                rem_data['metadata']['source'] = correct_source

                # Rebuild the file content
                yaml_str = yaml.dump(rem_data['metadata'], default_flow_style=False, allow_unicode=True)
                new_content = f"---\n{yaml_str}---\n{rem_data['content']}"

                with open(rem_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

            except Exception as e:
                result['status'] = 'error'
                result['error'] = str(e)
    else:
        result['status'] = 'orphaned'

    return result


def main():
    parser = argparse.ArgumentParser(description='Repair broken conversation links in Rems')
    parser.add_argument('--workers', type=int, default=20, help='Number of parallel workers')
    parser.add_argument('--dry-run', action='store_true', help='Simulate repairs without modifying files')
    parser.add_argument('--report-path', type=str, default='docs/dev/repair-report.json',
                       help='Path for the repair report')
    args = parser.parse_args()

    # Find all Rem files (exclude README, INDEX, and non-Rem files)
    kb_dir = Path.cwd() / 'knowledge-base'
    all_md_files = kb_dir.rglob('*.md')
    rem_files = [
        f for f in all_md_files
        if f.name not in ['README.md', 'INDEX.md', 'index.md', 'rem-template.md']
        and 'INDEX' not in f.name.upper()
        and 'README' not in f.name.upper()
        and '-index.md' not in f.name  # Exclude numbered index files like 001-index.md
        and '_templates' not in str(f)
        and '_taxonomy' not in str(f)
        and '_index' not in str(f)
    ]

    print(f"Found {len(rem_files)} Rem files to check")
    print(f"Using {args.workers} parallel workers")
    if args.dry_run:
        print("DRY RUN - no files will be modified")

    # Process in parallel
    results = []
    fixed_count = 0
    orphaned_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(repair_rem, rem, args.dry_run): rem for rem in rem_files}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            if result['status'] == 'fixed':
                fixed_count += 1
                print(f"✅ Fixed: {result['rem']}")
            elif result['status'] == 'orphaned':
                orphaned_count += 1
                print(f"❌ Orphaned: {result['rem']}")
            elif result['status'] == 'error':
                error_count += 1
                print(f"⚠️ Error: {result['rem']} - {result['error']}")

    # Generate report
    report = {
        'timestamp': datetime.now().isoformat(),
        'dry_run': args.dry_run,
        'total_rems': len(rem_files),
        'fixed': fixed_count,
        'orphaned': orphaned_count,
        'errors': error_count,
        'valid': len([r for r in results if r['status'] == 'valid']),
        'no_source': len([r for r in results if r['status'] == 'no_source']),
        'template': len([r for r in results if r['status'] == 'template']),
        'details': results
    }

    # Save report
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "="*60)
    print("REPAIR SUMMARY")
    print("="*60)
    print(f"Total Rems checked: {len(rem_files)}")
    print(f"✅ Fixed: {fixed_count}")
    print(f"❌ Orphaned (no match found): {orphaned_count}")
    print(f"⚠️ Errors: {error_count}")
    print(f"✓ Already valid: {report['valid']}")
    print(f"- No source field: {report['no_source']}")
    print(f"- Template files: {report['template']}")
    print(f"\nReport saved to: {report_path}")

    return 0 if error_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())