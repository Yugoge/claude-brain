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

    if lock_reason == 'sequence_violation':
        sys.stderr.write(
            f'\n🚫 STEP SKIPPING DETECTED: /{cmd_name} workflow is locked.\n'
            f'You attempted to skip or reorder steps.\n'
            f'Call TodoWrite to fix the sequence — complete steps one at a time, in order.\n'
        )
    elif lock_reason == 'count_mismatch':
        sys.stderr.write(
            f'\n🚫 STEP COUNT VIOLATION: /{cmd_name} workflow is locked.\n'
            f'TodoWrite was called with the wrong number of steps.\n'
            f'Call TodoWrite with the complete canonical step list.\n'
        )
    else:
        sys.stderr.write(
            f'\n⚠️  CHECKLIST NOT STARTED: /{cmd_name} workflow is active.\n'
            f'Call TodoWrite to initialize the checklist before using other tools.\n'
            f'The workflow has pre-generated steps — use TodoWrite to mark Step 1 as in_progress.\n'
        )
    sys.exit(2)


if __name__ == '__main__':
    main()
