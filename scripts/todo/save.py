#!/usr/bin/env python3
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
        {
            "content": "Step 0: Initialize Workflow Checklist",
            "activeForm": "Initializing workflow checklist",
            "status": "pending"
        },
        {
            "content": "Step 1: Pre-Processing (Batch Execution)",
            "activeForm": "Running pre-processing orchestrator",
            "status": "pending"
        },
        {
            "content": "Step 2: Domain Classification & ISCED Path",
            "activeForm": "Classifying domain",
            "status": "pending"
        },
        {
            "content": "Step 3: Extract Concepts",
            "activeForm": "Extracting concepts",
            "status": "pending"
        },
        {
            "content": "Step 4: Question Type Classification (Review Sessions Only)",
            "activeForm": "Classifying question types",
            "status": "pending"
        },
        {
            "content": "Step 5: Enrich with Typed Relations (MANDATORY)",
            "activeForm": "Enriching with typed relations",
            "status": "pending"
        },
        {
            "content": "Step 6: Rem Extraction Transparency",
            "activeForm": "Presenting extracted Rems",
            "status": "pending"
        },
        {
            "content": "Step 7: Generate Preview",
            "activeForm": "Generating preview",
            "status": "pending"
        },
        {
            "content": "Step 8: User Confirmation",
            "activeForm": "Awaiting user confirmation",
            "status": "pending"
        },
        {
            "content": "Step 9: Update Learning Material Progress (Learn Sessions Only)",
            "activeForm": "Updating learning material progress",
            "status": "pending"
        },
        {
            "content": "Step 10: Execute Post-Processing (Batch Execution)",
            "activeForm": "Running post-processing orchestrator",
            "status": "pending"
        }
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
