---
description: "Run knowledge base maintenance tasks"
allowed-tools: Bash, Read, TodoWrite
argument-hint: "[--check-only | --fix-all | --validate]"
---

# Knowledge Base Maintenance

Automated maintenance for Rem files and knowledge graph.

## Usage

```
/maintain [--check-only | --fix-all | --validate]
```

### Modes

- **Interactive** (default): Present menu to select individual tasks
- **--check-only**: Run all checks without making changes (dry-run)
- **--fix-all**: Run all tasks and apply fixes automatically
- **--validate**: Run only validation checks (tasks 1-3)

## Examples

Run in interactive mode to select specific tasks, or use mode flags for automated execution.

## Implementation

**IMPORTANT**: Load todos from `scripts/todo/maintain.py` at start:

```bash
source venv/bin/activate && python scripts/todo/maintain.py
```

Use output to create TodoWrite with all 9 tasks. Mark each task as in_progress before starting, completed after finishing.

### Task Execution Order (Logical Flow)

Tasks are ordered from validation → basic fixes → advanced maintenance.

**Note**: Wikilink normalization is automatically handled by `/save` command. This command focuses on manual maintenance tasks.

---

## Phase 1: Validation (Check Current State)

### Task 1: Validate Rem Formats (v2.0 Compliance)
**Purpose**: Check YAML frontmatter compliance with v2.0 format
**Checks**: rem_id, isced, created, source fields

```bash
source venv/bin/activate && python scripts/validation/check_rem_formats.py
```

- Read-only check, no modifications
- Reports non-compliant files
- Run first to identify format issues
- Optional verbosity flag available

### Task 2: Validate Rem Size (150-200 Token Target)
**Purpose**: Check token size compliance with Story 1.10 standards
**Target**: 150-200 tokens per Rem, hard limit 250 tokens

```bash
source venv/bin/activate && python scripts/validation/validate-rem-size.py
```

- Reports violations with file paths
- Helps identify Rems that need compression

### Task 3: Validate YAML Frontmatter
**Purpose**: Check YAML syntax and detect common issues
**Detects**: Unquoted colons, special characters, syntax errors

```bash
source venv/bin/activate && python scripts/validation/validate-yaml-frontmatter.py
```

- Default: check-only mode
- Optional fix flag available to automatically correct issues

### Task 4: Check Source Fields
**Purpose**: Check distribution of source field values
**Reports**: chats/ vs unarchived distribution

```bash
source venv/bin/activate && python scripts/utilities/check-source-fields.py
```

- Read-only statistics
- Helps identify Rems with missing or invalid source attribution

---

## Phase 2: Basic Fixes (Foundational Corrections)

### Task 5: Add Missing rem_ids
**Purpose**: Add rem_id field to Rems that are missing it
**Strategy**: Generates rem_id from filename

```bash
source venv/bin/activate && python scripts/add-missing-rem-ids.py
```

- Dry-run by default, execution flag available to apply changes
- Run early to ensure all Rems have IDs

---

## Phase 3: Advanced Maintenance (Graph & Naming)

### Task 6: Rebuild Backlinks (Full Rebuild)
**Purpose**: Full rebuild of backlinks index from scratch
**When to use**: After major changes, when backlinks.json is corrupted, or for periodic deep maintenance

```bash
source venv/bin/activate && python scripts/knowledge-graph/rebuild-backlinks.py
```

- Full scan of all Rems in knowledge-base
- Rebuilds backlinks.json with typed relations
- Use when incremental updates (from `/save`) are insufficient
- Optional verbosity flag available
- **Note**: `/save` automatically does incremental updates; this is for manual deep maintenance

### Task 7: Sync Related Rems from Backlinks
**Purpose**: Auto-populate "Related Rems" sections from backlinks index
**Requires**: Up-to-date backlinks.json (run rebuild-backlinks.py first if needed)

```bash
source venv/bin/activate && python scripts/knowledge-graph/sync-related-rems-from-backlinks.py
```

