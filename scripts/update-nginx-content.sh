#!/bin/bash
# Update Nginx-hosted analytics content after /save
#
# Usage:
#   sudo bash scripts/update-nginx-content.sh

SOURCE_DIR="/root/knowledge-system"
WEB_ROOT="/var/www/analytics"

echo "=================================================="
echo "🔄 Updating Nginx Analytics Content"
echo "=================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if web root exists
if [ ! -d "$WEB_ROOT" ]; then
    echo "❌ Error: Web root not found at $WEB_ROOT"
    echo "Run setup-nginx-hosting.sh first"
    exit 1
fi

# Check if HTML files exist
if [ ! -f "$SOURCE_DIR/analytics-dashboard.html" ]; then
    echo "❌ Error: analytics-dashboard.html not found"
    echo "Run /save first to generate analytics"
    exit 1
fi

echo "📋 Copying updated HTML files..."
cp "$SOURCE_DIR/analytics-dashboard.html" "$WEB_ROOT/index.html"
cp "$SOURCE_DIR/knowledge-graph.html" "$WEB_ROOT/graph.html"

# Set permissions
chown -R www-data:www-data "$WEB_ROOT"
chmod -R 755 "$WEB_ROOT"

echo "✓ Content updated"
echo ""
echo "=================================================="
echo "✅ Update Complete!"
echo "=================================================="
echo ""
echo "Your analytics are now refreshed and live!"
echo "=================================================="
