#!/bin/bash
# Deploy analytics HTML to Cloudflare Workers KV (Key-Value Storage)
# This is the SIMPLEST solution - no repository needed!
#
# Prerequisites:
#   1. Cloudflare account
#   2. Wrangler CLI: npm install -g wrangler
#   3. Login: wrangler login
#
# Setup (first time only):
#   cd /root/knowledge-system/cloudflare-worker
#   wrangler kv:namespace create ANALYTICS
#   # Copy the namespace ID to wrangler.toml
#
# Usage:
#   bash scripts/deploy-to-cloudflare-kv.sh

set -e

SOURCE_DIR="/root/knowledge-system"
WORKER_DIR="$SOURCE_DIR/cloudflare-worker"
KV_NAMESPACE="ANALYTICS"

echo "=================================================="
echo "🚀 Deploying to Cloudflare Workers + KV"
echo "=================================================="

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Error: Wrangler CLI not installed"
    echo ""
    echo "Install with: npm install -g wrangler"
    echo "Then login: wrangler login"
    exit 1
fi

# Check if HTML files exist
if [ ! -f "$SOURCE_DIR/analytics-dashboard.html" ]; then
    echo "❌ Error: analytics-dashboard.html not found"
    echo "Run /save first to generate analytics"
    exit 1
fi

# Create worker directory if not exists
if [ ! -d "$WORKER_DIR" ]; then
    echo "📁 Creating worker directory..."
    mkdir -p "$WORKER_DIR"

    # Create wrangler.toml
    cat > "$WORKER_DIR/wrangler.toml" <<EOF
name = "analytics-viewer"
main = "worker.js"
compatibility_date = "2024-01-01"

[[kv_namespaces]]
binding = "ANALYTICS"
id = "YOUR_NAMESPACE_ID_HERE"  # Run: wrangler kv:namespace create ANALYTICS
EOF

    echo "⚠️  First time setup required!"
    echo ""
    echo "Run these commands:"
    echo "  cd $WORKER_DIR"
    echo "  wrangler kv:namespace create ANALYTICS"
    echo ""
    echo "Then update wrangler.toml with the namespace ID"
    exit 1
fi

# Read HTML files
echo "📋 Reading HTML files..."
DASHBOARD_CONTENT=$(cat "$SOURCE_DIR/analytics-dashboard.html")
GRAPH_CONTENT=$(cat "$SOURCE_DIR/knowledge-graph.html")

# Upload to KV
cd "$WORKER_DIR"

echo "📤 Uploading to Cloudflare KV..."

# Create temporary files
echo "$DASHBOARD_CONTENT" > /tmp/dashboard.html
echo "$GRAPH_CONTENT" > /tmp/graph.html

# Upload to KV
wrangler kv:key put --binding=ANALYTICS "index.html" --path=/tmp/dashboard.html
wrangler kv:key put --binding=ANALYTICS "knowledge-graph.html" --path=/tmp/graph.html

# Cleanup
rm /tmp/dashboard.html /tmp/graph.html

echo "✓ Uploaded to KV storage"

# Deploy worker
echo ""
echo "📤 Deploying worker..."
wrangler deploy

echo ""
echo "=================================================="
echo "✅ Deployment Complete!"
echo "=================================================="
echo ""
echo "Your analytics are now live at:"
echo "  Dashboard: https://analytics-viewer.YOUR_SUBDOMAIN.workers.dev/"
echo "  Graph:     https://analytics-viewer.YOUR_SUBDOMAIN.workers.dev/knowledge-graph.html"
echo ""
echo "=================================================="
