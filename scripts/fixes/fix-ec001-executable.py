#!/usr/bin/env python3
"""
Fix EC001 violations in executable code (scripts, .claude commands/agents, tests)

Skips:
- docs/ (documentation samples)
- chats/ (conversation archives)
- knowledge-base/ (learning content)

Usage:
    source venv/bin/activate && source venv/bin/activate && python3 fix-ec001-executable.py [--dry-run] [--verbose]
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
DRY_RUN = "--dry-run" in sys.argv
VERBOSE = "--verbose" in sys.argv

# Directories to fix
FIX_DIRS = [
    "scripts",
    ".claude",
    "tests",
    "README.md"
]

# Patterns to fix
PATTERNS = [
    # Pattern 1: python3/python at line start
    (r'^(\s*)(python3?\s+)', r'\1source venv/bin/activate && \2'),

    # Pattern 2: After pipe/semicolon/ampersand
    (r'([|;&]\s*)(python3?\s+)', r'\1source venv/bin/activate && \2'),

    # Pattern 3: In subshells $(python3 ...)
    (r'\$\((python3?\s+)', r'$(source venv/bin/activate && \1'),

    # Pattern 4: In backticks `python3 ...`
    (r'`(python3?\s+)', r'`source venv/bin/activate && \1'),
]

# Skip patterns (already correct)
SKIP_PATTERNS = [
    r'source.*venv.*activate.*&&.*python',
    r'#.*python',  # Comments
    r'^\s*python:',  # YAML keys
    r'```python',  # Code block markers
]

def should_skip_line(line: str) -> bool:
    """Check if line should be skipped"""
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False

def fix_line(line: str) -> Tuple[str, bool]:
    """Fix a single line, return (fixed_line, was_modified)"""
    if should_skip_line(line):
        return line, False

    original = line
    for pattern, replacement in PATTERNS:
        line = re.sub(pattern, replacement, line)

    return line, (line != original)

def fix_file(filepath: Path) -> int:
    """Fix a file, return number of lines changed"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0

    fixed_lines = []
    changes = 0

    for line in lines:
        fixed, modified = fix_line(line)
        fixed_lines.append(fixed)
        if modified:
            changes += 1

    if changes > 0:
        if DRY_RUN:
            print(f"Would fix {changes} lines in: {filepath.relative_to(PROJECT_ROOT)}")
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(fixed_lines)
            print(f"Fixed {changes} lines in: {filepath.relative_to(PROJECT_ROOT)}")
    elif VERBOSE:
        print(f"No changes needed: {filepath.relative_to(PROJECT_ROOT)}")

    return changes

def find_files_to_fix() -> List[Path]:
    """Find all files that need fixing"""
    files = []

    for dir_name in FIX_DIRS:
        dir_path = PROJECT_ROOT / dir_name

        if dir_path.is_file():
            # README.md
            files.append(dir_path)
        elif dir_path.is_dir():
            # Find all .sh, .py, .md files recursively
            for ext in ['*.sh', '*.py', '*.md']:
                files.extend(dir_path.rglob(ext))

    # Filter out venv, node_modules, etc
    filtered = []
    for f in files:
        rel_path = str(f.relative_to(PROJECT_ROOT))
        if any(skip in rel_path for skip in ['venv/', 'node_modules/', '__pycache__/']):
            continue
        filtered.append(f)

    return sorted(filtered)

def main():
    print("="*60)
    print("EC001 Executable Code Fixer")
    print("="*60)
    print()

    if DRY_RUN:
        print("🔍 DRY RUN MODE - No files will be modified")
        print()

    files = find_files_to_fix()
    print(f"Found {len(files)} files to check")
    print()

    if VERBOSE:
        print("Checking:")
        for f in files[:10]:
            print(f"  {f.relative_to(PROJECT_ROOT)}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
        print()

    total_files_fixed = 0
    total_lines_fixed = 0

    for filepath in files:
        changes = fix_file(filepath)
        if changes > 0:
            total_files_fixed += 1
            total_lines_fixed += changes

    print()
    print("="*60)
    print("Summary")
    print("="*60)
    print(f"Files checked: {len(files)}")
    print(f"Files modified: {total_files_fixed}")
    print(f"Lines changed: {total_lines_fixed}")

    if DRY_RUN:
        print()
        print("This was a dry run. Run without --dry-run to apply changes.")

if __name__ == "__main__":
    main()
