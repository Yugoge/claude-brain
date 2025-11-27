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

```
/maintain                 # Interactive menu
/maintain --check-only    # Dry-run all tasks
/maintain --fix-all       # Auto-fix everything
/maintain --validate      # Validation only
```

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
source venv/bin/activate && python scripts/validation/check_rem_formats.py [--verbose]
```

- Read-only check, no modifications
- Reports non-compliant files
- Run first to identify format issues

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
source venv/bin/activate && python scripts/validation/validate-yaml-frontmatter.py [--fix]
```

- Use without `--fix` for check-only mode
- Use `--fix` to automatically correct YAML issues

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
source venv/bin/activate && python scripts/add-missing-rem-ids.py [--execute]
```

- Dry-run by default, use `--execute` to apply
- Run early to ensure all Rems have IDs

---

## Phase 3: Advanced Maintenance (Graph & Naming)

### Task 6: Rebuild Backlinks (Full Rebuild)
**Purpose**: Full rebuild of backlinks index from scratch
**When to use**: After major changes, when backlinks.json is corrupted, or for periodic deep maintenance

```bash
source venv/bin/activate && python scripts/knowledge-graph/rebuild-backlinks.py [--verbose]
```

- Full scan of all Rems in knowledge-base
- Rebuilds backlinks.json with typed relations
- Use when incremental updates (from `/save`) are insufficient
- **Note**: `/save` automatically does incremental updates; this is for manual deep maintenance

### Task 7: Sync Related Rems from Backlinks
**Purpose**: Auto-populate "Related Rems" sections from backlinks index
**Requires**: Up-to-date backlinks.json (run rebuild-backlinks.py first if needed)

```bash
source venv/bin/activate && python scripts/knowledge-graph/sync-related-rems-from-backlinks.py [--dry-run] [--verbose]
```

- Use `--dry-run` for preview
- Updates "Related Rems" sections based on actual link structure

### Task 8: Standardize Rem Names (Domain-Specific)
**Purpose**: Standardize naming conventions for a specific domain
**Scope**: Updates KB + chat archives + FSRS schedule

```bash
source venv/bin/activate && python scripts/knowledge-graph/standardize-rem-names.py --domain <domain> [--dry-run] [--verbose]
```

- **Interactive**: Ask user which domain to process (auto-discover available ISCED paths by scanning knowledge-base)
- Use `--dry-run` for preview
- Run last because it renames files and updates references

### Task 9: Sync to FSRS Review Schedule
**Purpose**: Sync all Rems to review system (add new, update metadata)
**When to use**: After adding rem_ids (Task 5), importing external Rems, or updating Rem titles

```bash
source venv/bin/activate && python scripts/utilities/scan-and-populate-rems.py [--force] [--verbose]
```

- Add new Rems to `.review/schedule.json` with initial FSRS state
- With `--force`: Update metadata (title, domain) while preserving FSRS history (difficulty, stability, review_count)
- **Note**: `/save` automatically syncs; this is for manual maintenance only
- Extracts titles from Markdown headings (`# Title`) for better readability in review sessions

---

## Workflow Logic

### Interactive Mode (Default)
Present menu:
```
Knowledge Base Maintenance Tasks:

PHASE 1: VALIDATION
1. Validate Rem Formats (v2.0)
2. Validate Rem Size (150-200 tokens)
3. Validate YAML Frontmatter
4. Check Source Fields

PHASE 2: BASIC FIXES
5. Add Missing rem_ids

PHASE 3: ADVANCED MAINTENANCE
6. Rebuild Backlinks (full rebuild)
7. Sync Related Rems from Backlinks
8. Standardize Rem Names (domain-specific)
9. Sync to FSRS Review Schedule

Select tasks to run (comma-separated, e.g., 1,2,5,9 or 'all' or 'validate'):
```

### Mode Behaviors

**--validate**: Run tasks 1-4 (validation only)
**--check-only**: Run all 9 tasks with dry-run flags
**--fix-all**:
1. Run tasks 1-4 (validation - no changes)
2. Run task 5 with `--execute` (basic fixes)
3. Run tasks 6-8 with execution flags (advanced maintenance)
4. Run task 9 with `--yes` (sync to FSRS)
5. Ask for domain when reaching task 8

### Summary Report

After completion, show:
```
Maintenance Summary:
────────────────────
✓ Validation: X issues found
✓ Basic Fixes: Y changes applied
✓ Advanced Maintenance: Z files updated

Recommendations:
• Run /kb-init --repair-all if major issues found
• Review validation reports for manual fixes
• Run Task 6 (rebuild backlinks) if major graph changes detected
```

## Notes

- **Execution Order Matters**: Validation first, basic fixes second, advanced maintenance last
- **Dependencies**: Task 7 requires Task 6 (backlinks must be up-to-date before syncing)
- **Safety**: All tasks support dry-run mode for preview
- **Impact**: Task 8 (standardize names) has highest impact - review carefully before executing
- **Graph Maintenance**: Wikilink normalization is automatically handled by `/save` command

## Architecture Notes

**Why these tasks, not others?**

- ✅ **Included**: Manual maintenance tasks (validation, deep rebuild, batch sync)
- ❌ **Excluded**: Auto-maintenance tasks handled by `/save` (wikilink normalization, incremental backlinks update)
- 🎯 **Purpose**: `/maintain` is for periodic deep maintenance, not daily workflow
