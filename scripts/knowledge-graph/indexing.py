#!/usr/bin/env python3
"""
Knowledge Graph Indexing Utilities

Algorithms for maintaining bidirectional links, taxonomy classification,
and index generation.

Used by: knowledge-indexer agent

Usage:
    from scripts.knowledge_graph.indexing import (
        load_taxonomy,
        apply_taxonomy,
        detect_domain,
        extract_links,
        sync_backlinks,
        generate_domain_index
    )
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


# ==================== Taxonomy Operations ====================

def load_taxonomy() -> Dict[str, Any]:
    """
    Load taxonomy mappings from configuration file.

    Returns:
        dict: Taxonomy configuration with ISCED and Dewey mappings
    """
    taxonomy_file = Path('knowledge-base/.taxonomy.json')
    with open(taxonomy_file) as f:
        return json.load(f)


def detect_domain(file_path: Path) -> str:
    """
    Detect domain from knowledge base file path.

    Args:
        file_path: Path to concept file

    Returns:
        str: Domain name (finance, programming, language, science, general)
    """
    path_str = str(file_path).lower()

    if 'finance' in path_str:
        return 'finance'
    elif 'programming' in path_str:
        return 'programming'
    elif 'language' in path_str:
        return 'language'
    elif 'science' in path_str:
        return 'science'
    else:
        return 'general'


def apply_taxonomy(concept_path: Path, domain: str) -> Dict[str, Any]:
    """
    Apply taxonomy codes to a concept based on its domain.

    Args:
        concept_path: Path to the concept markdown file
        domain: Domain name (finance, programming, language, science, general)

    Returns:
        dict: Dictionary with taxonomy codes to add to frontmatter

    Example:
        >>> apply_taxonomy(Path('kb/finance/call-option.md'), 'finance')
        {'taxonomy': {'isced': ['34'], 'dewey': ['300', '330'], 'source': '.taxonomy.json'}}
    """
    taxonomy = load_taxonomy()

    # Get codes for the domain
    isced_codes = taxonomy['isced_mappings'].get(domain, ['00'])
    dewey_codes = taxonomy['dewey_mappings'].get(domain, ['000'])

    # Return frontmatter format
    return {
        'taxonomy': {
            'isced': isced_codes,
            'dewey': dewey_codes,
            'source': '.taxonomy.json'
        }
    }


# ==================== Link Extraction ====================

def extract_links(markdown_text: str) -> List[str]:
    """
    Extract all [[concept-id]] links from markdown.

    Args:
        markdown_text: Markdown content to scan

    Returns:
        list: Concept IDs found in wikilinks

    Example:
        >>> extract_links("See [[call-option]] and [[put-option]]")
        ['call-option', 'put-option']
    """
    pattern = r'\[\[([a-z0-9-]+)\]\]'
    return re.findall(pattern, markdown_text)


# ==================== Backlink Sync ====================

def sync_backlinks(concept_id: str, new_links: List[str],
                  backlinks: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, List[str]]]:
    """
    Update bidirectional links for a concept.

    Steps:
    1. Get old links from backlinks.json
    2. Find added links: new_links - old_links
    3. Find removed links: old_links - new_links
    4. Update backlinks.json
    5. Return updated backlinks structure

    Args:
        concept_id: Concept being updated
        new_links: New outgoing links
        backlinks: Current backlinks structure

    Returns:
        dict: Updated backlinks structure

    Example:
        >>> backlinks = {'a': {'links_to': [], 'linked_from': []}}
        >>> sync_backlinks('a', ['b', 'c'], backlinks)
        {'a': {'links_to': ['b', 'c'], 'linked_from': []},
         'b': {'links_to': [], 'linked_from': ['a']},
         'c': {'links_to': [], 'linked_from': ['a']}}
    """
    # Initialize if concept not in backlinks
    if concept_id not in backlinks:
        backlinks[concept_id] = {'links_to': [], 'linked_from': []}

    old_links = backlinks[concept_id]['links_to']

    added = set(new_links) - set(old_links)
    removed = set(old_links) - set(new_links)

    # Add backlinks to newly linked concepts
    for target_id in added:
        if target_id not in backlinks:
            backlinks[target_id] = {'links_to': [], 'linked_from': []}
        if concept_id not in backlinks[target_id]['linked_from']:
            backlinks[target_id]['linked_from'].append(concept_id)

    # Remove backlinks from unlinked concepts
    for target_id in removed:
        if target_id in backlinks and concept_id in backlinks[target_id]['linked_from']:
            backlinks[target_id]['linked_from'].remove(concept_id)

    # Update source concept
    backlinks[concept_id]['links_to'] = new_links

    return backlinks


# ==================== Index Generation ====================

def generate_domain_index(domain: str, concepts: List[Dict[str, Any]],
                         taxonomy: Dict[str, Any]) -> str:
    """
    Generate index for a specific domain.

    Args:
        domain: Domain name
        concepts: List of concept dicts with id, title, created, isced, etc.
        taxonomy: Taxonomy configuration

    Returns:
        str: Markdown index content

    Example structure:
        # Finance Knowledge Index

        Total concepts: 45

        ## 0412 - Finance, banking and insurance

        - [[call-option-intrinsic-value]] - Call Option Intrinsic Value
        - [[put-option-intrinsic-value]] - Put Option Intrinsic Value
    """
    # Sort by creation date (newest first)
    concepts_sorted = sorted(concepts, key=lambda c: c.get('created', ''), reverse=True)

    markdown = f"# {domain.title()} Knowledge Index\n\n"
    markdown += f"Total concepts: {len(concepts_sorted)}\n\n"

    # Group by ISCED code
    isced_groups = {}
    for concept in concepts_sorted:
        isced_code = concept.get('isced', ['00'])[0] if concept.get('isced') else '00'
        if isced_code not in isced_groups:
            isced_groups[isced_code] = []
        isced_groups[isced_code].append(concept)

    # Generate sections
    for isced_code in sorted(isced_groups.keys()):
        # Get category name from taxonomy
        category = taxonomy.get('isced', {}).get(isced_code, 'Unknown')
        markdown += f"## {isced_code} - {category}\n\n"

        for concept in isced_groups[isced_code]:
            markdown += f"- [[{concept['id']}]] - {concept.get('title', concept['id'])}\n"

        markdown += "\n"

    return markdown


# ==================== Orphan Detection ====================

def find_orphans(backlinks: Dict[str, Dict[str, List[str]]]) -> List[str]:
    """
    Find concepts with no incoming or outgoing links.

    Args:
        backlinks: Backlinks structure

    Returns:
        list: Orphaned concept IDs

    Example:
        >>> backlinks = {
        ...     'a': {'links_to': [], 'linked_from': []},
        ...     'b': {'links_to': ['a'], 'linked_from': []}
        ... }
        >>> find_orphans(backlinks)
        ['a']
    """
    orphans = []
    for concept_id, data in backlinks.items():
        if len(data['links_to']) == 0 and len(data['linked_from']) == 0:
            orphans.append(concept_id)
    return orphans


# ==================== Quality Checks ====================

def check_link_integrity(all_concepts: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Verify all [[links]] point to existing concepts.

    Args:
        all_concepts: List of all concept dicts with id and content

    Returns:
        list: Broken link records with source and target

    Example:
        >>> concepts = [{'id': 'a', 'content': '[[b]] [[c]]'}, {'id': 'b', 'content': ''}]
        >>> check_link_integrity(concepts)
        [{'source': 'a', 'target': 'c'}]
    """
    broken_links = []
    concept_ids = {c['id'] for c in all_concepts}

    for concept in all_concepts:
        links = extract_links(concept.get('content', ''))
        for link in links:
            if link not in concept_ids:
                broken_links.append({
                    'source': concept['id'],
                    'target': link
                })

    return broken_links


