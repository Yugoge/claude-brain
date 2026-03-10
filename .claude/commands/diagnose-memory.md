---
description: "Diagnose MCP memory server issues"
allowed-tools: Bash
argument-hint: "[--health | --storage | --errors | --all]"
disable-model-invocation: true
---

# MCP Memory Diagnostic Tool

Comprehensive diagnostics for MCP memory server issues.

## Usage

```
/diagnose-memory [--health | --storage | --errors | --all]
```

### Options

- `--health`: Check MCP server health and configuration
- `--storage`: Detect MCP storage location
- `--errors`: Diagnose JSON parsing errors
- `--all` or no args: Run all diagnostics (default)

## Examples

```
/diagnose-memory              # Run all diagnostics
/diagnose-memory --health     # Only health check
```

## Implementation

Run diagnostic tools sequentially and present consolidated results.

### Full Diagnostic (Default)

```bash
echo "=== MCP Memory Server Diagnostics ===" && \
echo "" && \
echo "1. Health Check:" && \
echo "────────────────────────────────────" && \
source venv/bin/activate && python scripts/memory/check-memory-server.py && \
echo "" && \
echo "2. Storage Detection:" && \
echo "────────────────────────────────────" && \
source venv/bin/activate && python scripts/memory/detect_mcp_storage.py && \
echo "" && \
echo "3. Error Diagnosis:" && \
echo "────────────────────────────────────" && \
source venv/bin/activate && python scripts/memory/diagnose_mcp_error.py
```

### Individual Diagnostics

**Health Check**:
```bash
source venv/bin/activate && python scripts/memory/check-memory-server.py
```

**Storage Detection**:
```bash
source venv/bin/activate && python scripts/memory/detect_mcp_storage.py
```

**Error Diagnosis**:
```bash
source venv/bin/activate && python scripts/memory/diagnose_mcp_error.py
```

## Output

Present results in clear sections with:
- ✅ Success indicators
- ❌ Error indicators
- 💡 Actionable recommendations
