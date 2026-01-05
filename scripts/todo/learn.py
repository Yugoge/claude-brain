#!/usr/bin/env python3
"""
Preloaded TodoList for learn workflow.

Auto-generated from workflow steps extraction.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
    {
        "content": "Step 1: Validate Input & File Size",
        "activeForm": "Step 1: Validate Input & File Size",
        "status": "pending"
    },
    {
        "content": "Step 2: Detect Material Type & Domain",
        "activeForm": "Step 2: Detect Material Type & Domain",
        "status": "pending"
    },
    {
        "content": "Step 3: Load or Create Progress File",
        "activeForm": "Step 3: Load or Create Progress File",
        "status": "pending"
    },
    {
        "content": "Step 4: Image-Heavy PDF Workflow",
        "activeForm": "Step 4: Image-Heavy PDF Workflow",
        "status": "pending"
    },
    {
        "content": "Step 5: Single-Page PDF Extraction",
        "activeForm": "Step 5: Single-Page PDF Extraction",
        "status": "pending"
    },
    {
        "content": "Step 6: Smart Material Loading",
        "activeForm": "Step 6: Smart Material Loading",
        "status": "pending"
    },
    {
        "content": "Step 7: Determine Chunk to Learn",
        "activeForm": "Step 7: Determine Chunk to Learn",
        "status": "pending"
    },
    {
        "content": "Step 8: Segment Content for Progressive Display",
        "activeForm": "Step 8: Segment Content for Progressive Display",
        "status": "pending"
    },
    {
        "content": "Step 9: Select Appropriate Agent",
        "activeForm": "Step 9: Select Appropriate Agent",
        "status": "pending"
    },
    {
        "content": "Step 10: Domain Focus Constraints",
        "activeForm": "Step 10: Domain Focus Constraints",
        "status": "pending"
    },
    {
        "content": "Step 11: Consultation-Based Learning",
        "activeForm": "Step 11: Consultation-Based Learning",
        "status": "pending"
    },
    {
        "content": "Step 12: Post-Session Actions",
        "activeForm": "Step 12: Post-Session Actions",
        "status": "pending"
    },
    {
        "content": "Step 13: User-Facing Output",
        "activeForm": "Step 13: User-Facing Output",
        "status": "pending"
    }
]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
