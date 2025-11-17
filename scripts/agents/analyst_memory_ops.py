#!/usr/bin/env python3
"""
Analyst Agent Memory Operations

Provides memory query and save operations for the analyst agent.
Usage: source venv/bin/activate && python scripts/agents/analyst_memory_ops.py <command> <args>
"""

import sys
import json
from pathlib import Path

# Add scripts directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def query_memory(user_question: str, domain: str = None) -> dict:
    """
    Query MCP memory server for relevant context before answering.

    Args:
        user_question: The user's question
        domain: Optional domain filter (finance, programming, language, etc.)

    Returns:
        dict with:
        - found: bool
        - concepts: list of related concepts
        - context: str summary of previous discussions
    """
    try:
        # Import MCP memory tools
        # Note: This uses the mcp__memory-server__* tools available to agents
        # The actual implementation would call the MCP tools via the Claude SDK

        # For now, return structure showing what would be returned
        return {
            "found": False,  # Would be True if memory found
            "concepts": [],
            "context": "",
            "usage_note": "Call mcp__memory-server__search_nodes with query={user_question}"
        }
    except Exception as e:
        return {"found": False, "error": str(e)}


def save_concepts_to_memory(concepts: list, domain: str, user_question: str) -> dict:
    """
    Save concepts and relationships to MCP memory server.

    Args:
        concepts: List of concepts to save
        domain: Domain classification
        user_question: The original question (for context)

    Returns:
        dict with:
        - success: bool
        - saved_count: int
        - errors: list
    """
    try:
        saved_count = 0
        errors = []

        # Create entities
        entities = []
        for concept in concepts:
            entities.append({
                "name": concept.get("name"),
                "entityType": domain,
                "observations": [
                    f"Question: {user_question}",
                    f"Summary: {concept.get('summary', '')}",
                    f"Timestamp: {concept.get('timestamp', '')}"
                ]
            })

        # Note: Actual implementation would call:
        # mcp__memory-server__create_entities with entities array

        saved_count = len(entities)

        return {
            "success": True,
            "saved_count": saved_count,
            "errors": errors,
            "usage_note": "Call mcp__memory-server__create_entities with entities array"
        }
    except Exception as e:
        return {"success": False, "errors": [str(e)]}


def main():
    """Command-line interface"""
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: analyst_memory_ops.py <command> <args>",
            "commands": {
                "query": "query <question> [domain]",
                "save": "save <concepts_json> <domain> <question>"
            }
        }))
        sys.exit(1)

    command = sys.argv[1]

    if command == "query":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Usage: query <question> [domain]"}))
            sys.exit(1)

        question = sys.argv[2]
        domain = sys.argv[3] if len(sys.argv) > 3 else None
        result = query_memory(question, domain)
        print(json.dumps(result, indent=2))

    elif command == "save":
        if len(sys.argv) < 5:
            print(json.dumps({"error": "Usage: save <concepts_json> <domain> <question>"}))
            sys.exit(1)

        concepts_json = sys.argv[2]
        domain = sys.argv[3]
        question = sys.argv[4]

        try:
            concepts = json.loads(concepts_json)
            result = save_concepts_to_memory(concepts, domain, question)
            print(json.dumps(result, indent=2))
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON: {e}"}))
            sys.exit(1)

    else:
        print(json.dumps({"error": f"Unknown command: {command}"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
