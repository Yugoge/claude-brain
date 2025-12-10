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
        "content": "Load Rems and Show Timeline",
        "activeForm": "Loading Rems and showing timeline",
        "status": "pending"
    },
    {
        "content": "Conduct Review Dialogue",
        "activeForm": "Conducting review dialogue",
        "status": "pending"
    },
    {
        "content": "Show Post-Session Summary",
        "activeForm": "Showing post-session summary",
        "status": "pending"
    }
]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
