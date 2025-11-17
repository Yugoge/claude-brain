#!/usr/bin/env python3
"""
Validation script to detect Chinese characters in command files.
Usage: python scripts/validation/check-chinese-in-commands.py <file-path>
"""

import re
import sys


def find_chinese(file_path):
    """Find all lines containing Chinese characters in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    chinese_pattern = re.compile(r'[\u4e00-\u9fa5]+')
    found = []

    for i, line in enumerate(lines, start=1):
        if chinese_pattern.search(line):
            found.append((i, line.strip()))

    return found


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python check-chinese-in-commands.py <file-path>")
        sys.exit(1)

    file = sys.argv[1]
    results = find_chinese(file)

    if results:
        print(f"❌ Found {len(results)} lines with Chinese characters:\n")
        for line_num, content in results:
            print(f"Line {line_num}: {content}")
        sys.exit(1)
    else:
        print("✅ No Chinese characters found")
        sys.exit(0)
