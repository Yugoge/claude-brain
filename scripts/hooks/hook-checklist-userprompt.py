#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Checklist Injection for Slash Commands

Phase A (slash command detected):
  - Runs scripts/todo/<command>.py to get the step list
  - Writes todos to Claude Code's official todos file
  - Writes {session_id, command} to .claude/workflow-{session_id}.json (bookmark only)
  - Prints checklist-ready message to stdout

Phase B (subsequent prompts, no slash command):
  - Reads official todos file for current session
  - Injects current progress if there are incomplete steps

State: only ~/.claude/todos/{sid}.json (official) + .claude/workflow-{session_id}.json (command bookmark)
No blocking_count cached anywhere — computed fresh from todo script when needed.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))


def extract_command_name(user_input: str) -> str:
    text = user_input.strip()
    if not text.startswith('/'):
        return ''
    parts = text.split()
    return parts[0][1:] if parts else ''


def official_todos_path(session_id: str) -> Path:
    return Path.home() / '.claude' / 'todos' / f'{session_id}-agent-{session_id}.json'


def workflow_bookmark_path(session_id: str) -> Path:
    return PROJECT_DIR / '.claude' / f'workflow-{session_id}.json'


def run_todo_script(cmd_name: str) -> list:
    todo_script = PROJECT_DIR / 'scripts' / 'todo' / f'{cmd_name}.py'
    if not todo_script.exists():
        global_todo = Path.home() / '.claude' / 'scripts' / 'todo' / f'{cmd_name}.py'
        if global_todo.exists():
            todo_script = global_todo
        else:
            return []
    result = subprocess.run(
        ['python3', str(todo_script)],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        return json.loads(result.stdout)
    except Exception:
        return []


def format_progress(todos: list) -> str:
    total = len(todos)
    lines = [f'ACTIVE WORKFLOW: {total} steps — continue with the next pending step.']
    for i, todo in enumerate(todos, 1):
        lines.append(f'  {i}. {todo["content"]}')
    return '\n'.join(lines)


def main():
    try:
        data = json.load(sys.stdin)
        user_input = data.get('prompt', '')
        session_id = data.get('session_id', 'default')
        cmd_name = extract_command_name(user_input)

        if not cmd_name:
            # Phase B: inject progress if workflow active
            todos_file = official_todos_path(session_id)
            if todos_file.exists():
                try:
                    todos = json.loads(todos_file.read_text())
                    if todos and any(t.get('status') != 'completed' for t in todos):
                        print(format_progress(todos))
                except Exception:
                    pass
            sys.exit(0)

        # Phase A: run todo script to get canonical steps
        todos = run_todo_script(cmd_name)
        if not todos:
            sys.exit(0)

        # Write todos to official file
        todos_file = official_todos_path(session_id)
        todos_file.parent.mkdir(parents=True, exist_ok=True)
        todos_file.write_text(json.dumps(todos, ensure_ascii=False))

        # Write command bookmark (session_id + command only — no blocking_count cache)
        bookmark = workflow_bookmark_path(session_id)
        try:
            bookmark.parent.mkdir(parents=True, exist_ok=True)
            bookmark.write_text(json.dumps({'command': cmd_name, 'todo_acknowledged': False}))
        except Exception:
            pass

        first_step = todos[0]['content'] if todos else 'first step'
        print('\n'.join([
            f'CHECKLIST PRE-INITIALIZED for /{cmd_name.upper()}:',
            f'Your workflow checklist ({len(todos)} steps) has been created.',
            f'Use TodoRead to view it. Begin immediately with: {first_step}',
            f'Mark each step in_progress then completed as you work through them.',
        ]))

    except Exception:
        pass
    sys.exit(0)


if __name__ == '__main__':
    main()
