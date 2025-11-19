#!/usr/bin/env python3
"""
Preloaded TodoList for stats workflow.

Auto-generated from workflow steps extraction.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
    {"content": "Step 1: Generate Analytics", "activeForm": "Step 1: Generate Analytics", "status": "pending"},
    {"content": "Step 2: Load Analytics Cache", "activeForm": "Step 2: Load Analytics Cache", "status": "pending"},
    {"content": "Step 3: Create React Dashboard", "activeForm": "Step 3: Create React Dashboard", "status": "pending"},
    {"content": "Step 4: Display Summary Statistics", "activeForm": "Step 4: Display Summary Statistics", "status": "pending"}
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
