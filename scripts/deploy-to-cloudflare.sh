#!/bin/bash
# Deploy analytics HTML to Cloudflare Pages via separate public repository
#
# Prerequisites:
#   1. Create a PUBLIC repository (e.g., username/analytics-web)
#   2. Clone it: git clone https://github.com/username/analytics-web.git ~/analytics-web
#   3. Connect to Cloudflare Pages: https://pages.cloudflare.com/
#
# Usage:
#   bash scripts/deploy-to-cloudflare.sh

set -e

# Configuration
ANALYTICS_DIR="$HOME/analytics-web"
SOURCE_DIR="/root/knowledge-system"

echo "=================================================="
echo "🚀 Deploying Analytics to Cloudflare Pages"
echo "=================================================="

# Check if public repo exists
if [ ! -d "$ANALYTICS_DIR" ]; then
    echo "❌ Error: Public repository not found at $ANALYTICS_DIR"
    echo ""
    echo "Setup instructions:"
    echo "1. Create a PUBLIC repository on GitHub (e.g., analytics-web)"
    echo "2. Clone it: git clone https://github.com/username/analytics-web.git ~/analytics-web"
    echo "3. Connect to Cloudflare Pages: https://pages.cloudflare.com/"
    exit 1
fi

# Check if HTML files exist
if [ ! -f "$SOURCE_DIR/analytics-dashboard.html" ]; then
    echo "❌ Error: analytics-dashboard.html not found"
    echo "Run /save first to generate analytics"
    exit 1
fi

echo "📋 Copying HTML files..."
cp "$SOURCE_DIR/analytics-dashboard.html" "$ANALYTICS_DIR/index.html"
cp "$SOURCE_DIR/knowledge-graph.html" "$ANALYTICS_DIR/graph.html"

echo "✓ Files copied:"
echo "  • analytics-dashboard.html → index.html"
echo "  • knowledge-graph.html → graph.html"

# Navigate to public repo
cd "$ANALYTICS_DIR"

echo ""
echo "📝 Creating commit..."
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
git add index.html graph.html
git commit -m "Update analytics - $TIMESTAMP" || echo "No changes to commit"

echo ""
echo "📤 Pushing to GitHub..."
git push origin main

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "Your analytics are now available at:"
echo "  Dashboard: https://your-project.pages.dev/"
echo "  Graph:     https://your-project.pages.dev/graph.html"
echo ""
echo "First time setup:"
echo "1. Go to https://pages.cloudflare.com/"
echo "2. Connect your GitHub repository (analytics-web)"
echo "3. Deploy! (automatic)"
echo "=================================================="
