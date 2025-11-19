#!/usr/bin/env python3
"""
Preloaded TodoList for ask workflow.

Auto-generated from workflow steps extraction.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
    {"content": "Step 1: Parse Question", "activeForm": "Step 1: Parse Question", "status": "pending"},
    {"content": "Step 2: Initial Analyst Consultation", "activeForm": "Step 2: Initial Analyst Consultation", "status": "pending"},
    {"content": "Step 3: Validate and Parse Analyst Response", "activeForm": "Step 3: Validate and Parse Analyst Response", "status": "pending"},
    {"content": "Step 4: Internalize Guidance and Respond Naturally", "activeForm": "Step 4: Internalize Guidance and Respond Naturally", "status": "pending"},
    {"content": "Step 5: Multi-Turn Dialogue Loop", "activeForm": "Step 5: Multi-Turn Dialogue Loop", "status": "pending"},
    {"content": "Step 6: Natural Conclusion Detection", "activeForm": "Step 6: Natural Conclusion Detection", "status": "pending"},
    {"content": "Step 7: Post-Conversation Archival Prompt", "activeForm": "Step 7: Post-Conversation Archival Prompt", "status": "pending"},
    {"content": "Step 8: Handle Archival Response", "activeForm": "Step 8: Handle Archival Response", "status": "pending"}
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
