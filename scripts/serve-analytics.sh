#!/bin/bash
# Simple HTTP server for viewing HTML analytics locally
# Usage: bash scripts/serve-analytics.sh [port]
#
# Default port: 8000
# Access at: http://localhost:8000/analytics-dashboard.html
#            http://localhost:8000/knowledge-graph.html

PORT="${1:-8000}"
cd /root/knowledge-system

echo "=================================================="
echo "🌐 Starting HTTP Server for Analytics"
echo "=================================================="
echo ""
echo "📊 Analytics Dashboard:"
echo "   http://localhost:${PORT}/analytics-dashboard.html"
echo ""
echo "🔗 Knowledge Graph:"
echo "   http://localhost:${PORT}/knowledge-graph.html"
echo ""
echo "Press Ctrl+C to stop"
echo "=================================================="
echo ""

python3 -m http.server "$PORT"
