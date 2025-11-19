#!/usr/bin/env python3
"""
Preloaded TodoList for visualize workflow.

Auto-generated from workflow steps extraction.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
    {"content": "Step 1: Generate Graph Data", "activeForm": "Step 1: Generate Graph Data", "status": "pending"},
    {"content": "Step 2: Generate Visualization HTML", "activeForm": "Step 2: Generate Visualization HTML", "status": "pending"},
    {"content": "Step 3: Display Summary", "activeForm": "Step 3: Display Summary", "status": "pending"}
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
