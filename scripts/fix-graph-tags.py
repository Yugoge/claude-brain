#!/usr/bin/env python3
"""
Fix missing tags in knowledge graph by syncing from conversation files.
"""

import json
import os
import re
from pathlib import Path

def extract_tags_from_conversation(file_path):
    """Extract tags from conversation file front matter."""
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract front matter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 2:
            front_matter = parts[1]
            # Find tags line
            for line in front_matter.split('\n'):
                if line.startswith('tags:'):
                    # Extract tags list
                    tags_str = line.replace('tags:', '').strip()
                    # Handle both formats: [tag1, tag2] or tag1, tag2
                    tags_str = tags_str.strip('[]')
                    tags = [t.strip().strip('"\'') for t in tags_str.split(',')]
                    return [t for t in tags if t]  # Filter empty
    return []

def fix_graph_tags():
    """Main function to fix missing tags in graph."""

    # Load graph data
    graph_path = 'knowledge-base/_index/graph-data.json'
    with open(graph_path, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)

    fixed_count = 0

    for node in graph_data['nodes']:
        # Skip template node
        if node['id'].startswith('{'):
            continue

        # If tags are empty or missing
        if not node.get('tags'):
            # Try to get tags from conversations
            if 'conversations' in node:
                all_tags = set()
                for conv in node['conversations']:
                    conv_path = conv.get('path', '')
                    if conv_path:
                        # Fix path if needed
                        if not os.path.exists(conv_path):
                            # Try removing -3 suffix
                            conv_path = conv_path.replace('-3.md', '.md')

                        tags = extract_tags_from_conversation(conv_path)
                        all_tags.update(tags)

                if all_tags:
                    node['tags'] = list(all_tags)
                    fixed_count += 1
                    print(f"Fixed tags for {node['id']}: {node['tags']}")

    # Save updated graph
    with open(graph_path, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2, ensure_ascii=False)

    print(f"\nTotal nodes fixed: {fixed_count}")
    return fixed_count

if __name__ == '__main__':
    fix_graph_tags()