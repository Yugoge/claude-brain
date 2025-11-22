#!/usr/bin/env python3
"""
Debug tool: Visualize review session clustering

Analyzes how Rems are clustered in review sessions using the
graph clustering algorithm from review_loader.py.

Usage:
    python3 scripts/review/debug_clustering.py              # Today's due Rems
    python3 scripts/review/debug_clustering.py --date 2025-11-22  # Specific date
    python3 scripts/review/debug_clustering.py --all        # All Rems (ignores schedule)

Output:
    - Cluster visualization with typed relations
    - Connection strength analysis
    - Effectiveness metrics
"""
import sys
sys.path.append('scripts/review')
sys.path.append('scripts/utilities')

from review_loader import ReviewLoader
from review_scheduler import ReviewScheduler
from datetime import datetime, timezone
from pathlib import Path
import json
from collections import defaultdict

def analyze_clustering(rems: list, scheduler) -> dict:
    """
    Analyze clustering structure for a set of Rems.

    Returns:
        dict with cluster analysis data
    """
    if len(rems) <= 1:
        return {
            "total_rems": len(rems),
            "clusters": [],
            "effectiveness": "N/A (too few Rems)"
        }

    # Build set of session Rem IDs
    session_ids = {rem.get("id") for rem in rems}
    id_to_rem = {rem.get("id"): rem for rem in rems}

    # Load backlinks to build relation graph
    backlinks_path = Path("knowledge-base/_index/backlinks.json")
    if not backlinks_path.exists():
        return {
            "total_rems": len(rems),
            "clusters": [],
            "effectiveness": "ERROR: backlinks.json not found"
        }

    with open(backlinks_path, "r", encoding="utf-8") as f:
        backlinks_data = json.load(f)
    backlinks = backlinks_data.get("links", {})

    # Build adjacency list (undirected graph) with relation types
    # Graph structure: {rem_id: {neighbor_id: [relation_types]}}
    graph = {rem_id: defaultdict(list) for rem_id in session_ids}

    for rem_id in session_ids:
        if rem_id not in backlinks:
            continue
        rem_links = backlinks[rem_id]

        # Add outgoing typed links
        for link in rem_links.get("typed_links_to", []):
            target_id = link["to"]
            rel_type = link["type"]
            if target_id in session_ids:
                graph[rem_id][target_id].append(rel_type)
                graph[target_id][rem_id].append(f"{rel_type} (inverse)")

        # Add incoming typed links
        for link in rem_links.get("typed_linked_from", []):
            source_id = link["from"]
            rel_type = link["type"]
            if source_id in session_ids:
                graph[rem_id][source_id].append(f"{rel_type} (from)")
                graph[source_id][rem_id].append(rel_type)

    # Find connected components using DFS
    visited = set()
    clusters = []

    def dfs(node, cluster):
        visited.add(node)
        cluster.append(node)
        for neighbor in graph[node].keys():
            if neighbor not in visited:
                dfs(neighbor, cluster)

    for rem_id in session_ids:
        if rem_id not in visited:
            cluster = []
            dfs(rem_id, cluster)
            clusters.append(cluster)

    # Build cluster analysis
    cluster_data = []
    total_connections = 0

    for idx, cluster_ids in enumerate(clusters, 1):
        cluster_size = len(cluster_ids)

        # Get connections within cluster
        connections = []
        for rem_id in cluster_ids:
            for neighbor_id, rel_types in graph[rem_id].items():
                if neighbor_id in cluster_ids:
                    # Deduplicate bidirectional edges
                    edge = tuple(sorted([rem_id, neighbor_id]))
                    connections.append({
                        "edge": edge,
                        "from": rem_id,
                        "to": neighbor_id,
                        "types": rel_types
                    })

        # Deduplicate connections
        seen_edges = set()
        unique_connections = []
        for conn in connections:
            edge = conn["edge"]
            if edge not in seen_edges:
                seen_edges.add(edge)
                unique_connections.append(conn)

        total_connections += len(unique_connections)

        cluster_data.append({
            "cluster_id": idx,
            "size": cluster_size,
            "rem_ids": cluster_ids,
            "connections": unique_connections,
            "is_isolated": cluster_size == 1 and len(unique_connections) == 0
        })

    # Calculate effectiveness
    connected_rems = sum(c["size"] for c in cluster_data if not c["is_isolated"])
    effectiveness = f"{connected_rems}/{len(rems)} Rems ({connected_rems*100//len(rems)}%) have cluster connections"

    return {
        "total_rems": len(rems),
        "total_clusters": len(clusters),
        "clusters": cluster_data,
        "total_connections": total_connections,
        "effectiveness": effectiveness
    }

def format_cluster_output(analysis: dict, id_to_rem: dict):
    """
    Format cluster analysis as human-readable output.
    """
    print("\n" + "="*70)
    print(f"Review Session Clustering Analysis - {datetime.now().strftime('%Y-%m-%d')}")
    print("="*70)
    print(f"Total Rems: {analysis['total_rems']}")
    print(f"Clusters found: {analysis['total_clusters']}")
    print(f"Total connections: {analysis['total_connections']}")
    print(f"\nEffectiveness: {analysis['effectiveness']}")
    print("="*70)

    for cluster in analysis["clusters"]:
        cluster_id = cluster["cluster_id"]
        size = cluster["size"]
        rem_ids = cluster["rem_ids"]
        connections = cluster["connections"]
        is_isolated = cluster["is_isolated"]

        print(f"\nCluster {cluster_id} (Size: {size}):")

        # List Rems with titles
        for rem_id in rem_ids:
            rem = id_to_rem.get(rem_id, {})
            title = rem.get("title", "Unknown")
            print(f"  - [{rem_id}] {title}")

        # Show connections
        if is_isolated:
            print("  Connections: None (isolated)")
        else:
            print(f"  Connections ({len(connections)}):")
            for conn in connections:
                from_id = conn["from"]
                to_id = conn["to"]
                types = ", ".join(conn["types"])
                from_rem = id_to_rem.get(from_id, {})
                to_rem = id_to_rem.get(to_id, {})
                from_title = from_rem.get("title", "Unknown")[:30]
                to_title = to_rem.get("title", "Unknown")[:30]
                print(f"    {from_title} ←→ {to_title}")
                print(f"      Relations: {types}")

    print("\n" + "="*70)

def main():
    """
    Main entry point for clustering debug tool.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Debug review session clustering")
    parser.add_argument("--date", type=str, help="Specific date (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="Analyze all Rems (ignore schedule)")
    args = parser.parse_args()

    # Initialize
    loader = ReviewLoader()
    scheduler = ReviewScheduler()

    # Get Rems
    if args.all:
        # Load all Rems from schedule
        schedule_data = scheduler.load_schedule()
        rems = list(schedule_data.get("concepts", {}).values())
        print(f"[DEBUG] Analyzing ALL {len(rems)} Rems in schedule")
    else:
        # Load today's due Rems
        criteria = loader.parse_arguments([])
        rems = loader.filter_rems(criteria)
        rems = loader.sort_by_relation_and_urgency(rems, scheduler)
        print(f"[DEBUG] Analyzing {len(rems)} Rems due today")

    if len(rems) == 0:
        print("No Rems to analyze. Try --all to see all Rems.")
        return

    # Build id_to_rem mapping
    id_to_rem = {rem.get("id"): rem for rem in rems}

    # Analyze clustering
    analysis = analyze_clustering(rems, scheduler)

    # Format output
    format_cluster_output(analysis, id_to_rem)

if __name__ == "__main__":
    main()
