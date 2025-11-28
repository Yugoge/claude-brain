#!/bin/bash
# Deploy analytics HTML to Cloudflare R2 (Object Storage) + Workers
# This keeps EVERYTHING private and uses pre-signed URLs or Workers for access
#
# Prerequisites:
#   1. Cloudflare account
#   2. R2 enabled (free tier: 10GB storage)
#   3. Wrangler CLI installed: npm install -g wrangler
#   4. Wrangler login: wrangler login
#
# Setup (first time):
#   wrangler r2 bucket create analytics
#
# Usage:
#   bash scripts/deploy-to-cloudflare-r2.sh

set -e

SOURCE_DIR="/root/knowledge-system"
BUCKET_NAME="analytics"

echo "=================================================="
echo "🚀 Deploying to Cloudflare R2"
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

echo "📋 Uploading files to R2..."

# Upload dashboard as index.html
wrangler r2 object put "$BUCKET_NAME/index.html" \
    --file="$SOURCE_DIR/analytics-dashboard.html" \
    --content-type="text/html"

echo "✓ Uploaded: index.html"

# Upload knowledge graph
wrangler r2 object put "$BUCKET_NAME/knowledge-graph.html" \
    --file="$SOURCE_DIR/knowledge-graph.html" \
    --content-type="text/html"

echo "✓ Uploaded: knowledge-graph.html"

echo ""
echo "=================================================="
echo "✅ Upload Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Create a Cloudflare Worker to serve these files"
echo "2. Or enable R2 public access (if you want public URLs)"
echo ""
echo "Public access setup:"
echo "  - Go to Cloudflare Dashboard → R2"
echo "  - Select 'analytics' bucket"
echo "  - Settings → Public Access → Enable"
echo "  - Get public URL: https://pub-xxxxx.r2.dev/"
echo ""
echo "Private access with Worker:"
echo "  - Use scripts/cloudflare-worker-template.js"
echo "  - Deploy with: wrangler deploy"
echo "=================================================="
