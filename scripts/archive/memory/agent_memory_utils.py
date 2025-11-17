#!/usr/bin/env python3
"""
Shared memory utilities for all agents.

Provides common memory operations:
- query_context: Get relevant context before responding
- save_concept: Save concept to knowledge graph
- update_preference: Update user preferences
- track_struggle: Record user struggles
- create_relationship: Link concepts in knowledge graph
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from knowledge_graph_memory import KnowledgeGraphMemory
from memory_client import MemoryClient


class AgentMemory:
    """Memory operations for agents."""

    def __init__(self):
        """Initialize agent memory with knowledge graph and client."""
        self.kg = KnowledgeGraphMemory()
        self.client = MemoryClient()

    def query_context(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Query relevant memories for context.

        Args:
            query: Search query
            domain: Optional domain filter
            limit: Maximum results

        Returns:
            List of relevant memories with scores
        """
        try:
            # Use knowledge graph semantic search
            results = self.kg.semantic_search(query, domain, limit)

            # Convert to dict format with relevance
            memories = []
            for entity, score in results:
                memories.append({
                    "name": entity.get("name"),
                    "type": entity.get("entityType"),
                    "observations": entity.get("observations", []),
                    "relevance_score": score
                })

            return memories

        except Exception as e:
            print(f"⚠️  Memory query failed: {e}")
            return []

    def save_concept(
        self,
        name: str,
        domain: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Save concept to knowledge graph.

        Args:
            name: Concept name
            domain: Domain (finance, programming, language, science)
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.kg.add_concept_node(name, domain, metadata or {})
        except Exception as e:
            print(f"⚠️  Failed to save concept: {e}")
            return False

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
            return self.kg.add_observation(concept_name, observation)
        except Exception as e:
            print(f"⚠️  Failed to add observation: {e}")
            return False

    def update_preference(self, key: str, value: any) -> bool:
        """
        Update user preference.

        Args:
            key: Preference key (e.g., "difficulty", "learning_pace")
            value: Preference value

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create preferences entity
            prefs = self.kg.get_concept("user_preferences")

            if prefs:
                # Update existing preferences
                obs = f"{key}: {value} (updated: {datetime.now().isoformat()})"
                return self.kg.add_observation("user_preferences", obs)
            else:
                # Create preferences entity
                metadata = {
                    key: value,
                    "created": datetime.now().isoformat()
                }
                return self.kg.add_concept_node(
                    "user_preferences",
                    "preferences",
                    metadata
                )

        except Exception as e:
            print(f"⚠️  Failed to update preference: {e}")
            return False

    def get_all_preferences(self) -> Dict:
        """
        Get all user preferences.

        Returns:
            Dictionary of preferences
        """
        try:
            prefs = self.kg.get_concept("user_preferences")
            if not prefs:
                return {}

            # Parse preferences from observations
            preferences = {}
            for obs in prefs.get("observations", []):
                if ":" in obs and not obs.startswith("Domain:") and not obs.startswith("Added:"):
                    key, value = obs.split(":", 1)
                    preferences[key.strip()] = value.split("(updated:")[0].strip()

            return preferences

        except Exception as e:
            print(f"⚠️  Failed to get preferences: {e}")
            return {}

    def track_struggle(
        self,
        concept: str,
        difficulty: float,
        domain: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Track concept user struggles with.

        Args:
            concept: Concept name
            difficulty: Difficulty score (0.0-1.0)
            domain: Domain
            metadata: Additional metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            struggle_name = f"struggle_{concept}"

            # Check if struggle already tracked
            existing = self.kg.get_concept(struggle_name)

            if existing:
                # Add observation to existing struggle
                obs = f"Struggled again: difficulty={difficulty:.2f}, timestamp={datetime.now().isoformat()}"
                return self.kg.add_observation(struggle_name, obs)
            else:
                # Create new struggle entity
                meta = metadata or {}
                meta.update({
                    "difficulty": difficulty,
                    "timestamp": datetime.now().isoformat(),
                    "original_concept": concept
                })
                return self.kg.add_concept_node(struggle_name, "struggles", meta)

        except Exception as e:
            print(f"⚠️  Failed to track struggle: {e}")
            return False

    def create_relationship(
        self,
        concept1: str,
        concept2: str,
        rel_type: str,
        strength: float = 0.7
    ) -> bool:
        """
        Create relationship between concepts.

        Args:
            concept1: Source concept name
            concept2: Target concept name
            rel_type: Relationship type (prerequisite_of, related_to, example_of)
            strength: Relationship strength (0.0-1.0)

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.kg.create_relationship(concept1, concept2, rel_type, strength)
        except Exception as e:
            print(f"⚠️  Failed to create relationship: {e}")
            return False

    def get_related_concepts(self, concept_name: str) -> List[Dict]:
        """
        Get concepts related to given concept.

        Args:
            concept_name: Concept name

        Returns:
            List of related concepts
        """
        try:
            return self.kg.get_related_concepts(concept_name)
        except Exception as e:
            print(f"⚠️  Failed to get related concepts: {e}")
            return []

    def get_concept(self, concept_name: str) -> Optional[Dict]:
        """
        Get concept by name.

        Args:
            concept_name: Concept name

        Returns:
            Concept dict or None
        """
        try:
            return self.kg.get_concept(concept_name)
        except Exception as e:
            print(f"⚠️  Failed to get concept: {e}")
            return None

    def get_struggles(self, domain: Optional[str] = None) -> List[Dict]:
        """
        Get all struggles, optionally filtered by domain.

        Args:
            domain: Optional domain filter

        Returns:
            List of struggle concepts
        """
        try:
            # Search for struggles
            results = self.kg.semantic_search("struggle", domain=domain, limit=100)

            struggles = []
            for entity, score in results:
                name = entity.get("name", "")
                if name.startswith("struggle_"):
                    struggles.append({
                        "concept": name.replace("struggle_", ""),
                        "entity": entity,
                        "score": score
                    })

            return struggles

        except Exception as e:
            print(f"⚠️  Failed to get struggles: {e}")
            return []


# Convenience functions with error handling


def safe_query_memory(
    query: str,
    domain: Optional[str] = None,
    fallback: Optional[List] = None
) -> List[Dict]:
    """
    Query memory with graceful error handling.

    Args:
        query: Search query
        domain: Optional domain filter
        fallback: Fallback value if error

    Returns:
        List of memories or fallback
    """
    try:
        memory = AgentMemory()
        return memory.query_context(query, domain)
    except Exception as e:
        print(f"⚠️  Memory query error: {e}, using fallback")
        return fallback or []


def safe_save_concept(
    name: str,
    domain: str,
    metadata: Optional[Dict] = None
) -> bool:
    """
    Save concept with graceful error handling.

    Args:
        name: Concept name
        domain: Domain
        metadata: Additional metadata

    Returns:
        True if successful, False otherwise
    """
    try:
        memory = AgentMemory()
        return memory.save_concept(name, domain, metadata)
    except Exception as e:
        print(f"⚠️  Memory save error: {e}")
        return False


def safe_track_struggle(
    concept: str,
    difficulty: float,
    domain: str
) -> bool:
    """
    Track struggle with graceful error handling.

    Args:
        concept: Concept name
        difficulty: Difficulty score (0.0-1.0)
        domain: Domain

    Returns:
        True if successful, False otherwise
    """
    try:
        memory = AgentMemory()
        return memory.track_struggle(concept, difficulty, domain)
    except Exception as e:
        print(f"⚠️  Struggle tracking error: {e}")
        return False


def main():
    """CLI interface for agent memory utilities."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent Memory Utilities")
    parser.add_argument("command", choices=[
        "query", "save", "preference", "struggle", "relate", "struggles"
    ])
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--name", help="Concept name")
    parser.add_argument("--domain", help="Domain")
    parser.add_argument("--key", help="Preference key")
    parser.add_argument("--value", help="Preference value")
    parser.add_argument("--difficulty", type=float, help="Difficulty score (0.0-1.0)")
    parser.add_argument("--from", dest="from_concept", help="Source concept")
    parser.add_argument("--to", dest="to_concept", help="Target concept")
    parser.add_argument("--type", help="Relationship type")
    parser.add_argument("--limit", type=int, default=10, help="Max results")

    args = parser.parse_args()
    memory = AgentMemory()

    if args.command == "query":
        if not args.query:
            print("❌ Error: --query required")
            sys.exit(1)
        results = memory.query_context(args.query, args.domain, args.limit)
        print(f"\n🔎 Query Results: {len(results)} matches\n")
        for mem in results:
            print(f"   [{mem['relevance_score']:.2f}] {mem['name']} ({mem['type']})")
            if mem['observations']:
                print(f"      Observations: {len(mem['observations'])}")

    elif args.command == "save":
        if not args.name or not args.domain:
            print("❌ Error: --name and --domain required")
            sys.exit(1)
        memory.save_concept(args.name, args.domain, {})

    elif args.command == "preference":
        if args.key and args.value:
            memory.update_preference(args.key, args.value)
        else:
            prefs = memory.get_all_preferences()
            print(f"\n⚙️  User Preferences:\n")
            for key, value in prefs.items():
                print(f"   {key}: {value}")

    elif args.command == "struggle":
        if not args.name or not args.difficulty or not args.domain:
            print("❌ Error: --name, --difficulty, and --domain required")
            sys.exit(1)
        memory.track_struggle(args.name, args.difficulty, args.domain)

    elif args.command == "relate":
        if not args.from_concept or not args.to_concept or not args.type:
            print("❌ Error: --from, --to, and --type required")
            sys.exit(1)
        memory.create_relationship(args.from_concept, args.to_concept, args.type)

    elif args.command == "struggles":
        struggles = memory.get_struggles(args.domain)
        print(f"\n📉 Struggles: {len(struggles)} found\n")
        for struggle in struggles:
            print(f"   - {struggle['concept']} (score: {struggle['score']:.2f})")


if __name__ == "__main__":
    main()
