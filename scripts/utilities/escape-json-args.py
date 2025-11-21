#!/usr/bin/env python3
"""
Bash-Safe JSON Argument Escaper

Escapes JSON strings for safe use in bash command-line arguments.
Handles special characters like parentheses, quotes, and brackets.

Usage:
    # From file
    python escape-json-args.py < input.json

    # From stdin
    echo '["Text (with parens)"]' | python escape-json-args.py

    # In bash commands
    --mistakes "$(python escape-json-args.py < mistakes.json)"

Why needed:
    Bash interprets parentheses as subshell operators even in single quotes
    when passed through eval. This script escapes special chars for safety.

Examples:
    Input:  ["Assuming HFT (High Frequency Trading) works"]
    Output: [\"Assuming HFT \\(High Frequency Trading\\) works\"]
"""

import sys
import json
import shlex

def escape_json_for_bash(data):
    """
    Escape JSON data for bash command-line usage.

    Args:
        data: Python object (list, dict, str, etc.)

    Returns:
        str: Bash-safe escaped JSON string
    """
    # Convert to JSON string
    json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    # Use shlex.quote for proper shell escaping
    # This handles all special characters including (), [], {}, $, `, etc.
    return shlex.quote(json_str)

def main():
    try:
        # Read from stdin
        input_data = sys.stdin.read().strip()

        if not input_data:
            print("Error: No input provided", file=sys.stderr)
            print("Usage: echo '[]' | python escape-json-args.py", file=sys.stderr)
            sys.exit(1)

        # Parse JSON
        try:
            data = json.loads(input_data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON - {e}", file=sys.stderr)
            sys.exit(1)

        # Escape and output
        escaped = escape_json_for_bash(data)
        print(escaped)

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
