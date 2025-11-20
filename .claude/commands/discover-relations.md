---
description: "Discover and add typed relations to existing Rems"
allowed-tools: Read, Edit, Bash, Task, TodoWrite
argument-hint: "<rem-id | --domain domain-path>"
model: inherit
---

# Discover Relations Command

Retrospectively discover typed relations for existing Rems using domain tutor.





## Step 0: Initialize Workflow Checklist

**Load todos from**: `scripts/todo/discover-relations.py`

Execute via venv:
```bash
source venv/bin/activate && python scripts/todo/discover-relations.py
```

Use output to create TodoWrite with all workflow steps.

**Rules**: Mark `in_progress` before each step, `completed` after. NEVER skip steps.

---


## Usage

```
/discover-relations <rem-id>
/discover-relations --domain <domain-path>
```

## Examples

```
/discover-relations csharp-null-conditional-operator
/discover-relations --domain 0611-computer-use
```

## What This Command Does

1. Load existing Rem file(s)
2. Load all concepts in same domain
3. Call domain tutor to suggest typed relations
4. Present preview to user
5. Update Rem files with new relations (if approved)
6. Rebuild backlinks index

## Implementation

### Step 1: Parse Arguments

Extract rem_id or domain path from `$ARGUMENTS`:

- **Single Rem**: `csharp-null-conditional-operator` → Process one Rem
- **Domain**: `--domain 0611-computer-use` → Process all Rems in domain

### Step 2: Load Target Rems

**Script**: `scripts/archival/list_rems_in_domain.py`

**Usage**:
```bash
source venv/bin/activate && python scripts/archival/list_rems_in_domain.py \
  --domain-path "$domain_path" \
  --output target_rems.json
```

**Required Parameters**:
- `--domain-path`: Domain path relative to knowledge-base (e.g., "0231-language-acquisition")
- `--output`: Output JSON file path

**Output Format**: JSON array with `[{"rem_id": "rem-id", "title": "Title", "file_path": "path.md"}, ...]`

### Step 3: Load Existing Concepts

```bash
source venv/bin/activate && python scripts/archival/get_domain_concepts.py \
  --domain-path "$domain_path" \
  --format json > existing_concepts.json
```

### Step 4: Call Domain Tutor

Use `workflow_orchestrator.py`:

```bash
source venv/bin/activate && python scripts/archival/workflow_orchestrator.py \
  --domain "$domain" \
  --isced-path "$domain_path" \
  --candidate-rems target_rems.json
```

Follow orchestrator instructions to call Task tool and merge results.

### Step 5: Present Preview

For each Rem with new relations found:

```
🔍 Discovered relations for: [[rem-id]]

New typed relations:
1. [[existing-concept-1]] {rel: synonym}
   Rationale: Both operators simplify null handling in C#

2. [[existing-concept-2]] {rel: prerequisite_of}
   Rationale: Must understand X before learning Y

Add these {N} relations to [[rem-id]]?
```

Options:
```xml
<options>
    <option>Approve All</option>
    <option>Approve for this Rem only</option>
    <option>Skip this Rem</option>
    <option>Cancel</option>
</options>
```

### Step 6: Update Rem Files

**Script**: `scripts/archival/add_typed_relations.py`

**Usage**:
```bash
source venv/bin/activate && python scripts/archival/add_typed_relations.py \
  --enriched-rems enriched_rems.json
```

**Optional Parameters**:
- `--dry-run`: Preview changes without writing files

**Required Parameters**:
- `--enriched-rems`: Path to enriched_rems.json (output from workflow_orchestrator.py)

**Behavior**:
- Reads existing Rem file content
- Finds `## Related Rems` section
- Appends new wikilinks with typed relations (format: `- [[id]] {rel: type}`)
- Skips relations that already exist (checks by concept ID)
- Preserves all existing content (FSRS state, frontmatter, etc.)

**Output**: Reports added/skipped relations for each Rem

### Step 7: Rebuild Backlinks

```bash
source venv/bin/activate && python scripts/knowledge-graph/rebuild-backlinks.py
```

### Step 8: Normalize Links

```bash
source venv/bin/activate && python scripts/knowledge-graph/normalize-links.py --mode replace
```

## Success Report

```
✅ Relations Discovery Complete

📝 Updated Rems ({N}):
   - [[rem-id-1]]: Added {M} relations
   - [[rem-id-2]]: Added {K} relations

🔗 Graph Updated:
   ✅ Backlinks rebuilt
   ✅ Links normalized

💡 Tip: Run /visualize to see updated knowledge graph
```

## Notes

- Preserves existing FSRS learning progress
- Non-destructive (appends relations, doesn't replace)
- Can be run multiple times (idempotent)
- Useful for fixing historical Rems missing relations
