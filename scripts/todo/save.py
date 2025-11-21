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
            "content": "Step 1: Archive Conversation",
            "activeForm": "Archiving conversation",
            "status": "pending"
        },
        {
            "content": "Step 2: Parse Arguments",
            "activeForm": "Parsing arguments",
            "status": "pending"
        },
        {
            "content": "Step 3: Session Validation",
            "activeForm": "Validating session",
            "status": "pending"
        },
        {
            "content": "Step 4: Filter FSRS Test Dialogues (Review Sessions Only)",
            "activeForm": "Filtering FSRS test dialogues",
            "status": "pending"
        },
        {
            "content": "Step 5: Domain Classification & ISCED Path",
            "activeForm": "Classifying domain",
            "status": "pending"
        },
        {
            "content": "Step 6: Extract Concepts",
            "activeForm": "Extracting concepts",
            "status": "pending"
        },
        {
            "content": "Step 7: Question Type Classification (Review Sessions Only)",
            "activeForm": "Classifying question types",
            "status": "pending"
        },
        {
            "content": "Step 8: Enrich with Typed Relations (MANDATORY)",
            "activeForm": "Enriching with typed relations",
            "status": "pending"
        },
        {
            "content": "Step 9: Rem Extraction Transparency",
            "activeForm": "Presenting extracted Rems",
            "status": "pending"
        },
        {
            "content": "Step 10: Generate Preview",
            "activeForm": "Generating preview",
            "status": "pending"
        },
        {
            "content": "Step 11: User Confirmation",
            "activeForm": "Awaiting user confirmation",
            "status": "pending"
        },
        {
            "content": "Step 12: Execute Post-Processing (automated Steps 12-22)",
            "activeForm": "Executing post-processing",
            "status": "pending"
        }
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
