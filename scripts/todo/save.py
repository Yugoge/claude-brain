#!/usr/bin/env python3
"""
Preloaded TodoList for save workflow.

Auto-generated from workflow steps extraction.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
    {"content": "Step 0: Archive Conversation", "activeForm": "Step 0: Archive Conversation", "status": "pending"},
    {"content": "Step 1: Parse Arguments & Detect Session Type", "activeForm": "Step 1: Parse Arguments & Detect Session Type", "status": "pending"},
    {"content": "Step 1.1: Detect Session Type", "activeForm": "Step 1.1: Detect Session Type", "status": "pending"},
    {"content": "Step 2: Validate Conversation & Filter FSRS Tests", "activeForm": "Step 2: Validate Conversation & Filter FSRS Tests", "status": "pending"},
    {"content": "Step 2.1: Filter FSRS Test Dialogues", "activeForm": "Step 2.1: Filter FSRS Test Dialogues", "status": "pending"},
    {"content": "Step 2.5: Domain Classification & ISCED Path Determination", "activeForm": "Step 2.5: Domain Classification & ISCED Path Determination", "status": "pending"},
    {"content": "Step 3: Extract Concepts", "activeForm": "Step 3: Extract Concepts", "status": "pending"},
    {"content": "Step 3.1: Question Type Classification", "activeForm": "Step 3.1: Question Type Classification", "status": "pending"},
    {"content": "Step 3.5: Enrich with Typed Relations via Domain Tutor", "activeForm": "Step 3.5: Enrich with Typed Relations via Domain Tutor", "status": "pending"},
    {"content": "Step 3.6: Rem Extraction Transparency", "activeForm": "Step 3.6: Rem Extraction Transparency", "status": "pending"},
    {"content": "Step 4: Generate Preview", "activeForm": "Step 4: Generate Preview", "status": "pending"},
    {"content": "Step 4.1: Learn/Ask Session Preview", "activeForm": "Step 4.1: Learn/Ask Session Preview", "status": "pending"},
    {"content": "Step 4.2: Review Session Preview", "activeForm": "Step 4.2: Review Session Preview", "status": "pending"},
    {"content": "Step 5: User Confirmation", "activeForm": "Step 5: User Confirmation", "status": "pending"},
    {"content": "Step 5.5: Pre-creation Validation", "activeForm": "Step 5.5: Pre-creation Validation", "status": "pending"},
    {"content": "Step 6: Create Files", "activeForm": "Step 6: Create Files", "status": "pending"},
    {"content": "Step 7: Update Conversation Rem Links", "activeForm": "Step 7: Update Conversation Rem Links", "status": "pending"},
    {"content": "Step 8: Auto-generate Statistics & Visualizations", "activeForm": "Step 8: Auto-generate Statistics & Visualizations", "status": "pending"},
    {"content": "Step 8.1: Generate Learning Analytics", "activeForm": "Step 8.1: Generate Learning Analytics", "status": "pending"},
    {"content": "Step 8.2: Generate Interactive Visualizations", "activeForm": "Step 8.2: Generate Interactive Visualizations", "status": "pending"},
    {"content": "Step 8.3: Display Summary to User", "activeForm": "Step 8.3: Display Summary to User", "status": "pending"},
    {"content": "Step 9: Completion Report", "activeForm": "Step 9: Completion Report", "status": "pending"}
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
