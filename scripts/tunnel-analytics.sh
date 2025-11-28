#!/bin/bash
# SSH tunnel helper for remote access to analytics HTML files
#
# This script provides instructions for accessing your analytics
# remotely via SSH tunnel.
#
# Prerequisites:
#   1. SSH access to your server
#   2. HTTP server running on remote server (port 8000)
#
# Usage:
#   bash scripts/tunnel-analytics.sh

echo "=================================================="
echo "🔒 SSH Tunnel Setup for Remote Analytics Access"
echo "=================================================="
echo ""
echo "Step 1: Start HTTP server on remote server"
echo "   ssh your-username@your-server-ip"
echo "   cd /root/knowledge-system"
echo "   bash scripts/serve-analytics.sh"
echo ""
echo "Step 2: Create SSH tunnel (run on LOCAL machine)"
echo "   ssh -L 8000:localhost:8000 your-username@your-server-ip"
echo ""
echo "Step 3: Open in browser (on LOCAL machine)"
echo "   http://localhost:8000/analytics-dashboard.html"
echo "   http://localhost:8000/knowledge-graph.html"
echo ""
echo "=================================================="
echo "💡 Alternative: Use SSH -N flag for tunnel only"
echo "=================================================="
echo ""
echo "Keep tunnel running in background:"
echo "   ssh -N -L 8000:localhost:8000 your-username@your-server-ip"
echo ""
echo "Then open browser at: http://localhost:8000/analytics-dashboard.html"
echo "=================================================="
