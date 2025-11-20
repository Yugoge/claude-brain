#!/usr/bin/env python3
"""
Run review session with comprehensive timeline view.

Usage:
    python3 scripts/review/run_review.py              # Default: show timeline + due Rems
    python3 scripts/review/run_review.py --timeline   # Show timeline only (no filtering)
    python3 scripts/review/run_review.py --days 14    # Timeline with 14-day lookahead
    python3 scripts/review/run_review.py finance      # Domain-specific review
    python3 scripts/review/run_review.py [[rem-id]]   # Specific Rem review
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

    # Fallback: Fuzzy match by checking if filename contains all rem_id parts
    # Example: rem_id "fx-pricing-shift-types" matches "041-fx-derivatives-pricing-shift-types.md"
    all_md_files = list(kb_root.glob("**/*.md"))
    for md_file in all_md_files:
        filename_lower = md_file.stem.lower()
        # Check if all rem_id parts appear in filename (in any order)
        if all(part in filename_lower for part in rem_id_parts):
            if domain in str(md_file):
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
future_days = 7  # Default lookahead

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

# Remove timeline flag from args for loader
args = [a for a in args if a != '--timeline']

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
        'last_modified': rem_data.get('last_modified')
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
    # Filter for rems due today
    rems = [r for r in schedule if r.get('fsrs_state', {}).get('next_review') == today]
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
    # Default to all due today
    rems = [r for r in schedule if r.get('fsrs_state', {}).get('next_review') == today]

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
sorted_rems = loader.sort_by_urgency(rems, scheduler)

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

# Output JSON for agent to use
output = {
    'mode': criteria['mode'],
    'total': total_rems,
    'showing': len(sorted_rems_limited),
    'has_more': has_more,
    'rems': sorted_rems_limited,
    'by_domain': {k: len(v) for k, v in by_domain.items()}
}
print(f"\n--- DATA ---")
print(json.dumps(output, indent=2))