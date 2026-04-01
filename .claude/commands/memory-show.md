---
description: "Display memories in a readable format with filtering options"
allowed-tools: Read, Grep, Glob, TodoWrite
disable-model-invocation: true
---

**CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Show Command

Display memories in a human-readable format with optional filtering.

## Usage

```
/memory-show [options]
```

## Examples

```
/memory-show                              # Show all memories (summary)
/memory-show --detailed                   # Show with full content
/memory-show --category concepts          # Show only concepts
/memory-show --domain finance             # Show finance domain
/memory-show --query "Black-Scholes"      # Search for specific memory
/memory-show --recent 10                  # Show 10 most recent entries
/memory-show --category concepts --detailed  # Detailed view of concepts
/memory-show --query "options pricing" --detailed  # Search with details
```

## What This Command Does

1. **Reads memory files** - Scans all .md files in auto-memory directory
2. **Formats output** - Displays in human-readable format
3. **Applies filters** - Filters by category, domain, or search query
4. **Controls detail level** - Shows summary or detailed view with full content

## Implementation

Query auto-memory files using built-in tools:

1. **List all memory files**:
```
Glob:
  pattern: "*.md"
  path: /root/.claude/projects/-root/memory/
```

2. **Search memories** (if query/category/domain provided):
```
Grep:
  pattern: "{search_query}"
  path: /root/.claude/projects/-root/memory/
  output_mode: content
  context: 3
```

3. **Read full files** (if --detailed flag):
```
Read: /root/.claude/projects/-root/memory/{filename}.md
```

4. **Format output**:
   - Summary mode: Show section headers and key entries per file
   - Detailed mode: Show full content of matching sections

**Note**: This command uses Grep and Read tools on auto-memory files. No MCP tools needed.

## Notes

- See also: `/memory-status` (memory health and statistics), `/memory-export` (export memories to file), `/memory-forget` (remove specific memories), `/memory-clear` (clear all memories)
