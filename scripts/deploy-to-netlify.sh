#!/bin/bash
# Deploy analytics HTML to Netlify via Netlify CLI
#
# Prerequisites:
#   1. Install Netlify CLI: npm install -g netlify-cli
#   2. Login: netlify login
#   3. Create site: netlify init (first time only)
#
# Usage:
#   bash scripts/deploy-to-netlify.sh

set -e

SOURCE_DIR="/root/knowledge-system"
DEPLOY_DIR="/tmp/analytics-deploy"

echo "=================================================="
echo "🚀 Deploying Analytics to Netlify"
echo "=================================================="

# Check if Netlify CLI is installed
if ! command -v netlify &> /dev/null; then
    echo "❌ Error: Netlify CLI not installed"
    echo ""
    echo "Install with: npm install -g netlify-cli"
    echo "Then login: netlify login"
    exit 1
fi

# Check if HTML files exist
if [ ! -f "$SOURCE_DIR/analytics-dashboard.html" ]; then
    echo "❌ Error: analytics-dashboard.html not found"
    echo "Run /save first to generate analytics"
    exit 1
fi

echo "📋 Preparing deployment directory..."
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

echo "📋 Copying HTML files..."
cp "$SOURCE_DIR/analytics-dashboard.html" "$DEPLOY_DIR/index.html"
cp "$SOURCE_DIR/knowledge-graph.html" "$DEPLOY_DIR/graph.html"

echo "✓ Files prepared:"
echo "  • analytics-dashboard.html → index.html"
echo "  • knowledge-graph.html → graph.html"

echo ""
echo "📤 Deploying to Netlify..."
cd "$DEPLOY_DIR"

# Deploy (will prompt for site selection on first run)
netlify deploy --prod --dir .

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "Your analytics are now live at:"
echo "  Dashboard: https://your-site.netlify.app/"
echo "  Graph:     https://your-site.netlify.app/graph.html"
echo ""
echo "To get your URL, run: netlify status"
echo "=================================================="

# Cleanup
rm -rf "$DEPLOY_DIR"
