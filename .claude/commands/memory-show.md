---
description: "Display memories in a readable format with filtering options"
allowed-tools: Read, mcp__memory-server__search_nodes, mcp__memory-server__open_nodes, TodoWrite
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Show Command

Display memories in a human-readable format with optional filtering.

## Usage

```
/memory-show [options]
```

## Examples

```
/memory-show                              # Show all memories (summary)
/memory-show --detailed                   # Show with full observations
/memory-show --category concepts          # Show only concepts
/memory-show --domain finance             # Show finance domain
/memory-show --query "Black-Scholes"      # Search for specific memory
/memory-show --recent 10                  # Show 10 most recent
/memory-show --category concepts --detailed  # Detailed view of concepts
/memory-show --query "options pricing" --detailed  # Search with details
```

## What This Command Does

1. **Queries memory graph** - Searches based on category, domain, query, or recency
2. **Formats output** - Displays in human-readable format
3. **Applies filters** - Filters by category, domain, or search query
4. **Controls detail level** - Shows summary or detailed view with full observations

## Implementation

Use `scripts/memory/memory-show.py` for implementation.

## Notes

- See also: `/memory-status` (memory server health and statistics), `/memory-export` (export memories to file), `/memory-forget` (remove specific memories), `/memory-clear` (clear all memories)
