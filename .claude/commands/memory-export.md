---
description: "Export memories to external file formats (JSON, Markdown)"
allowed-tools: Read, Write, Glob, Bash, TodoWrite
disable-model-invocation: true
---

**CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Export Command

Export memories to external file formats for backup, analysis, or transfer.

## Usage

```
/memory-export <filename>
/memory-export <filename> --format json
/memory-export <filename> --category concepts
/memory-export <filename> --domain finance
```

## Examples

```
/memory-export memories-backup.json                         # Export all to JSON
/memory-export memories-backup.md                           # Export as combined Markdown
/memory-export finance-concepts.json --category concepts --domain finance  # Finance concepts only
/memory-export my-struggles.json --category struggles        # Export struggles
```

## What This Command Does

1. **Reads memory files** - Reads all .md files from auto-memory directory
2. **Filters data** - Filters by category and domain if specified
3. **Formats data** - Converts to JSON or combined Markdown format
4. **Writes to file** - Exports to specified filename

## Implementation

Export auto-memory files using built-in tools:

1. **List all memory files**:
```
Glob:
  pattern: "*.md"
  path: /root/.claude/projects/-root/memory/
```

2. **Read each memory file**:
```
Read: /root/.claude/projects/-root/memory/MEMORY.md
```
(Repeat for each .md file)

3. **Format data**:
   - JSON: Structure as `{"files": [{"name": "...", "content": "..."}], "exported_at": "..."}`
   - Markdown: Concatenate all files with headers

4. **Write to file**:
```
Write:
  file_path: "{output_path}"
  content: "{formatted_data}"
```

**Note**: This command uses Read, Glob, and Write tools on auto-memory files. No MCP tools needed.

## Notes

- Export preserves ALL data (no filtering by retention policy)
- Exported files can be version controlled with git
- Use JSON for structured backups
- Use Markdown for human-readable combined export
- See also: `/memory-show` (display memories in terminal), `/memory-status` (memory statistics and health)
