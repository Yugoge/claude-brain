#!/usr/bin/env python3
"""
Run review session with comprehensive timeline view.

Usage:
    source venv/bin/activate && python scripts/review/run_review.py              # Default: show timeline + due Rems
    source venv/bin/activate && python scripts/review/run_review.py --timeline   # Show timeline only (no filtering)
    source venv/bin/activate && python scripts/review/run_review.py --blind      # Blind mode (minimal output, only paths/IDs)
    source venv/bin/activate && python scripts/review/run_review.py --days 14    # Timeline with 14-day lookahead
    source venv/bin/activate && python scripts/review/run_review.py --format m   # Force multiple-choice format
    source venv/bin/activate && python scripts/review/run_review.py --lang zh    # Force Chinese dialogue
    source venv/bin/activate && python scripts/review/run_review.py finance      # Domain-specific review
    source venv/bin/activate && python scripts/review/run_review.py [[rem-id]]   # Specific Rem review

Format codes: m=multiple-choice, c=cloze, s=short-answer, p=problem-solving
Language codes: zh=Chinese, en=English, fr=French

Blind mode: Outputs only Rem ID and path (no title/domain/fsrs_state). Used by main agent to prevent
bypassing review-master subagent consultation. Only review-master should see full Rem data.
"""
import sys
sys.path.append('scripts/review')
sys.path.append('scripts/utilities')
from review_loader import ReviewLoader
from review_scheduler import ReviewScheduler
from review_stats_lib import ReviewStats
from datetime import datetime
import subprocess
import json
from pathlib import Path

# Resolve actual content path, preferring .md with .rem.md fallback
# This prevents failures when some Rems still use the legacy .rem.md extension
# Example targets:
# - knowledge-base/language/etymology.md
# - knowledge-base/language/etymology.rem.md

def resolve_content_path(domain: str, rem_id: str) -> str:
    """
    Resolve the actual path to a Rem file by searching recursively.
    Handles files with numeric prefixes and subdomain insertion.
    Examples:
      rem_id: fx-pricing-shift-types
      filename: 041-fx-derivatives-pricing-shift-types.md (subdomain inserted)
    Prefers .md extension, falls back to .rem.md for legacy files.
    """
    kb_root = Path("knowledge-base")

    # Extract potential parts for flexible matching
    # rem_id may be missing subdomain that appears in filename
    # Strategy: Search by substring after removing common delimiters
    rem_id_parts = rem_id.replace('-', ' ').split()

    # Pattern priority:
    # 1. Exact match with optional numeric prefix: NNN-{rem_id}.md
    # 2. Exact match without prefix: {rem_id}.md
    # 3. Filename contains all words from rem_id (handles subdomain insertion)
    patterns = [
        f"**/*-{rem_id}.md",     # Match: 041-fx-pricing-shift-types.md
        f"**/{rem_id}.md",        # Match: fx-pricing-shift-types.md
        f"**/*{rem_id}*.md",      # Match: any file containing rem_id
    ]

    for pattern in patterns:
        matches = list(kb_root.glob(pattern))
        if matches:
            # Prefer domain match, then shortest path
            domain_matches = [m for m in matches if domain in str(m)]
            if domain_matches:
                return str(sorted(domain_matches, key=lambda x: len(str(x)))[0])
            # Fall back to first match
            return str(matches[0])

    # Fallback: Fuzzy match by checking if filename contains most rem_id parts
    # Example: rem_id "fx-greeks-delta-vs-fxdelta" matches "040-fx-derivatives-delta-vs-fxdelta.md"
    # (greeks→derivatives substitution)
    # Require at least 70% of parts to match (handles subdomain/category swaps)
    domain_pattern = f"{domain}/*.md" if domain and '/' not in domain else "**/*.md"
    all_md_files = list(kb_root.glob(domain_pattern))
    # Filter by domain if pattern was too broad
    if '/' in domain:
        all_md_files = [f for f in all_md_files if domain in str(f)]
    for md_file in all_md_files:
        filename_lower = md_file.stem.lower()
        matching_parts = sum(1 for part in rem_id_parts if part in filename_lower)
        match_ratio = matching_parts / len(rem_id_parts) if rem_id_parts else 0
        # Require 70% match + domain match
        if match_ratio >= 0.7:
            return str(md_file)

    # Legacy .rem.md extension (same logic)
    for pattern in [f"**/*-{rem_id}.rem.md", f"**/{rem_id}.rem.md", f"**/*{rem_id}*.rem.md"]:
        matches = list(kb_root.glob(pattern))
        if matches:
            domain_matches = [m for m in matches if domain in str(m)]
            if domain_matches:
                return str(sorted(domain_matches, key=lambda x: len(str(x)))[0])
            return str(matches[0])

    # File not found - return expected path for error reporting
    return str(kb_root / domain / f"{rem_id}.md")

