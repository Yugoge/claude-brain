#!/usr/bin/env python3
"""
MCP Memory Server Health Check Script

Verifies that the MCP memory server is properly configured and accessible.
Since the server uses stdio transport (not HTTP), we verify configuration and file existence.
"""

import sys
import json
import os
import subprocess
from pathlib import Path


def check_memory_server():
    """Check MCP memory server health."""
    print("🔍 Checking MCP Memory Server Health...\n")

    all_checks_passed = True

    # Check 1: Verify MCP server is configured
    print("1️⃣  Checking MCP server configuration...")
    try:
        result = subprocess.run(
            ["claude", "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "memory-server" in result.stdout and "Connected" in result.stdout:
            print("   ✅ Memory server is configured and connected\n")
        else:
            print("   ❌ Memory server not found in MCP configuration\n")
            all_checks_passed = False
    except Exception as e:
        print(f"   ❌ Error checking MCP configuration: {e}\n")
        all_checks_passed = False

    # Check 2: Verify storage directory exists
    print("2️⃣  Checking storage directory...")
    storage_dir = Path("/root/knowledge-system/.mcp/memory")
    if storage_dir.exists() and storage_dir.is_dir():
        print(f"   ✅ Storage directory exists: {storage_dir}")

        # Check permissions
        stat_info = os.stat(storage_dir)
        permissions = oct(stat_info.st_mode)[-3:]
        if permissions == "700":
            print(f"   ✅ Permissions are secure: {permissions}\n")
        else:
            print(f"   ⚠️  Permissions should be 700, found: {permissions}\n")
    else:
        print(f"   ❌ Storage directory not found: {storage_dir}\n")
        all_checks_passed = False

    # Check 3: Verify config file exists
    print("3️⃣  Checking configuration file...")
    config_file = Path("/root/knowledge-system/.mcp/config.json")
    if config_file.exists():
        print(f"   ✅ Configuration file exists: {config_file}")
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"   ✅ Configuration is valid JSON")
            print(f"   📋 Version: {config.get('version', 'unknown')}\n")
        except json.JSONDecodeError as e:
            print(f"   ❌ Configuration JSON is invalid: {e}\n")
            all_checks_passed = False
    else:
        print(f"   ⚠️  Configuration file not found: {config_file}\n")

    # Check 4: Check if memory file exists (optional - created on first use)
    print("4️⃣  Checking memory storage file...")
    memory_file = Path("/root/knowledge-system/.mcp/memory/memories.json")
    if memory_file.exists():
        try:
            with open(memory_file, 'r') as f:
                memories = json.load(f)
            memory_count = len(memories.get('entities', []))
            relation_count = len(memories.get('relations', []))
            print(f"   ✅ Memory file exists with {memory_count} entities, {relation_count} relations\n")
        except Exception as e:
            print(f"   ⚠️  Memory file exists but couldn't read: {e}\n")
    else:
        print(f"   ℹ️  Memory file not yet created (will be created on first use)\n")

    # Check 5: Verify gitignore
    print("5️⃣  Checking .gitignore...")
    gitignore = Path("/root/knowledge-system/.gitignore")
    if gitignore.exists():
        with open(gitignore, 'r') as f:
            content = f.read()
        if ".mcp/memory/" in content:
            print(f"   ✅ Memory storage is properly gitignored\n")
        else:
            print(f"   ⚠️  Memory storage not in .gitignore (should add .mcp/memory/)\n")
    else:
        print(f"   ⚠️  .gitignore not found\n")

    # Summary
    print("=" * 60)
    if all_checks_passed:
        print("✅ All critical checks passed! Memory server is healthy.")
        print("\n📖 Usage:")
        print("   - Memory server runs automatically with Claude Code")
        print("   - Use MCP tools during conversations to store/retrieve memories")
        print("   - Memories persist in .mcp/memory/memories.json")
        return 0
    else:
        print("❌ Some checks failed. Please review errors above.")
        print("\n🔧 Quick fixes:")
        print("   - Run: claude mcp add --transport stdio memory-server --env MEMORY_FILE_PATH=/root/knowledge-system/.mcp/memory/memories.json -- npx -y @modelcontextprotocol/server-memory")
        print("   - Run: mkdir -p /root/knowledge-system/.mcp/memory && chmod 700 /root/knowledge-system/.mcp/memory")
        return 1


if __name__ == "__main__":
    sys.exit(check_memory_server())
