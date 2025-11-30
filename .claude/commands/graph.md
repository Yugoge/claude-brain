---
description: "Generate and deploy knowledge graph visualization and analytics dashboard to GitHub Pages"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, TodoWrite
argument-hint: "[--period <days>] [--domain <domain>] [--deploy] [--netlify]"
model: inherit
---

# Graph Command

Generate knowledge graph visualization and analytics dashboard, optionally deploy to GitHub Pages (default) or Netlify (legacy).

## Usage

```
/graph                          # Generate visualizations (default: 30 days, all domains)
/graph --deploy                 # Generate and deploy to GitHub Pages
/graph --period 7               # Generate for last 7 days
/graph --domain finance         # Generate for finance domain only
/graph --period 90 --deploy     # Generate 90-day view and deploy to GitHub Pages
/graph --deploy --netlify       # Deploy to Netlify (legacy option)
```

## What This Command Does

1. **Generate Analytics**: Create 30-day (or custom period) analytics from review data
2. **Build Knowledge Graph**: Generate interactive D3.js graph visualization
3. **Create HTML Files**: Produce standalone HTML files with embedded data
4. **Deploy to GitHub Pages** (default): Publish to https://{username}.github.io/{current-repo}-graph/
5. **Deploy to Netlify** (legacy): Publish to https://knowledge-analytics.netlify.app/

## Implementation

### Step 1: Parse Arguments

Extract parameters from command arguments:
- `--period <N>`: Time period in days (default: 30)
- `--domain <name>`: Filter by specific domain (default: all)
- `--deploy`: Deploy after generation (default: GitHub Pages)
- `--netlify`: Use Netlify instead of GitHub Pages (legacy option)

### Step 2: Generate Analytics Data

```bash
source venv/bin/activate && python scripts/analytics/generate-analytics-isced.py \
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

### Step 6: Deploy (if --deploy flag)

**Default: GitHub Pages**

Run deployment script:
```bash
bash scripts/deploy-to-github.sh
```

The script automatically:
1. Detects GitHub username from git config
2. Determines repository name: `{current-repo}-graph`
3. Checks if repository exists
4. Creates repository if needed (using GITHUB_TOKEN)
5. Pushes HTML files to gh-pages branch
6. Enables GitHub Pages automatically
7. Returns live URLs

**Authentication options**:
- **Option 1 (Recommended)**: Personal Access Token
  ```bash
  export GITHUB_TOKEN='your_token_here'
  ```
  Get token from: https://github.com/settings/tokens/new
  Required scopes: `repo`, `workflow`

- **Option 2**: SSH Keys
  - Must be configured: `~/.ssh/id_rsa` or `~/.ssh/id_ed25519`
  - Add to GitHub: https://github.com/settings/keys

**Show deployment result**:
```
🌐 Deployed to GitHub Pages Successfully!

Live URLs:
• Dashboard: https://{username}.github.io/{current-repo}-graph/
• Graph: https://{username}.github.io/{current-repo}-graph/graph.html

⏱️ Note: GitHub Pages may take 1-2 minutes to build
📁 Repository: https://github.com/{username}/{current-repo}-graph

Share these links to view your knowledge system analytics from anywhere!
```

**Legacy: Netlify (if --netlify flag)**

Only use if `--netlify` flag is specified:
```bash
bash scripts/deploy-to-netlify.sh
```

Requires:
- Netlify CLI: `npm install -g netlify-cli`
- Auth token: `export NETLIFY_AUTH_TOKEN='your_token_here'`

**Note**: Netlify has rate limits and may require payment. GitHub Pages is recommended.

## Error Handling

**Missing data**:
- If no analytics cache exists → Run with empty data, show warning
- If no graph data exists → Generate from scratch
- If no Rems exist → Show "No data" message in HTML

**Deployment errors**:
- Git not configured → Provide git config commands
- No GitHub token/SSH keys → Show authentication setup instructions
- Repository creation fails → Check token permissions or create manually
- Push fails → Check network/authentication
- GitHub Pages not enabled → Provide manual setup instructions
- (Legacy) Netlify CLI not installed → Provide installation command
- (Legacy) Netlify rate limit → Suggest GitHub Pages instead

**Generation errors**:
- Script failures → Show error, suggest manual run
- Invalid period → Default to 30 days
- Unknown domain → Show available domains

## Options for User

After generation, present options:
```xml
<options>
    <option>Deploy to GitHub Pages</option>
    <option>Deploy to Netlify (legacy)</option>
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
- ✅ (Optional) Deployed to GitHub Pages with live URLs
- ✅ Repository auto-created if needed
- ✅ Clear summary with metrics shown
- ✅ Error messages helpful with recovery steps