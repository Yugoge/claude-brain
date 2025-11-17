#!/usr/bin/env python3
"""
Knowledge Graph Memory Structure

Implements knowledge graph for concept relationships using MCP memory server.
Provides semantic search, importance weighting, and relationship management.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from memory_client import MemoryClient


class KnowledgeGraphMemory:
    """
    Knowledge graph structure for concept relationships.

    Nodes: Concepts (from knowledge base)
    Edges: Relationships (prerequisite, related_to, example_of)
    """

    def __init__(self, memory_client: Optional[MemoryClient] = None):
        """
        Initialize knowledge graph memory.

        Args:
            memory_client: Optional MemoryClient instance, creates new if None
        """
        self.client = memory_client or MemoryClient()

    def add_concept_node(
        self,
        concept_name: str,
        domain: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add concept to knowledge graph.

        Args:
            concept_name: Name of the concept
            domain: Domain (finance, programming, language, science)
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read current memory
            data = self.client._read_memory_file()
            if data is None:
                data = {"entities": [], "relations": []}

            # Check if concept already exists
            for entity in data["entities"]:
                if entity.get("name") == concept_name:
                    print(f"⚠️  Concept '{concept_name}' already exists")
                    return False

            # Create entity with observations
            observations = []
            if metadata:
                # Add metadata as observations
                observations.append(f"Domain: {domain}")
                observations.append(f"Added: {datetime.now().isoformat()}")
                for key, value in metadata.items():
                    observations.append(f"{key}: {value}")

            entity = {
                "name": concept_name,
                "entityType": domain,
                "observations": observations
            }

            # Add to entities
            data["entities"].append(entity)

            # Write back
            if self.client._write_memory_file(data):
                print(f"✅ Added concept: {concept_name} ({domain})")
                return True
            else:
                print(f"❌ Failed to write concept: {concept_name}")
                return False

        except Exception as e:
            print(f"❌ Error adding concept: {e}")
            return False

    def create_relationship(
        self,
        concept1_name: str,
        concept2_name: str,
        rel_type: str,
        strength: float = 0.7
    ) -> bool:
        """
        Create relationship between concepts.

        Args:
            concept1_name: Source concept name
            concept2_name: Target concept name
            rel_type: Relationship type (prerequisite_of, related_to, example_of)
            strength: Relationship strength (0.0-1.0)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate strength
            if not 0.0 <= strength <= 1.0:
                print(f"⚠️  Invalid strength: {strength} (must be 0.0-1.0)")
                return False

            # Read current memory
            data = self.client._read_memory_file()
            if data is None:
                print("❌ Failed to read memory")
                return False

            # Verify both concepts exist
            entity_names = {e.get("name") for e in data["entities"]}
            if concept1_name not in entity_names:
                print(f"❌ Concept not found: {concept1_name}")
                return False
            if concept2_name not in entity_names:
                print(f"❌ Concept not found: {concept2_name}")
                return False

            # Check if relationship already exists
            for relation in data.get("relations", []):
                if (relation.get("from") == concept1_name and
                    relation.get("to") == concept2_name and
                    relation.get("relationType") == rel_type):
                    print(f"⚠️  Relationship already exists: {concept1_name} -> {concept2_name} ({rel_type})")
                    return False

            # Create relationship
            relation = {
                "from": concept1_name,
                "to": concept2_name,
                "relationType": rel_type
            }

            # Add to relations
            if "relations" not in data:
                data["relations"] = []
            data["relations"].append(relation)

            # Write back
            if self.client._write_memory_file(data):
                print(f"✅ Created relationship: {concept1_name} --[{rel_type}]--> {concept2_name}")
                return True
            else:
                print(f"❌ Failed to write relationship")
                return False

        except Exception as e:
            print(f"❌ Error creating relationship: {e}")
            return False

    def get_related_concepts(self, concept_name: str) -> List[Dict]:
        """
        Get concepts related to given concept.

        Args:
            concept_name: Concept name to query

        Returns:
            List of related concepts with relationship info
        """
        try:
            data = self.client._read_memory_file()
            if data is None:
                return []

            related = []
            relations = data.get("relations", [])

            # Find all relationships where concept is source or target
            for relation in relations:
                if relation.get("from") == concept_name:
                    related.append({
                        "concept": relation.get("to"),
                        "relationship": relation.get("relationType"),
                        "direction": "outgoing"
                    })
                elif relation.get("to") == concept_name:
                    related.append({
                        "concept": relation.get("from"),
                        "relationship": relation.get("relationType"),
                        "direction": "incoming"
                    })

            return related

        except Exception as e:
            print(f"❌ Error getting related concepts: {e}")
            return []

    def semantic_search(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[Tuple[Dict, float]]:
        """
        Search for concepts semantically.

        Args:
            query: Search query
            domain: Optional domain filter
            limit: Maximum number of results

        Returns:
            List of (entity, relevance_score) tuples
        """
        try:
            data = self.client._read_memory_file()
            if data is None:
                return []

            entities = data.get("entities", [])
            results = []

            query_lower = query.lower()
            query_terms = set(query_lower.split())

            for entity in entities:
                # Filter by domain if specified
                if domain and entity.get("entityType") != domain:
                    continue

                # Calculate relevance score
                score = 0.0

                # Name match (highest weight)
                name = entity.get("name", "").lower()
                if query_lower in name:
                    score += 1.0
                # Partial term matches in name
                name_terms = set(name.split())
                name_overlap = len(query_terms & name_terms)
                if name_overlap > 0:
                    score += 0.5 * (name_overlap / len(query_terms))

                # Observation matches (medium weight)
                observations = entity.get("observations", [])
                for obs in observations:
                    obs_lower = obs.lower()
                    if query_lower in obs_lower:
                        score += 0.3
                    obs_terms = set(obs_lower.split())
                    obs_overlap = len(query_terms & obs_terms)
                    if obs_overlap > 0:
                        score += 0.1 * (obs_overlap / len(query_terms))

                # Add to results if relevant
                if score > 0:
                    results.append((entity, score))

            # Sort by relevance score (descending)
            results.sort(key=lambda x: x[1], reverse=True)

            # Apply limit
            return results[:limit]

        except Exception as e:
            print(f"❌ Error in semantic search: {e}")
            return []

    def get_concept(self, concept_name: str) -> Optional[Dict]:
        """
        Get concept by name.

        Args:
            concept_name: Concept name

        Returns:
            Entity dictionary or None if not found
        """
        try:
            data = self.client._read_memory_file()
            if data is None:
                return None

            for entity in data.get("entities", []):
                if entity.get("name") == concept_name:
                    return entity

            return None

        except Exception as e:
            print(f"❌ Error getting concept: {e}")
            return None

    def add_observation(self, concept_name: str, observation: str) -> bool:
        """
        Add observation to existing concept.

        Args:
            concept_name: Concept name
            observation: Observation to add

        Returns:
            True if successful, False otherwise
        """
        try:
            data = self.client._read_memory_file()
            if data is None:
                return False

            # Find concept
            found = False
            for entity in data["entities"]:
                if entity.get("name") == concept_name:
                    if "observations" not in entity:
                        entity["observations"] = []
                    entity["observations"].append(observation)
                    found = True
                    break

            if not found:
                print(f"❌ Concept not found: {concept_name}")
                return False

            # Write back
            if self.client._write_memory_file(data):
                print(f"✅ Added observation to: {concept_name}")
                return True
            else:
                print(f"❌ Failed to write observation")
                return False

        except Exception as e:
            print(f"❌ Error adding observation: {e}")
            return False


def calculate_importance(
    access_count: int,
    recency_days: int,
    user_flagged: bool
) -> float:
    """
    Calculate memory importance score.

    Factors:
    - Frequency: More accesses = higher importance
    - Recency: Recent accesses = higher importance
    - User flag: User-marked important = 2x multiplier

    Args:
        access_count: Number of times accessed
        recency_days: Days since last access
        user_flagged: Whether user marked as important

    Returns:
        Importance score (0.1-10.0)
    """
    # Frequency score (max 1.5x)
    frequency_score = min(access_count / 10, 1.5)

    # Recency score (decay over 90 days, min 0.3x, max 1.3x)
    recency_score = max(1.0 - (recency_days / 90), 0.3) * 1.3

    # User flag multiplier (2x if flagged)
    flag_multiplier = 2.0 if user_flagged else 1.0

    # Calculate final score
    importance = frequency_score * recency_score * flag_multiplier

    # Clamp to valid range (0.1-10.0)
    return max(0.1, min(importance, 10.0))


def main():
    """CLI interface for knowledge graph memory."""
    import argparse

    parser = argparse.ArgumentParser(description="Knowledge Graph Memory")
    parser.add_argument("command", choices=[
        "add-concept", "add-relation", "search", "related", "info", "add-obs"
    ])
    parser.add_argument("--name", help="Concept name")
    parser.add_argument("--domain", help="Domain (finance, programming, language, science)")
    parser.add_argument("--from", dest="from_concept", help="Source concept")
    parser.add_argument("--to", dest="to_concept", help="Target concept")
    parser.add_argument("--type", help="Relationship type")
    parser.add_argument("--strength", type=float, default=0.7, help="Relationship strength (0.0-1.0)")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--observation", help="Observation to add")
    parser.add_argument("--limit", type=int, default=10, help="Max results for search")

    args = parser.parse_args()
    kg = KnowledgeGraphMemory()

    if args.command == "add-concept":
        if not args.name or not args.domain:
            print("❌ Error: --name and --domain required")
            sys.exit(1)
        kg.add_concept_node(args.name, args.domain, {})

    elif args.command == "add-relation":
        if not args.from_concept or not args.to_concept or not args.type:
            print("❌ Error: --from, --to, and --type required")
            sys.exit(1)
        kg.create_relationship(args.from_concept, args.to_concept, args.type, args.strength)

    elif args.command == "search":
        if not args.query:
            print("❌ Error: --query required")
            sys.exit(1)
        results = kg.semantic_search(args.query, args.domain, args.limit)
        print(f"\n🔎 Search Results: {len(results)} matches\n")
        for entity, score in results:
            name = entity.get("name", "Unknown")
            entity_type = entity.get("entityType", "unknown")
            print(f"   {score:.2f} - {name} ({entity_type})")

    elif args.command == "related":
        if not args.name:
            print("❌ Error: --name required")
            sys.exit(1)
        related = kg.get_related_concepts(args.name)
        print(f"\n🔗 Related Concepts: {len(related)} found\n")
        for rel in related:
            concept = rel["concept"]
            rel_type = rel["relationship"]
            direction = rel["direction"]
            arrow = "-->" if direction == "outgoing" else "<--"
            print(f"   {arrow} {concept} ({rel_type})")

    elif args.command == "info":
        if not args.name:
            print("❌ Error: --name required")
            sys.exit(1)
        concept = kg.get_concept(args.name)
        if concept:
            print(f"\n📖 Concept: {concept.get('name')}\n")
            print(f"   Type: {concept.get('entityType')}")
            observations = concept.get("observations", [])
            print(f"   Observations ({len(observations)}):")
            for obs in observations:
                print(f"      - {obs}")
        else:
            print(f"❌ Concept not found: {args.name}")

    elif args.command == "add-obs":
        if not args.name or not args.observation:
            print("❌ Error: --name and --observation required")
            sys.exit(1)
        kg.add_observation(args.name, args.observation)


if __name__ == "__main__":
    main()
