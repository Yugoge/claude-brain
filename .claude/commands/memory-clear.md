---
description: "Clear all memories (nuclear option with confirmation)"
allowed-tools: mcp__memory-server__delete_entities, TodoWrite
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Clear Command

WARNING: This command clears ALL memories from the knowledge graph. This is a nuclear option that should only be used when you want to completely reset the memory system.

## Usage

```
/memory-clear
/memory-clear --confirm
```

## Examples

```
/memory-clear            # Clear all memories (with confirmation)
/memory-clear --confirm  # Skip confirmation prompt
```

## What This Command Does

1. **Previews deletion** - Shows statistics of what will be deleted
2. **Requires confirmation** - User must type "DELETE ALL" to confirm
3. **Creates backup** - Automatic timestamped backup before deletion
4. **Deletes all memories** - Removes all concept entities, preference settings, struggle tracking, relationships, observations, ALL memory data
5. **Verifies backup** - Option to cancel if backup fails

## Implementation

Clear all memory entities using MCP tools:

1. **Read current graph** (for backup):
```
mcp__memory-server__read_graph
```

2. **Show warning** and require confirmation

3. **Get all entity names** from graph

4. **Delete all entities**:
```
mcp__memory-server__delete_entities:
  entityNames: [all entity names from graph]
```

**Note**: This command uses MCP tools directly, no Python script needed.

## Notes

**Backup Location**: `.mcp/memory/memories-backup-YYYYMMDD-HHMMSS.json`

**Recovery**: If you accidentally clear memories, restore from backup:
```
ls -la .mcp/memory/memories-backup-*.json
cp .mcp/memory/memories-backup-20251029-092345.json .mcp/memory/memories.json
```

**When to Use**:
- Starting fresh with a clean memory system
- Testing memory integration
- Removing all test data
- Resolving memory corruption issues

**DO NOT use when**:
- You just want to remove specific memories (use `/memory-forget` instead)
- You want to filter by domain (use `/memory-forget --domain`)
- You're unsure about the implications

**Alternative Commands**: `/memory-forget <concept>` (remove specific concept), `/memory-forget --type struggles` (remove all struggles), `/memory-forget --domain finance` (remove finance concepts), `/memory-status` (review what's in memory first)

**See also**: `/memory-status` (view current memories), `/memory-forget` (remove specific memories)
