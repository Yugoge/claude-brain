#!/usr/bin/env python3
"""
Unified Memory Interface

Combines Claude MCP Memory with existing memory utilities into a single,
comprehensive API for cross-session memory operations.

This module provides:
- Unified memory saving (concepts, preferences, context, struggles)
- Intelligent querying across all memory types
- Retention policy management
- Auto-save triggers for key events
- Export/import functionality
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_memory_utils import AgentMemory
from memory_client import MemoryClient


class RetentionPolicy:
    """Retention policy management for memory entries."""

    DEFAULT_POLICIES = {
        "preferences": {
            "ttl_days": 730,  # 2 years
            "priority": "high",
            "auto_save": True
        },
        "concepts": {
            "ttl_days": 365,  # 1 year
            "priority": "high",
            "auto_save": True
        },
        "context": {
            "ttl_days": 180,  # 6 months
            "priority": "medium",
            "auto_save": True
        },
        "struggles": {
            "ttl_days": 365,  # 1 year
            "priority": "high",
            "auto_save": True
        }
    }

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize retention policy.

        Args:
            config_file: Path to policy configuration file
        """
        self.config_file = Path(config_file) if config_file else None
        self.policies = self._load_policies()

    def _load_policies(self) -> Dict:
        """Load retention policies from config or use defaults."""
        if self.config_file and self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                return config.get("retention_policies", self.DEFAULT_POLICIES)
            except Exception as e:
                print(f"⚠️  Failed to load policies: {e}, using defaults")

        return self.DEFAULT_POLICIES

    def get_policy(self, category: str) -> Dict:
        """Get retention policy for category."""
        return self.policies.get(category, self.policies["concepts"])

    def should_auto_save(self, category: str) -> bool:
        """Check if category should auto-save."""
        policy = self.get_policy(category)
        return policy.get("auto_save", True)

    def is_expired(self, timestamp: str, category: str) -> bool:
        """
        Check if memory entry is expired.

        Args:
            timestamp: ISO format timestamp
            category: Memory category

        Returns:
            True if expired, False otherwise
        """
        try:
            created = datetime.fromisoformat(timestamp)
            policy = self.get_policy(category)
            ttl_days = policy.get("ttl_days", 365)
            expiry = created + timedelta(days=ttl_days)
            return datetime.now() > expiry
        except Exception:
            return False


