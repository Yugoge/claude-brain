#!/usr/bin/env python3
"""
Preloaded TodoList for maintain workflow.

Provides structured task list for /maintain command's 9 maintenance tasks.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
        # Phase 1: Validation
        {
            "content": "Task 1: Validate Rem Formats (v2.0 Compliance)",
            "activeForm": "Validating Rem formats",
            "status": "pending"
        },
        {
            "content": "Task 2: Validate Rem Size (150-200 Token Target)",
            "activeForm": "Validating Rem sizes",
            "status": "pending"
        },
        {
            "content": "Task 3: Validate YAML Frontmatter",
            "activeForm": "Validating YAML frontmatter",
            "status": "pending"
        },
        {
            "content": "Task 4: Check Source Fields",
            "activeForm": "Checking source fields",
            "status": "pending"
        },
        # Phase 2: Basic Fixes
        {
            "content": "Task 5: Add Missing rem_ids",
            "activeForm": "Adding missing rem_ids",
            "status": "pending"
        },
        # Phase 3: Advanced Maintenance
        {
            "content": "Task 6: Rebuild Backlinks (Full Rebuild)",
            "activeForm": "Rebuilding backlinks index",
            "status": "pending"
        },
        {
            "content": "Task 7: Sync Related Rems from Backlinks",
            "activeForm": "Syncing related Rems sections",
            "status": "pending"
        },
        {
            "content": "Task 8: Standardize Rem Names (Domain-Specific)",
            "activeForm": "Standardizing Rem names",
            "status": "pending"
        },
        {
            "content": "Task 9: Sync to FSRS Review Schedule",
            "activeForm": "Syncing to FSRS review schedule",
            "status": "pending"
        }
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
