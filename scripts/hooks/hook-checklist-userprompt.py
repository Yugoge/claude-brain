#!/usr/bin/env python3
"""
UserPromptSubmit Hook: Checklist Injection for Slash Commands

Phase A (slash command detected):
  - Runs scripts/todo/<command>.py to get the step list
  - Writes todos to Claude Code's official todos file
  - Writes {session_id, command} to .claude/workflow-{session_id}.json (bookmark only)
  - Prints checklist-ready message + exact first TodoWrite call to use

Phase B (subsequent prompts, no slash command):
  - Reads official todos file for current session
  - Injects current progress + exact next TodoWrite call template

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


def build_next_todowrite_call(todos: list, mark_first_inprogress: bool = False) -> str:
    """
    Generate the exact JSON array to pass to TodoWrite for the next action.

    If mark_first_inprogress=True (Phase A): marks the first step as in_progress.
    Otherwise (Phase B): determines next action from current state:
      - If a step is in_progress, show it as-is (agent should complete it first)
      - If no step is in_progress, mark the next pending step as in_progress
    """
    if not todos:
        return ''

    result = [t.copy() for t in todos]

    if mark_first_inprogress:
        # Phase A: first call should mark step 1 as in_progress
        result[0]['status'] = 'in_progress'
    else:
        # Phase B: determine what the next logical call should be
        has_inprogress = any(t.get('status') == 'in_progress' for t in result)
        if not has_inprogress:
            # Find next pending and mark it in_progress
            for t in result:
                if t.get('status') == 'pending':
                    t['status'] = 'in_progress'
                    break

    return json.dumps(result, ensure_ascii=False, separators=(",", ": "))


def build_completion_template(todos: list) -> str:
    """
    When a step is in_progress, generate the template for AFTER the work is done:
    mark current in_progress as completed, mark next pending as in_progress.
    """
    result = [t.copy() for t in todos]
    in_progress_idx = next((i for i, t in enumerate(result) if t.get('status') == 'in_progress'), None)
    if in_progress_idx is not None:
        result[in_progress_idx]['status'] = 'completed'
        # Mark next pending as in_progress
        for t in result[in_progress_idx + 1:]:
            if t.get('status') == 'pending':
                t['status'] = 'in_progress'
                break
    return json.dumps(result, ensure_ascii=False, separators=(",", ": "))


def format_progress(todos: list, lock_reason: str = '', canonical: list = None,
                    todo_acknowledged: bool = False) -> str:
    """Phase B: show current progress. JSON template only shown before first successful TodoWrite."""
    total = len(todos)
    completed = sum(1 for t in todos if t.get('status') == 'completed')
    in_progress = next((t for t in todos if t.get('status') == 'in_progress'), None)

    # Locked states always show recovery template regardless of todo_acknowledged
    if lock_reason == 'count_mismatch' and canonical:
        lines = [
            f'WORKFLOW LOCKED (count_mismatch): TodoWrite was called with wrong number of steps.',
            f'You MUST re-call TodoWrite with ALL {len(canonical)} canonical steps.',
            f'Call TodoWrite with this exact todos array:',
            '',
            build_next_todowrite_call(canonical, mark_first_inprogress=False),
        ]
        return '\n'.join(lines)

    if lock_reason == 'sequence_violation':
        current = in_progress["content"] if in_progress else "current step"
        lines = [
            f'WORKFLOW LOCKED (sequence_violation): Steps were skipped or completed out of order.',
            f'REQUIRED: complete "{current}" first, then advance ONE step at a time.',
            f'Call TodoWrite to fix the sequence.',
        ]
        return '\n'.join(lines)

    lines = [f'ACTIVE WORKFLOW: {completed}/{total} steps completed.']

    if in_progress:
        lines.append(f'Currently in_progress: {in_progress["content"]}')
    else:
        next_pending = next((t for t in todos if t.get('status') == 'pending'), None)
        if next_pending:
            lines.append(f'Next step: {next_pending["content"]}')

    # Show JSON template only until the agent has successfully called TodoWrite once
    if not todo_acknowledged:
        if in_progress:
            lines.append(f'Complete the work above, THEN call TodoWrite — copy the JSON below EXACTLY into the todos parameter (do NOT retype or reformat):')
            lines.append('')
            lines.append(build_completion_template(todos))
        else:
            lines.append('')
            lines.append('Call TodoWrite NOW — copy the JSON below EXACTLY into the todos parameter (do NOT retype or reformat):')
            lines.append(build_next_todowrite_call(todos, mark_first_inprogress=False))

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
                    if not todos or all(t.get('status') == 'completed' for t in todos):
                        sys.exit(0)

                    # Read lock state and todo_acknowledged from bookmark
                    lock_reason = ''
                    canonical = []
                    todo_acknowledged = False
                    bookmark = workflow_bookmark_path(session_id)
                    if bookmark.exists():
                        try:
                            state = json.loads(bookmark.read_text())
                            lock_reason = state.get('lock_reason', '')
                            todo_acknowledged = state.get('todo_acknowledged', False)
                            # Fetch canonical list only when needed for recovery
                            if lock_reason == 'count_mismatch':
                                bookmark_cmd = state.get('command', '')
                                if bookmark_cmd:
                                    canonical = run_todo_script(bookmark_cmd)
                        except Exception:
                            pass

                    print(format_progress(todos, lock_reason=lock_reason, canonical=canonical,
                                          todo_acknowledged=todo_acknowledged))
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

        first_call = build_next_todowrite_call(todos, mark_first_inprogress=True)
        lines = [
            f'CHECKLIST PRE-INITIALIZED for /{cmd_name.upper()}:',
            f'Your workflow checklist ({len(todos)} steps) has been created.',
            f'FIRST ACTION: copy the JSON below EXACTLY into the TodoWrite todos parameter (do NOT retype or reformat):',
            f'(you MUST pass ALL {len(todos)} items every TodoWrite call):',
            '',
            first_call,
        ]
        print('\n'.join(lines))

    except Exception:
        pass
    sys.exit(0)


if __name__ == '__main__':
    main()
