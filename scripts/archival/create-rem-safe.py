#!/usr/bin/env python3
"""
Safe wrapper for create-rem-file.py that handles JSON escaping correctly.

Usage:
    python create-rem-safe.py \
        --rem-id "..." \
        --title "..." \
        --core-points-json '["point1", "point2", "point3"]' \
        --mistakes-json '["mistake1", "mistake2"]' \
        ...
"""

import sys
import json
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Safe Rem file creator with JSON escaping")

    # String arguments (no escaping needed)
    parser.add_argument("--rem-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--isced", required=True)
    parser.add_argument("--subdomain", required=True)
    parser.add_argument("--usage-scenario", required=True)
    parser.add_argument("--conversation-file", required=True)
    parser.add_argument("--conversation-title", required=True)
    parser.add_argument("--output-path", required=True)

    # JSON arguments (need safe handling)
    parser.add_argument("--core-points-json", required=True)
    parser.add_argument("--mistakes-json", required=True)
    parser.add_argument("--related-rems-json", default="[]")

    args = parser.parse_args()

    # Validate JSON inputs
    try:
        core_points = json.loads(args.core_points_json)
        mistakes = json.loads(args.mistakes_json)
        related_rems = json.loads(args.related_rems_json)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}", file=sys.stderr)
        sys.exit(1)

    # Build command for create-rem-file.py
    cmd = [
        "python", "scripts/archival/create-rem-file.py",
        "--rem-id", args.rem_id,
        "--title", args.title,
        "--isced", args.isced,
        "--subdomain", args.subdomain,
        "--usage-scenario", args.usage_scenario,
        "--conversation-file", args.conversation_file,
        "--conversation-title", args.conversation_title,
        "--output-path", args.output_path,
        "--core-points", json.dumps(core_points),  # Re-serialize with proper escaping
        "--mistakes", json.dumps(mistakes),
        "--related-rems", json.dumps(related_rems)
    ]

    # Execute with proper venv activation
    result = subprocess.run(
        ["bash", "-c", f"source venv/bin/activate && {' '.join(cmd)}"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
