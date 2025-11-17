#!/usr/bin/env python3
"""
Conversation Index Auto-Updater

Automatically adds new conversation to chats/index.json and updates metadata.

Usage:
    python scripts/archival/update-conversation-index.py \\
        --id "conversation-id" \\
        --title "Conversation Title" \\
        --date "2025-11-07" \\
        --file "chats/2025-11/conversation.md" \\
        --agent "analyst" \\
        --domain "finance" \\
        --session-type "ask" \\
        --turns 18

Exit codes:
    0 - Success
    1 - Error (missing params, file not found, etc.)
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse


def load_index(index_file: Path) -> dict:
    """Load conversation index JSON."""
    if not index_file.exists():
        # Create new index if doesn't exist
        return {
            "version": "1.0.0",
            "conversations": {},
            "metadata": {
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "total_conversations": 0,
                "total_turns": 0,
                "total_rems_extracted": 0,
                "by_domain": {},
                "by_agent": {},
                "by_month": {}
            }
        }

    with open(index_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_index(index_file: Path, data: dict):
    """Save conversation index JSON with backup."""
    # Create backup
    if index_file.exists():
        backup_path = index_file.parent / f"{index_file.name}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        import shutil
        shutil.copy2(index_file, backup_path)

    # Write updated index
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_index(
    conversation_id: str,
    title: str,
    date: str,
    file_path: str,
    agent: str,
    domain: str,
    session_type: str,
    turns: int,
    rems_extracted: int = 0,
    index_file: Path = None
) -> bool:
    """
    Add conversation to index and update metadata.

    Returns:
        True if successful, False otherwise
    """
    if index_file is None:
        index_file = Path("chats/index.json")

    # Load current index
    data = load_index(index_file)

    # Check if conversation already exists
    if conversation_id in data["conversations"]:
        print(f"⚠️  Warning: Conversation '{conversation_id}' already exists in index")
        print(f"   Updating existing entry...")

    # Add/update conversation entry
    data["conversations"][conversation_id] = {
        "title": title,
        "date": date,
        "file": file_path,
        "agent": agent,
        "domain": domain,
        "session_type": session_type,
        "turns": turns
    }

    # Update metadata
    metadata = data["metadata"]

    # Recalculate totals by scanning all conversations
    metadata["total_conversations"] = len(data["conversations"])
    metadata["total_turns"] = sum(conv.get("turns", 0) for conv in data["conversations"].values())

    # Update by_domain
    domain_counts = {}
    for conv in data["conversations"].values():
        conv_domain = conv.get("domain", "unknown")
        domain_counts[conv_domain] = domain_counts.get(conv_domain, 0) + 1
    metadata["by_domain"] = domain_counts

    # Update by_agent
    agent_counts = {}
    for conv in data["conversations"].values():
        conv_agent = conv.get("agent", "unknown")
        agent_counts[conv_agent] = agent_counts.get(conv_agent, 0) + 1
    metadata["by_agent"] = agent_counts

    # Update by_month (YYYY-MM format)
    month_counts = {}
    for conv in data["conversations"].values():
        conv_date = conv.get("date", "")
        if conv_date:
            month = conv_date[:7]  # YYYY-MM
            month_counts[month] = month_counts.get(month, 0) + 1
    metadata["by_month"] = month_counts

    # Update last_updated
    metadata["last_updated"] = datetime.now().strftime("%Y-%m-%d")

    # Update total_rems_extracted if provided
    if rems_extracted > 0:
        metadata["total_rems_extracted"] = metadata.get("total_rems_extracted", 0) + rems_extracted

    # Save updated index
    save_index(index_file, data)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Automatically update conversation index"
    )
    parser.add_argument("--id", required=True, help="Conversation ID (unique key)")
    parser.add_argument("--title", required=True, help="Conversation title")
    parser.add_argument("--date", required=True, help="Date (YYYY-MM-DD)")
    parser.add_argument("--file", required=True, help="Relative path to conversation file")
    parser.add_argument("--agent", required=True, help="Agent name (analyst, main, etc.)")
    parser.add_argument("--domain", required=True, help="Domain (finance, language, etc.)")
    parser.add_argument("--session-type", required=True, help="Session type (learn, ask, review)")
    parser.add_argument("--turns", type=int, required=True, help="Number of turns in conversation")
    parser.add_argument("--rems", type=int, default=0, help="Number of Rems extracted")
    parser.add_argument("--index-file", type=str, default="chats/index.json", help="Path to index file")

    args = parser.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"❌ Error: Invalid date format '{args.date}' (expected YYYY-MM-DD)")
        sys.exit(1)

    # Update index
    try:
        success = update_index(
            conversation_id=args.id,
            title=args.title,
            date=args.date,
            file_path=args.file,
            agent=args.agent,
            domain=args.domain,
            session_type=args.session_type,
            turns=args.turns,
            rems_extracted=args.rems,
            index_file=Path(args.index_file)
        )

        if success:
            print(f"✅ Updated conversation index: {args.index_file}")
            print(f"   ID: {args.id}")
            print(f"   Title: {args.title}")
            print(f"   Domain: {args.domain} | Agent: {args.agent}")
            print(f"   Turns: {args.turns} | Rems: {args.rems}")
            sys.exit(0)
        else:
            print(f"❌ Failed to update index")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
