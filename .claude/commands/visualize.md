---
description: "Generate interactive knowledge graph visualization"
allowed-tools: Bash, TodoWrite
argument-hint: "[domain]"
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Visualize Command

Generate an interactive knowledge graph visualization showing all concepts and their relationships.


## Step 0: Initialize Workflow Checklist

**IMMEDIATELY after command invocation**, create complete TodoWrite with ALL workflow steps:

```python
TodoWrite([
  {"content": "Step 1: Generate Graph Data", "activeForm": "Step 1: Generate Graph Data", "status": "pending"},
  {"content": "Step 2: Generate Visualization HTML", "activeForm": "Step 2: Generate Visualization HTML", "status": "pending"},
  {"content": "Step 3: Display Summary", "activeForm": "Step 3: Display Summary", "status": "pending"}
])
```

**Rules**:
- Mark `in_progress` BEFORE starting each step
- Mark `completed` IMMEDIATELY after finishing
- NEVER skip steps - all todos must reach `completed` or `cancelled`
- User sees real-time progress via todo list

---


## Usage

```
/visualize
/visualize <domain>
```

## Examples

```
/visualize           # All concepts
/visualize finance   # Finance domain only
```

## What This Command Does

1. **Generates graph data** from knowledge-base
2. **Creates visualization HTML** with D3.js force-directed graph
3. **Outputs standalone file** (knowledge-graph.html)

## Implementation

### Step 1: Generate Graph Data

```bash
source venv/bin/activate && python scripts/knowledge-graph/generate-graph-data.py [--domain DOMAIN] --force
```

### Step 2: Generate Visualization HTML

```bash
source venv/bin/activate && python scripts/knowledge-graph/generate-visualization-html.py
```

### Step 3: Display Summary

Inform user they can open `knowledge-graph.html` in their browser.

## Notes

- Interactive D3.js force-directed graph
- Click nodes for details, hover for connections
- Search to filter by concept name or tags
- Domain-colored nodes, size scaled by review count
- Automatic cluster detection
- Standalone HTML (works offline)
- Valid domains: finance, programming, language, science, arts, mathematics, social
