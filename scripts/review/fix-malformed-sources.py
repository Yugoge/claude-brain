#!/usr/bin/env python3
"""Fix malformed YAML sources that have Markdown link syntax."""

import re
from pathlib import Path

PROJECT_ROOT = Path("/root/knowledge-system")

# Find all malformed sources
kb_path = PROJECT_ROOT / "knowledge-base"
malformed_rems = []

for rem_file in kb_path.rglob("*.md"):
    if rem_file.name in ['INDEX.md', 'README.md']:
        continue
    
    content = rem_file.read_text(encoding='utf-8')
    
    # Check if source field has Markdown link syntax
    match = re.search(r'^source:\s*\[([^\]]+)\]\(([^\)]+)\)\s*$', content, re.MULTILINE)
    if match:
        title = match.group(1)
        path = match.group(2)
        malformed_rems.append((rem_file, title, path))

print(f"Found {len(malformed_rems)} malformed sources\n")

for rem_file, title, path in malformed_rems:
    # Extract plain path
    # Path format: ../../chats/... or similar
    # Convert to: chats/...
    clean_path = path.lstrip('../')
    if not clean_path.startswith('chats/'):
        clean_path = f"chats/{clean_path.split('chats/', 1)[-1]}"
    
    # Read file content
    content = rem_file.read_text(encoding='utf-8')
    
    # Replace malformed source with clean format
    old_source = f"source: [{title}]({path})"
    new_source = f"source: {clean_path}"
    
    content = content.replace(old_source, new_source)
    
    # Write back
    rem_file.write_text(content, encoding='utf-8')
    
    print(f"✓ Fixed: {rem_file.relative_to(PROJECT_ROOT)}")
    print(f"  Old: source: [{title}]({path})")
    print(f"  New: source: {clean_path}\n")

print(f"\nFixed {len(malformed_rems)} Rems")
