#!/bin/bash
# Setup Nginx to host analytics HTML files with public access
#
# Prerequisites:
#   1. Nginx installed: apt install nginx
#   2. Domain/subdomain pointing to your server (optional)
#   3. Certbot for HTTPS (optional): apt install certbot python3-certbot-nginx
#
# Usage:
#   sudo bash scripts/setup-nginx-hosting.sh [domain]
#
# Examples:
#   sudo bash scripts/setup-nginx-hosting.sh analytics.yourdomain.com
#   sudo bash scripts/setup-nginx-hosting.sh  # Use IP address only

DOMAIN="${1:-}"
SOURCE_DIR="/root/knowledge-system"
WEB_ROOT="/var/www/analytics"

echo "=================================================="
echo "🌐 Setting up Nginx for Analytics Hosting"
echo "=================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: This script must be run as root (use sudo)"
    exit 1
fi

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "❌ Error: Nginx not installed"
    echo "Install with: apt install nginx"
    exit 1
fi

# Create web root directory
echo "📁 Creating web root: $WEB_ROOT"
mkdir -p "$WEB_ROOT"

# Copy HTML files
echo "📋 Copying HTML files..."
if [ ! -f "$SOURCE_DIR/analytics-dashboard.html" ]; then
    echo "⚠️  Warning: analytics-dashboard.html not found, creating placeholder"
    echo "<h1>Analytics Dashboard</h1><p>Run /save to generate content</p>" > "$WEB_ROOT/index.html"
else
    cp "$SOURCE_DIR/analytics-dashboard.html" "$WEB_ROOT/index.html"
fi

if [ ! -f "$SOURCE_DIR/knowledge-graph.html" ]; then
    echo "⚠️  Warning: knowledge-graph.html not found, creating placeholder"
    echo "<h1>Knowledge Graph</h1><p>Run /save to generate content</p>" > "$WEB_ROOT/graph.html"
else
    cp "$SOURCE_DIR/knowledge-graph.html" "$WEB_ROOT/graph.html"
fi

# Set permissions
chown -R www-data:www-data "$WEB_ROOT"
chmod -R 755 "$WEB_ROOT"

# Create Nginx configuration
if [ -n "$DOMAIN" ]; then
    NGINX_CONF="/etc/nginx/sites-available/analytics"
    SERVER_NAME="$DOMAIN"
    echo "🔧 Creating Nginx config for domain: $DOMAIN"
else
    NGINX_CONF="/etc/nginx/sites-available/analytics"
    SERVER_NAME="_"
    echo "🔧 Creating Nginx config for IP access only"
fi

cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    root $WEB_ROOT;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    # Cache static files
    location ~* \.(html|css|js|json)$ {
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

# Enable site
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/analytics

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✓ Nginx configuration valid"
    echo "🔄 Reloading Nginx..."
    systemctl reload nginx

    echo ""
    echo "=================================================="
    echo "✅ Setup Complete!"
    echo "=================================================="
    echo ""

    if [ -n "$DOMAIN" ]; then
        echo "Your analytics are now available at:"
        echo "  Dashboard: http://$DOMAIN/"
        echo "  Graph:     http://$DOMAIN/graph.html"
        echo ""
        echo "🔒 To enable HTTPS (recommended):"
        echo "  sudo certbot --nginx -d $DOMAIN"
        echo ""
        echo "After HTTPS setup, access via:"
        echo "  Dashboard: https://$DOMAIN/"
        echo "  Graph:     https://$DOMAIN/graph.html"
    else
        SERVER_IP=$(hostname -I | awk '{print $1}')
        echo "Your analytics are now available at:"
        echo "  Dashboard: http://$SERVER_IP/"
        echo "  Graph:     http://$SERVER_IP/graph.html"
        echo ""
        echo "💡 For domain access, run:"
        echo "  sudo bash scripts/setup-nginx-hosting.sh your-domain.com"
    fi

    echo ""
    echo "=================================================="
    echo "📝 To update content after /save:"
    echo "  sudo bash scripts/update-nginx-content.sh"
    echo "=================================================="
else
    echo "❌ Nginx configuration test failed"
    exit 1
fi