class UnifiedMemory:
    """
    Unified memory interface combining MCP memory with local utilities.

    Provides single API for:
    - Saving memories (concepts, preferences, context, struggles)
    - Querying memories with relevance ranking
    - Auto-save triggers
    - Retention policy management
    - Export/import functionality
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize unified memory interface.

        Args:
            config_file: Path to configuration file
        """
        self.agent_memory = AgentMemory()
        self.client = MemoryClient()
        self.retention = RetentionPolicy(config_file)

    # ========== Memory Saving ==========

    def save_memory(
        self,
        content: str,
        category: str,
        name: Optional[str] = None,
        metadata: Optional[Dict] = None,
        auto: bool = False
    ) -> bool:
        """
        Save memory entry.

        Args:
            content: Memory content
            category: Category (preferences, concepts, context, struggles)
            name: Optional explicit name
            metadata: Additional metadata
            auto: True if auto-saved (respects retention policy)

        Returns:
            True if successful, False otherwise
        """
        # Check auto-save policy
        if auto and not self.retention.should_auto_save(category):
            return True  # Silently skip if policy says no auto-save

        # Route to appropriate handler
        if category == "preferences":
            return self._save_preference(content, metadata or {})
        elif category == "concepts":
            return self._save_concept(content, name, metadata or {})
        elif category == "context":
            return self._save_context(content, metadata or {})
        elif category == "struggles":
            return self._save_struggle(content, metadata or {})
        else:
            print(f"⚠️  Unknown category: {category}")
            return False

    def _save_preference(self, content: str, metadata: Dict) -> bool:
        """Save preference memory."""
        # Parse key: value from content
        if ":" in content:
            key, value = content.split(":", 1)
            return self.agent_memory.update_preference(key.strip(), value.strip())
        else:
            return self.agent_memory.update_preference("note", content)

    def _save_concept(self, content: str, name: Optional[str], metadata: Dict) -> bool:
        """Save concept memory."""
        concept_name = name or content.split()[0]  # Use first word if no name
        domain = metadata.get("domain", "general")

        # Check if concept exists
        existing = self.agent_memory.get_concept(concept_name)
        if existing:
            # Add observation to existing
            return self.agent_memory.add_observation(concept_name, content)
        else:
            # Create new concept
            return self.agent_memory.save_concept(concept_name, domain, metadata)

    def _save_context(self, content: str, metadata: Dict) -> bool:
        """Save context memory."""
        # Save as concept with context domain
        context_name = f"context_{datetime.now().strftime('%Y%m%d')}"
        return self.agent_memory.save_concept(context_name, "context", {
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **metadata
        })

    def _save_struggle(self, content: str, metadata: Dict) -> bool:
        """Save struggle memory."""
        concept = metadata.get("concept", content.split()[0])
        difficulty = metadata.get("difficulty", 0.7)
        domain = metadata.get("domain", "general")
        return self.agent_memory.track_struggle(concept, difficulty, domain, metadata)

    # ========== Memory Querying ==========

    def query_memory(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        domain: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Query memories with relevance ranking.

        Args:
            query: Search query
            categories: Optional category filter
            domain: Optional domain filter
            limit: Maximum results

        Returns:
            List of relevant memories with metadata
        """
        results = self.agent_memory.query_context(query, domain, limit * 2)

        # Filter by category if specified
        if categories:
            results = [
                r for r in results
                if r.get("type") in categories or
                any(cat in r.get("name", "").lower() for cat in categories)
            ]

        # Add retention info
        for result in results:
            obs = result.get("observations", [])
            if obs:
                # Try to extract timestamp from first observation
                first_obs = obs[0]
                if "timestamp=" in first_obs or "updated:" in first_obs:
                    try:
                        timestamp_str = first_obs.split("timestamp=")[1].split(",")[0] if "timestamp=" in first_obs else first_obs.split("updated:")[1].split(")")[0]
                        result["expired"] = self.retention.is_expired(
                            timestamp_str.strip(),
                            result.get("type", "concepts")
                        )
                    except Exception:
                        result["expired"] = False
                else:
                    result["expired"] = False

        return results[:limit]

    def get_all_memories(self, category: Optional[str] = None) -> Dict:
        """
        Get all memories, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            Dictionary with entities and relations
        """
        data = self.client._read_memory_file()
        if not data:
            return {"entities": [], "relations": []}

        if category:
            entities = [
                e for e in data.get("entities", [])
                if e.get("entityType") == category
            ]
            data["entities"] = entities

        return data

    # ========== Auto-Save Triggers ==========

    def after_ask_session(
        self,
        question: str,
        answer: str,
        concepts: List[str],
        domain: Optional[str] = None
    ):
        """
        Auto-save trigger after /ask session.

        Args:
            question: User question
            answer: Answer provided
            concepts: Concepts discussed
            domain: Optional domain
        """
        for concept in concepts:
            self.save_memory(
                content=f"Discussed in /ask: {question[:100]}...",
                category="concepts",
                name=concept,
                metadata={
                    "domain": domain or "general",
                    "timestamp": datetime.now().isoformat(),
                    "source": "ask_session"
                },
                auto=True
            )

    def after_learning_session(
        self,
        material: str,
        concepts_learned: List[str],
        preferences: Optional[Dict] = None,
        domain: Optional[str] = None
    ):
        """
        Auto-save trigger after learning session.

        Args:
            material: Learning material name
            concepts_learned: Concepts learned
            preferences: User preferences observed
            domain: Optional domain
        """
        # Save concepts
        for concept in concepts_learned:
            self.save_memory(
                content=f"Learned from {material}",
                category="concepts",
                name=concept,
                metadata={
                    "domain": domain or "general",
                    "material": material,
                    "timestamp": datetime.now().isoformat()
                },
                auto=True
            )

        # Save preferences
        if preferences:
            for key, value in preferences.items():
                self.save_memory(
                    content=f"{key}: {value}",
                    category="preferences",
                    metadata={"source": "learning_session"},
                    auto=True
                )

    def after_review_session(
        self,
        concept: str,
        performance: Dict,
        domain: Optional[str] = None
    ):
        """
        Auto-save trigger after review session.

        Args:
            concept: Concept reviewed
            performance: Performance data (correct, rating, etc.)
            domain: Optional domain
        """
        # Track struggle if review was incorrect
        if not performance.get("correct", True):
            difficulty = 1.0 - (performance.get("rating", 0) / 4.0)  # Invert rating to difficulty
            self.save_memory(
                content=f"Struggled with review: rating={performance.get('rating')}",
                category="struggles",
                metadata={
                    "concept": concept,
                    "difficulty": difficulty,
                    "domain": domain or "general",
                    "timestamp": datetime.now().isoformat()
                },
                auto=True
            )

    def after_archival(
        self,
        conversation_id: str,
        concepts_extracted: List[str],
        domain: Optional[str] = None
    ):
        """
        Auto-save trigger after conversation archival.

        Args:
            conversation_id: Conversation ID
            concepts_extracted: Concepts extracted from conversation
            domain: Optional domain
        """
        # Save context about archived conversation
        self.save_memory(
            content=f"Archived conversation with {len(concepts_extracted)} concepts",
            category="context",
            metadata={
                "conversation_id": conversation_id,
                "concepts": concepts_extracted,
                "domain": domain or "general",
                "timestamp": datetime.now().isoformat()
            },
            auto=True
        )

    # ========== Export/Import ==========

    def export_memories(
        self,
        output_file: str,
        format: str = "json",
        category: Optional[str] = None
    ) -> bool:
        """
        Export memories to file.

        Args:
            output_file: Output file path
            format: Export format (json or csv)
            category: Optional category filter

        Returns:
            True if successful, False otherwise
        """
        try:
            data = self.get_all_memories(category)
            output_path = Path(output_file)

            if format == "json":
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            elif format == "csv":
                import csv
                with open(output_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Name', 'Type', 'Observations', 'Observation_Count'])
                    for entity in data.get("entities", []):
                        obs = entity.get("observations", [])
                        writer.writerow([
                            entity.get("name", ""),
                            entity.get("entityType", ""),
                            " | ".join(obs),
                            len(obs)
                        ])
            else:
                print(f"❌ Unknown format: {format}")
                return False

            print(f"✅ Exported {len(data.get('entities', []))} memories to {output_file}")
            return True

        except Exception as e:
            print(f"❌ Export failed: {e}")
            return False

    # ========== Statistics ==========

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive memory statistics.

        Returns:
            Statistics dictionary
        """
        stats = self.client.get_statistics()
        if not stats:
            return {}

        # Add retention policy info
        stats["retention_policies"] = self.retention.policies

        # Add category breakdown
        data = self.get_all_memories()
        entities = data.get("entities", [])

        category_stats = {}
        for entity in entities:
            cat = entity.get("entityType", "unknown")
            if cat not in category_stats:
                category_stats[cat] = {
                    "count": 0,
                    "observations": 0,
                    "expired": 0
                }
            category_stats[cat]["count"] += 1
            category_stats[cat]["observations"] += len(entity.get("observations", []))

        stats["category_details"] = category_stats

        return stats


def main():
    """CLI interface for unified memory."""
    import argparse

    parser = argparse.ArgumentParser(description="Unified Memory Interface")
    parser.add_argument("command", choices=[
        "save", "query", "export", "stats", "trigger"
    ])
    parser.add_argument("--content", help="Memory content")
    parser.add_argument("--category", help="Memory category")
    parser.add_argument("--name", help="Memory name")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--domain", help="Domain filter")
    parser.add_argument("--output", help="Output file")
    parser.add_argument("--format", default="json", help="Export format (json or csv)")
    parser.add_argument("--limit", type=int, default=10, help="Query result limit")

    args = parser.parse_args()
    memory = UnifiedMemory()

    if args.command == "save":
        if not args.content or not args.category:
            print("❌ Error: --content and --category required")
            sys.exit(1)
        success = memory.save_memory(args.content, args.category, args.name)
        if success:
            print(f"✅ Saved memory: {args.content[:50]}...")

    elif args.command == "query":
        if not args.query:
            print("❌ Error: --query required")
            sys.exit(1)
        results = memory.query_memory(args.query, domain=args.domain, limit=args.limit)
        print(f"\n🔎 Query Results: {len(results)} matches\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['name']} ({result['type']}) - Score: {result['relevance_score']:.2f}")
            if result.get("expired"):
                print(f"   ⚠️  EXPIRED")
            for obs in result['observations'][:2]:
                print(f"   - {obs[:80]}...")

    elif args.command == "export":
        if not args.output:
            print("❌ Error: --output required")
            sys.exit(1)
        memory.export_memories(args.output, args.format, args.category)

    elif args.command == "stats":
        stats = memory.get_statistics()
        print("\n📊 Unified Memory Statistics")
        print("=" * 60)
        print(f"\nTotal Entities: {stats.get('total_entities', 0)}")
        print(f"Total Relations: {stats.get('total_relations', 0)}")
        print(f"Total Observations: {stats.get('total_observations', 0)}")
        print(f"\nCategory Breakdown:")
        for cat, details in stats.get("category_details", {}).items():
            print(f"  {cat}:")
            print(f"    Entities: {details['count']}")
            print(f"    Observations: {details['observations']}")
            print(f"    Expired: {details.get('expired', 0)}")

    elif args.command == "trigger":
        print("Trigger commands:")
        print("  after_ask_session")
        print("  after_learning_session")
        print("  after_review_session")
        print("  after_archival")


if __name__ == "__main__":
    main()
