#!/usr/bin/env python3
"""
PostToolUse Hook: Output checklist progress after every TodoWrite call.

Fires after every TodoWrite call:
1. Reads command name from .claude/workflow-{session_id}.json bookmark
2. Runs todo script to get canonical blocking_count (fresh, no cache)
3. Prints current checklist progress to stdout (injected into Claude's context)

Hook type: PostToolUse (TodoWrite matcher)
Exit codes: 0 always (never blocks)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

STATUS_SYMBOL = {'completed': '[x]', 'in_progress': '[~]', 'pending': '[ ]'}


def run_todo_script(cmd_name: str, project_dir: Path) -> list:
    todo_script = project_dir / 'scripts' / 'todo' / f'{cmd_name}.py'
    if not todo_script.exists():
        global_todo = Path.home() / '.claude' / 'scripts' / 'todo' / f'{cmd_name}.py'
        if global_todo.exists():
            todo_script = global_todo
        else:
            return []
    result = subprocess.run(
        ['python3', str(todo_script)],
        capture_output=True, text=True, cwd=str(project_dir)
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        return json.loads(result.stdout)
    except Exception:
        return []


def format_checklist(command: str, todos: list, blocking_count: int) -> str:
    completed_count = sum(1 for t in todos if t.get('status') == 'completed')
    lines = [f"WORKFLOW PROGRESS ({command}): {completed_count}/{blocking_count} steps completed"]
    for todo in todos:
        symbol = STATUS_SYMBOL.get(todo.get('status', 'pending'), '[ ]')
        lines.append(f"  {symbol} {todo['content']}")
    if completed_count < blocking_count:
        lines.append("Continue with the next required step.")
    return '\n'.join(lines)


def main():
    try:
        data = json.load(sys.stdin)
        todos = data.get('tool_input', {}).get('todos', [])
        if not todos:
            sys.exit(0)

        session_id = data.get('session_id', 'default')
        project_dir = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))
        bookmark = project_dir / '.claude' / f'workflow-{session_id}.json'

        cmd_name = '?'
        if bookmark.exists():
            try:
                cmd_name = json.loads(bookmark.read_text()).get('command', '?')
            except Exception:
                pass

        # Get blocking_count fresh from todo script — never from cache
        canonical = run_todo_script(cmd_name, project_dir) if cmd_name != '?' else []
        blocking_count = len(canonical) if canonical else len(todos)

        print(format_checklist('/' + cmd_name, todos, blocking_count))

    except Exception:
        pass
    sys.exit(0)


if __name__ == '__main__':
    main()
