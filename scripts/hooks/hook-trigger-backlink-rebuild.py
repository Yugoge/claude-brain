#!/usr/bin/env python3
"""
PostToolUse Edit Hook: Trigger link normalization and backlink rebuild
after knowledge-base edits. Automatically maintains graph integrity.

Story 1.13 - Automated workflow:
1. Normalize [[wikilinks]] to clickable [Title](path.md) links
2. Rebuild backlinks index with typed and inferred links
"""

import sys
import json
import subprocess
import os
from pathlib import Path

# Portable project root detection using CLAUDE_PROJECT_DIR
# This environment variable is set by Claude Code to the project root
PROJECT_DIR = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))


def main():
    """Trigger link normalization and backlink rebuild if KB file was edited"""
    try:
        # Read stdin JSON
        data = json.load(sys.stdin)
        file_path = data.get('tool_input', {}).get('file_path', '')

        # Check if knowledge-base concept file was edited
        # Only trigger for actual concept files to avoid excessive runs
        if 'knowledge-base/' in file_path and '/concepts/' in file_path:
            scripts_dir = PROJECT_DIR / 'scripts'
            
            # Step 1: Normalize wikilinks to markdown file links
            normalize_script = scripts_dir / 'normalize-links.py'
            if normalize_script.exists():
                subprocess.run(
                    ['python3', str(normalize_script), '--mode', 'replace'],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    cwd=PROJECT_DIR
                )
            
            # Step 2: Rebuild backlinks index (includes typed + inferred links)
            # Auto-cleanup: keep only 1 most recent backup
            rebuild_script = scripts_dir / 'rebuild-backlinks.py'
            if rebuild_script.exists():
                subprocess.run(
                    ['python3', str(rebuild_script), '--cleanup-backups', '1'],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    cwd=PROJECT_DIR
                )

        sys.exit(0)  # Always succeed (don't block workflow)

    except Exception:
        # Silent fail - automation shouldn't block workflow
        sys.exit(0)


if __name__ == '__main__':
    main()
