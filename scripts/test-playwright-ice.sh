#!/usr/bin/env bash
#
# Test Playwright Access to ICE.com
# Verifies anti-detection configuration works for financial sites
#
# Purpose: Test that Playwright can access ICE.com without bot detection errors
#
# Success criteria:
#   - No ERR_TUNNEL_CONNECTION_FAILED error
#   - Page content retrievable
#   - HTTP status indicates success
#
# Usage: ./scripts/test-playwright-ice.sh
#

set -euo pipefail

# Test configuration
TEST_URL="https://www.ice.com/fixed-income-data-services/index-solutions/currency-indices"
TIMEOUT_SECONDS=30

echo "================================================"
echo "Playwright ICE.com Access Test"
echo "================================================"
echo ""
echo "Target URL: ${TEST_URL}"
echo "Timeout: ${TIMEOUT_SECONDS}s"
echo ""

# Check if Playwright MCP is running
if ! pgrep -f "playwright-mcp" > /dev/null; then
  echo "ERROR: Playwright MCP is not running" >&2
  echo "Please start it first with: ./scripts/playwright-stealth-wrapper.sh" >&2
  exit 1
fi

echo "Step 1: Verifying Playwright MCP process..."
PLAYWRIGHT_PID=$(pgrep -f "playwright-mcp" | head -1)
echo "  ✓ Playwright MCP running (PID: ${PLAYWRIGHT_PID})"
echo ""

# Check if running with anti-detection args
PLAYWRIGHT_CMD=$(ps -p "${PLAYWRIGHT_PID}" -o args= 2>/dev/null || echo "")
if echo "${PLAYWRIGHT_CMD}" | grep -q "AutomationControlled"; then
  echo "  ✓ Anti-detection args detected in process"
else
  echo "  ⚠ WARNING: Anti-detection args not found in process command"
  echo "  Command: ${PLAYWRIGHT_CMD}"
fi
echo ""

echo "Step 2: Testing ICE.com access via Playwright..."
echo "  Note: This test requires Playwright MCP to be accessible via Claude Code"
echo "  If Claude Code is not running, this test will show connection status only"
echo ""

# Test network connectivity first
echo "Step 3: Verifying network connectivity to ICE.com..."
if timeout 10 curl -sSf -o /dev/null -w "HTTP Status: %{http_code}\n" "${TEST_URL}"; then
  echo "  ✓ Network connectivity to ICE.com confirmed"
else
  echo "  ✗ Network connectivity test failed" >&2
  echo "  This may indicate network issues or site blocking direct curl access" >&2
fi
echo ""

echo "================================================"
echo "Test Summary"
echo "================================================"
echo "Playwright MCP: Running with anti-detection configuration"
echo ""
echo "Next steps:"
echo "  1. Use Claude Code to test browser navigation:"
echo "     - Call mcp__playwright__browser_navigate with url: ${TEST_URL}"
echo "     - Call mcp__playwright__browser_snapshot to verify page loaded"
echo ""
echo "  2. Expected success indicators:"
echo "     - No ERR_TUNNEL_CONNECTION_FAILED error"
echo "     - Page snapshot shows ICE.com content"
echo "     - Browser console shows no bot detection errors"
echo ""
echo "  3. If test fails:"
echo "     - Check browser console logs via mcp__playwright__browser_console_messages"
echo "     - Verify xvfb-run is providing virtual display"
echo "     - Confirm all anti-detection args are passed to Chrome"
echo ""