# Ensure schedule populated
subprocess.run(['python3', 'scripts/utilities/scan-and-populate-rems.py'], capture_output=True)

# Initialize
loader = ReviewLoader()
scheduler = ReviewScheduler()
stats = ReviewStats()

# Parse args
args = sys.argv[1:] if len(sys.argv) > 1 else []

# Check for special flags
timeline_only = '--timeline' in args
blind_mode = '--blind' in args  # Minimal output for main agent (only paths/IDs)
future_days = 7  # Default lookahead
format_preference = None
lang_preference = None

# Extract --days parameter if present
if '--days' in args:
    days_index = args.index('--days')
    if days_index + 1 < len(args):
        try:
            future_days = int(args[days_index + 1])
            args = [a for a in args if a not in ['--days', str(future_days)]]
        except ValueError:
            print("Error: --days must be followed by a number")
            sys.exit(1)

# Extract --format parameter if present
if '--format' in args:
    format_index = args.index('--format')
    if format_index + 1 < len(args):
        format_code = args[format_index + 1]
        # Validate format code
        format_map = {
            'm': 'multiple-choice',
            'c': 'cloze',
            's': 'short-answer',
            'p': 'problem-solving'
        }
        if format_code in format_map:
            format_preference = format_map[format_code]
            args = [a for a in args if a not in ['--format', format_code]]
        else:
            print(f"Error: Invalid format code '{format_code}'. Valid codes: m, c, s, p")
            sys.exit(1)
    else:
        print("Error: --format must be followed by a format code (m, c, s, p)")
        sys.exit(1)

# Extract --lang parameter if present
if '--lang' in args:
    lang_index = args.index('--lang')
    if lang_index + 1 < len(args):
        lang_code = args[lang_index + 1]
        # Validate language code
        valid_langs = ['zh', 'en', 'fr']
        if lang_code in valid_langs:
            lang_preference = lang_code
            args = [a for a in args if a not in ['--lang', lang_code]]
        else:
            print(f"Error: Invalid language code '{lang_code}'. Valid codes: zh, en, fr")
            sys.exit(1)
    else:
        print("Error: --lang must be followed by a language code (zh, en, fr)")
        sys.exit(1)

# Remove special flags from args for loader
args = [a for a in args if a not in ['--timeline', '--blind']]

criteria = loader.parse_arguments(args)

# Load schedule - it returns the full schedule dict
with open('.review/schedule.json', 'r', encoding='utf-8') as f:
    schedule_data = json.load(f)

# Convert to list format for filtering
schedule = []
missing_files = []
for rem_id, rem_data in schedule_data.get('concepts', {}).items():
    path = resolve_content_path(rem_data.get('domain', ''), rem_id)

    # Validate file exists before adding to schedule
    if not Path(path).exists():
        missing_files.append({
            'id': rem_id,
            'title': rem_data.get('title', rem_id),
            'path': path
        })
        continue

    rem = {
        'id': rem_id,
        'title': rem_data.get('title', rem_id),
        'domain': rem_data.get('domain', ''),
        'path': path,
        'fsrs_state': rem_data.get('fsrs_state', {}),
        'created': rem_data.get('created'),
        'last_modified': rem_data.get('last_modified'),
        'conversation_source': rem_data.get('source')  # Extract from schedule.json (optional field)
    }
    schedule.append(rem)

# Warn about missing files (non-fatal)
if missing_files:
    print(f"\n⚠️  Warning: {len(missing_files)} Rem file(s) missing:")
    for mf in missing_files[:5]:  # Show max 5
        print(f"   - {mf['id']} ({mf['path']})")
    if len(missing_files) > 5:
        print(f"   ... and {len(missing_files) - 5} more")
    print(f"\nThese Rems will be skipped. Run /maintain to clean up schedule.\n")

