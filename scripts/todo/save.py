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
    {"content": "Step 1: Archive Conversation", "activeForm": "Step 1: Archive Conversation", "status": "pending"},
    {"content": "Step 2: Parse Arguments & Detect Session Type", "activeForm": "Step 2: Parse Arguments & Detect Session Type", "status": "pending"},
    {"content": "Step 3: Detect Session Type", "activeForm": "Step 3: Detect Session Type", "status": "pending"},
    {"content": "Step 4: Validate Conversation & Filter FSRS Tests", "activeForm": "Step 4: Validate Conversation & Filter FSRS Tests", "status": "pending"},
    {"content": "Step 5: Filter FSRS Test Dialogues", "activeForm": "Step 5: Filter FSRS Test Dialogues", "status": "pending"},
    {"content": "Step 6: Domain Classification & ISCED Path Determination", "activeForm": "Step 6: Domain Classification & ISCED Path Determination", "status": "pending"},
    {"content": "Step 7: Extract Concepts", "activeForm": "Step 7: Extract Concepts", "status": "pending"},
    {"content": "Step 8: Question Type Classification", "activeForm": "Step 8: Question Type Classification", "status": "pending"},
    {"content": "Step 9: Enrich with Typed Relations via Domain Tutor", "activeForm": "Step 9: Enrich with Typed Relations via Domain Tutor", "status": "pending"},
    {"content": "Step 10: Rem Extraction Transparency", "activeForm": "Step 10: Rem Extraction Transparency", "status": "pending"},
    {"content": "Step 11: Generate Preview", "activeForm": "Step 11: Generate Preview", "status": "pending"},
    {"content": "Step 12: Learn/Ask Session Preview", "activeForm": "Step 12: Learn/Ask Session Preview", "status": "pending"},
    {"content": "Step 13: Review Session Preview", "activeForm": "Step 13: Review Session Preview", "status": "pending"},
    {"content": "Step 14: User Confirmation", "activeForm": "Step 14: User Confirmation", "status": "pending"},
    {"content": "Step 15: Pre-creation Validation", "activeForm": "Step 15: Pre-creation Validation", "status": "pending"},
    {"content": "Step 16: Create Files", "activeForm": "Step 16: Create Files", "status": "pending"},
    {"content": "Step 17: Update Conversation Rem Links", "activeForm": "Step 17: Update Conversation Rem Links", "status": "pending"},
    {"content": "Step 18: Auto-generate Statistics & Visualizations", "activeForm": "Step 18: Auto-generate Statistics & Visualizations", "status": "pending"},
    {"content": "Step 19: Generate Learning Analytics", "activeForm": "Step 19: Generate Learning Analytics", "status": "pending"},
    {"content": "Step 20: Generate Interactive Visualizations", "activeForm": "Step 20: Generate Interactive Visualizations", "status": "pending"},
    {"content": "Step 21: Display Summary to User", "activeForm": "Step 21: Display Summary to User", "status": "pending"},
    {"content": "Step 22: Completion Report", "activeForm": "Step 22: Completion Report", "status": "pending"}
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
