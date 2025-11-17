#!/usr/bin/env python3
"""Check final distribution of source fields in Rem files."""

from pathlib import Path

kb_dir = Path("/root/knowledge-system/knowledge-base")
stats = {
    'chats': 0,
    'unarchived': 0,
    'other': 0
}

for md_file in kb_dir.glob('**/*.md'):
    if md_file.name == 'rem-template.md':
        continue

    with open(md_file, 'r') as f:
        content = f.read()
        if 'source: chats/' in content:
            stats['chats'] += 1
        elif 'source: unarchived' in content:
            stats['unarchived'] += 1
        else:
            stats['other'] += 1

print('📊 Final Source Field Distribution:')
print(f'  ✅ Linked to chat archives: {stats["chats"]}')
print(f'  📌 Marked as unarchived: {stats["unarchived"]}')
print(f'  ⚠️  Other/Invalid: {stats["other"]}')
print(f'  📝 Total: {sum(stats.values())}')
