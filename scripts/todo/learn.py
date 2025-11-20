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
        "content": "Step 1: Validate Input & Check File Size + Content Type",
        "activeForm": "Step 1: Validate Input & Check File Size + Content Type",
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
        "content": "Step 4: Image-Heavy PDF Workflow (2-Phase Approach)",
        "activeForm": "Step 4: Image-Heavy PDF Workflow (2-Phase Approach)",
        "status": "pending"
    },
    {
        "content": "Step 5: Dynamic Single-Page PDF Extraction (Zero-Pollution Visual Study)",
        "activeForm": "Step 5: Dynamic Single-Page PDF Extraction (Zero-Pollution Visual Study)",
        "status": "pending"
    },
    {
        "content": "Step 6: Smart Material Loading (Size-Aware)",
        "activeForm": "Step 6: Smart Material Loading (Size-Aware)",
        "status": "pending"
    },
    {
        "content": "Step 7: Determine Chunk to Learn",
        "activeForm": "Step 7: Determine Chunk to Learn",
        "status": "pending"
    },
    {
        "content": "Step 8: Select Appropriate Agent",
        "activeForm": "Step 8: Select Appropriate Agent",
        "status": "pending"
    },
    {
        "content": "Step 9: Domain Focus Constraints",
        "activeForm": "Step 9: Domain Focus Constraints",
        "status": "pending"
    },
    {
        "content": "Step 10: Consultation-Based Learning Session",
        "activeForm": "Step 10: Consultation-Based Learning Session",
        "status": "pending"
    },
    {
        "content": "Step 11: Post-Session Actions",
        "activeForm": "Step 11: Post-Session Actions",
        "status": "pending"
    },
    {
        "content": "Step 12: User-Facing Output",
        "activeForm": "Step 12: User-Facing Output",
        "status": "pending"
    }
]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
