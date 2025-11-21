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
        "activeForm": "Step 0: Initialize Workflow Checklist",
        "status": "pending"
    },
    {
        "content": "Step 1: Archive Conversation",
        "activeForm": "Step 1: Archive Conversation",
        "status": "pending"
    },
    {
        "content": "Step 2: Parse Arguments & Detect Session Type",
        "activeForm": "Step 2: Parse Arguments & Detect Session Type",
        "status": "pending"
    },
    {
        "content": "Step 3: Session Validation",
        "activeForm": "Step 3: Session Validation",
        "status": "pending"
    },
    {
        "content": "Step 4: Filter FSRS Test Dialogues (Review Sessions Only)",
        "activeForm": "Step 4: Filter FSRS Test Dialogues (Review Sessions Only)",
        "status": "pending"
    },
    {
        "content": "Step 5: Domain Classification & ISCED Path Determination",
        "activeForm": "Step 5: Domain Classification & ISCED Path Determination",
        "status": "pending"
    },
    {
        "content": "Step 6: Extract Concepts",
        "activeForm": "Step 6: Extract Concepts",
        "status": "pending"
    },
    {
        "content": "Step 7: Question Type Classification (Review Sessions Only)",
        "activeForm": "Step 7: Question Type Classification (Review Sessions Only)",
        "status": "pending"
    },
    {
        "content": "Step 8: Enrich with Typed Relations via Domain Tutor (MANDATORY)",
        "activeForm": "Step 8: Enrich with Typed Relations via Domain Tutor (MANDATORY)",
        "status": "pending"
    },
    {
        "content": "Step 9: Rem Extraction Transparency",
        "activeForm": "Step 9: Rem Extraction Transparency",
        "status": "pending"
    },
    {
        "content": "Step 10: Generate Preview (Format depends on session type)",
        "activeForm": "Step 10: Generate Preview (Format depends on session type)",
        "status": "pending"
    },
    {
        "content": "Step 11: User Confirmation",
        "activeForm": "Step 11: User Confirmation",
        "status": "pending"
    },
    {
        "content": "Step 12: Pre-creation Validation",
        "activeForm": "Step 12: Pre-creation Validation",
        "status": "pending"
    },
    {
        "content": "Step 13: Create Knowledge Rems",
        "activeForm": "Step 13: Create Knowledge Rems",
        "status": "pending"
    },
    {
        "content": "Step 14: Process Conversation Archive",
        "activeForm": "Step 14: Process Conversation Archive",
        "status": "pending"
    },
    {
        "content": "Step 15: Update Existing Rems (Review Sessions with Type A Clarifications)",
        "activeForm": "Step 15: Update Existing Rems (Review Sessions with Type A Clarifications)",
        "status": "pending"
    },
    {
        "content": "Step 16: Update Knowledge Graph",
        "activeForm": "Step 16: Update Knowledge Graph",
        "status": "pending"
    },
    {
        "content": "Step 17: Materialize Inferred Links (Optional)",
        "activeForm": "Step 17: Materialize Inferred Links (Optional)",
        "status": "pending"
    },
    {
        "content": "Step 18: Sync Rems to Review Schedule (Auto)",
        "activeForm": "Step 18: Sync Rems to Review Schedule (Auto)",
        "status": "pending"
    },
    {
        "content": "Step 19: Record to Memory MCP (Auto)",
        "activeForm": "Step 19: Record to Memory MCP (Auto)",
        "status": "pending"
    },
    {
        "content": "Step 20: Update Conversation Rem Links",
        "activeForm": "Step 20: Update Conversation Rem Links",
        "status": "pending"
    },
    {
        "content": "Step 21: Generate Analytics & Visualizations",
        "activeForm": "Step 21: Generate Analytics & Visualizations",
        "status": "pending"
    },
    {
        "content": "Step 22: Display Completion Report",
        "activeForm": "Step 22: Display Completion Report",
        "status": "pending"
    }
]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
