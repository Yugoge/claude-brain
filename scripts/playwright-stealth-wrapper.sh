#!/usr/bin/env bash
#
# Playwright Stealth Wrapper
# Launches Playwright MCP with anti-detection configuration for financial sites
#
# Purpose: Bypass bot detection on sites like ICE.com by:
#   1. Using Xvfb virtual display for headless environment
#   2. Adding anti-detection Chrome arguments
#   3. Hiding webdriver markers
#
# Usage: ./scripts/playwright-stealth-wrapper.sh [display_num] [screen_res] [output_dir] [browser]
#

set -euo pipefail

# Configuration (with defaults)
DISPLAY_NUM="${1:-99}"
SCREEN_RES="${2:-1920x1080x24}"
OUTPUT_DIR="${3:-.playwright-mcp}"
BROWSER="${4:-chrome}"

# Anti-detection Chrome arguments
CHROME_ARGS=(
  "--disable-blink-features=AutomationControlled"
  "--disable-features=IsolateOrigins,site-per-process"
  "--disable-web-security"
  "--disable-dev-shm-usage"
  "--disable-setuid-sandbox"
  "--no-first-run"
  "--no-default-browser-check"
  "--window-size=1920,1080"
  "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Build chrome-arg string for playwright-mcp
CHROME_ARG_STRING=""
for arg in "${CHROME_ARGS[@]}"; do
  CHROME_ARG_STRING="${CHROME_ARG_STRING} --chrome-arg=${arg}"
done

# Check if Xvfb is available
if ! command -v xvfb-run &> /dev/null; then
  echo "ERROR: xvfb-run not found. Please install: sudo apt-get install xvfb" >&2
  exit 1
fi

# Kill existing Playwright MCP processes
echo "Stopping existing Playwright MCP processes..."
pkill -f "playwright-mcp" || true
sleep 2

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Launch Playwright MCP with Xvfb virtual display
echo "Starting Playwright MCP with anti-detection configuration..."
echo "Display: :${DISPLAY_NUM}"
echo "Resolution: ${SCREEN_RES}"
echo "Browser: ${BROWSER}"
echo "Anti-detection args: ${#CHROME_ARGS[@]} arguments configured"

# Use xvfb-run to provide virtual display for "headed" mode
exec xvfb-run \
  --server-num="${DISPLAY_NUM}" \
  --server-args="-screen 0 ${SCREEN_RES}" \
  npx playwright-mcp \
    --isolated \
    --browser "${BROWSER}" \
    --no-sandbox \
    --output-dir "${OUTPUT_DIR}" \
    ${CHROME_ARG_STRING}
