#!/usr/bin/env python3
"""
PreToolUse Hook: Require TodoWrite/TodoRead acknowledgment before other tools.

If an active workflow exists (bookmark present) and the agent has NOT yet
called TodoWrite or TodoRead (todo_acknowledged == false in bookmark), block
any other tool.

This prevents agents from ignoring the workflow checklist while still using
other tools freely.

Logic:
  1. If tool is TodoWrite or TodoRead → set todo_acknowledged=true → allow
  2. No bookmark → allow (no active workflow)
  3. todo_acknowledged == true → allow
  4. Otherwise → block

Exit codes:
  0: Allow tool use
  2: Block tool use (must call TodoWrite/TodoRead first)
"""

import json
import os
import sys
from pathlib import Path


def official_todos_path(session_id: str) -> Path:
    return Path.home() / '.claude' / 'todos' / f'{session_id}-agent-{session_id}.json'


def build_next_todowrite_call(session_id: str) -> str:
    """Read todos file and return ready-to-use JSON for the next TodoWrite call."""
    try:
        todos_file = official_todos_path(session_id)
        if not todos_file.exists():
            return ''
        todos = json.loads(todos_file.read_text())
        result = [t.copy() for t in todos]
        has_inprogress = any(t.get('status') == 'in_progress' for t in result)
        if not has_inprogress:
            for t in result:
                if t.get('status') == 'pending':
                    t['status'] = 'in_progress'
                    break
        return json.dumps(result, ensure_ascii=False, separators=(',', ': '))
    except Exception:
        return ''


def main():
    try:
        data = json.load(sys.stdin)
        tool_name = data.get('tool_name', '')
        session_id = data.get('session_id', 'default')
    except Exception:
        sys.exit(0)

    project_dir = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))
    bookmark_path = project_dir / '.claude' / f'workflow-{session_id}.json'

    # ToolSearch: allow through so agent can load TodoRead — but don't set flag
    if tool_name == 'ToolSearch':
        sys.exit(0)

    # TodoWrite → acknowledge and allow
    # (Stop hook enforces todo count >= blocking_count, so reducing todos is caught at session end)
    if tool_name == 'TodoWrite':
        if bookmark_path.exists():
            try:
                state = json.loads(bookmark_path.read_text())
                if not state.get('todo_acknowledged', False):
                    state['todo_acknowledged'] = True
                    state.pop('lock_reason', None)  # clear violation reason on unlock
                    bookmark_path.write_text(json.dumps(state))
            except Exception:
                pass
        sys.exit(0)

    # No bookmark → no active workflow → allow
    if not bookmark_path.exists():
        sys.exit(0)

    try:
        state = json.loads(bookmark_path.read_text())
    except Exception:
        sys.exit(0)

    # Already acknowledged → allow
    if state.get('todo_acknowledged', False):
        sys.exit(0)

    # Not acknowledged → block with reason-specific message
    cmd_name = state.get('command', '?')
    lock_reason = state.get('lock_reason', 'not_started')

    next_json = build_next_todowrite_call(session_id)
    json_hint = (
        f'\nCall TodoWrite with this exact todos array:\n{next_json}\n'
        if next_json else ''
    )

    if lock_reason == 'sequence_violation':
        sys.stderr.write(
            f'\n🚫 STEP SKIPPING DETECTED: /{cmd_name} workflow is locked.\n'
            f'You attempted to skip or reorder steps.\n'
            f'Call TodoWrite to fix the sequence — complete steps one at a time, in order.\n'
            + json_hint
        )
    elif lock_reason == 'count_mismatch':
        sys.stderr.write(
            f'\n🚫 STEP COUNT VIOLATION: /{cmd_name} workflow is locked.\n'
            f'TodoWrite was called with the wrong number of steps.\n'
            f'Call TodoWrite with the complete canonical step list.\n'
            + json_hint
        )
    else:
        sys.stderr.write(
            f'\n⚠️  CHECKLIST NOT STARTED: /{cmd_name} workflow is active.\n'
            f'Call TodoWrite to initialize the checklist before using other tools.\n'
            + json_hint
        )
    sys.exit(2)


if __name__ == '__main__':
    main()
