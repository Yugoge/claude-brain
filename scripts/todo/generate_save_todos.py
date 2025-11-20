#!/usr/bin/env python3
"""
Auto-generate scripts/todo/save.py from .claude/commands/save.md

Single source of truth: save.md
This script ensures perfect sync between command documentation and TodoWrite checklist.
"""

import re
import sys
from pathlib import Path

def extract_steps_from_save_md(save_md_path):
    """Extract step numbers and titles from save.md"""
    with open(save_md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: ### Step N: Title
    pattern = r'^### Step (\d+): (.+)$'
    matches = re.findall(pattern, content, re.MULTILINE)

    steps = []
    for num_str, title in matches:
        num = int(num_str)
        steps.append({
            'num': num,
            'title': title,
            'content': f'Step {num}: {title}',
            'activeForm': f'Step {num}: {title}',
            'status': 'pending'
        })

    return steps

def generate_save_py(steps, output_path):
    """Generate scripts/todo/save.py from extracted steps"""

    header = '''#!/usr/bin/env python3
"""
Preloaded TodoList for save workflow.

Auto-generated from .claude/commands/save.md by scripts/todo/generate_save_todos.py
DO NOT EDIT MANUALLY - edit save.md and re-run generator script.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
'''

    footer = ''']


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
'''

    # Generate todo items
    todo_items = []
    for step in steps:
        todo_item = f'''    {{
        "content": "{step['content']}",
        "activeForm": "{step['activeForm']}",
        "status": "{step['status']}"
    }}'''
        todo_items.append(todo_item)

    todos_str = ',\n'.join(todo_items)

    # Combine
    full_content = header + todos_str + '\n' + footer

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_content)

    return len(steps)

def main():
    root = Path(__file__).parent.parent.parent
    save_md = root / '.claude' / 'commands' / 'save.md'
    save_py = root / 'scripts' / 'todo' / 'save.py'

    if not save_md.exists():
        print(f"❌ Error: {save_md} not found", file=sys.stderr)
        return 1

    # Extract steps
    steps = extract_steps_from_save_md(save_md)
    print(f"✓ Extracted {len(steps)} steps from save.md", file=sys.stderr)

    # Show step range
    if steps:
        print(f"  Step range: {steps[0]['num']} to {steps[-1]['num']}", file=sys.stderr)

    # Generate save.py
    count = generate_save_py(steps, save_py)
    print(f"✅ Generated {save_py} with {count} steps", file=sys.stderr)

    return 0

if __name__ == '__main__':
    sys.exit(main())
