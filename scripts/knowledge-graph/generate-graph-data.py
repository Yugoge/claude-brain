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
    match = re.search(r'knowledge-base/(\d{2})-', file_path)
    if match:
        code = match.group(1)
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
    """Load metadata from concept files"""
    metadata = {}

    # Search for all concept markdown files
    for concept_file in knowledge_base_path.rglob('**/*.md'):
        if concept_file.name.startswith('_') or 'index' in concept_file.name:
            continue

        try:
            with open(concept_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = parts[1]

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

                        # Extract domain using new function
                        frontmatter_data = {
                            'isced': isced,
                            'subdomain': subdomain
                        }
                        domain = extract_isced_domain(file_path, frontmatter_data)

                        metadata[rem_id] = {
                            'domain': domain,
                            'isced': isced,
                            'subdomain': subdomain,
                            'tags': tags,
                            'file': file_path
                        }
        except Exception as e:
            print(f"⚠ Warning: Could not parse {concept_file}: {e}", file=sys.stderr)
            continue

    return metadata


def calculate_pagerank(graph: nx.Graph) -> dict:
    """Calculate PageRank for each node"""
    if len(graph.nodes()) == 0:
        return {}
    try:
        return nx.pagerank(graph, alpha=0.85)
    except:
        # Return uniform distribution if PageRank fails
        return {node: 1.0 / len(graph.nodes()) for node in graph.nodes()}


def detect_communities(graph: nx.Graph) -> dict:
    """Detect communities using Louvain algorithm"""
    if len(graph.nodes()) == 0:
        return {}

    try:
        from networkx.algorithms import community
        communities = community.louvain_communities(graph)
        node_to_community = {}
        for idx, comm in enumerate(communities):
            for node in comm:
                node_to_community[node] = idx
        return node_to_community
    except ImportError:
        print("⚠ Warning: Louvain algorithm not available, using connected components")
        # Fallback to connected components
        components = list(nx.connected_components(graph))
        node_to_community = {}
        for idx, comp in enumerate(components):
            for node in comp:
                node_to_community[node] = idx
        return node_to_community


def transform_to_graph_format(backlinks_data: dict, concept_metadata: dict, domain_filter: str = None) -> dict:
    """Transform backlinks to graph visualization format"""

    links_data = backlinks_data.get('links', {})
    concepts_data = backlinks_data.get('concepts', {})

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

    # Build NetworkX graph for analysis
    G = nx.Graph()

    # Add all nodes first
    for concept_id in concept_metadata.keys():
        G.add_node(concept_id)

    # Add edges from links_to
    for node_id, link_info in links_data.items():
        if node_id not in concept_metadata:
            continue

        links_to = link_info.get('links_to', [])
        for target in links_to:
            if target in concept_metadata:
                G.add_edge(node_id, target)

    # Calculate metrics
    pagerank = calculate_pagerank(G) if len(G.nodes()) > 0 else {}
    communities = detect_communities(G) if len(G.nodes()) > 0 else {}
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
        tags = metadata.get('tags', [])

        # Get title from concepts_data if available
        title = concepts_data.get(concept_id, {}).get('title', concept_id)

        # Review count (currently 0 as we don't have review data yet)
        review_count = 0

        nodes.append({
            'id': concept_id,
            'label': title,
            'domain': domain,
            'color': domain_colors.get(domain, domain_colors['generic']),
            'size': 10 + (3 * (1 + review_count) ** 0.5),  # Logarithmic scaling
            'reviewCount': review_count,
            'pageRank': pagerank.get(concept_id, 0),
            'cluster': communities.get(concept_id, 0),
            'degree': degree.get(concept_id, 0),
            'tags': tags,
            'file': metadata.get('file', '')
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

    return {
        'nodes': nodes,
        'edges': edges,
        'metadata': {
            'nodeCount': len(nodes),
            'edgeCount': len(edges),
            'domainFilter': domain_filter,
            'clusters': len(set(communities.values())) if communities else 0,
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
    print(f"  Clusters: {metadata['clusters']}")
    if args.domain:
        print(f"  Domain filter: {args.domain}")
    print(f"  Output: {output_path}")


if __name__ == '__main__':
    main()
