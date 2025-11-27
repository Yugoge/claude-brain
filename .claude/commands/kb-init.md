---
description: "Initialize or reinitialize the knowledge system"
allowed-tools: Bash, Read, TodoWrite
argument-hint: "[--dry-run | --non-interactive | --verbose | --repair-all]"
---

**⚠️ CRITICAL**: Load todos from `scripts/todo/kb-init.py` at start:

```bash
source venv/bin/activate && python scripts/todo/kb-init.py
```

Use output to create TodoWrite with all 10 checks. Mark each check as in_progress before starting, completed immediately after.

# Knowledge Base Init Command

Initialize or reinitialize the knowledge system for first-time use or after major changes.

## Usage

```
/kb-init [options]
```

## Examples

```
/kb-init                              # Interactive mode (default)
/kb-init --dry-run                    # Preview without making changes
/kb-init --non-interactive --repair-all  # Auto-repair all issues
/kb-init --verbose                    # Detailed output
```

## Options

- `--dry-run` - Preview checks without making changes
- `--non-interactive` - Auto-apply safe repairs without prompting
- `--verbose` - Increase logging detail
- `--repair-all` - Automatically repair all detected issues

## What This Command Does

1. **Validates directory structure** - Checks all required directories exist
2. **Validates JSON files** - Verifies backlinks.json, taxonomy.json, index.json, schedule.json
3. **Repairs corrupted files** - Automatically fixes or regenerates corrupted JSON
4. **Verifies agent files** - Checks all agent instruction files exist and are valid
5. **Git health check** - Validates Git repository, remote, .gitignore
6. **Python dependencies** - Checks all required packages are installed
7. **Script permissions** - Verifies and fixes executable permissions
8. **Comprehensive report** - Generates detailed initialization report
9. **Interactive repairs** - Prompts for fixes or auto-repairs with flags
10. **Idempotent execution** - Safe to run multiple times

## Implementation

Execute the hardened initialization script:

```bash
source venv/bin/activate && python scripts/utilities/kb-init.py "$@"
```

Script Return Codes

The `kb-init.py` script returns the following exit codes:

- `0` - Success, all checks passed
- `1` - Warning, some checks failed but system is functional
- `2` - Error, critical issues detected, manual intervention required

## Notes

- This command is idempotent - safe to run multiple times
- Full reset option requires confirmation before deletion
- Health checks provide actionable error messages
- Getting started guide is context-aware (shows relevant next steps)
