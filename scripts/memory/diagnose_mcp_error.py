#!/usr/bin/env python3
"""
Diagnose MCP Memory Server JSON Error

Tests different query formats to identify the issue with:
"Expected property name or '}' in JSON at position 1"
"""

import json
import sys


def test_query_formats():
    """Test different query string formats."""

    test_cases = [
        # Original query
        {
            "name": "Original Query",
            "query": "theta time scenario PLBase incremental cumulative"
        },
        # Simple query
        {
            "name": "Simple Query",
            "query": "theta"
        },
        # Query with special characters
        {
            "name": "Query with Hyphen",
            "query": "option-value"
        },
        # Empty query
        {
            "name": "Empty Query",
            "query": ""
        },
        # Query with quotes
        {
            "name": "Query with Quotes",
            "query": "\"theta time\""
        }
    ]

    print("🔍 Testing MCP Query Formats\n")
    print("=" * 60)

    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   Query: {test['query']}")

        # Test JSON serialization
        try:
            payload = {"query": test["query"]}
            json_str = json.dumps(payload)
            print(f"   ✅ JSON: {json_str}")

            # Test deserialization
            parsed = json.loads(json_str)
            print(f"   ✅ Parsed: {parsed}")

        except json.JSONDecodeError as e:
            print(f"   ❌ JSON Error: {e}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)


def check_memory_file_format():
    """Check if memory file has valid JSON format."""

    memory_file = "/root/knowledge-system/.mcp/memory/memories.json"

    print("\n📁 Checking Memory File Format\n")
    print("=" * 60)
    print(f"File: {memory_file}\n")

    try:
        with open(memory_file, 'r') as f:
            content = f.read()

        # Check for common JSON issues
        issues = []

        # Check for BOM
        if content.startswith('\ufeff'):
            issues.append("⚠️  File starts with BOM (Byte Order Mark)")

        # Check for leading whitespace issues
        if content and not content[0] in ['{', '[']:
            issues.append(f"⚠️  File starts with unexpected character: {repr(content[0])}")

        # Try to parse
        data = json.loads(content)
        print(f"✅ Valid JSON structure")
        print(f"   Entities: {len(data.get('entities', []))}")
        print(f"   Relations: {len(data.get('relations', []))}")

        if issues:
            print("\n⚠️  Issues found:")
            for issue in issues:
                print(f"   {issue}")

    except FileNotFoundError:
        print("❌ Memory file not found")
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        print(f"   Position: {e.pos}")
        print(f"   Line: {e.lineno}, Column: {e.colno}")

        # Show context around error
        if 'content' in locals():
            start = max(0, e.pos - 50)
            end = min(len(content), e.pos + 50)
            print(f"\n   Context: ...{content[start:end]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("=" * 60)


def test_mcp_search_simulation():
    """Simulate MCP search_nodes tool call."""

    print("\n🧪 Simulating MCP search_nodes Call\n")
    print("=" * 60)

    # Simulate what MCP tool receives
    query = "theta time scenario PLBase incremental cumulative"

    print(f"Query String: {query}")
    print(f"Query Length: {len(query)}")
    print(f"Query Type: {type(query)}")

    # Simulate MCP tool parameter
    mcp_params = {
        "query": query
    }

    print(f"\nMCP Parameters:")
    print(f"  {json.dumps(mcp_params, indent=2)}")

    # Check for problematic characters
    problematic = []
    for char in query:
        if ord(char) > 127:
            problematic.append(f"{char} (U+{ord(char):04X})")

    if problematic:
        print(f"\n⚠️  Non-ASCII characters found: {', '.join(problematic)}")
    else:
        print(f"\n✅ All characters are ASCII")

    print("=" * 60)


def main():
    """Run all diagnostic tests."""

    print("\n" + "=" * 60)
    print("  MCP Memory Server Error Diagnostic Tool")
    print("=" * 60)

    test_query_formats()
    check_memory_file_format()
    test_mcp_search_simulation()

    print("\n📋 Summary & Recommendations:\n")
    print("1. If JSON serialization tests pass → Issue is in MCP server")
    print("2. If memory file has issues → Rebuild with:")
    print("   python scripts/rebuild-indexes.py")
    print("3. If query has special chars → Simplify query string")
    print("4. Check MCP server logs for detailed error trace")
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
