#!/bin/bash
# Deploy analytics HTML to Netlify via Netlify CLI
#
# Prerequisites:
#   1. Install Netlify CLI: npm install -g netlify-cli
#   2. Get Personal Access Token from: https://app.netlify.com/user/applications#personal-access-tokens
#   3. Set token: export NETLIFY_AUTH_TOKEN="your_token_here"
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
    exit 1
fi

# Check if authenticated
if [ -z "$NETLIFY_AUTH_TOKEN" ]; then
    echo "⚠️  Warning: NETLIFY_AUTH_TOKEN not set"
    echo ""
    echo "To authenticate without browser:"
    echo "1. Visit: https://app.netlify.com/user/applications#personal-access-tokens"
    echo "2. Create a new token"
    echo "3. Run: export NETLIFY_AUTH_TOKEN='your_token_here'"
    echo "4. Run this script again"
    echo ""
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

# Fixed site ID for knowledge-analytics.netlify.app
# This prevents creating new sites on every deployment
SITE_ID="521fdc68-d271-408b-af64-b62c1342c4f2"

echo "Deploying to knowledge-analytics.netlify.app (site: $SITE_ID)..."
# Temporarily disable proxy for Netlify API calls
http_proxy="" https_proxy="" HTTP_PROXY="" HTTPS_PROXY="" \
    netlify deploy --prod --dir . --site "$SITE_ID"

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "Your analytics are now live at:"
echo "  Dashboard: https://knowledge-analytics.netlify.app/"
echo "  Graph:     https://knowledge-analytics.netlify.app/graph.html"
echo ""
echo "=================================================="

# Cleanup
rm -rf "$DEPLOY_DIR"
