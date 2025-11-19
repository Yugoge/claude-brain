#!/usr/bin/env python3
"""
Preloaded TodoList for discover-relations workflow.

Auto-generated from workflow steps extraction.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
    {"content": "Step 1: Parse Arguments", "activeForm": "Step 1: Parse Arguments", "status": "pending"},
    {"content": "Step 2: Load Target Rems", "activeForm": "Step 2: Load Target Rems", "status": "pending"},
    {"content": "Step 3: Load Existing Concepts", "activeForm": "Step 3: Load Existing Concepts", "status": "pending"},
    {"content": "Step 4: Call Domain Tutor", "activeForm": "Step 4: Call Domain Tutor", "status": "pending"},
    {"content": "Step 5: Present Preview", "activeForm": "Step 5: Present Preview", "status": "pending"},
    {"content": "Step 6: Update Rem Files", "activeForm": "Step 6: Update Rem Files", "status": "pending"},
    {"content": "Step 7: Rebuild Backlinks", "activeForm": "Step 7: Rebuild Backlinks", "status": "pending"},
    {"content": "Step 8: Normalize Links", "activeForm": "Step 8: Normalize Links", "status": "pending"}
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
