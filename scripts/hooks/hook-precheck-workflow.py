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

    # If tool is TodoWrite or TodoRead → acknowledge and allow
    if tool_name in ('TodoWrite', 'TodoRead'):
        if bookmark_path.exists():
            try:
                state = json.loads(bookmark_path.read_text())
                if not state.get('todo_acknowledged', False):
                    state['todo_acknowledged'] = True
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

    # Not acknowledged → block
    cmd_name = state.get('command', '?')
    sys.stderr.write(
        f'\n⚠️  CHECKLIST NOT STARTED: /{cmd_name} workflow is active.\n'
        f'You must call TodoWrite FIRST before using any other tools.\n'
        f'Initialize the checklist: mark Step 1 as in_progress, then proceed.\n'
    )
    sys.exit(2)


if __name__ == '__main__':
    main()
