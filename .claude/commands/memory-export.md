---
description: "Export memories to external file formats (JSON, CSV)"
allowed-tools: Read, Write, mcp__memory-server__read_graph, TodoWrite
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Memory Export Command

Export memories to external file formats for backup, analysis, or transfer.

## Usage

```
/memory-export <filename>
/memory-export <filename> --format csv
/memory-export <filename> --category concepts
/memory-export <filename> --domain finance
```

## Examples

```
/memory-export memories-backup.json                         # Export all to JSON
/memory-export memories.csv --format csv                    # Export as CSV
/memory-export finance-concepts.json --category concepts --domain finance  # Finance concepts only
/memory-export my-struggles.csv --category struggles --format csv  # Export struggles
```

## What This Command Does

1. **Queries memory graph** - Filters by category and domain if specified
2. **Formats data** - Converts to JSON or CSV format
3. **Writes to file** - Exports to specified filename
4. **Preserves all data** - No filtering by retention policy

## Implementation

Use `scripts/memory/memory-export.py` for implementation.

## Notes

- Export preserves ALL data (no filtering by retention policy)
- Exported files can be version controlled with git
- Use JSON for complete backups
- Use CSV for data analysis in spreadsheet tools
- Large exports (1000+ entities) may take a few seconds
- See also: `/memory-show` (display memories in terminal), `/memory-status` (memory statistics and health)
