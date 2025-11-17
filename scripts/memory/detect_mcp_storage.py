#!/usr/bin/env python3
"""
Detect MCP Memory Server Storage Location

Detects where MCP memory server stores its data files.
Useful after restart to verify storage location and migrate if needed.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def get_platform_default_paths():
    """
    Get default MCP storage paths by platform.

    Returns:
        dict: Platform-specific default paths
    """
    system = platform.system()
    home = Path.home()

    paths = {
        "platform": system,
        "home": str(home),
        "candidates": []
    }

    if system in ["Linux", "Darwin"]:  # Darwin = macOS
        paths["candidates"] = [
            home / ".local" / "share" / "@modelcontextprotocol" / "server-memory",
            home / ".local" / "share" / "mcp" / "memory",
            home / ".mcp" / "memory",
            Path.cwd() / ".mcp" / "memory",  # Current working directory
            home / "Library" / "Application Support" / "mcp" / "memory" if system == "Darwin" else None
        ]
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        local_appdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))

        paths["candidates"] = [
            appdata / "@modelcontextprotocol" / "server-memory",
            appdata / "mcp" / "memory",
            local_appdata / "mcp" / "memory",
            Path.cwd() / ".mcp" / "memory"
        ]

    # Filter out None values
    paths["candidates"] = [p for p in paths["candidates"] if p is not None]

    return paths


def find_memory_files():
    """
    Search for memories.json files in common locations.

    Returns:
        list: List of found memory file paths with metadata
    """
    found = []

    # Get platform defaults
    platform_paths = get_platform_default_paths()

    # Search candidates
    for candidate in platform_paths["candidates"]:
        memory_file = candidate / "memories.json"

        if memory_file.exists():
            try:
                # Get file stats
                stats = memory_file.stat()

                # Load and validate
                with open(memory_file, 'r') as f:
                    data = json.load(f)

                entity_count = len(data.get("entities", []))
                relation_count = len(data.get("relations", []))

                found.append({
                    "path": str(memory_file),
                    "directory": str(candidate),
                    "size_bytes": stats.st_size,
                    "modified": stats.st_mtime,
                    "entities": entity_count,
                    "relations": relation_count,
                    "valid": True
                })
            except Exception as e:
                found.append({
                    "path": str(memory_file),
                    "directory": str(candidate),
                    "error": str(e),
                    "valid": False
                })

    return found


def check_mcp_config():
    """
    Check Claude Code configuration for MCP memory server.

    Returns:
        dict: MCP configuration info
    """
    config_paths = [
        Path.home() / ".claude.json",
        Path.home() / ".config" / "claude" / "config.json",
        Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        Path.home() / "AppData" / "Roaming" / "Claude" / "config.json"
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)

                # Look for MCP servers in current project
                projects = config.get("projects", {})
                cwd = str(Path.cwd())

                if cwd in projects:
                    mcp_servers = projects[cwd].get("mcpServers", {})

                    for server_name, server_config in mcp_servers.items():
                        if "memory" in server_name.lower():
                            return {
                                "found": True,
                                "config_path": str(config_path),
                                "server_name": server_name,
                                "command": server_config.get("command"),
                                "args": server_config.get("args", []),
                                "env": server_config.get("env", {}),
                                "custom_path": server_config.get("env", {}).get("MEMORY_FILE_PATH")
                            }

            except Exception:
                pass

    return {"found": False}


def test_mcp_server():
    """
    Test if MCP memory server is running and responsive.

    Returns:
        dict: Server status
    """
    try:
        # Try to run MCP server with test request
        result = subprocess.run(
            ["npx", "-y", "@modelcontextprotocol/server-memory"],
            input='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n',
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and "result" in result.stdout:
            return {"status": "running", "output": result.stdout[:200]}
        else:
            return {"status": "error", "error": result.stderr[:200]}

    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


def main():
    """CLI interface for storage detection."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect MCP memory server storage location"
    )
    parser.add_argument(
        "--test-server",
        action="store_true",
        help="Test if MCP server is responsive"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Gather information
    platform_info = get_platform_default_paths()
    found_files = find_memory_files()
    mcp_config = check_mcp_config()

    if args.test_server:
        server_status = test_mcp_server()
    else:
        server_status = None

    # Output
    if args.json:
        output = {
            "platform": platform_info,
            "found_memory_files": found_files,
            "mcp_config": mcp_config,
            "server_status": server_status
        }
        print(json.dumps(output, indent=2))
        return

    # Human-readable output
    print("\n" + "=" * 60)
    print("  MCP Memory Storage Detection")
    print("=" * 60 + "\n")

    # Platform info
    print(f"🖥️  Platform: {platform_info['platform']}")
    print(f"🏠 Home: {platform_info['home']}\n")

    # MCP Configuration
    print("📋 MCP Configuration:")
    if mcp_config["found"]:
        print(f"   ✅ Found in: {mcp_config['config_path']}")
        print(f"   Server: {mcp_config['server_name']}")
        print(f"   Command: {mcp_config['command']} {' '.join(mcp_config.get('args', []))}")

        if mcp_config.get("custom_path"):
            print(f"   ⚠️  Custom Path: {mcp_config['custom_path']}")
        else:
            print(f"   ℹ️  Using default storage location")
    else:
        print("   ❌ No MCP memory server configured")

    print()

    # Found memory files
    print("📁 Found Memory Files:")
    if found_files:
        for i, file_info in enumerate(found_files, 1):
            print(f"\n   {i}. {file_info['path']}")

            if file_info.get("valid"):
                print(f"      ✅ Valid: {file_info['entities']} entities, {file_info['relations']} relations")
                print(f"      Size: {file_info['size_bytes']:,} bytes")
            else:
                print(f"      ❌ Invalid: {file_info.get('error')}")
    else:
        print("   ❌ No memory files found in standard locations")

    print()

    # Server status
    if server_status:
        print("🔧 MCP Server Status:")
        if server_status["status"] == "running":
            print("   ✅ Server is responsive")
        elif server_status["status"] == "timeout":
            print("   ⏱️  Server timeout (may not be running)")
        else:
            print(f"   ❌ Server error: {server_status.get('error', 'Unknown')}")
        print()

    # Recommendations
    print("💡 Recommendations:")
    if not found_files:
        print("   1. Restart Claude Code to initialize MCP server")
        print("   2. Create a test memory to generate storage file")
        print("   3. Run this script again to detect location")
    elif len(found_files) > 1:
        print("   ⚠️  Multiple memory files found!")
        print("   - Determine which is active")
        print("   - Consider consolidating with migrate_memory_to_default.py")
    else:
        print(f"   ✅ Memory storage detected: {found_files[0]['directory']}")
        print("   - This is where MCP server stores data")
        print("   - Update documentation with this path")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
