#!/usr/bin/env python3
"""
Get Next Rem from Persisted Review Session.

Root cause fix: Session state only in conversation context caused hallucinated
Rem IDs when context was compressed during long 50-Rem sessions.

Multi-session support: Each session uses .review/session-{session_id}.json.

Usage:
    source venv/bin/activate && python scripts/review/get_next_rem.py --session-id <uuid>
    source venv/bin/activate && python scripts/review/get_next_rem.py --session-id <uuid> --cleanup

Exit codes: 0=success, 1=error, 2=session complete
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

SESSION_DIR = Path('.review')
STALE_THRESHOLD_HOURS = 4


def session_file_for(session_id: str) -> Path:
    """Return the session file path for a given session_id."""
    return SESSION_DIR / f'session-{session_id}.json'


def parse_args():
    """Parse CLI arguments for session-id and cleanup."""
    parser = argparse.ArgumentParser(description='Get next Rem from review session')
    parser.add_argument('--session-id', required=True, help='UUID of the review session')
    parser.add_argument('--cleanup', action='store_true', help='Delete session file')
    return parser.parse_args()


def load_session(session_id: str):
    """Load and validate session-{session_id}.json. Returns (session_dict, error_str)."""
    sf = session_file_for(session_id)
    if not sf.exists():
        return None, f"Session file not found: {sf.name}"
    try:
        with open(sf, 'r', encoding='utf-8') as f:
            session = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return None, f"Failed to read session file: {e}"
    required = ['session_id', 'created_at', 'total', 'current_index', 'rems']
    missing = [f for f in required if f not in session]
    if missing:
        return None, f"Invalid session file: missing fields {missing}"
    return session, None


def check_stale(session):
    """Return stale warning dict if session exceeds age threshold."""
    try:
        created = datetime.fromisoformat(session['created_at'])
        age = datetime.now() - created
        hours = round(age.total_seconds() / 3600, 1)
        if age > timedelta(hours=STALE_THRESHOLD_HOURS):
            return {'stale': True, 'age_hours': hours}
    except (ValueError, TypeError):
        pass
    return {'stale': False}


def find_next_pending(rems, start_index):
    """Find next Rem with status=pending starting from index."""
    for i in range(start_index, len(rems)):
        if rems[i].get('status', 'pending') == 'pending':
            return rems[i], i
    return None, None


def count_by_status(rems):
    """Count reviewed and pending Rems. Returns (reviewed, pending)."""
    reviewed = sum(1 for r in rems if r.get('status') == 'reviewed')
    pending = sum(1 for r in rems if r.get('status', 'pending') == 'pending')
    return reviewed, pending


def make_rem_entry(rem):
    """Extract id, path, conversation_source from a Rem dict."""
    return {
        'id': rem['id'],
        'path': rem['path'],
        'conversation_source': rem.get('conversation_source'),
    }


def make_session_meta(session):
    """Extract session-level metadata for output."""
    return {
        'difficulty_mode': session.get('difficulty_mode', 'normal'),
        'format_preference': session.get('format_preference'),
        'lang_preference': session.get('lang_preference'),
        'format_history': session.get('format_history', []),
    }


def build_complete_result(session, reviewed):
    """Build result dict when all Rems are reviewed."""
    msg = f'All {reviewed} Rems reviewed. Session complete.'
    result = {
        'success': True,
        'session_complete': True,
        'session_id': session.get('session_id'),
        'total': session.get('total', 0),
        'reviewed': reviewed,
        'message': msg,
    }
    return result


def build_next_result(session, rem, idx, reviewed, pending):
    """Build result dict for the next pending Rem."""
    result = {
        'success': True,
        'session_complete': False,
        'session_id': session.get('session_id'),
        'rem': make_rem_entry(rem),
        'index': idx,
        'total': session.get('total', 0),
        'reviewed': reviewed,
        'remaining': pending,
    }
    result.update(make_session_meta(session))
    return result


def get_next_rem(session_id: str):
    """Find and return the next pending Rem from session."""
    session, error = load_session(session_id)
    if error:
        return {'success': False, 'error': error}
    rems = session.get('rems', [])
    start = session.get('current_index', 0)
    next_rem, next_idx = find_next_pending(rems, start)
    reviewed, pending = count_by_status(rems)
    if next_rem is None:
        return build_complete_result(session, reviewed)
    result = build_next_result(session, next_rem, next_idx, reviewed, pending)
    stale = check_stale(session)
    if stale.get('stale'):
        result['stale_warning'] = stale
    return result


def cleanup_session(session_id: str):
    """Delete session-{session_id}.json at session end."""
    sf = session_file_for(session_id)
    if not sf.exists():
        return {'success': True, 'message': f'No session file to clean up ({sf.name})'}
    try:
        sf.unlink()
        return {'success': True, 'message': f'Session file cleaned up ({sf.name})'}
    except IOError as e:
        return {'success': False, 'error': f'Failed to delete {sf.name}: {e}'}


def main():
    """Entry point: dispatch to get_next_rem or cleanup."""
    args = parse_args()
    if args.cleanup:
        result = cleanup_session(args.session_id)
    else:
        result = get_next_rem(args.session_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result.get('success'):
        sys.exit(1)
    if result.get('session_complete'):
        sys.exit(2)
    sys.exit(0)


if __name__ == '__main__':
    main()
