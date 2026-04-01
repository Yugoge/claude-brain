---
description: "View current memory status and stored memories"
allowed-tools: Read, Glob, Bash, TodoWrite
disable-model-invocation: true
---

**CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Status Command

Display comprehensive memory status including auto-memory health, storage usage, memory count by topic, recent memories, and file statistics.

## Usage

```
/memory-status
/memory-status <domain>
/memory-status <topic>
```

## Examples

```
/memory-status            # Show all memory files
/memory-status finance    # Show finance-related memory entries
/memory-status concepts   # Show concept-related entries
```

## What This Command Does

1. **Checks auto-memory health** - Verifies memory directory exists, file permissions, file structure
2. **Displays memory statistics** - Total files, total size, topics covered, entry counts
3. **Lists memory files** - Shows all .md files in memory directory with sizes
4. **Filters by topic** (if specified) - Shows topic-specific entries from memory files

## Implementation

Query auto-memory files in `/root/.claude/projects/-root/memory/`:

1. **List memory directory**:
```bash
ls -la /root/.claude/projects/-root/memory/
```

2. **Count files and calculate size**:
```bash
# Count .md files
find /root/.claude/projects/-root/memory/ -name "*.md" | wc -l
# Total size
du -sh /root/.claude/projects/-root/memory/
```

3. **Read each memory file** to extract topics and entry counts:
```
Read: /root/.claude/projects/-root/memory/MEMORY.md
```
(Repeat for each .md file found)

4. **Search for domain/topic** (if filter provided):
```
Grep:
  pattern: "{domain}"
  path: /root/.claude/projects/-root/memory/
  output_mode: content
```

**Note**: This command uses Read, Glob, and Bash tools on auto-memory files. No MCP tools needed.

## Notes

- Memory files are stored at `/root/.claude/projects/-root/memory/`
- Primary file is `MEMORY.md`, additional topic-specific `.md` files may exist
- See also: `/memory-forget` (remove specific memories), `/memory-clear` (clear all memories)
