#!/usr/bin/env python3
"""
Preloaded TodoList for graph workflow.

Aligned with .claude/commands/graph.md workflow steps.
"""


def get_todos():
    """
    Return list of todo items for TodoWrite.

    Returns:
        list[dict]: Todo items with content, activeForm, status
    """
    return [
        {
            "content": "Step 1: Parse Arguments",
            "activeForm": "Parsing command arguments",
            "status": "pending"
        },
        {
            "content": "Step 2: Generate Analytics Data",
            "activeForm": "Generating analytics data",
            "status": "pending"
        },
        {
            "content": "Step 3: Generate Knowledge Graph Data",
            "activeForm": "Generating knowledge graph data",
            "status": "pending"
        },
        {
            "content": "Step 4: Generate Visualization HTML Files",
            "activeForm": "Generating HTML visualizations",
            "status": "pending"
        },
        {
            "content": "Step 5: Preview Results",
            "activeForm": "Previewing generated files",
            "status": "pending"
        },
        {
            "content": "Step 6: Auto-Deploy (if credentials available)",
            "activeForm": "Deploying to GitHub Pages",
            "status": "pending"
        }
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
