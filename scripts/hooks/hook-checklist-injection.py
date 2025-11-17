#!/usr/bin/env python3
"""
PreToolUse Hook: Checklist Injection for Slash Commands

This hook runs before SlashCommand tool execution and:
1. Detects the command being executed
2. Loads workflow specification from command file
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


def extract_command_name(command_string: str) -> str:
    """
    Extract command name from slash command string.

    Examples:
        "/learn file.pdf" → "learn"
        "/save topic" → "save"
        "/review" → "review"

    Args:
        command_string: Full command string from tool input

    Returns:
        Command name without leading slash
    """
    if not command_string or not command_string.startswith("/"):
        return ""

    # Split and get first word, remove leading slash
    parts = command_string.split()
    if not parts:
        return ""

    cmd_name = parts[0][1:]  # Remove leading "/"

    # Handle nested commands (e.g., "/BMad:agents:analyst" → "BMad/agents/analyst")
    cmd_name = cmd_name.replace(":", "/")

    return cmd_name


def main():
    """Main hook execution function."""
    try:
        # Read tool input from stdin
        tool_input = json.load(sys.stdin)
        command = tool_input.get("command", "")

        # Extract command name
        cmd_name = extract_command_name(command)

        if not cmd_name:
            # Not a slash command, allow execution
            return {"status": "allow"}

        # Load workflow specification
        workflow_spec = load_workflow_spec(cmd_name, spec_type="command")

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

        # TODO: Implement "first_time" logic with state tracking
        # For now, treat "first_time" as "always"

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

        # Return checklist injection
        return {
            "status": status,
            "message": checklist
        }

    except Exception as e:
        # On error, allow execution (fail-safe)
        return {
            "status": "allow",
            "message": f"⚠️  Checklist hook error: {str(e)}"
        }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
