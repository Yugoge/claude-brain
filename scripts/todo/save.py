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
        "content": "Step 1: Pre-Processing (Batch Execution)",
        "activeForm": "Step 1: Pre-Processing (Batch Execution)",
        "status": "pending"
    },
    {
        "content": "Step 2: Domain Classification & ISCED Path (AI + Subagent)",
        "activeForm": "Step 2: Domain Classification & ISCED Path (AI + Subagent)",
        "status": "pending"
    },
    {
        "content": "Step 3: Extract Concepts (AI-driven, no file creation)",
        "activeForm": "Step 3: Extract Concepts (AI-driven, no file creation)",
        "status": "pending"
    },
    {
        "content": "Step 4: Analyze User Learning & Rem Updates (Learn/Review Sessions)",
        "activeForm": "Step 4: Analyze User Learning & Rem Updates (Learn/Review Sessions)",
        "status": "pending"
    },
    {
        "content": "Step 5: Enrich with Typed Relations via Domain Tutor (AI + Subagent)",
        "activeForm": "Step 5: Enrich with Typed Relations via Domain Tutor (AI + Subagent)",
        "status": "pending"
    },
    {
        "content": "Step 6: Rem Extraction Transparency",
        "activeForm": "Step 6: Rem Extraction Transparency",
        "status": "pending"
    },
    {
        "content": "Step 7: Generate Preview",
        "activeForm": "Step 7: Generate Preview",
        "status": "pending"
    },
    {
        "content": "Step 8: User Confirmation",
        "activeForm": "Step 8: User Confirmation",
        "status": "pending"
    },
    {
        "content": "Step 9: Update Learning Material Progress (Learn Sessions Only)",
        "activeForm": "Step 9: Update Learning Material Progress (Learn Sessions Only)",
        "status": "pending"
    },
    {
        "content": "Step 10: Execute Automated Post-Processing",
        "activeForm": "Step 10: Execute Automated Post-Processing",
        "status": "pending"
    }
]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
