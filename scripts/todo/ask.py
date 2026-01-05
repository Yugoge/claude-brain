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
    {"content": "Step 1: Parse Question", "activeForm": "Step 1: Parsing Question", "status": "pending"},
    {"content": "Step 2: Initial Analyst Consultation", "activeForm": "Step 2: Consulting Analyst", "status": "pending"},
    {"content": "Step 3: Validate and Parse Analyst Response", "activeForm": "Step 3: Validating Analyst Response", "status": "pending"},
    {"content": "Step 4: Confidence Gate and Escalation", "activeForm": "Step 4: Checking Confidence Gate", "status": "pending"},
    {"content": "Step 5: Internalize Guidance and Respond", "activeForm": "Step 5: Responding to User", "status": "pending"},
    {"content": "Step 6: Multi-Turn Dialogue Loop", "activeForm": "Step 6: Conducting Dialogue", "status": "pending"},
    {"content": "Step 7: Deep Dive Mode (optional)", "activeForm": "Step 7: Deep Dive Mode", "status": "pending"},
    {"content": "Step 8: Natural Conclusion Detection", "activeForm": "Step 8: Detecting Conclusion", "status": "pending"},
    {"content": "Step 9: Post-Conversation Archival Prompt", "activeForm": "Step 9: Prompting Archival", "status": "pending"},
    {"content": "Step 10: Handle Archival Response", "activeForm": "Step 10: Handling Archival", "status": "pending"}
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