def check_bidirectional_consistency(backlinks: Dict[str, Dict[str, List[str]]]) -> List[str]:
    """
    Ensure A→B implies B→A.

    Args:
        backlinks: Backlinks structure

    Returns:
        list: Inconsistency descriptions

    Example:
        >>> backlinks = {
        ...     'a': {'links_to': ['b'], 'linked_from': []},
        ...     'b': {'links_to': [], 'linked_from': []}
        ... }
        >>> check_bidirectional_consistency(backlinks)
        ['a → b (missing backlink)']
    """
    inconsistencies = []

    for concept_id, data in backlinks.items():
        for target in data['links_to']:
            if target in backlinks:
                if concept_id not in backlinks[target]['linked_from']:
                    inconsistencies.append(f"{concept_id} → {target} (missing backlink)")
            else:
                inconsistencies.append(f"{concept_id} → {target} (target not in backlinks)")

    return inconsistencies


# ==================== Example Usage ====================

if __name__ == "__main__":
    print("Knowledge Graph Indexing Utilities")
    print("\nAvailable functions:")
    print("  - load_taxonomy()")
    print("  - detect_domain(file_path)")
    print("  - apply_taxonomy(concept_path, domain)")
    print("  - extract_links(markdown_text)")
    print("  - sync_backlinks(concept_id, new_links, backlinks)")
    print("  - generate_domain_index(domain, concepts, taxonomy)")
    print("  - find_orphans(backlinks)")
    print("  - check_link_integrity(all_concepts)")
    print("  - check_bidirectional_consistency(backlinks)")
