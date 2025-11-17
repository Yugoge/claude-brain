---
description: "Add newly created Rem files to FSRS review schedule"
allowed-tools: Bash, TodoWrite
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Sync Rems Command

Add newly created Rem files to FSRS review schedule.

## Usage

```
/sync-rems
```

## What This Command Does

1. **Scans knowledge-base/** for Rem files not yet in `.review/schedule.json`
2. **Parses YAML frontmatter** for rem_id
3. **Adds missing Rems** with initial FSRS state
4. **Saves atomically** to `.review/schedule.json`

## Implementation
```bash
source venv/bin/activate && python scripts/utilities/scan-and-populate-rems.py --verbose
```

Initial FSRS state for new Rems:
- difficulty: 5.0 (neutral)
- stability: 1.0 (new concept)
- retrievability: 1.0 (fresh memory)
- next_review: tomorrow

## Notes

- Usually NOT needed - `/save` command auto-syncs in Step 6.7
- Use when: Manual Rem creation (bypassed /save), schedule file corruption (rebuild needed), external Rem import
- Idempotent operation (safe to run multiple times)
- Already-scheduled Rems are skipped (no duplicates)
- First review typically scheduled for tomorrow
- Algorithm: FSRS (Free Spaced Repetition Scheduler)
