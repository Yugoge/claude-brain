#!/usr/bin/env python3
"""
Preloaded TodoList for classification-expert workflow.

Auto-generated from workflow steps extraction.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
    {"content": "Step 1: Load Taxonomy Reference", "activeForm": "Step 1: Load Taxonomy Reference", "status": "pending"},
    {"content": "Step 2: Analyze Question Semantics", "activeForm": "Step 2: Analyze Question Semantics", "status": "pending"},
    {"content": "Step 3: Classify with Confidence Scoring", "activeForm": "Step 3: Classify with Confidence Scoring", "status": "pending"},
    {"content": "Step 4: Map to ISCED Taxonomy Codes", "activeForm": "Step 4: Map to ISCED Taxonomy Codes", "status": "pending"},
    {"content": "Step 5: Generate Rationale", "activeForm": "Step 5: Generate Rationale", "status": "pending"}
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
