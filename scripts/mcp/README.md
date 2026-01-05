# Playwright MCP Process Management Scripts

**Created:** 2025-12-31  
**Purpose:** Resolve recurring Playwright MCP connection failures caused by orphaned process accumulation

---

## Quick Start

### Fix Playwright MCP Issues Now

```bash
# 1. Check current health
./check-playwright-health.sh --verbose

# 2. Clean up orphaned processes
./cleanup-playwright-processes.sh

# 3. Restart MCP server properly
./restart-playwright-mcp.sh

# 4. Verify single healthy process
./check-playwright-health.sh --verbose
```

---

## Scripts

### cleanup-playwright-processes.sh

Kill all Playwright MCP processes (parent + child).

**Usage:**
```bash
./cleanup-playwright-processes.sh [--dry-run]
```

**Exit codes:**
- 0: Success (all killed or none found)
- 1: Error (failed to kill)

---

### check-playwright-health.sh

Monitor MCP process health and count.

**Usage:**
```bash
./check-playwright-health.sh [--verbose] [--json]
```

**Exit codes:**
- 0: Healthy (0-1 process)
- 1: Unhealthy (2+ processes)
- 2: Error

**JSON output:**
```bash
./check-playwright-health.sh --json | jq '.process_count'
```

---

### restart-playwright-mcp.sh

Safe restart with cleanup and verification.

**Usage:**
```bash
./restart-playwright-mcp.sh [OPTIONS]

Options:
  --isolated              Use isolated mode (default)
  --headless              Run headless
  --browser <name>        chrome|firefox|webkit (default: chrome)
  --no-sandbox            Disable sandbox
  --wait-timeout <secs>   Cleanup timeout (default: 10)
  --dry-run               Preview only
```

**Examples:**
```bash
# Standard restart
./restart-playwright-mcp.sh

# Headless Chrome without sandbox
./restart-playwright-mcp.sh --headless --no-sandbox

# Firefox browser
./restart-playwright-mcp.sh --browser firefox
```

**Exit codes:**
- 0: Success (1 healthy process)
- 1: Error (cleanup/startup/verification failed)

---

## Troubleshooting

See comprehensive guide: [docs/troubleshooting/playwright-mcp.md](../../docs/troubleshooting/playwright-mcp.md)

**Common issues:**
- "Invalid URL: undefined" → Run cleanup + restart
- Multiple processes detected → Run cleanup
- Startup failed → Check browser installation: `npx playwright install chrome`

---

## Automation

### Add to Shell Profile

```bash
# Add to ~/.bashrc or ~/.zshrc
alias pw-status='/path/to/scripts/mcp/check-playwright-health.sh --verbose'
alias pw-fix='/path/to/scripts/mcp/restart-playwright-mcp.sh'
```

### Daily Health Check (Cron)

```bash
# Add to crontab: crontab -e
0 9 * * * /path/to/scripts/mcp/check-playwright-health.sh || /path/to/scripts/mcp/restart-playwright-mcp.sh
```

---

## Implementation Details

See full report: [docs/dev/dev-report-20251231-141909.json](../../docs/dev/dev-report-20251231-141909.json)

**Root cause:** Process accumulation - no automated cleanup mechanism  
**Solution:** Three-layer prevention (cleanup, monitoring, safe restart)  
**Testing:** Validated on live system with 10 orphaned processes

---

**Need help?** Check script `--help` output or read the troubleshooting guide.
