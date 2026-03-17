#!/usr/bin/env python3
"""
Preloaded TodoList for kb-init workflow.

Provides structured task list for /kb-init command's initialization checks.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
        {
            "content": "Check 1: Validate Directory Structure",
            "activeForm": "Validating directory structure",
            "status": "pending"
        },
        {
            "content": "Check 2: Validate JSON Files (backlinks, taxonomy, index, schedule)",
            "activeForm": "Validating JSON files",
            "status": "pending"
        },
        {
            "content": "Check 3: Repair Corrupted Files",
            "activeForm": "Repairing corrupted files",
            "status": "pending"
        },
        {
            "content": "Check 4: Verify Agent Files",
            "activeForm": "Verifying agent files",
            "status": "pending"
        },
        {
            "content": "Check 5: Git Health Check",
            "activeForm": "Running Git health check",
            "status": "pending"
        },
        {
            "content": "Check 6: Python Dependencies",
            "activeForm": "Checking Python dependencies",
            "status": "pending"
        },
        {
            "content": "Check 7: Script Permissions",
            "activeForm": "Verifying script permissions",
            "status": "pending"
        },
        {
            "content": "Check 8: Generate Comprehensive Report",
            "activeForm": "Generating comprehensive report",
            "status": "pending"
        },
        {
            "content": "Check 9: Interactive Repairs (if needed)",
            "activeForm": "Running interactive repairs",
            "status": "pending"
        },
        {
            "content": "Check 10: Final Validation",
            "activeForm": "Running final validation",
            "status": "pending"
        }
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
