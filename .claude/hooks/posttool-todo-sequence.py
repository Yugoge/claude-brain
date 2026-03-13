#!/usr/bin/env python3
"""
PostToolUse Hook: Enforce one-step-at-a-time progression in workflow checklists.

Reads previous todo state from bookmark.last_todos. Compares against the new
TodoWrite input. Blocks if agent completed multiple steps at once, skipped
in_progress, or set multiple steps to in_progress simultaneously.

State: stored in .claude/workflow-{session_id}.json as 'last_todos' field.

Exit codes:
  0: Valid transition, allow
  2: Sequence violation, block
"""

import json
import os
import sys
from pathlib import Path


def main():
    try:
        data = json.load(sys.stdin)
        new_todos = data.get('tool_input', {}).get('todos', [])
        session_id = data.get('session_id', 'default')
    except Exception:
        sys.exit(0)

    if not new_todos:
        sys.exit(0)

    project_dir = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))
    bookmark_path = project_dir / '.claude' / f'workflow-{session_id}.json'

    if not bookmark_path.exists():
        sys.exit(0)

    try:
        state = json.loads(bookmark_path.read_text())
    except Exception:
        sys.exit(0)

    cmd_name = state.get('command', '?')
    last_todos = state.get('last_todos')  # None on first call

    violations = []

    if last_todos is None:
        # First call — save current state as baseline, no validation possible yet
        try:
            state['last_todos'] = new_todos
            bookmark_path.write_text(json.dumps(state))
        except Exception:
            pass
        sys.exit(0)
    else:
        # Subsequent call: enforce sequence rules
        if len(last_todos) != len(new_todos):
            # Count mismatch handled by hook-enforce-todo-count; skip validation
            # But reset baseline so next correct-count call can be tracked
            try:
                state['last_todos'] = new_todos
                bookmark_path.write_text(json.dumps(state))
            except Exception:
                pass
            sys.exit(0)

        prev_completed = {i for i, t in enumerate(last_todos) if t.get('status') == 'completed'}
        new_completed = {i for i, t in enumerate(new_todos) if t.get('status') == 'completed'}
        newly_completed = new_completed - prev_completed

        # Rule 1: max 1 newly completed per call
        if len(newly_completed) > 1:
            names = [f'Step {i}: "{new_todos[i]["content"]}"' for i in sorted(newly_completed)]
            violations.append(
                f"Completed {len(newly_completed)} steps in one call (max 1 allowed):\n"
                + '\n'.join(f'  - {n}' for n in names)
            )

        # Rule 2: no pending -> completed (must pass through in_progress)
        for idx in newly_completed:
            if last_todos[idx].get('status') == 'pending':
                violations.append(
                    f'Step {idx} ("{new_todos[idx]["content"]}"): '
                    f'went from pending -> completed without in_progress'
                )

        # Rule 3: max 1 in_progress at a time
        in_progress = [t for t in new_todos if t.get('status') == 'in_progress']
        if len(in_progress) > 1:
            violations.append(
                f"Multiple steps in_progress simultaneously ({len(in_progress)}): "
                + ', '.join(f'"{t["content"]}"' for t in in_progress)
            )

        # Rule 4: can't start step N if any earlier step is still pending
        newly_in_progress = [
            i for i, (prev, new) in enumerate(zip(last_todos, new_todos))
            if prev.get('status') == 'pending' and new.get('status') == 'in_progress'
        ]
        for idx in newly_in_progress:
            for prev_idx in range(idx):
                if new_todos[prev_idx].get('status') != 'completed':
                    violations.append(
                        f'Step {idx} ("{new_todos[idx]["content"]}"): cannot start before '
                        f'Step {prev_idx} ("{new_todos[prev_idx]["content"]}") is completed'
                    )
                    break

    if violations:
        # Find what step should actually be next
        next_hint = ''
        if last_todos:
            for i, t in enumerate(last_todos):
                if t.get('status') == 'in_progress':
                    next_hint = (
                        f'\nREQUIRED ACTION: Mark Step {i} ("{t["content"]}") as completed, '
                        f'then mark Step {i+1} as in_progress -- one TodoWrite at a time.'
                    )
                    break

        # Reset lock so PreToolUse blocks all tools until agent fixes the TodoWrite.
        # Fresh read before write to capture any state changes from other PostToolUse hooks
        # (tracker may have run concurrently and written todo_acknowledged=True).
        try:
            fresh = json.loads(bookmark_path.read_text())
            fresh['todo_acknowledged'] = False
            fresh['lock_reason'] = 'sequence_violation'
            bookmark_path.write_text(json.dumps(fresh))
        except Exception:
            pass

        sys.stderr.write(
            f'\n⛔ STEP SEQUENCE VIOLATION in /{cmd_name}:\n'
            + '\n'.join(f'  [{j+1}] {v}' for j, v in enumerate(violations))
            + '\n\nMANDATORY RULES:\n'
            '  1. Complete exactly ONE step per TodoWrite call\n'
            '  2. Each step must pass through in_progress before completed\n'
            '  3. Only ONE step can be in_progress at a time\n'
            '  4. Steps must be completed in order — no skipping ahead\n'
            + next_hint + '\n'
        )
        sys.exit(2)

    # Valid transition -- persist new state
    try:
        state['last_todos'] = new_todos
        bookmark_path.write_text(json.dumps(state))
    except Exception:
        pass

    sys.exit(0)


if __name__ == '__main__':
    main()
