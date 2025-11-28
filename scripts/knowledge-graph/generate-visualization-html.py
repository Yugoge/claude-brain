#!/usr/bin/env python3
"""
Generate standalone HTML visualization file with embedded graph data
"""

import json
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description='Generate knowledge graph visualization HTML')
    parser.add_argument('--input', type=str, default='knowledge-base/_index/graph-data.json',
                       help='Input graph data JSON file')
    parser.add_argument('--template', type=str, default='scripts/knowledge-graph/graph-visualization-template.html',
                       help='HTML template file')
    parser.add_argument('--output', type=str, default='docs/knowledge-graph.html',
                       help='Output HTML file')
    args = parser.parse_args()

    # Load graph data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"⚠ Error: Graph data not found: {input_path}")
        print("  Run: python scripts/generate-graph-data.py")
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)

    # Load template
    template_path = Path(args.template)
    if not template_path.exists():
        print(f"⚠ Error: Template not found: {template_path}")
        sys.exit(1)

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Embed graph data
    graph_data_js = f"const graphData = {json.dumps(graph_data, indent=2)};"
    html = template.replace('// GRAPH_DATA_PLACEHOLDER\n        const graphData = null;  // Will be replaced by actual data',
                           graph_data_js)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure docs/ exists
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # Print summary
    print(f"✓ Visualization generated successfully")
    print(f"  Nodes: {graph_data['metadata']['nodeCount']}")
    print(f"  Edges: {graph_data['metadata']['edgeCount']}")
    print(f"  Clusters: {graph_data['metadata']['clusters']}")
    if graph_data['metadata'].get('domainFilter'):
        print(f"  Domain: {graph_data['metadata']['domainFilter']}")
    print(f"  Output: {output_path.absolute()}")
    print(f"\nOpen in browser: file://{output_path.absolute()}")


if __name__ == '__main__':
    main()
