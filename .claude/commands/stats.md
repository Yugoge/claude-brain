---
description: "Learning analytics dashboard with interactive visualizations"
allowed-tools: Bash, Read, TodoWrite
argument-hint: "[domain] [period]"
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Stats Command

Display comprehensive learning analytics with interactive visualizations.



## Step 0: Initialize Workflow Checklist

**IMMEDIATELY after command invocation**, load and execute preloaded TodoList:

```bash
cat scripts/todo/stats.json
```

Then create TodoWrite with all steps from JSON (status: "pending").

**Rules**:
- Mark `in_progress` BEFORE starting each step
- Mark `completed` IMMEDIATELY after finishing
- NEVER skip steps - all must reach `completed` or `cancelled`

---


## Usage

```
/stats [domain] [period]
```

## Examples

```
/stats                      # Full analytics (30 days, all domains)
/stats finance              # Finance domain only
/stats weekly               # Last 7 days, all domains
/stats programming 90       # Last 90 days, programming domain
```

## Arguments

- `domain` (optional): Filter by domain (e.g., `finance`, `programming`, `language`)
- `period` (optional): Analysis period
  - `weekly` or `7` → Last 7 days
  - `monthly` or `30` → Last 30 days (default)
  - `quarterly` or `90` → Last 90 days
  - `all` → All time

## What This Command Does

1. **Parses arguments** to determine domain filter and time period
2. **Generates analytics** using `scripts/generate-analytics.py`
3. **Creates React dashboard** artifact with Chart.js visualizations
4. **Displays interactive charts** with tooltips and click events

### Step 1: Generate Analytics

```bash
source venv/bin/activate && python scripts/generate-analytics.py --domain <domain> --period <days>
```

### Step 2: Load Analytics Cache

Read `.review/analytics-cache.json` for visualization data.

### Step 3: Create React Dashboard

Create interactive React artifact with Chart.js visualizations:
- Retention Curves: Line chart showing memory decay over 30 days
- Learning Velocity: Bar chart of concepts mastered per week
- Mastery Heatmap: Grid showing all concepts color-coded by mastery level
- Review Adherence: Gauge chart showing on-time review percentage
- Time Distribution: Pie chart of hours invested per domain
- Streak Calendar: Activity heatmap (GitHub-style contributions)
- Mastery Timeline: Predicted dates when concepts reach 80% mastery

### Step 4: Display Summary Statistics

At the top of dashboard:
- Current streak
- Total concepts tracked
- Average velocity
- Review adherence

## Notes

- Interactive charts with tooltips and click events
- Optional export to PDF/CSV
- React artifact with Chart.js visualizations
- Standalone HTML file for offline viewing
