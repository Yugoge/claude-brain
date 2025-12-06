#!/usr/bin/env python3
"""
Incremental Backlinks Update Script

Purpose: Update backlinks.json without full rebuild (token optimization)
Story: 1.12 - Optimize Archival Token Consumption
Target: 70% reduction (1000 → 300 tokens)

Usage:
    python scripts/update-backlinks-incremental.py concept-id-1 concept-id-2 ...
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

# Portable project root
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent


def extract_typed_links_from_rem(rem_file: Path) -> List[Dict[str, str]]:
    """Extract links with {rel: type} annotations from a Rem file.

    Supports both formats:
    - Markdown links: [concept-id](file.md) {rel: type}
    - Wiki links: [[concept-id]] {rel: type}

    Returns list of dicts: [{'to': 'concept-id', 'type': 'relation_type'}, ...]
    """
    content = rem_file.read_text(encoding='utf-8')
    typed_links = []
    seen_targets = set()

    # Pattern 1: Match - [concept-id](file.md) {rel: type}
    markdown_typed_pattern = r'-\s*\[([^\]]+)\]\([^\)]+\)\s*\{rel:\s*([^}]+)\}'
    markdown_matches = re.findall(markdown_typed_pattern, content)

    for concept_id, rel_type in markdown_matches:
        target_id = concept_id.strip()
        if target_id and target_id not in seen_targets:
            typed_links.append({
                'to': target_id,
                'type': rel_type.strip()
            })
            seen_targets.add(target_id)

    # Pattern 2: Match - [[concept-id]] {rel: type}
    # or:          - [[concept-id|display]] {rel: type}
    wikilink_typed_pattern = r'-\s*\[\[([^\]|]+)(?:\|[^\]]+)?\]\]\s*\{rel:\s*([^}]+)\}'
    wikilink_matches = re.findall(wikilink_typed_pattern, content)

    for concept_id, rel_type in wikilink_matches:
        target_id = concept_id.strip()
        if target_id and target_id not in seen_targets:
            typed_links.append({
                'to': target_id,
                'type': rel_type.strip()
            })
            seen_targets.add(target_id)

    # Pattern 3: Also extract untyped markdown links [id](file.md) (assign default type)
    # Use more specific negative lookahead to avoid matching typed relations
    untyped_markdown_pattern = r'-\s*\[([^\]]+)\]\([^\)]+\)(?:\s*(?!\{rel:))'
    markdown_links = re.findall(untyped_markdown_pattern, content)

    for link in markdown_links:
        target_id = link.strip()
        if target_id and target_id not in seen_targets:
            # Default type for untyped links
            typed_links.append({
                'to': target_id,
                'type': 'related_to'
            })
            seen_targets.add(target_id)

    # Pattern 4: Also extract untyped [[wikilinks]] (assign default type)
    untyped_wikilink_pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\](?!\s*\{rel:)'
    wikilink_links = re.findall(untyped_wikilink_pattern, content)

    for link in wikilink_links:
        target_id = link.strip()
        if target_id and target_id not in seen_targets:
            # Default type for untyped links
            typed_links.append({
                'to': target_id,
                'type': 'related_to'
            })
            seen_targets.add(target_id)

    return typed_links


def load_backlinks() -> Dict:
    """Load existing backlinks.json."""
    backlinks_file = PROJECT_DIR / 'knowledge-base/_index/backlinks.json'

    if backlinks_file.exists():
        with open(backlinks_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Initialize if not exists
    return {"version": "1.0.0", "links": {}}


def save_backlinks(backlinks: Dict):
    """Save updated backlinks.json."""
    backlinks_file = PROJECT_DIR / 'knowledge-base/_index/backlinks.json'

    with open(backlinks_file, 'w', encoding='utf-8') as f:
        json.dump(backlinks, f, indent=2, ensure_ascii=False)


def find_rem_file(concept_id: str) -> Path:
    """Find Rem file by concept ID (recursively scan ISCED structure)."""
    kb_dir = PROJECT_DIR / 'knowledge-base'

    def scan_for_rem(directory: Path) -> Path:
        """Recursively search for rem_id match in frontmatter."""
        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                result = scan_for_rem(item)
                if result:
                    return result
            elif item.is_file() and item.suffix == '.md' and not item.stem.startswith('_'):
                # Check frontmatter for rem_id match
                try:
                    content = item.read_text(encoding='utf-8')
                    if content.startswith('---'):
                        end = content.find('\n---', 3)
                        if end != -1:
                            fm = content[3:end].strip()
                            for line in fm.splitlines():
                                if line.strip().startswith('rem_id:'):
                                    file_rem_id = line.split(':', 1)[1].strip().strip('"').strip("'")
                                    if file_rem_id == concept_id:
                                        return item
                except Exception:
                    pass
        return None

    for domain in kb_dir.iterdir():
        if domain.is_dir() and not domain.name.startswith('_'):
            result = scan_for_rem(domain)
            if result:
                return result

    raise FileNotFoundError(f"Rem file not found for concept: {concept_id}")


def update_backlinks_for_concepts(concept_ids: List[str]):
    """Update backlinks for specific concepts with typed relations."""
    backlinks = load_backlinks()
    links_map = backlinks.get('links', {})

    # Process each new concept
    for concept_id in concept_ids:
        try:
            rem_file = find_rem_file(concept_id)
            typed_links = extract_typed_links_from_rem(rem_file)

            # Initialize this concept's entry with typed structure
            if concept_id not in links_map:
                links_map[concept_id] = {
                    "typed_links_to": [],
                    "typed_linked_from": []
                }

            # Store typed relations
            links_map[concept_id]["typed_links_to"] = typed_links

            # Update reverse typed relations for targets
            for link in typed_links:
                target_id = link['to']
                rel_type = link['type']

                # Initialize target if not exists
                if target_id not in links_map:
                    links_map[target_id] = {
                        "typed_links_to": [],
                        "typed_linked_from": []
                    }

                # Add to target's typed_linked_from (if not duplicate)
                reverse_entry = {
                    'from': concept_id,
                    'type': rel_type
                }

                # Check if already exists
                existing = links_map[target_id]["typed_linked_from"]
                if not any(e.get('from') == concept_id and e.get('type') == rel_type for e in existing):
                    existing.append(reverse_entry)

            print(f"✅ Updated typed backlinks for: {concept_id} ({len(typed_links)} relations)")

        except FileNotFoundError as e:
            print(f"❌ {e}", file=sys.stderr)
            continue

    # Save updated backlinks
    backlinks['links'] = links_map
    save_backlinks(backlinks)

    print(f"\n✅ Incremental typed backlinks update complete ({len(concept_ids)} concepts)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/update-backlinks-incremental.py concept-id-1 concept-id-2 ...")
        sys.exit(1)

    concept_ids = sys.argv[1:]
    update_backlinks_for_concepts(concept_ids)


if __name__ == '__main__':
    main()
