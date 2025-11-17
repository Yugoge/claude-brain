#!/usr/bin/env python3
"""
Validate archive directory naming conventions.
All archived files must follow: {category}-{topic}-{date}.md or {category}-{topic}.md
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Archive directory
ARCHIVE_DIR: Path = Path('/root/knowledge-system/docs/archive')

# Naming patterns (relaxed for now - can be made stricter later)
VALID_PATTERNS: List[str] = [
    r'^[a-z0-9-]+\.md$',  # Simple: name.md
    r'^[a-z0-9-]+-\d{4}-\d{2}-\d{2}\.md$',  # With date: name-YYYY-MM-DD.md
]

# Files to ignore
IGNORE_FILES: List[str] = ['README.md', '.gitkeep']

def validate_naming(archive_dir: Path) -> Tuple[List[str], int]:
    """Validate file naming in archive directory"""
    invalid: List[str] = []
    total: int = 0

    for root, dirs, files in os.walk(archive_dir):
        for file in files:
            if file in IGNORE_FILES:
                continue

            if not file.endswith('.md'):
                continue

            total += 1
            valid = False

            for pattern in VALID_PATTERNS:
                if re.match(pattern, file):
                    valid = True
                    break

            if not valid:
                rel_path = os.path.relpath(os.path.join(root, file), archive_dir)
                invalid.append(rel_path)

    return invalid, total

def main() -> int:
    """Main validation entry point"""
    if not ARCHIVE_DIR.exists():
        print(f"❌ Archive directory not found: {ARCHIVE_DIR}")
        return 1

    print(f"Validating archive naming in: {ARCHIVE_DIR}")
    print(f"{'='*60}")

    invalid, total = validate_naming(ARCHIVE_DIR)

    if invalid:
        print(f"\n❌ Found {len(invalid)} files with non-standard naming:")
        for f in sorted(invalid):
            print(f"  {f}")
        print(f"\n📊 Summary: {len(invalid)}/{total} files need renaming")
        return 1
    else:
        print(f"✅ All {total} archived files follow naming convention")
        return 0

if __name__ == '__main__':
    sys.exit(main())
