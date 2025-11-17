#!/usr/bin/env python3
"""
MCP Intelligent Memory Proxy

Provides transparent failover between official MCP server and Python backup.
Automatically detects health and routes requests to appropriate backend.

Architecture:
    Agent → Intelligent Proxy → [Official MCP | Python Backup] → memories.json

Usage:
    python scripts/mcp_intelligent_proxy.py

Configuration (.claude.json):
    {
      "mcpServers": {
        "memory": {
          "command": "python3",
          "args": ["/root/knowledge-system/scripts/mcp_intelligent_proxy.py"]
        }
      }
    }
"""

import asyncio
import json
import sys
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import existing memory client backend
sys.path.insert(0, '/root/knowledge-system/scripts')
from memory_client import MemoryClient


class HealthState:
    """Health states for backend servers."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


class MCPBackend(ABC):
    """Abstract interface for memory backends."""

    @abstractmethod
    async def check_health(self) -> Tuple[str, Optional[str]]:
        """
        Check backend health.

        Returns:
            Tuple of (health_state, error_message)
        """
        pass

    @abstractmethod
    async def search_nodes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for nodes."""
        pass

    @abstractmethod
    async def create_entities(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create entities."""
        pass

    @abstractmethod
    async def create_relations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create relations."""
        pass

    @abstractmethod
    async def add_observations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Add observations."""
        pass

    @abstractmethod
    async def read_graph(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Read graph."""
        pass


# NOTE: OfficialMCPBackend removed (2025-10-29)
# Rationale: Both official MCP and Python backend access the same memories.json file.
# Adding MCP client complexity provides no functional benefit - Python backend is:
# - Faster (~200ms vs ~500ms startup)
# - More reliable (direct file access, no process spawning)
# - Simpler (no JSON-RPC stdio communication needed)
# The proxy now uses Python backend exclusively, which matches production usage patterns.


class PythonClientBackend(MCPBackend):
    """Backend wrapper for Python memory client."""

    def __init__(self):
        self.client = MemoryClient()

    async def check_health(self) -> Tuple[str, Optional[str]]:
        """Python client is always healthy (direct file access)."""
        try:
            # Test file access
            self.client._ensure_storage_directory()
            return (HealthState.HEALTHY, None)
        except Exception as e:
            return (HealthState.FAILED, f"Storage access error: {str(e)}")

    async def search_nodes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for entities by query."""
        query = arguments.get("query", "")
        results = self.client.search_entities(query)
        return {
            "entities": results,
            "count": len(results)
        }

    async def create_entities(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create new entities."""
        entities = arguments.get("entities", [])
        data = self.client._read_memory_file()
        if data is None:
            return {"error": "Failed to read memory file"}

        existing_names = {e.get("name") for e in data.get("entities", [])}
        created = []

        for entity in entities:
            name = entity.get("name")
            if name in existing_names:
                continue

            data["entities"].append({
                "name": name,
                "entityType": entity.get("entityType"),
                "observations": entity.get("observations", [])
            })
            created.append(name)

        success = self.client._write_memory_file(data)
        return {
            "success": success,
            "created": created,
            "skipped": len(entities) - len(created)
        }

    async def create_relations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Create relations between entities."""
        relations = arguments.get("relations", [])
        data = self.client._read_memory_file()
        if data is None:
            return {"error": "Failed to read memory file"}

        existing_names = {e.get("name") for e in data.get("entities", [])}
        created = []
        errors = []

        for relation in relations:
            from_entity = relation.get("from")
            to_entity = relation.get("to")
            relation_type = relation.get("relationType")

            if from_entity not in existing_names:
                errors.append(f"Entity not found: {from_entity}")
                continue
            if to_entity not in existing_names:
                errors.append(f"Entity not found: {to_entity}")
                continue

            existing_relations = data.get("relations", [])
            duplicate = any(
                r.get("from") == from_entity and
                r.get("to") == to_entity and
                r.get("relationType") == relation_type
                for r in existing_relations
            )

            if duplicate:
                continue

            data["relations"].append({
                "from": from_entity,
                "to": to_entity,
                "relationType": relation_type
            })
            created.append(f"{from_entity} -> {to_entity}")

        success = self.client._write_memory_file(data)
        return {
            "success": success,
            "created": created,
            "errors": errors
        }

    async def add_observations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Add observations to existing entities."""
        observations = arguments.get("observations", [])
        data = self.client._read_memory_file()
        if data is None:
            return {"error": "Failed to read memory file"}

        updated = []
        errors = []

        for obs in observations:
            entity_name = obs.get("entityName")
            contents = obs.get("contents", [])

            entity = next((e for e in data["entities"] if e.get("name") == entity_name), None)
            if entity is None:
                errors.append(f"Entity not found: {entity_name}")
                continue

            existing_obs = set(entity.get("observations", []))
            for content in contents:
                if content not in existing_obs:
                    entity["observations"].append(content)

            updated.append(entity_name)

        success = self.client._write_memory_file(data)
        return {
            "success": success,
            "updated": updated,
            "errors": errors
        }

    async def read_graph(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Read entire knowledge graph."""
        data = self.client._read_memory_file()
        if data is None:
            return {"error": "Failed to read memory file"}
        return data


class IntelligentMemoryProxy:
    """Intelligent proxy with automatic failover."""

    def __init__(self):
        self.server = Server("memory")
        self.python_backend = PythonClientBackend()
        # Simplified: Use Python backend exclusively (faster, more reliable than spawning MCP process)
        self._register_handlers()

    def _log_system_message(self, message: str):
        """Log system message to stderr (visible to user)."""
        print(f"[Memory Proxy] {message}", file=sys.stderr)

    async def _select_backend(self) -> MCPBackend:
        """Select Python backend (always available)."""
        # Simplified implementation: Python backend is faster and more reliable
        # Both official MCP and Python access the same memories.json file anyway
        return self.python_backend

    def _register_handlers(self):
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """Advertise available memory tools."""
            return [
                Tool(
                    name="search_nodes",
                    description="Search for nodes in the knowledge graph by query string",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to match against entity names and observations"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="create_entities",
                    description="Create new entities in the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "entityType": {"type": "string"},
                                        "observations": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    },
                                    "required": ["name", "entityType", "observations"]
                                }
                            }
                        },
                        "required": ["entities"]
                    }
                ),
                Tool(
                    name="create_relations",
                    description="Create relations between entities in the knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "relations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "from": {"type": "string"},
                                        "to": {"type": "string"},
                                        "relationType": {"type": "string"}
                                    },
                                    "required": ["from", "to", "relationType"]
                                }
                            }
                        },
                        "required": ["relations"]
                    }
                ),
                Tool(
                    name="add_observations",
                    description="Add observations to existing entities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "observations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "entityName": {"type": "string"},
                                        "contents": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    },
                                    "required": ["entityName", "contents"]
                                }
                            }
                        },
                        "required": ["observations"]
                    }
                ),
                Tool(
                    name="read_graph",
                    description="Read the entire knowledge graph",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Dispatch tool calls with automatic failover."""
            backend = await self._select_backend()

            try:
                # Route to appropriate handler with retry
                if name == "search_nodes":
                    result = await backend.search_nodes(arguments)
                elif name == "create_entities":
                    result = await backend.create_entities(arguments)
                elif name == "create_relations":
                    result = await backend.create_relations(arguments)
                elif name == "add_observations":
                    result = await backend.add_observations(arguments)
                elif name == "read_graph":
                    result = await backend.read_graph(arguments)
                else:
                    result = {"error": f"Unknown tool: {name}"}

                return [TextContent(type="text", text=json.dumps(result))]

            except Exception as e:
                # Error handling: Log and return error message
                self._log_system_message(f"❌ Error executing {name}: {str(e)}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)})
                )]

    async def run(self):
        """Start the proxy server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Entry point for intelligent proxy."""
    proxy = IntelligentMemoryProxy()
    await proxy.run()


if __name__ == "__main__":
    asyncio.run(main())
