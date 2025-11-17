#!/usr/bin/env python3
"""
MCP Memory Client Helper Library

Provides Python interface for safe memory operations with error handling.
Note: The official memory server uses MCP tools (not HTTP REST API).
This library provides convenience wrappers for Claude Code integrations.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


class MemoryClient:
    """Client helper for MCP Memory Server operations with error handling."""

    def __init__(self, storage_path: str = "/root/knowledge-system/.mcp/memory/memories.json"):
        """
        Initialize memory client.

        Args:
            storage_path: Path to memories.json file
        """
        self.storage_path = Path(storage_path)

    def _ensure_storage_directory(self) -> bool:
        """Ensure storage directory exists with proper permissions."""
        try:
            storage_dir = self.storage_path.parent
            if not storage_dir.exists():
                storage_dir.mkdir(parents=True, mode=0o700)
                print(f"✅ Created storage directory: {storage_dir}")
            return True
        except Exception as e:
            print(f"❌ Failed to create storage directory: {e}")
            return False

    def _read_memory_file(self) -> Optional[Dict]:
        """
        Read and parse memory file with error handling.

        Returns:
            Dictionary with entities and relations, or None if error
        """
        try:
            if not self.storage_path.exists():
                # Return empty graph structure
                return {"entities": [], "relations": []}

            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            # Validate structure
            if not isinstance(data, dict):
                print("⚠️  Memory file is not a dictionary, creating new structure")
                return {"entities": [], "relations": []}

            if "entities" not in data:
                data["entities"] = []
            if "relations" not in data:
                data["relations"] = []

            return data

        except json.JSONDecodeError as e:
            print(f"❌ Memory file is invalid JSON: {e}")
            print(f"   File: {self.storage_path}")
            return None
        except Exception as e:
            print(f"❌ Error reading memory file: {e}")
            return None

    def _write_memory_file(self, data: Dict) -> bool:
        """
        Write memory file with error handling.

        Args:
            data: Dictionary with entities and relations

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            if not self._ensure_storage_directory():
                return False

            # Write with pretty formatting
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

            return True

        except Exception as e:
            print(f"❌ Error writing memory file: {e}")
            return False

    def get_statistics(self) -> Optional[Dict[str, Any]]:
        """
        Get memory statistics.

        Returns:
            Dictionary with entity count, relation count, etc.
        """
        try:
            data = self._read_memory_file()
            if data is None:
                return None

            entities = data.get("entities", [])
            relations = data.get("relations", [])

            # Count by entity type
            entity_types: Dict[str, int] = {}
            total_observations = 0

            for entity in entities:
                entity_type = entity.get("entityType", "unknown")
                entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                total_observations += len(entity.get("observations", []))

            return {
                "total_entities": len(entities),
                "total_relations": len(relations),
                "total_observations": total_observations,
                "entity_types": entity_types,
                "storage_file": str(self.storage_path),
                "file_size_bytes": self.storage_path.stat().st_size if self.storage_path.exists() else 0,
                "last_modified": datetime.fromtimestamp(
                    self.storage_path.stat().st_mtime
                ).isoformat() if self.storage_path.exists() else None
            }

        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return None

    def search_entities(self, query: str, entity_type: Optional[str] = None) -> List[Dict]:
        """
        Simple text search for entities.

        Args:
            query: Search query string
            entity_type: Optional filter by entity type

        Returns:
            List of matching entities
        """
        try:
            data = self._read_memory_file()
            if data is None:
                return []

            entities = data.get("entities", [])
            results = []

            query_lower = query.lower()

            for entity in entities:
                # Filter by type if specified
                if entity_type and entity.get("entityType") != entity_type:
                    continue

                # Search in name
                if query_lower in entity.get("name", "").lower():
                    results.append(entity)
                    continue

                # Search in observations
                observations = entity.get("observations", [])
                if any(query_lower in obs.lower() for obs in observations):
                    results.append(entity)

            return results

        except Exception as e:
            print(f"❌ Error searching entities: {e}")
            return []

    def validate_memory_file(self) -> Dict[str, Any]:
        """
        Validate memory file structure and integrity.

        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "info": []
        }

        try:
            # Check if file exists
            if not self.storage_path.exists():
                results["warnings"].append("Memory file does not exist (will be created on first use)")
                results["valid"] = True
                return results

            # Read and parse
            data = self._read_memory_file()
            if data is None:
                results["errors"].append("Failed to read memory file")
                return results

            # Validate structure
            if not isinstance(data, dict):
                results["errors"].append("Memory data is not a dictionary")
                return results

            if "entities" not in data:
                results["errors"].append("Missing 'entities' field")
                return results

            if "relations" not in data:
                results["errors"].append("Missing 'relations' field")
                return results

            # Validate entities
            entities = data["entities"]
            if not isinstance(entities, list):
                results["errors"].append("'entities' is not a list")
                return results

            entity_names = set()
            for i, entity in enumerate(entities):
                if not isinstance(entity, dict):
                    results["errors"].append(f"Entity {i} is not a dictionary")
                    continue

                if "name" not in entity:
                    results["errors"].append(f"Entity {i} missing 'name' field")
                else:
                    name = entity["name"]
                    if name in entity_names:
                        results["warnings"].append(f"Duplicate entity name: {name}")
                    entity_names.add(name)

                if "entityType" not in entity:
                    results["warnings"].append(f"Entity '{entity.get('name', i)}' missing 'entityType'")

            # Validate relations
            relations = data["relations"]
            if not isinstance(relations, list):
                results["errors"].append("'relations' is not a list")
                return results

            for i, relation in enumerate(relations):
                if not isinstance(relation, dict):
                    results["errors"].append(f"Relation {i} is not a dictionary")
                    continue

                if "from" not in relation:
                    results["errors"].append(f"Relation {i} missing 'from' field")
                if "to" not in relation:
                    results["errors"].append(f"Relation {i} missing 'to' field")

                # Check if referenced entities exist
                from_entity = relation.get("from")
                to_entity = relation.get("to")
                if from_entity and from_entity not in entity_names:
                    results["warnings"].append(f"Relation references non-existent entity: {from_entity}")
                if to_entity and to_entity not in entity_names:
                    results["warnings"].append(f"Relation references non-existent entity: {to_entity}")

            # Summary info
            results["info"].append(f"Total entities: {len(entities)}")
            results["info"].append(f"Total relations: {len(relations)}")
            results["info"].append(f"Entity types: {len(set(e.get('entityType', 'unknown') for e in entities))}")

            # Overall validation
            if not results["errors"]:
                results["valid"] = True

            return results

        except Exception as e:
            results["errors"].append(f"Validation error: {e}")
            return results


def safe_read_memory() -> Optional[Dict]:
    """
    Safely read memory with error handling.

    Returns:
        Memory data or None if error
    """
    try:
        client = MemoryClient()
        return client._read_memory_file()
    except Exception as e:
        print(f"⚠️  Error reading memory: {e}")
        return None


def safe_get_statistics() -> Optional[Dict]:
    """
    Safely get memory statistics.

    Returns:
        Statistics dictionary or None if error
    """
    try:
        client = MemoryClient()
        return client.get_statistics()
    except Exception as e:
        print(f"⚠️  Error getting statistics: {e}")
        return None


def main():
    """CLI interface for memory client."""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Memory Client Helper")
    parser.add_argument("command", choices=["stats", "validate", "search"],
                        help="Command to execute")
    parser.add_argument("--query", help="Search query (for search command)")
    parser.add_argument("--type", help="Entity type filter (for search command)")

    args = parser.parse_args()
    client = MemoryClient()

    if args.command == "stats":
        stats = client.get_statistics()
        if stats:
            print("\n📊 Memory Statistics:")
            print(f"   Total Entities: {stats['total_entities']}")
            print(f"   Total Relations: {stats['total_relations']}")
            print(f"   Total Observations: {stats['total_observations']}")
            print(f"   Entity Types: {stats['entity_types']}")
            print(f"   Storage File: {stats['storage_file']}")
            print(f"   File Size: {stats['file_size_bytes']} bytes")
            if stats['last_modified']:
                print(f"   Last Modified: {stats['last_modified']}")

    elif args.command == "validate":
        results = client.validate_memory_file()
        print(f"\n🔍 Validation Results: {'✅ VALID' if results['valid'] else '❌ INVALID'}")

        if results['errors']:
            print("\n❌ Errors:")
            for error in results['errors']:
                print(f"   - {error}")

        if results['warnings']:
            print("\n⚠️  Warnings:")
            for warning in results['warnings']:
                print(f"   - {warning}")

        if results['info']:
            print("\nℹ️  Info:")
            for info in results['info']:
                print(f"   - {info}")

    elif args.command == "search":
        if not args.query:
            print("❌ Error: --query is required for search command")
            sys.exit(1)

        results = client.search_entities(args.query, args.type)
        print(f"\n🔎 Search Results: {len(results)} matches")
        for entity in results:
            name = entity.get("name", "Unknown")
            entity_type = entity.get("entityType", "unknown")
            obs_count = len(entity.get("observations", []))
            print(f"   - {name} ({entity_type}): {obs_count} observations")


if __name__ == "__main__":
    main()
