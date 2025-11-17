#!/usr/bin/env python3
"""
Memory Health Monitoring Hook

PostToolUse hook that tracks memory operation health metrics automatically.
Logs tool usage, backend, latency, and success/failure to health dashboard.

Hook Type: PostToolUse
Trigger: After MCP Memory Server tool execution
Action: Record metrics if tool is memory-related

Configuration (.claude/settings.json):
    {
      "hooks": {
        "PostToolUse": [{
          "matcher": "mcp__memory-server__.*",
          "hooks": [{
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/scripts/hooks/hook-memory-health.py",
            "stdin_json": true,
            "on_error": "ignore"
          }]
        }]
      }
    }
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Portable project root detection using CLAUDE_PROJECT_DIR
# This environment variable is set by Claude Code to the project root
PROJECT_DIR = Path(os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd()))


class MemoryHealthMonitor:
    """Monitor and log memory operation health metrics."""

    def __init__(self):
        # Use portable path with PROJECT_DIR
        self.health_file = PROJECT_DIR / '.mcp/memory/health.json'
        self.max_history = 100  # Keep last 100 operations

        # Memory-related tool prefixes
        self.memory_tools = {
            "search_nodes", "create_entities", "create_relations",
            "add_observations", "read_graph", "delete_entities",
            "delete_observations", "delete_relations", "open_nodes"
        }

    def _read_health_data(self) -> Dict[str, Any]:
        """Read current health metrics."""
        if not self.health_file.exists():
            return {
                "version": "1.0.0",
                "current_backend": "python",
                "health_status": "healthy",
                "last_updated": datetime.now().isoformat(),
                "metrics": {
                    "total_operations": 0,
                    "successful_operations": 0,
                    "failed_operations": 0,
                    "failover_count": 0,
                    "success_rate": 100.0,
                    "avg_latency_ms": 0.0,
                    "min_latency_ms": 0.0,
                    "max_latency_ms": 0.0,
                    "by_tool": {},
                    "by_backend": {"official": 0, "python": 0}
                },
                "history": []
            }

        try:
            with open(self.health_file, 'r') as f:
                return json.load(f)
        except Exception:
            # Return default on error
            return self._read_health_data()

    def _write_health_data(self, data: Dict[str, Any]) -> bool:
        """Write health metrics to file."""
        try:
            # Ensure directory exists
            self.health_file.parent.mkdir(parents=True, exist_ok=True)

            # Write atomically
            temp_file = self.health_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.health_file)
            return True
        except Exception:
            return False

    def _is_memory_tool(self, tool_name: str) -> bool:
        """Check if tool is memory-related."""
        return any(mem_tool in tool_name.lower() for mem_tool in self.memory_tools)

    def _calculate_metrics(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aggregated metrics from history."""
        if not history:
            return {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "failover_count": 0,
                "success_rate": 100.0,
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "by_tool": {},
                "by_backend": {"official": 0, "python": 0}
            }

        total = len(history)
        successful = sum(1 for h in history if h.get("success", False))
        failed = total - successful

        latencies = [h.get("latency_ms", 0) for h in history if h.get("latency_ms")]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        min_latency = min(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0

        # Tool usage breakdown
        by_tool = {}
        for h in history:
            tool = h.get("tool_name", "unknown")
            by_tool[tool] = by_tool.get(tool, 0) + 1

        # Backend usage breakdown
        by_backend = {"official": 0, "python": 0}
        for h in history:
            backend = h.get("backend", "python")
            if backend in by_backend:
                by_backend[backend] += 1

        return {
            "total_operations": total,
            "successful_operations": successful,
            "failed_operations": failed,
            "failover_count": 0,  # Tracked separately in proxy
            "success_rate": (successful / total * 100) if total > 0 else 100.0,
            "avg_latency_ms": avg_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "by_tool": by_tool,
            "by_backend": by_backend
        }

    def record_operation(self, tool_name: str, success: bool, latency_ms: float, backend: str = "python"):
        """Record a memory operation in health metrics."""
        # Only track memory-related tools
        if not self._is_memory_tool(tool_name):
            return

        # Read current data
        data = self._read_health_data()

        # Add operation to history
        operation = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "backend": backend,
            "success": success,
            "latency_ms": latency_ms
        }

        data["history"].append(operation)

        # Trim history to max size (circular buffer)
        if len(data["history"]) > self.max_history:
            data["history"] = data["history"][-self.max_history:]

        # Recalculate metrics
        data["metrics"] = self._calculate_metrics(data["history"])
        data["last_updated"] = datetime.now().isoformat()

        # Determine health status
        success_rate = data["metrics"]["success_rate"]
        if success_rate >= 95:
            data["health_status"] = "healthy"
        elif success_rate >= 80:
            data["health_status"] = "degraded"
        else:
            data["health_status"] = "failed"

        # Write back
        self._write_health_data(data)

    def process_hook_input(self, hook_data: Dict[str, Any]):
        """Process PostToolUse hook input."""
        # Extract tool information
        tool_name = hook_data.get("tool_name", "unknown")
        success = not hook_data.get("error", False)  # No error = success

        # Estimate latency (if provided, otherwise default)
        latency_ms = hook_data.get("duration_ms", 50.0)

        # Backend is always Python in current implementation
        backend = "python"

        # Record the operation
        self.record_operation(tool_name, success, latency_ms, backend)


def main():
    """Entry point for PostToolUse hook."""
    try:
        # Read hook input from stdin
        hook_input = sys.stdin.read()
        hook_data = json.loads(hook_input) if hook_input else {}

        # Process the hook
        monitor = MemoryHealthMonitor()
        monitor.process_hook_input(hook_data)

        # Hook success (no output needed)
        sys.exit(0)
    except Exception as e:
        # Hook failure (log to stderr)
        print(f"Memory health monitor error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
