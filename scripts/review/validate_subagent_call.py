#!/usr/bin/env python3
"""
Validate Review-Master Subagent Call

Validates that review-master Task call occurred for current Rem review.
Root cause: No enforcement mechanism allowed skipping subagent consultation.

Usage:
    source venv/bin/activate && python scripts/review/validate_subagent_call.py <rem_id> <session_id>

Arguments:
    rem_id: The Rem ID being reviewed
    session_id: Unique session identifier for audit trail

Returns:
    JSON with validation result and audit information

Exit codes:
    0: Validation passed (subagent called)
    1: Validation failed (subagent not called or error)
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def validate_subagent_call(rem_id, session_id):
    """
    Validate that review-master was called for this Rem.

    Args:
        rem_id: The Rem ID being reviewed
        session_id: Session identifier for audit

    Returns:
        dict: Validation result with audit trail
    """
    audit_file = Path('.review/subagent_audit.json')

    # Load audit log
    if not audit_file.exists():
        return {
            'success': False,
            'error': 'No audit file found - subagent was never called',
            'rem_id': rem_id,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }

    try:
        with open(audit_file, 'r', encoding='utf-8') as f:
            audit_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return {
            'success': False,
            'error': f'Failed to read audit log: {str(e)}',
            'rem_id': rem_id,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }

    # Check if this rem_id was consulted in this session
    session_calls = audit_data.get('sessions', {}).get(session_id, {}).get('calls', [])

    # Find call for this rem_id
    matching_calls = [call for call in session_calls if call.get('rem_id') == rem_id]

    if not matching_calls:
        return {
            'success': False,
            'error': f'No review-master call found for rem_id: {rem_id}',
            'rem_id': rem_id,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat(),
            'audit_summary': {
                'total_calls_in_session': len(session_calls),
                'rems_consulted': [c.get('rem_id') for c in session_calls]
            }
        }

    # Validation passed
    latest_call = matching_calls[-1]  # Use most recent if multiple
    return {
        'success': True,
        'rem_id': rem_id,
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'call_details': {
            'consultation_type': latest_call.get('consultation_type', 'question'),
            'call_timestamp': latest_call.get('timestamp'),
            'format_used': latest_call.get('format_used')
        }
    }


def record_subagent_call(rem_id, session_id, consultation_type='question', format_used=None):
    """
    Record that review-master was called for this Rem.

    Args:
        rem_id: The Rem ID being reviewed
        session_id: Session identifier
        consultation_type: Type of consultation ('question' or 'explanation')
        format_used: Question format used (if consultation_type='question')

    Returns:
        dict: Confirmation of recording
    """
    audit_file = Path('.review/subagent_audit.json')

    # Load existing audit data
    if audit_file.exists():
        try:
            with open(audit_file, 'r', encoding='utf-8') as f:
                audit_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            audit_data = {'sessions': {}}
    else:
        audit_data = {'sessions': {}}

    # Ensure session exists
    if session_id not in audit_data['sessions']:
        audit_data['sessions'][session_id] = {
            'session_start': datetime.now().isoformat(),
            'calls': []
        }

    # Record call
    call_record = {
        'rem_id': rem_id,
        'timestamp': datetime.now().isoformat(),
        'consultation_type': consultation_type
    }
    if format_used:
        call_record['format_used'] = format_used

    audit_data['sessions'][session_id]['calls'].append(call_record)

    # Write atomically
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = audit_file.with_suffix('.tmp')
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(audit_data, f, indent=2, ensure_ascii=False)
    temp_file.replace(audit_file)

    return {
        'success': True,
        'rem_id': rem_id,
        'session_id': session_id,
        'consultation_type': consultation_type,
        'total_calls_in_session': len(audit_data['sessions'][session_id]['calls'])
    }


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            'success': False,
            'error': 'Usage: validate_subagent_call.py <rem_id> <session_id> [--record] [--type question|explanation] [--format <format>]'
        }), file=sys.stderr)
        sys.exit(1)

    rem_id = sys.argv[1]
    session_id = sys.argv[2]

    # Check for record mode
    if '--record' in sys.argv:
        # Record mode
        consultation_type = 'question'
        format_used = None

        if '--type' in sys.argv:
            type_idx = sys.argv.index('--type')
            if type_idx + 1 < len(sys.argv):
                consultation_type = sys.argv[type_idx + 1]

        if '--format' in sys.argv:
            format_idx = sys.argv.index('--format')
            if format_idx + 1 < len(sys.argv):
                format_used = sys.argv[format_idx + 1]

        result = record_subagent_call(rem_id, session_id, consultation_type, format_used)
    else:
        # Validation mode
        result = validate_subagent_call(rem_id, session_id)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not result['success']:
        sys.exit(1)


if __name__ == '__main__':
    main()
