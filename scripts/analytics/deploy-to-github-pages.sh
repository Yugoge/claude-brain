#!/bin/bash
# Deploy analytics HTML to GitHub Pages
# 
# This script copies HTML files from root to docs/ for GitHub Pages deployment
# Root HTML files remain uncommitted (for private viewing)
# docs/ HTML files are committed and pushed (for public GitHub Pages)

set -e

echo "📤 Deploying Analytics to GitHub Pages..."
echo

# Ensure docs/ exists
mkdir -p docs

# Copy HTML files
if [ -f "analytics-dashboard.html" ]; then
    cp analytics-dashboard.html docs/
    echo "✅ Copied analytics-dashboard.html → docs/"
else
    echo "⚠️  analytics-dashboard.html not found. Run /save first."
    exit 1
fi

if [ -f "knowledge-graph.html" ]; then
    cp knowledge-graph.html docs/
    echo "✅ Copied knowledge-graph.html → docs/"
else
    echo "⚠️  knowledge-graph.html not found. Run /save first."
    exit 1
fi

# Check if docs/index.html exists, create if not
if [ ! -f "docs/index.html" ]; then
    cat > docs/index.html << 'HTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="0; url=./analytics-dashboard.html">
    <title>Knowledge System Analytics</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container { text-align: center; }
        h1 { font-size: 3em; margin-bottom: 20px; }
        p { font-size: 1.2em; margin-bottom: 30px; }
        .links { display: flex; gap: 20px; justify-content: center; }
        a {
            background: white;
            color: #667eea;
            padding: 15px 30px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            transition: transform 0.2s;
        }
        a:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.2);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Knowledge System Analytics</h1>
        <p>Redirecting to Analytics Dashboard...</p>
        <div class="links">
            <a href="./analytics-dashboard.html">Analytics Dashboard</a>
            <a href="./knowledge-graph.html">Knowledge Graph</a>
        </div>
    </div>
</body>
</html>
HTML
    echo "✅ Created docs/index.html"
fi

echo
echo "📊 Ready to deploy:"
echo "   docs/index.html"
echo "   docs/analytics-dashboard.html"
echo "   docs/knowledge-graph.html"
echo
echo "🚀 Next steps:"
echo "   git add docs/*.html"
echo "   git commit -m 'Deploy analytics to GitHub Pages'"
echo "   git push"
echo
echo "📍 After pushing:"
echo "   1. Go to GitHub repo Settings → Pages"
echo "   2. Source: main branch, /docs folder"
echo "   3. Visit: https://<username>.github.io/<repo>/"
