#!/usr/bin/env python3
"""
Generate graph visualization data from backlinks.json

Transforms RemNote-style backlinks into D3.js-compatible graph format
with additional metrics (PageRank, clustering, centrality)
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter
import sys

try:
    import networkx as nx
except ImportError:
    print("⚠ Error: networkx not installed")
    print("  Run: pip install networkx")
    sys.exit(1)


def load_backlinks(path: str) -> dict:
    """Load and validate backlinks.json"""
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def extract_isced_domain(file_path: str, frontmatter_data: dict) -> str:
    """
    Extract domain from ISCED path in file path or frontmatter

    Priority:
    1. ISCED path from frontmatter (04-business-... -> business-law)
    2. File path pattern (knowledge-base/04-... -> business-law)
    3. Subdomain mapping (equity-derivatives -> business-law)

    Args:
        file_path: Relative file path
        frontmatter_data: Parsed frontmatter dict with 'isced' and 'subdomain'

    Returns:
        Domain name (business-law, ict, language, etc.)
    """
    import re

    # ISCED to Domain mapping
    ISCED_TO_DOMAIN = {
        '01': 'education',
        '02': 'humanities',
        '03': 'social-sciences',
        '04': 'business-law',
        '05': 'natural-sciences',
        '06': 'ict',
        '07': 'engineering',
        '08': 'agriculture',
        '09': 'health',
        '10': 'services'
    }

    # Priority 1: Check frontmatter ISCED field
    isced = frontmatter_data.get('isced', '')
    if isced:
        # Extract first 2 digits (04-business-... -> 04)
        match = re.match(r'(\d{2})', isced)
        if match:
            code = match.group(1)
            domain = ISCED_TO_DOMAIN.get(code)
            if domain:
                return domain

    # Priority 2: Extract from file path
    # Try multiple patterns for different path structures
    patterns = [
        r'knowledge-base/(\d{2})-',  # Direct under knowledge-base
        r'/(\d{2})-[^/]+/',  # Any folder with 02-name pattern
        r'/(\d{3})-',  # 3-digit codes like 023
        r'/(\d{4})-',  # 4-digit codes like 0231
    ]

    for pattern in patterns:
        match = re.search(pattern, file_path)
        if match:
            code = match.group(1)[:2]  # Take first 2 digits
            domain = ISCED_TO_DOMAIN.get(code)
            if domain:
                return domain

    # Priority 3: Subdomain mapping (fallback)
    subdomain = frontmatter_data.get('subdomain', '').lower()
    subdomain_mapping = {
        'equity': 'business-law',
        'fixed-income': 'business-law',
        'derivatives': 'business-law',
        'fx': 'business-law',
        'commodities': 'business-law',
        'credit': 'business-law',
        'rates': 'business-law',
        'finance': 'business-law',
        'banking': 'business-law',
        'economics': 'social-sciences',
        'python': 'ict',
        'csharp': 'ict',
        'javascript': 'ict',
        'programming': 'ict',
        'software': 'ict',
        'french': 'language',
        'english': 'language',
        'chinese': 'language',
        'spanish': 'language'
    }

    for keyword, domain in subdomain_mapping.items():
        if keyword in subdomain:
            return domain

    return 'generic'


def load_concept_metadata(knowledge_base_path: Path) -> dict:
    """Load metadata and content from concept files"""
    metadata = {}

    # Search for all concept markdown files
    for concept_file in knowledge_base_path.rglob('**/*.md'):
        if concept_file.name.startswith('_') or 'index' in concept_file.name:
            continue

        try:
            with open(concept_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract frontmatter and body
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]
                    body = parts[2].strip()  # Get the actual content

                    # Simple YAML parsing for needed fields
                    rem_id = None
                    isced = ''
                    subdomain = ''
                    tags = []

                    for line in frontmatter.split('\n'):
                        line = line.strip()
                        if line.startswith('rem_id:'):
                            rem_id = line.split(':', 1)[1].strip()
                        elif line.startswith('isced:'):
                            isced = line.split(':', 1)[1].strip()
                        elif line.startswith('subdomain:'):
                            subdomain = line.split(':', 1)[1].strip()
                        elif line.startswith('tags:'):
                            # Parse tags array
                            tags_str = line.split(':', 1)[1].strip()
                            if tags_str.startswith('[') and tags_str.endswith(']'):
                                tags_str = tags_str[1:-1]
                                tags = [t.strip().strip('"\'') for t in tags_str.split(',') if t.strip()]

                    if rem_id:
                        file_path = str(concept_file.relative_to(knowledge_base_path.parent))

                        # Extract ISCED from path if not in frontmatter
                        if not isced:
                            # Try to extract from file path (e.g., 0231-language-acquisition)
                            import re
                            path_match = re.search(r'/(\d{4})-([^/]+)/', file_path)
                            if path_match:
                                isced = path_match.group(0).strip('/')  # Just use the full match
                            else:
                                # Try broader pattern for shorter codes
                                path_match = re.search(r'/(\d{2,3})-([^/]+)/', file_path)
                                if path_match:
                                    isced = path_match.group(0).strip('/')

                        # Extract domain using new function
                        frontmatter_data = {
                            'isced': isced,
                            'subdomain': subdomain
                        }
                        domain = extract_isced_domain(file_path, frontmatter_data)

                        # Extract conversation source and filter content
                        conversation_link = None
                        content_lines = []
                        skip_section = False
                        in_conv_source = False

                        import re
                        for line in body.split('\n'):
                            if line.startswith('## Conversation Source'):
                                skip_section = True
                                in_conv_source = True
                            elif line.startswith('## Related Rems'):
                                skip_section = True
                                in_conv_source = False
                            elif line.startswith('## ') and skip_section:
                                skip_section = False
                                in_conv_source = False

                            # Extract conversation link from source section
                            if in_conv_source and '> See:' in line:
                                # Extract title and path from markdown link
                                match = re.search(r'\[([^\]]+)\]\(([^\)]+)\)', line)
                                if match:
                                    conv_title = match.group(1)
                                    conv_path = match.group(2)
                                    # Normalize path (remove ../../.. prefix)
                                    conv_path = conv_path.replace('../', '')
                                    conversation_link = {
                                        'title': conv_title,
                                        'path': conv_path,
                                        'date': ''  # Can extract from filename if needed
                                    }

                            if not skip_section:
                                content_lines.append(line)

                        filtered_content = '\n'.join(content_lines).strip()

                        metadata[rem_id] = {
                            'domain': domain,
                            'isced': isced,
                            'subdomain': subdomain,
                            'tags': tags,
                            'file': file_path,
                            'content': filtered_content,  # EMBED FILTERED CONTENT
                            'conversation': conversation_link  # ADD CONVERSATION LINK
                        }
        except Exception as e:
            print(f"⚠ Warning: Could not parse {concept_file}: {e}", file=sys.stderr)
            continue

    return metadata


def load_review_stats() -> dict:
    """Load review statistics from schedule.json and history.json"""
    review_stats = {}

    # Load schedule for review counts
    schedule_path = Path('.review/schedule.json')
    if schedule_path.exists():
        with open(schedule_path, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
            concepts = schedule.get('concepts', {})
            for rem_id, rem_data in concepts.items():
                fsrs_state = rem_data.get('fsrs_state', {})
                review_stats[rem_id] = {
                    'review_count': fsrs_state.get('reviews', 0),
                    'stability': round(fsrs_state.get('stability', 0), 2),
                    'difficulty': round(fsrs_state.get('difficulty', 0), 2),
                    'last_reviewed': rem_data.get('last_reviewed', '')
                }

    return review_stats


def load_conversation_index() -> dict:
    """Load conversation index for linking"""
    conversations_by_rem = {}

    chats_index_path = Path('chats/index.json')
    if chats_index_path.exists():
        with open(chats_index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)

            # Handle both formats: 'entries' (new) or 'conversations' (old)
            conversations = index.get('conversations', {})

            # For now, we can't link conversations without metadata.extracted_concepts
            # This would require parsing each conversation file to extract rem references
            # TODO: Parse conversation files to extract [[rem_id]] references

            # As a workaround, link by domain matching (very broad)
            # This is temporary until we have proper concept extraction

    return conversations_by_rem


def transform_to_graph_format(backlinks_data: dict, concept_metadata: dict, domain_filter: str = None) -> dict:
    """Transform backlinks to graph visualization format"""

    links_data = backlinks_data.get('links', {})
    concepts_data = backlinks_data.get('concepts', {})

    # Load review statistics
    review_stats = load_review_stats()

    # Load conversation index
    conversations_index = load_conversation_index()

    # Filter by domain if specified
    if domain_filter:
        filtered_concepts = {}
        for concept_id, metadata in concept_metadata.items():
            if metadata.get('domain') == domain_filter:
                filtered_concepts[concept_id] = metadata
        concept_metadata = filtered_concepts

        # Filter links data to only include filtered concepts
        filtered_links = {}
        for concept_id in concept_metadata.keys():
            if concept_id in links_data:
                filtered_links[concept_id] = links_data[concept_id]
        links_data = filtered_links

    # Build NetworkX graph for calculating degree (connections)
    G = nx.Graph()

    # Add all nodes first
    for concept_id in concept_metadata.keys():
        G.add_node(concept_id)

    # Add edges from all link types
    for node_id, link_info in links_data.items():
        if node_id not in concept_metadata:
            continue

        # Typed links
        for typed_link in link_info.get('typed_links_to', []):
            target = typed_link.get('to') if isinstance(typed_link, dict) else typed_link
            if target in concept_metadata:
                G.add_edge(node_id, target)

        # Regular links
        for target in link_info.get('links_to', []):
            if target in concept_metadata:
                G.add_edge(node_id, target)

        # Inferred links
        for inferred_item in link_info.get('inferred_links_to', []):
            target = inferred_item.get('to') if isinstance(inferred_item, dict) else inferred_item
            if target in concept_metadata:
                G.add_edge(node_id, target)

    # Calculate degree (number of connections)
    degree = dict(G.degree())

    # Domain color mapping (UNESCO ISCED categories)
    domain_colors = {
        'business-law': '#3498db',      # Blue (04 - Business, Law, Finance)
        'ict': '#2ecc71',               # Green (06 - Programming, Software)
        'language': '#e74c3c',          # Red (09 - Languages, Humanities)
        'health': '#9b59b6',            # Purple (09 - Health, Medicine)
        'humanities': '#f39c12',        # Orange (02 - Arts, History)
        'natural-sciences': '#1abc9c',  # Teal (05 - Physics, Chemistry, Math)
        'social-sciences': '#34495e',   # Dark Gray (03 - Economics, Politics)
        'education': '#e67e22',         # Dark Orange (01 - Education, Pedagogy)
        'engineering': '#16a085',       # Dark Teal (07 - Engineering)
        'agriculture': '#27ae60',       # Forest Green (08 - Agriculture)
        'services': '#95a5a6',          # Light Gray (10 - Services)
        'generic': '#bdc3c7'            # Very Light Gray (Uncategorized)
    }

    # Transform nodes
    nodes = []
    for concept_id, metadata in concept_metadata.items():
        domain = metadata.get('domain', 'generic')
        isced = metadata.get('isced', '')
        subdomain = metadata.get('subdomain', '')
        tags = metadata.get('tags', [])

        # Get title from concepts_data if available
        title = concepts_data.get(concept_id, {}).get('title', concept_id)

        # Get review statistics
        stats = review_stats.get(concept_id, {})
        review_count = stats.get('review_count', 0)
        stability = stats.get('stability', 0)
        difficulty = stats.get('difficulty', 0)
        last_reviewed = stats.get('last_reviewed', '')

        nodes.append({
            'id': concept_id,
            'label': title,
            'isced': isced,
            'subdomain': subdomain,
            'domain': domain,  # Keep for backward compatibility
            'color': domain_colors.get(domain, domain_colors['generic']),
            'size': 10 + (3 * (1 + review_count) ** 0.5),  # Logarithmic scaling
            'reviewCount': review_count,
            'stability': stability,
            'difficulty': difficulty,
            'lastReviewed': last_reviewed,
            'connections': degree.get(concept_id, 0),
            'tags': tags,
            'file': metadata.get('file', ''),
            'content': metadata.get('content', ''),  # EMBED CONTENT HERE
            'conversations': [metadata.get('conversation')] if metadata.get('conversation') else []  # EMBED CONVERSATION FROM SOURCE
        })

    # Transform edges (typed + regular + inferred links)
    edges = []
    edge_id_set = set()  # Avoid duplicates (source, target, type)

    def get_link_type_color(link_type: str) -> str:
        """Map link type to color"""
        colors = {
            'prerequisite_of': '#e74c3c',  # Red (strong dependency)
            'uses': '#3498db',             # Blue (utility)
            'example_of': '#2ecc71',       # Green (instance)
            'contrasts_with': '#f39c12',   # Orange (comparison)
            'synonym': '#9b59b6',          # Purple (equivalence)
            'component_of': '#1abc9c',     # Teal (composition)
            'analogous_to': '#e67e22',     # Dark Orange (analogy)
            'linked-from-example_of': '#2ecc71',  # Green (reversed)
            'linked-from-used_in': '#3498db',     # Blue (reversed)
            'reference': '#95a5a6',        # Gray (generic)
            'inferred': '#d0d0d0'          # Very light gray (inferred)
        }
        return colors.get(link_type, '#999')

    for source_id, link_info in links_data.items():
        if source_id not in concept_metadata:
            continue

        # 1. Typed links (PRIORITY - Most important relationships)
        typed_links = link_info.get('typed_links_to', [])
        for typed_link in typed_links:
            if isinstance(typed_link, dict):
                target = typed_link.get('to')
                link_type = typed_link.get('type', 'reference')
            else:
                # Fallback for old format
                target = typed_link
                link_type = 'reference'

            if target and target in concept_metadata:
                edge_key = (source_id, target, link_type)
                if edge_key not in edge_id_set:
                    edges.append({
                        'source': source_id,
                        'target': target,
                        'type': link_type,
                        'weight': 2.5,  # Thicker line for typed relations
                        'color': get_link_type_color(link_type),
                        'dashed': False,
                        'bidirectional': False
                    })
                    edge_id_set.add(edge_key)

        # 2. Regular wikilinks (medium priority)
        links_to = link_info.get('links_to', [])
        for target in links_to:
            if target and target in concept_metadata:
                edge_key = (source_id, target, 'reference')
                if edge_key not in edge_id_set:
                    # Check if bidirectional
                    is_bidirectional = False
                    if target in links_data:
                        target_links = links_data[target].get('links_to', [])
                        is_bidirectional = source_id in target_links

                    edges.append({
                        'source': source_id,
                        'target': target,
                        'type': 'reference',
                        'weight': 1.0,
                        'color': get_link_type_color('reference'),
                        'dashed': False,
                        'bidirectional': is_bidirectional
                    })
                    edge_id_set.add(edge_key)

        # 3. Inferred links (lowest priority, shown as dashed lines)
        inferred_links = link_info.get('inferred_links_to', [])
        for inferred_item in inferred_links:
            # Handle both dict format {"to": "target"} and string format
            if isinstance(inferred_item, dict):
                target = inferred_item.get('to')
            else:
                target = inferred_item

            if target and target in concept_metadata:
                edge_key = (source_id, target, 'inferred')
                if edge_key not in edge_id_set:
                    edges.append({
                        'source': source_id,
                        'target': target,
                        'type': 'inferred',
                        'weight': 0.5,  # Thinner line
                        'color': get_link_type_color('inferred'),
                        'dashed': True,
                        'bidirectional': False
                    })
                    edge_id_set.add(edge_key)

    # Calculate domain distribution
    domain_counts = {}
    for node in nodes:
        domain = node['domain']
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    return {
        'nodes': nodes,
        'edges': edges,
        'metadata': {
            'nodeCount': len(nodes),
            'edgeCount': len(edges),
            'domainFilter': domain_filter,
            'domainDistribution': domain_counts,
            'generated': datetime.now().isoformat()
        }
    }


def main():
    parser = argparse.ArgumentParser(description='Generate graph visualization data')
    parser.add_argument('--domain', type=str, help='Filter by domain (finance, programming, language, etc.)')
    parser.add_argument('--output', type=str, default='knowledge-base/_index/graph-data.json',
                       help='Output file path')
    parser.add_argument('--force', action='store_true', help='Force regeneration even if cache is fresh')
    args = parser.parse_args()

    # Load backlinks
    backlinks_path = Path('knowledge-base/_index/backlinks.json')
    if not backlinks_path.exists():
        print("⚠ Error: backlinks.json not found")
        print(f"  Expected: {backlinks_path.absolute()}")
        sys.exit(1)

    # Check cache freshness
    output_path = Path(args.output)
    if not args.force and output_path.exists():
        cache_mtime = output_path.stat().st_mtime
        backlinks_mtime = backlinks_path.stat().st_mtime

        if cache_mtime > backlinks_mtime:
            print("✓ Using cached graph data (backlinks.json unchanged)")
            print(f"  Use --force to regenerate")
            return

    backlinks_data = load_backlinks(backlinks_path)

    # Load concept metadata
    knowledge_base_path = Path('knowledge-base')
    concept_metadata = load_concept_metadata(knowledge_base_path)

    if not concept_metadata:
        print("⚠ Error: No concepts found in knowledge base")
        print("  Run /learn to add concepts first")
        sys.exit(1)

    # Validate domain filter
    if args.domain:
        valid_domains = {'finance', 'programming', 'language', 'science', 'arts', 'mathematics', 'social'}
        if args.domain not in valid_domains:
            print(f"⚠ Warning: Domain '{args.domain}' not in standard set")
            print(f"  Valid domains: {', '.join(sorted(valid_domains))}")
            print("  Proceeding anyway...")

    # Transform to graph format
    graph_data = transform_to_graph_format(backlinks_data, concept_metadata, args.domain)

    # Check if result is empty
    if graph_data['metadata']['nodeCount'] == 0:
        print("⚠ Error: No concepts match the filter criteria")
        if args.domain:
            print(f"  No concepts found for domain: {args.domain}")
        sys.exit(1)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2)

    # Print summary
    metadata = graph_data['metadata']
    print(f"✓ Graph data generated successfully")
    print(f"  Nodes: {metadata['nodeCount']}")
    print(f"  Edges: {metadata['edgeCount']}")
    domain_dist = metadata.get('domainDistribution', {})
    if domain_dist:
        print(f"  Domains: {', '.join(f'{d}({c})' for d, c in sorted(domain_dist.items(), key=lambda x: -x[1])[:5])}")
    if args.domain:
        print(f"  Domain filter: {args.domain}")
    print(f"  Output: {output_path}")


if __name__ == '__main__':
    main()
