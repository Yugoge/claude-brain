#!/usr/bin/env python3
"""
Validate Rem Token Size Compliance

Checks that all Rems comply with Story 1.10 minimal format standards:
- Target: 150-200 tokens per Rem
- Maximum: 250 tokens (hard limit with warning)
- Reports violations and provides remediation guidance

Usage:
    python3 scripts/validate-rem-size.py [path]

    If no path provided, scans entire knowledge-base/ directory
"""

import os
import sys
import glob
import argparse
from pathlib import Path
from typing import List, Tuple, Dict

# Token estimation constants
CHARS_PER_TOKEN = 3  # Rough estimate: ~3 characters = 1 token

# Thresholds
TOKEN_TARGET_MIN = 150
TOKEN_TARGET_MAX = 200
TOKEN_HARD_LIMIT = 250

def estimate_tokens(text: str) -> int:
    """Estimate token count based on character count"""
    return len(text) // CHARS_PER_TOKEN

def parse_rem_file(file_path: str) -> Dict:
    """Parse Rem file and extract metadata"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    token_count = estimate_tokens(content)

    # Extract rem_id from frontmatter
    rem_id = None
    if '---' in content:
        frontmatter = content.split('---')[1]
        for line in frontmatter.split('\n'):
            if line.strip().startswith('rem_id:'):
                rem_id = line.split(':', 1)[1].strip()
                break

    return {
        'path': file_path,
        'rem_id': rem_id or Path(file_path).stem,
        'token_count': token_count,
        'char_count': len(content),
        'compliant': TOKEN_TARGET_MIN <= token_count <= TOKEN_TARGET_MAX,
        'over_hard_limit': token_count > TOKEN_HARD_LIMIT
    }

def scan_rems(base_path: str) -> List[Dict]:
    """Scan all Rem files in knowledge-base"""
    pattern = os.path.join(base_path, '**', '*.md')
    rem_files = glob.glob(pattern, recursive=True)

    # Exclude backup directories
    rem_files = [f for f in rem_files if '.backup-' not in f]

    results = []
    for file_path in rem_files:
        # Skip session files and templates
        if '/sessions/' in file_path or '/_templates/' in file_path:
            continue

        try:
            result = parse_rem_file(file_path)
            results.append(result)
        except Exception as e:
            print(f"⚠️  Error parsing {file_path}: {e}", file=sys.stderr)

    return results

def print_report(results: List[Dict]):
    """Print validation report"""
    total = len(results)
    compliant = sum(1 for r in results if r['compliant'])
    over_limit = sum(1 for r in results if r['over_hard_limit'])

    print("=" * 70)
    print("📊 REM SIZE VALIDATION REPORT (Story 1.10 Compliance)")
    print("=" * 70)
    print()

    print(f"Total Rems scanned: {total}")
    print(f"✅ Compliant (150-200 tokens): {compliant} ({compliant/total*100:.1f}%)")
    print(f"⚠️  Non-compliant: {total - compliant} ({(total-compliant)/total*100:.1f}%)")
    print(f"❌ Over hard limit (>250 tokens): {over_limit}")
    print()

    if total - compliant > 0:
        print("-" * 70)
        print("VIOLATIONS:")
        print("-" * 70)

        violations = [r for r in results if not r['compliant']]
        violations.sort(key=lambda x: x['token_count'], reverse=True)

        for r in violations:
            status = "❌ CRITICAL" if r['over_hard_limit'] else "⚠️  WARNING"
            print(f"{status} {r['rem_id']}")
            print(f"  Path: {r['path']}")
            print(f"  Tokens: {r['token_count']} (target: 150-200, limit: 250)")
            print(f"  Characters: {r['char_count']}")

            if r['token_count'] < TOKEN_TARGET_MIN:
                print(f"  ⬆️  Action: Add more core facts or context")
            else:
                print(f"  ⬇️  Action: Reduce to minimal format (see learning-materials/_templates/minimal-rem-template.md)")
            print()

    print("-" * 70)
    print("STORY 1.10 MINIMAL FORMAT REQUIREMENTS:")
    print("-" * 70)
    print("✅ INCLUDE (Essential):")
    print("  - 3-5 core memory points (~50 tokens)")
    print("  - User's actual mistake (~20 tokens)")
    print("  - Usage scenario (1 sentence, ~20 tokens)")
    print("  - Related concepts WITH reasons (~30 tokens)")
    print("  - Metadata (learning_audit, mastery, ~50 tokens)")
    print()
    print("❌ EXCLUDE (Move to session transcript):")
    print("  - Extended explanations")
    print("  - Multiple example variations")
    print("  - Detailed memory techniques")
    print("  - Complete dialogue transcripts")
    print("  - Q&A sections")
    print()
    print("📖 Reference: learning-materials/_templates/minimal-rem-template.md")
    print("=" * 70)

    # Exit code: 0 if all compliant, 1 if violations, 2 if critical violations
    if over_limit > 0:
        sys.exit(2)
    elif total - compliant > 0:
        sys.exit(1)
    else:
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(
        description='Validate Rem token size compliance with Story 1.10 standards'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='knowledge-base',
        help='Path to scan (default: knowledge-base/)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"❌ Error: Path not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    results = scan_rems(args.path)

    if not results:
        print(f"⚠️  No Rem files found in {args.path}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print_report(results)

if __name__ == '__main__':
    main()