# Filter based on mode
today = datetime.now().strftime('%Y-%m-%d')
if criteria['mode'] == 'automatic':
    # Filter for rems due today OR overdue (next_review <= today)
    # Fixed: Changed == to <= to include accumulated overdue Rems
    # Root cause: commit b86de74 only considered 'due today', not overdue
    rems = [r for r in schedule if r.get('fsrs_state', {}).get('next_review') <= today]
elif criteria['mode'] == 'domain':
    domain_query = criteria['domain'].lower()
    # Domain filtering with hierarchical matching support
    # Supports: "finance", "language", "02-arts-and-humanities", full paths, etc.
    rems = [r for r in schedule
            if domain_query in r.get('domain', '').lower() or
               any(domain_query in part for part in r.get('domain', '').lower().split('/'))]
elif criteria['mode'] == 'specific':
    rem_id = criteria['rem_id']
    rems = [r for r in schedule if r.get('id') == rem_id]
else:
    # Default to all due today OR overdue (next_review <= today)
    # Fixed: Changed == to <= to include accumulated overdue Rems
    rems = [r for r in schedule if r.get('fsrs_state', {}).get('next_review') <= today]

# ALWAYS show comprehensive timeline first
timeline = stats.format_timeline(schedule_data, 'fsrs', today, future_days)
print(timeline)
print()

# If timeline-only mode, exit here
if timeline_only:
    sys.exit(0)

# Otherwise, continue with filtered review session
print("=" * 60)
print("REVIEW SESSION")
print("=" * 60)
print()

# Display filtered overview
by_domain = loader.group_by_domain(rems)
sorted_rems = loader.sort_by_relation_and_urgency(rems, scheduler)

# Apply batch limit to prevent token overflow (max 20 Rems per session)
BATCH_LIMIT = 20
total_rems = len(sorted_rems)
sorted_rems_limited = sorted_rems[:BATCH_LIMIT]
has_more = total_rems > BATCH_LIMIT

overview = stats.format_overview(sorted_rems_limited, by_domain, 'fsrs', today)
print(overview)

# Warn if batch limit reached
if has_more:
    print(f"\n📊 Batch Limit: Showing first {BATCH_LIMIT} of {total_rems} Rems")
    print(f"   (Remaining {total_rems - BATCH_LIMIT} will appear in next session)")
    print(f"   Tip: Review regularly to avoid accumulation.\n")

# Load format history for session continuity (tracks question formats to ensure variety)
# Root cause fix: commit 3ed6b6f added format tracking but didn't persist across stateless architecture
# Solution: External state file tracks format_history, main agent reads and passes to review-master
format_history_file = Path('.review/format_history.json')
format_history = []
if format_history_file.exists():
    try:
        with open(format_history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
            # Load recent formats (last 5 for session diversity)
            # Extract just format strings for review-master consumption
            recent_formats = history_data.get('recent_formats', [])[-5:]
            format_history = [f['format'] if isinstance(f, dict) else f for f in recent_formats]
    except (json.JSONDecodeError, IOError):
        format_history = []

# Output JSON for agent to use
if blind_mode:
    # Blind mode: Only output minimal data (paths and IDs)
    # Main agent CANNOT see title/domain/fsrs_state to prevent bypassing review-master
    blind_rems = [
        {
            'id': r['id'],
            'path': r['path']
        }
        for r in sorted_rems_limited
    ]
    output = {
        'mode': criteria['mode'],
        'total': total_rems,
        'showing': len(sorted_rems_limited),
        'has_more': has_more,
        'rems': blind_rems,
        'format_history': format_history,
        'format_preference': format_preference,
        'lang_preference': lang_preference,
        'blind': True  # Flag indicating blind mode active
    }
else:
    # Full mode: Output all data (for review-master subagent)
    output = {
        'mode': criteria['mode'],
        'total': total_rems,
        'showing': len(sorted_rems_limited),
        'has_more': has_more,
        'rems': sorted_rems_limited,
        'by_domain': {k: len(v) for k, v in by_domain.items()},
        'format_history': format_history,
        'format_preference': format_preference,
        'lang_preference': lang_preference,
        'blind': False
    }

print(f"\n--- DATA ---")
print(json.dumps(output, indent=2))