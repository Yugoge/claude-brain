#!/usr/bin/env python3
"""
PreToolUse Hook: Checklist Injection for Subagent Task Calls

This hook runs before Task tool execution and:
1. Detects the subagent being invoked
2. Loads workflow specification from agent file
3. Generates and injects visual checklist
4. Returns appropriate status based on enforcement level
"""

import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from checklist_generator import (
        load_workflow_spec,
        generate_checklist_markdown
    )
except ImportError:
    # Fallback if import fails
    def load_workflow_spec(name, spec_type):
        return None
    def generate_checklist_markdown(spec):
        return ""


def extract_subagent_type(tool_params: dict) -> str:
    """
    Extract subagent type from Task tool parameters.

    Args:
        tool_params: Parameters passed to Task tool

    Returns:
        Subagent type name or empty string
    """
    return tool_params.get("subagent_type", "")


def main():
    """Main hook execution function."""
    try:
        # Read tool input from stdin
        tool_input = json.load(sys.stdin)

        # Extract subagent type
        subagent_type = extract_subagent_type(tool_input)

        if not subagent_type:
            # Not a Task call or no subagent specified
            return {"status": "allow"}

        # Load workflow specification for this agent
        workflow_spec = load_workflow_spec(subagent_type, spec_type="agent")

        if not workflow_spec:
            # No workflow spec found, allow execution
            return {"status": "allow"}

        # Check if checklist is enabled
        if not workflow_spec.get("enabled", False):
            # Checklist disabled, allow execution
            return {"status": "allow"}

        # Check auto_display setting
        auto_display = workflow_spec.get("auto_display", "always")

        if auto_display == "never":
            # Checklist exists but auto-display disabled
            return {"status": "allow"}

        # Generate checklist
        checklist = generate_checklist_markdown(workflow_spec, current_step=0)

        if not checklist:
            # Empty checklist, allow execution
            return {"status": "allow"}

        # Determine status based on enforcement level
        enforcement = workflow_spec.get("enforcement", "advisory")

        if enforcement == "mandatory":
            status = "warn"  # Show warning (non-blocking but visible)
        else:
            status = "allow"  # Advisory only

        # Add agent-specific header
        agent_header = f"\n🤖 SUBAGENT WORKFLOW: {subagent_type}\n"
        full_message = agent_header + checklist

        # Return checklist injection
        return {
            "status": status,
            "message": full_message
        }

    except Exception as e:
        # On error, allow execution (fail-safe)
        return {
            "status": "allow",
            "message": f"⚠️  Subagent checklist hook error: {str(e)}"
        }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
