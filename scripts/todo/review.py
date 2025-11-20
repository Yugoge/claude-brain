#!/usr/bin/env python3
"""
Preloaded TodoList for review workflow.

Auto-generated from workflow steps extraction.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
    {
        "content": "Step 1: Load Rems and Show Timeline",
        "activeForm": "Step 1: Load Rems and Show Timeline",
        "status": "pending"
    },
    {
        "content": "Step 2: Conduct Review Session (Main Agent Dialogue Loop)",
        "activeForm": "Step 2: Conduct Review Session (Main Agent Dialogue Loop)",
        "status": "pending"
    },
    {
        "content": "Step 3: Post-Session Summary",
        "activeForm": "Step 3: Post-Session Summary",
        "status": "pending"
    }
]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
