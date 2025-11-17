---
description: "Remove specific memories by topic or name"
allowed-tools: mcp__memory-server__search_nodes, mcp__memory-server__delete_entities, TodoWrite
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Forget Command

Remove specific memories from the knowledge graph by entity name, search query, entity type, or domain.

## Usage

```
/memory-forget <concept-name>
/memory-forget --query <search-query>
/memory-forget --type <entity-type>
/memory-forget --domain <domain>
```

## Examples

```
/memory-forget "Black-Scholes Model"  # Delete specific concept
/memory-forget --query "option"       # Delete all matching "option"
/memory-forget --type struggles       # Delete all struggles
/memory-forget --domain finance       # Delete all finance concepts
```

## What This Command Does

1. **Searches for matches** - Finds entities by name, query, type, or domain
2. **Shows preview** - Lists all memories that will be deleted
3. **Requires confirmation** - Always asks for confirmation before deletion
4. **Deletes entities** - Removes matching entities from memory graph
5. **Cleans up relationships** - Automatically removes orphaned relationships

## Implementation

Delete memory entities using MCP tools:

1. **Search for matches**:
```
mcp__memory-server__search_nodes:
  query: "{concept_name}"  # Or query/type/domain
```

2. **Show preview** and ask for confirmation

3. **Delete entities**:
```
mcp__memory-server__delete_entities:
  entityNames: ["{entity_1}", "{entity_2}", ...]
```

**Note**: MCP automatically removes orphaned relationships.
**Note**: This command uses MCP tools directly, no Python script needed.

This command modifies the memory graph by removing entities and their relationships.

## Notes

**WARNING**: This action is irreversible! Deleted memories cannot be recovered unless you have a backup of the memory file.

**Backup before deletion**:
```
cp .mcp/memory/memories.json .mcp/memory/memories-backup-$(date +%Y%m%d).json
```

**Consider using `/memory-status` first to review what will be deleted.**

**See also**: `/memory-status` (view current memories), `/memory-clear` (clear all memories - nuclear option)
