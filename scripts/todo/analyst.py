#!/usr/bin/env python3
"""
Preloaded TodoList for analyst workflow.

Auto-generated from workflow steps extraction.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
    {"content": "Step 0: Query MCP Memory", "activeForm": "Step 0: Query MCP Memory", "status": "pending"},
    {"content": "Step 1: Analyze Question", "activeForm": "Step 1: Analyze Question", "status": "pending"},
    {"content": "Step 2: Check Existing Knowledge", "activeForm": "Step 2: Check Existing Knowledge", "status": "pending"},
    {"content": "Step 3: Research", "activeForm": "Step 3: Research", "status": "pending"},
    {"content": "Step 4: Synthesize Answer", "activeForm": "Step 4: Synthesize Answer", "status": "pending"},
    {"content": "Step 5: Save to Memory", "activeForm": "Step 5: Save to Memory", "status": "pending"},
    {"content": "Step 6: Link to Knowledge Base", "activeForm": "Step 6: Link to Knowledge Base", "status": "pending"},
    {"content": "Step 7: Suggest Follow-ups", "activeForm": "Step 7: Suggest Follow-ups", "status": "pending"}
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
