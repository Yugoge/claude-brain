# Hierarchical Contradiction Fix Scripts (Archive)

**Date**: 2025-12-05  
**Status**: Completed - One-time fix  
**Purpose**: Fixed 84 hierarchical contradictions in knowledge graph

## What This Was

A one-time maintenance operation to fix bidirectional relation contradictions in `knowledge-base/_index/backlinks.json`.

### Problem
- 84 hierarchical relations (example_of, prerequisite_of, extends) were incorrectly bidirectional
- Should be unidirectional: specific→general, not both ways

### Solution
Created two scripts to detect and fix:
1. `fix-hierarchical-contradictions.py` (29KB) - Full-featured with analysis
2. `fix-hierarchical-relation-contradictions.py` (17KB) - Streamlined aggressive fix

### Result
- ✅ Fixed all 84 contradictions
- ✅ Preserved 38 valid symmetric relations (related_to, contrasts_with)
- ✅ Generated backup: `backlinks.json.backup-20251205-171203`

## Why Archived

These scripts completed their purpose on 2025-12-05. They are not part of ongoing maintenance workflows and have no references in active commands.

Kept for historical reference and potential future similar issues.

See `fix-report.md` for detailed execution report.
