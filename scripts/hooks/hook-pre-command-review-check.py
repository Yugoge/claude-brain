#!/usr/bin/env python3
"""
PreToolUse Hook: Pre-Command Review Check (Review Gating Mode)

This hook implements input-output balance for knowledge management:
- Before input tasks (learn/ask/fact-check), enforce output (review)
- Prevents knowledge accumulation without consolidation
- Maintains FSRS schedule effectiveness through consistent review

Hook behavior:
- Checks if command requires review gating (configurable via env)
- If reviews are due: Returns instruction to conduct mini review
- After review completion: Original command proceeds
- No hardcoded commands, messages, or thresholds

Architecture:
- Hook → Returns JSON instruction
- Main agent → Interprets instruction, generates dialogue
- Review-master → Provides question guidance (JSON consultant)
"""

import sys
import json
import os
import subprocess
from pathlib import Path

# Portable project root detection
PROJECT_DIR = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))

# Configuration from environment (NO hardcoded defaults)
# All configuration MUST come from .claude/settings.json env field
TRIGGER_COMMANDS_STR = os.environ.get('REVIEW_GATE_COMMANDS', '')
TRIGGER_COMMANDS = TRIGGER_COMMANDS_STR.split(',') if TRIGGER_COMMANDS_STR else []
ENABLED = os.environ.get('REVIEW_GATE_ENABLED', '0') == '1'
THRESHOLD = int(os.environ.get('REVIEW_GATE_THRESHOLD', '0'))


def extract_command_name(command_string: str) -> str:
    """Extract command name from slash command string."""
    if not command_string or not command_string.startswith("/"):
        return ""

    parts = command_string.split()
    if not parts:
        return ""

    return parts[0]


def call_mini_review_selector(original_command: str) -> dict:
    """
    Call mini_review_session.py to select rem and get instruction.

    Returns:
        {
          "status": "review_required" | "no_reviews_due",
          "instruction": {...} | None
        }
    """
    script_path = PROJECT_DIR / 'scripts/review/mini_review_session.py'
    schedule_path = PROJECT_DIR / '.review/schedule.json'

    try:
        # Use venv python
        venv_python = PROJECT_DIR / 'venv/bin/python'
        if not venv_python.exists():
            # Fallback to system python if venv not found
            venv_python = 'python3'

        result = subprocess.run(
            [str(venv_python), str(script_path),
             '--schedule', str(schedule_path),
             '--command', original_command],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "message": f"Mini review selector failed: {result.stderr}"
            }

        return json.loads(result.stdout)

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Mini review selector timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Mini review selector error: {str(e)}"
        }


def format_review_gate_instruction(instruction: dict) -> str:
    """
    Format minimal instruction for main agent.

    Returns ONLY data in JSON format - NO messages, NO workflow steps.
    Main agent interprets data and generates dialogue/workflow flexibly.
    """
    # Return minimal JSON data only
    return json.dumps(instruction, indent=2)


def main():
    """Main hook execution function."""
    try:
        # Check if enabled
        if not ENABLED:
            return {"status": "allow"}

        # Read tool input from stdin
        tool_input = json.load(sys.stdin)
        command = tool_input.get("command", "")

        # Extract command name
        cmd_name = extract_command_name(command)

        if not cmd_name:
            return {"status": "allow"}

        # Check if command requires review gating
        if cmd_name not in TRIGGER_COMMANDS:
            return {"status": "allow"}

        # Call mini review selector
        selection_result = call_mini_review_selector(command)

        if selection_result.get("status") == "no_reviews_due":
            # No reviews pending, allow execution
            return {"status": "allow"}

        if selection_result.get("status") == "error":
            # Error in selector, fail-safe to allow
            return {
                "status": "allow",
                "message": f"⚠️ Review gate error (allowing): {selection_result.get('message')}"
            }

        # Review required
        instruction = selection_result.get("instruction")
        if not instruction:
            return {"status": "allow"}

        # Format minimal instruction (data only, no message)
        instruction_json = format_review_gate_instruction(instruction)

        # Return minimal data - main agent generates dialogue
        return {
            "status": "warn",
            "message": instruction_json
        }

    except Exception as e:
        # Fail-safe: allow execution on error
        return {
            "status": "allow",
            "message": f"⚠️ Review check error: {str(e)}"
        }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result))
