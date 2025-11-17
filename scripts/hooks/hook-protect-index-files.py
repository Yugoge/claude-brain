#!/usr/bin/env python3
import os
import sys


"""
PreToolUse Edit Hook: Protect knowledge-base/_index/ from direct edits
Index files should only be modified by knowledge-indexer agent
"""

import sys
import json
from pathlib import Path

# Portable project root detection using CLAUDE_PROJECT_DIR
# This environment variable is set by Claude Code to the project root
PROJECT_DIR = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))



def main():
    """Block edits to index directory"""
    try:
        # Read stdin JSON
        data = json.load(sys.stdin)
        file_path = data.get('tool_input', {}).get('file_path', '')

        # Check if editing protected index files
        if 'knowledge-base/_index/' in file_path:
            print("⚠️  Warning: Cannot edit index files directly. Use knowledge-indexer agent.")
            sys.exit(1)  # Block with warning

        sys.exit(0)  # Allow

    except Exception:
        # On error, don't block
        sys.exit(0)


if __name__ == '__main__':
    main()
