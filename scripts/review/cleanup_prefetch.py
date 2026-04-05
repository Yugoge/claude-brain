#!/usr/bin/env python3
"""
Clean up prefetch files left by the review pipeline.

Removes all .review/prefetch-*.json files. Safe to run anytime.

Usage:
    source venv/bin/activate && python scripts/review/cleanup_prefetch.py
"""

import json
import glob
from pathlib import Path

PREFETCH_PATTERN = '.review/prefetch-*.json'


def cleanup():
    """Remove all prefetch files and report results."""
    files = glob.glob(PREFETCH_PATTERN)
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
        'removed': removed,
        'count': len(removed),
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    cleanup()
