---
description: "Generate and deploy knowledge graph visualization and analytics dashboard to Netlify"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, TodoWrite
argument-hint: "[--period <days>] [--domain <domain>] [--deploy]"
model: inherit
---

# Graph Command

Generate knowledge graph visualization and analytics dashboard, optionally deploy to Netlify.

## Usage

```
/graph                          # Generate visualizations (default: 30 days, all domains)
/graph --deploy                 # Generate and deploy to Netlify
/graph --period 7               # Generate for last 7 days
/graph --domain finance         # Generate for finance domain only
/graph --period 90 --deploy     # Generate 90-day view and deploy
```

## What This Command Does

1. **Generate Analytics**: Create 30-day (or custom period) analytics from review data
2. **Build Knowledge Graph**: Generate interactive D3.js graph visualization
3. **Create HTML Files**: Produce standalone HTML files with embedded data
4. **Deploy to Netlify** (optional): Publish to https://knowledge-analytics.netlify.app/

## Implementation

### Step 1: Parse Arguments

Extract parameters from command arguments:
- `--period <N>`: Time period in days (default: 30)
- `--domain <name>`: Filter by specific domain (default: all)
- `--deploy`: Deploy to Netlify after generation

### Step 2: Generate Analytics Data

```bash
source venv/bin/activate && python scripts/analytics/generate-analytics.py \
  --period ${PERIOD:-30} \
  ${DOMAIN:+--domain "$DOMAIN"}
```

This creates `.review/analytics-isced.json` with:
- Retention curves by domain
- Learning velocity metrics
- Review adherence rates
- Time distribution
- Streak tracking

### Step 3: Generate Knowledge Graph Data

```bash
source venv/bin/activate && python scripts/knowledge-graph/generate-graph-data.py --force
```

This creates `knowledge-base/_index/graph-data.json` with:
- All Rems as nodes (with ISCED classification colors)
- Typed relations as edges
- Embedded content and conversations
- Graph metadata (node count, edge count, domain distribution)

### Step 4: Generate Visualization HTML Files

**Analytics Dashboard**:
```bash
source venv/bin/activate && python scripts/analytics/generate-dashboard-html.py \
  --input .review/analytics-isced.json \
  --output analytics-dashboard.html
```

**Knowledge Graph**:
```bash
source venv/bin/activate && python scripts/knowledge-graph/generate-visualization-html.py \
  --input knowledge-base/_index/graph-data.json \
  --output knowledge-graph.html
```

Both files are standalone HTML with:
- Embedded data (no external dependencies)
- Premium minimalist design (Swiss spa aesthetic)
- Font Awesome icons (no emojis)
- Responsive layout (mobile-optimized)
- Interactive charts/graph (Chart.js/D3.js)

### Step 5: Preview Results

Show generation summary:
```
✅ Visualizations Generated Successfully

📊 Analytics Dashboard: analytics-dashboard.html
   • Period: ${PERIOD} days
   • Domain: ${DOMAIN:-all}
   • Concepts tracked: ${CONCEPT_COUNT}
   • Review adherence: ${ADHERENCE}%
   • Current streak: ${STREAK} days

🗺️ Knowledge Graph: knowledge-graph.html
   • Nodes: ${NODE_COUNT}
   • Edges: ${EDGE_COUNT}
   • Domains: ${DOMAIN_COUNT}

📁 Local Files:
   • file:///root/knowledge-system/analytics-dashboard.html
   • file:///root/knowledge-system/knowledge-graph.html
```

### Step 6: Deploy to Netlify (if --deploy flag)

**Check prerequisites**:
1. Verify Netlify CLI installed: `command -v netlify`
2. Check auth token: `$NETLIFY_AUTH_TOKEN`
3. If missing, provide instructions

**Deploy**:
```bash
# Create deployment directory
rm -rf /tmp/analytics-deploy
mkdir -p /tmp/analytics-deploy

# Copy files
cp analytics-dashboard.html /tmp/analytics-deploy/index.html
cp knowledge-graph.html /tmp/analytics-deploy/graph.html

# Deploy to fixed site (knowledge-analytics.netlify.app)
cd /tmp/analytics-deploy
http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY="" \
  netlify deploy --prod --dir . --site "521fdc68-d271-408b-af64-b62c1342c4f2"

# Cleanup
rm -rf /tmp/analytics-deploy
```

**Show deployment result**:
```
🌐 Deployed to Netlify Successfully!

Live URLs:
• Dashboard: https://knowledge-analytics.netlify.app/
• Graph: https://knowledge-analytics.netlify.app/graph.html

Share these links to view your knowledge system analytics from anywhere!
```

## Error Handling

**Missing data**:
- If no analytics cache exists → Run with empty data, show warning
- If no graph data exists → Generate from scratch
- If no Rems exist → Show "No data" message in HTML

**Deployment errors**:
- Netlify CLI not installed → Provide installation command
- No auth token → Show token setup instructions
- Network error → Retry with instructions

**Generation errors**:
- Script failures → Show error, suggest manual run
- Invalid period → Default to 30 days
- Unknown domain → Show available domains

## Options for User

After generation, present options:
```xml
<options>
    <option>Deploy to Netlify</option>
    <option>Generate different period</option>
    <option>Filter by domain</option>
    <option>View local files</option>
</options>
```

## Success Criteria

- ✅ Analytics and graph data generated successfully
- ✅ HTML files created with embedded data
- ✅ Premium design (no emojis, minimalist aesthetic)
- ✅ Local files viewable in browser
- ✅ (Optional) Deployed to Netlify with live URLs
- ✅ Clear summary with metrics shown
- ✅ Error messages helpful with recovery steps