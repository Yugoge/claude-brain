#!/usr/bin/env python3
import os
import sys


"""
UserPromptSubmit Hook: Safety check for destructive commands
Blocks user input containing dangerous commands: rm, -rf, rd, del
"""

import sys
import json
import re
from pathlib import Path

# Portable project root detection using CLAUDE_PROJECT_DIR
# This environment variable is set by Claude Code to the project root
PROJECT_DIR = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))



def main():
    """Check user input for destructive commands"""
    try:
        # Read stdin JSON
        data = json.load(sys.stdin)
        user_input = data.get('user_input', '')

        # Check for destructive patterns
        if user_input and re.search(r'rm\s|-rf|rd\s|del\s', user_input, re.IGNORECASE):
            print("⚠️  Warning: Destructive command detected in user input")
            sys.exit(1)  # Block with warning

        sys.exit(0)  # Allow

    except Exception:
        # On error, don't block
        sys.exit(0)


if __name__ == '__main__':
    main()
