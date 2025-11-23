#!/usr/bin/env python3
"""
Get Next Sequential Number for Rem Files

Returns the next available sequential number (NNN) for a new Rem file in a directory.

Usage:
    python scripts/utilities/get-next-number.py --directory <path>

Example:
    python scripts/utilities/get-next-number.py \
        --directory knowledge-base/02-arts-and-humanities/023-languages/0231-language-acquisition

Output:
    007  (if directory has 001-foo.md, 002-bar.md, ..., 006-baz.md)

Logic:
    1. Scan directory for files matching pattern: NNN-*.md
    2. Extract all three-digit numbers (NNN)
    3. Return max(numbers) + 1, zero-padded to 3 digits
    4. If no numbered files exist, return 001
"""

import sys
import argparse
import re
from pathlib import Path


def get_next_number(directory: Path) -> str:
    """
    Get next sequential number for Rem files in directory.

    Args:
        directory: Path to directory containing Rem files

    Returns:
        Next number as zero-padded 3-digit string (e.g., "007")
    """
    if not directory.exists():
        # Directory doesn't exist yet, start with 001
        return "001"

    # Pattern: NNN-*.md (three digits followed by dash)
    pattern = re.compile(r'^(\d{3})-.*\.md$')

    numbers = []
    for file in directory.iterdir():
        if file.is_file() and file.suffix == '.md':
            match = pattern.match(file.name)
            if match:
                numbers.append(int(match.group(1)))

    if not numbers:
        # No numbered files found, start with 001
        return "001"

    # Return max + 1, zero-padded to 3 digits
    next_num = max(numbers) + 1
    return f"{next_num:03d}"


def main():
    parser = argparse.ArgumentParser(
        description='Get next sequential number for Rem files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--directory',
        required=True,
        help='Directory path to scan for numbered Rem files'
    )

    args = parser.parse_args()

    try:
        directory = Path(args.directory)
        next_number = get_next_number(directory)

        # Output only the number (for easy script piping)
        print(next_number)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