- Optional dry-run flag for preview
- Optional verbosity flag available
- Updates "Related Rems" sections based on actual link structure

### Task 8: Standardize Rem Names (Domain-Specific)
**Purpose**: Standardize naming conventions for a specific domain
**Scope**: Updates KB + chat archives + FSRS schedule

```bash
source venv/bin/activate && python scripts/knowledge-graph/standardize-rem-names.py --domain <domain>
```

- **Interactive**: Ask user which domain to process (auto-discover available ISCED paths by scanning knowledge-base)
- Optional dry-run flag for preview
- Optional verbosity flag available
- Run last because it renames files and updates references

### Task 9: Sync to FSRS Review Schedule
**Purpose**: Sync all Rems to review system (add new, update metadata)
**When to use**: After adding rem_ids (Task 5), importing external Rems, or updating Rem titles

```bash
source venv/bin/activate && python scripts/utilities/scan-and-populate-rems.py
```

- Add new Rems to `.review/schedule.json` with initial FSRS state
- Optional force flag to update metadata while preserving FSRS history
- Optional verbosity flag available
- **Note**: `/save` automatically syncs; this is for manual maintenance only
- Extracts titles from Markdown headings for better readability in review sessions

### Task 10: Fix Multi-Pair Relations
**Purpose**: Detect and remove redundant paired relations using semantic priority

```bash
source venv/bin/activate && python scripts/knowledge-graph/fix-source-multi-pair-relations.py
```

- Optional execution flag to apply fixes
- **Must run before rebuilding backlinks to prevent propagating conflicts**

### Task 11: Sync Renamed Rems to Schedule
**Purpose**: Detect and sync file path/rem_id changes to schedule.json automatically
**When to use**: After file renames, to prevent orphaned schedule entries

```bash
source venv/bin/activate && python scripts/review/sync-renamed-rems.py
```

- Auto-detects orphaned schedule entries (rem_id not in any Rem file)
- Uses domain + pattern matching to find renamed files
- Preserves ALL FSRS history (difficulty, stability, review_count)
- Only updates rem_id, domain, title, last_modified
- Optional dry-run flag for preview
- Optional verbosity flag available
- Safe to run repeatedly (idempotent)
- **Root cause**: Prevents issues where files are renamed but schedule.json isn't updated

---

## Workflow Logic

### Interactive Mode (Default)
Present menu with three phases:
- **Phase 1: Validation** - Format checks, size validation, YAML syntax, source fields
- **Phase 2: Basic Fixes** - Add missing rem_ids
- **Phase 3: Advanced Maintenance** - Graph operations, naming, FSRS sync

User can select individual tasks, all tasks, or validation-only subset.

### Mode Behaviors

Different execution modes available:
- Validation-only mode runs checks without modifications
- Check-only mode runs all tasks in dry-run mode
- Fix-all mode applies all fixes automatically
- Execution order follows dependency graph: validation first, then basic fixes, then advanced maintenance

### Summary Report

After completion, present structured summary showing:
- Validation results with issue counts
- Basic fixes applied with change counts
- Advanced maintenance operations with file update counts
- Recommendations for follow-up actions based on findings

## Notes

- **Execution Order Matters**: Validation first, basic fixes second, advanced maintenance last
- **Critical Order**: Fix multi-pair → rebuild backlinks → sync related rems
- **Rationale**: Source cleanup must complete before graph rebuild to prevent conflict propagation
- **Safety**: All tasks support dry-run mode for preview
- **Impact**: Task 8 (standardize names) has highest impact - review carefully before executing
- **Graph Maintenance**: Wikilink normalization is automatically handled by `/save` command

## Architecture Notes

**Why these tasks, not others?**

- ✅ **Included**: Manual maintenance tasks (validation, deep rebuild, batch sync)
- ❌ **Excluded**: Auto-maintenance tasks handled by `/save` (wikilink normalization, incremental backlinks update)
- 🎯 **Purpose**: `/maintain` is for periodic deep maintenance, not daily workflow
