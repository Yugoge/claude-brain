---
description: "View current memory status and stored memories"
allowed-tools: Read, mcp__memory-server__read_graph, mcp__memory-server__search_nodes, TodoWrite
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Status Command

Display comprehensive memory status including memory server health, storage usage, memory count by category, recent memories, top concepts, and relationships count.

## Usage

```
/memory-status
/memory-status <domain>
/memory-status <entity-type>
```

## Examples

```
/memory-status            # Show all memories
/memory-status finance    # Show finance domain memories
/memory-status concepts   # Show concept entities
```

## What This Command Does

1. **Checks memory server health** - Verifies storage directory, file permissions, memory file structure
2. **Displays memory statistics** - Total entities, relations, observations, entity types breakdown
3. **Lists recent memories** - Shows recently added entities, observations, relationship counts
4. **Filters by domain** (if specified) - Shows domain-specific concepts and related concepts

## Implementation

Query memory graph statistics using MCP tools:

1. **Read full graph**:
```
mcp__memory-server__read_graph
```

2. **Calculate statistics**:
   - Count entities by type
   - Count relations
   - Count observations
   - Group by domain

3. **Search recent memories** (optional):
```
mcp__memory-server__search_nodes:
  query: "{domain}"  # If domain filter provided
```

**Note**: This command uses MCP tools directly, no Python script needed.

## Notes

- Uses agent_memory_utils library to query and display memory information
- See also: `/memory-forget` (remove specific memories), `/memory-clear` (clear all memories)
