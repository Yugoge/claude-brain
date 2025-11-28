#!/usr/bin/env python3
"""
Construct complete enriched_rems.json from Step 5 output + session metadata.

This script solves Bug 2: workflow_orchestrator.py only generates partial metadata.
Main agent provides complete session metadata, this script merges with enriched Rems.

Usage:
    python scripts/archival/construct_enriched_rems.py \\
        --enriched-rems enriched_rems.json \\
        --session-id "topic-slug-2025-11-24" \\
        --title "Session Title" \\
        --summary "User learned..." \\
        --archived-file "chats/2025-11/conversation.md" \\
        --session-type learn \\
        --domain domain-name \\
        --subdomain subdomain-slug \\
        --isced-path "02-.../0222-..." \\
        --tags "tag1,tag2" \\
        --output enriched_rems_complete.json

Outputs: Complete JSON with full session_metadata ready for save_post_processor.py
"""

import json
import sys
import argparse
from pathlib import Path

def construct_complete_json(
    enriched_rems_file,
    session_id,
    title,
    summary,
    archived_file,
    session_type,
    domain,
    subdomain,
    isced_path,
    tags,
    output_file
):
    """
    Merge Step 5 enriched Rems with complete session metadata.

    Args:
        enriched_rems_file: Path to enriched_rems.json from Step 5
        session_id: Conversation ID
        title: Conversation title
        summary: 2-3 sentence summary of what user learned
        archived_file: Path to archived conversation
        session_type: learn | ask | review
        domain: Domain name
        subdomain: Subdomain slug
        isced_path: Full ISCED path
        tags: Comma-separated tags
        output_file: Output path for complete JSON

    Returns: Exit code (0 = success, 1 = error)
    """
    try:
        # Load Step 5 output
        with open(enriched_rems_file, 'r', encoding='utf-8') as f:
            step5_data = json.load(f)

        # Validate and normalize input format (supports both list and dict)
        if isinstance(step5_data, list):
            # Format: [{rem_id: ..., ...}, ...]
            print(f"⚠️  Warning: Input is raw array format (legacy)", file=sys.stderr)
            print(f"   Auto-converting to standard dict format...", file=sys.stderr)
            enriched_rems = step5_data
        elif isinstance(step5_data, dict):
            # Format: {"rems": [...], "session_metadata": {...}}
            enriched_rems = step5_data.get('rems', [])
            if not enriched_rems:
                print(f"❌ Error: Dict format but missing 'rems' key or empty array", file=sys.stderr)
                print(f"   Expected format: {{'rems': [...], 'session_metadata': {{...}}}}", file=sys.stderr)
                print(f"   Received keys: {list(step5_data.keys())}", file=sys.stderr)
                return 1
        else:
            print(f"❌ Error: Invalid JSON type: {type(step5_data).__name__}", file=sys.stderr)
            print(f"   Expected: list (legacy) or dict with 'rems' key (standard)", file=sys.stderr)
            print(f"   Standard format: {{'rems': [...], 'session_metadata': {{...}}}}", file=sys.stderr)
            return 1

        if not enriched_rems:
            print(f"❌ No Rems found in {enriched_rems_file}", file=sys.stderr)
            return 1

        # Parse tags
        tag_list = [t.strip() for t in tags.split(',')] if tags else []

        # Construct complete JSON
        complete_data = {
            "session_metadata": {
                "id": session_id,
                "title": title,
                "summary": summary,
                "archived_file": archived_file,
                "session_type": session_type,
                "domain": domain,
                "subdomain": subdomain,
                "isced_path": isced_path,
                "agent": "main",
                "tags": tag_list
            },
            "rems": enriched_rems,
            "rems_to_update": []
        }

        # Write output
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(complete_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Created: {output_file}", file=sys.stderr)
        print(f"   Session: {title}", file=sys.stderr)
        print(f"   Rems: {len(enriched_rems)}", file=sys.stderr)
        print(f"   Domain: {domain} > {subdomain}", file=sys.stderr)

        return 0

    except FileNotFoundError as e:
        print(f"❌ File not found: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='Construct complete enriched_rems.json with full session metadata'
    )

    # Required args
    parser.add_argument('--enriched-rems', required=True, help='Path to Step 5 enriched_rems.json')
    parser.add_argument('--session-id', required=True, help='Session ID')
    parser.add_argument('--title', required=True, help='Conversation title')
    parser.add_argument('--summary', required=True, help='2-3 sentence summary')
    parser.add_argument('--archived-file', required=True, help='Path to archived conversation')
    parser.add_argument('--session-type', required=True, choices=['learn', 'ask', 'review'])
    parser.add_argument('--domain', required=True, help='Domain name (from classification-expert)')
    parser.add_argument('--subdomain', required=True, help='Subdomain slug')
    parser.add_argument('--isced-path', required=True, help='Full ISCED path')

    # Optional args
    parser.add_argument('--tags', default='', help='Comma-separated tags')
    parser.add_argument('--output', default='/tmp/enriched_rems_complete.json', help='Output file path')

    args = parser.parse_args()

    return construct_complete_json(
        enriched_rems_file=args.enriched_rems,
        session_id=args.session_id,
        title=args.title,
        summary=args.summary,
        archived_file=args.archived_file,
        session_type=args.session_type,
        domain=args.domain,
        subdomain=args.subdomain,
        isced_path=args.isced_path,
        tags=args.tags,
        output_file=args.output
    )


if __name__ == '__main__':
    sys.exit(main())
