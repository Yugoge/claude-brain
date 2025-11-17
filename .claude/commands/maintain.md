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

**IMPORTANT**: Use TodoWrite to track progress through all 8 tasks.

Mark each task as in_progress before starting, completed after finishing.

### Task Execution Order (Logical Flow)

Tasks are ordered from validation → basic fixes → advanced maintenance.

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

### Task 6: Convert Wikilinks
**Purpose**: Convert [[wikilinks]] to markdown [Title](path.md) format
**Benefits**: Better compatibility, clearer references

```bash
source venv/bin/activate && python scripts/convert-wikilinks.py [--execute]
```

- Dry-run by default, use `--execute` to apply
- Automatically resolves file paths and extracts titles
- Run after adding rem_ids for better link resolution

---

## Phase 3: Advanced Maintenance (Graph & Naming)

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

- **Interactive**: Ask user which domain to process
  - `language/french` - French language Rems
  - `finance` - Finance Rems
  - `programming` - Programming Rems
- Use `--dry-run` for preview
- Run last because it renames files and updates references

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
6. Convert Wikilinks

PHASE 3: ADVANCED MAINTENANCE
7. Sync Related Rems from Backlinks
8. Standardize Rem Names (domain-specific)

Select tasks to run (comma-separated, e.g., 1,2,5 or 'all' or 'validate'):
```

### Mode Behaviors

**--validate**: Run tasks 1-4 (validation only)
**--check-only**: Run all 8 tasks with dry-run flags
**--fix-all**:
1. Run tasks 1-4 (validation - no changes)
2. Run tasks 5-6 with `--execute` (basic fixes)
3. Run tasks 7-8 with execution flags (advanced maintenance)
4. Ask for domain when reaching task 8

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
• Consider running rebuild-backlinks.py if graph changed
```

## Notes

- **Execution Order Matters**: Validation first, basic fixes second, advanced maintenance last
- **Dependencies**: Some tasks depend on others (e.g., wikilink conversion works better after rem_ids are added)
- **Safety**: All tasks support dry-run mode for preview
- **Impact**: Task 8 (standardize names) has highest impact - review carefully before executing
