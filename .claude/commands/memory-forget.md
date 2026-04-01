---
description: "Remove specific memories by topic or name"
allowed-tools: Read, Edit, Grep, Glob, TodoWrite
disable-model-invocation: true
---

**CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Forget Command

Remove specific memories from auto-memory files by topic, keyword, or domain.

## Usage

```
/memory-forget <concept-name>
/memory-forget --query <search-query>
/memory-forget --type <entry-type>
/memory-forget --domain <domain>
```

## Examples

```
/memory-forget "Black-Scholes Model"  # Delete specific concept entries
/memory-forget --query "option"       # Delete all matching "option"
/memory-forget --type struggles       # Delete all struggle entries
/memory-forget --domain finance       # Delete all finance entries
```

## What This Command Does

1. **Searches for matches** - Finds entries by keyword, type, or domain in memory files
2. **Shows preview** - Lists all entries that will be removed
3. **Requires confirmation** - Always asks for confirmation before deletion
4. **Removes entries** - Uses Edit tool to remove matching sections from memory files
5. **Cleans up** - Removes empty sections after deletion

## Implementation

Find and remove entries from auto-memory files:

1. **Search for matches**:
```
Grep:
  pattern: "{concept_name}"
  path: /root/.claude/projects/-root/memory/
  output_mode: content
  context: 5
```

2. **Show preview** and ask for confirmation

3. **Remove matching entries** using Edit tool:
```
Edit:
  file_path: /root/.claude/projects/-root/memory/{file}.md
  old_string: "{matched section text}"
  new_string: ""
```

**Note**: This command uses Grep and Edit tools on auto-memory files. No MCP tools needed.

This command modifies memory files by removing matching entries.

## Notes

**WARNING**: This action modifies memory files. Consider creating a backup first.

**Backup before deletion**:
```bash
cp -r /root/.claude/projects/-root/memory/ /root/.claude/projects/-root/memory-backup-$(date +%Y%m%d)/
```

**Consider using `/memory-status` first to review what will be deleted.**

**See also**: `/memory-status` (view current memories), `/memory-clear` (clear all memories - nuclear option)
