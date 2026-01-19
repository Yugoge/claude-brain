#!/usr/bin/env python3
"""
Hook: Record Review-Master Task Calls

Automatically records when review-master is called via Task tool.
This creates an audit trail for validation enforcement.

Root cause: No enforcement mechanism allowed skipping subagent consultation.
Solution: Automatic recording of Task calls to review-master.

Hook type: PostToolUse (Task matcher)
Trigger: After any Task tool invocation
Action: If subagent_type=review-master, record call to audit log

Exit codes:
    0: Success (call recorded or not review-master)
    Non-zero: Error (logged but ignored per on_error: ignore)
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def extract_session_and_rem(tool_input):
    """
    Extract session_id and rem_id from Task tool input.

    Args:
        tool_input: The tool input JSON from hook

    Returns:
        tuple: (session_id, rem_id, consultation_type, format_used) or (None, None, None, None)
    """
    # Check if this is a review-master call
    subagent_type = tool_input.get('subagent_type', '')
    if subagent_type != 'review-master':
        return None, None, None, None

    # Parse prompt to extract rem_id and session context
    prompt = tool_input.get('prompt', '')

    # Try to extract JSON from prompt
    try:
        # Find JSON block in prompt (between { and })
        json_start = prompt.find('{')
        json_end = prompt.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = prompt[json_start:json_end]
            data = json.loads(json_str)

            rem_id = data.get('rem_data', {}).get('id')
            session_context = data.get('session_context', {})
            consultation_type = session_context.get('consultation_type', 'question')

            # Generate session_id from current_index + total (deterministic within session)
            total_rems = session_context.get('total_rems', 0)
            current_index = session_context.get('current_index', 0)
            session_id = f"session-{datetime.now().strftime('%Y%m%d')}-{total_rems}rems"

            # Extract format if consultation_type is question
            format_used = None
            if consultation_type == 'question':
                # Format will be in review_guidance response, not in prompt
                # We'll update this in a separate PostToolUse hook if needed
                pass

            return session_id, rem_id, consultation_type, format_used
    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    return None, None, None, None


def record_call(session_id, rem_id, consultation_type, format_used=None):
    """
    Record the review-master call to audit log.

    Args:
        session_id: Session identifier
        rem_id: Rem ID being reviewed
        consultation_type: Type of consultation
        format_used: Question format (optional)

    Returns:
        bool: Success status
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

    return True


def main():
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)

        # Extract tool input
        tool_input = hook_input.get('tool', {}).get('input', {})

        # Extract session and rem info
        session_id, rem_id, consultation_type, format_used = extract_session_and_rem(tool_input)

        if session_id and rem_id:
            # Record the call
            success = record_call(session_id, rem_id, consultation_type, format_used)
            if success:
                # Silent success (hook should not interfere with user experience)
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            # Not a review-master call or couldn't extract info - that's fine
            sys.exit(0)

    except Exception as e:
        # Log error but don't fail (on_error: ignore)
        error_log = Path('.review/hook_errors.log')
        with open(error_log, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()} - Record review-master call hook error: {str(e)}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
