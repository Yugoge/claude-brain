#!/usr/bin/env python3
"""
Clean up prefetch files for a specific review session.

File naming convention: .review/prefetch-{session_id}-{rem_id}.json

Usage:
    source venv/bin/activate && python scripts/review/cleanup_prefetch.py --session-id <uuid>

Exit codes: 0=success, 1=error
"""

import json
import glob
import argparse
from pathlib import Path

REVIEW_DIR = '.review'


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description='Clean up session prefetch files')
    parser.add_argument('--session-id', required=True, help='UUID of the review session')
    return parser.parse_args()


def cleanup(session_id: str):
    """Remove prefetch files for a specific session."""
    pattern = f'{REVIEW_DIR}/prefetch-{session_id}-*.json'
    files = glob.glob(pattern)
    removed = []
    for f in files:
        try:
            Path(f).unlink()
            removed.append(f)
        except OSError as e:
            print(json.dumps({'success': False, 'error': str(e)}))
            return

    print(json.dumps({
        'success': True,
        'session_id': session_id,
        'removed': removed,
        'count': len(removed),
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    args = parse_args()
    cleanup(args.session_id)
