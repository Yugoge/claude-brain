#!/usr/bin/env python3
"""
Hook: Detect and block python3 -c inline code usage
Enforces CLAUDE.md Script Usage Requirements
"""
import sys
import json
import re

def main():
    # Read stdin JSON
    data = json.load(sys.stdin)
    command = data.get("command", "")

    # Check for python3 -c pattern
    if re.search(r'python3?\s+-c\s+["\']', command):
        print("❌ ERROR: Inline Python detected", file=sys.stderr)
        print("", file=sys.stderr)
        print("You tried to use:", file=sys.stderr)
        print(f"  {command[:100]}...", file=sys.stderr)
        print("", file=sys.stderr)
        print("✅ Instead, use existing script:", file=sys.stderr)
        print("  python3 scripts/archival/session_detector.py", file=sys.stderr)
        print("  python3 scripts/archival/concept_extractor.py", file=sys.stderr)
        print("  python3 scripts/archive/utilities/process_tutor_response.py", file=sys.stderr)
        print("", file=sys.stderr)
        print("See CLAUDE.md lines 77-90 for Script Usage Requirements", file=sys.stderr)
        sys.exit(1)  # Block execution

    # Allow other bash commands
    sys.exit(0)

if __name__ == "__main__":
    main()
