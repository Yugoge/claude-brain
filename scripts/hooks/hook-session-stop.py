#!/usr/bin/env python3
import os
import sys
"""
SessionStop Hook: Prompt user to archive conversation and commit Git changes
Runs when session ends, checks for uncommitted changes and valuable commands used
"""

import json
import sys
import subprocess
from pathlib import Path

# Portable project root detection using CLAUDE_PROJECT_DIR
# This environment variable is set by Claude Code to the project root
PROJECT_DIR = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))



def check_git_changes() -> tuple[bool, int]:
    """
    Check if there are uncommitted Git changes
    Returns: (has_changes, file_count)
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout.strip()
        if output:
            file_count = len(output.split('\n'))
            return (True, file_count)
        return (False, 0)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return (False, 0)


def main():
    """Main hook execution"""
    try:
        # Read stdin JSON if provided
        stdin_data = {}
        if not sys.stdin.isatty():
            try:
                stdin_data = json.load(sys.stdin)
            except json.JSONDecodeError:
                pass

        # Check Git status
        has_changes, file_count = check_git_changes()

        # Only show prompt if there are changes or notable activity
        if has_changes:
            print("\n💡 Session Summary:")
            print(f"   - Git changes: {file_count} file(s) modified")
            print("\n   Next steps:")
            print("   • /archive-conversation - Archive this dialogue")
            print("   • git commit - Save your changes")
            print("   • Or continue working\n")

        # Always exit 0 (don't block session stop)
        sys.exit(0)

    except Exception as e:
        # Silent fail - don't block session stop
        sys.exit(0)


if __name__ == '__main__':
    main()
