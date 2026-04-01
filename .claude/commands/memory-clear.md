---
description: "Clear all memories (nuclear option with confirmation)"
allowed-tools: Read, Write, Bash, Glob, TodoWrite
disable-model-invocation: true
---

**CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Clear Command

WARNING: This command clears ALL memories from the auto-memory files. This is a nuclear option that should only be used when you want to completely reset the memory system.

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
4. **Clears all memory files** - Resets all .md files in memory directory to empty state
5. **Verifies backup** - Option to cancel if backup fails

## Implementation

Clear auto-memory files using built-in tools:

1. **List current files** (for preview):
```
Glob:
  pattern: "*.md"
  path: /root/.claude/projects/-root/memory/
```

2. **Read each file** to show what will be deleted:
```
Read: /root/.claude/projects/-root/memory/MEMORY.md
```

3. **Show warning** and require confirmation

4. **Create backup** before clearing:
```bash
cp -r /root/.claude/projects/-root/memory/ /root/.claude/projects/-root/memory-backup-$(date +%Y%m%d-%H%M%S)/
```

5. **Clear each memory file** by writing empty/minimal content:
```
Write:
  file_path: /root/.claude/projects/-root/memory/MEMORY.md
  content: "# Memory\n\n(Cleared on YYYY-MM-DD)\n"
```

**Note**: This command uses Read, Write, and Bash tools on auto-memory files. No MCP tools needed.

## Notes

**Backup Location**: `/root/.claude/projects/-root/memory-backup-YYYYMMDD-HHMMSS/`

**Recovery**: If you accidentally clear memories, restore from backup:
```
ls -la /root/.claude/projects/-root/memory-backup-*/
cp /root/.claude/projects/-root/memory-backup-YYYYMMDD-HHMMSS/*.md /root/.claude/projects/-root/memory/
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
