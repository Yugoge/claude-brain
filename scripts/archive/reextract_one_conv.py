#!/usr/bin/env python3
"""
Re-extract a single conversation using BUG 4-fixed chat_archiver.
Usage: python3 reextract_one_conv.py <conv_id>
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

def find_best_session(date_str: str, title: str) -> str:
    """Find the best matching JSONL session for a conversation."""

    target_date = datetime.strptime(date_str, '%Y-%m-%d')
    project_dir = Path.home() / '.claude/projects/-root-knowledge-system'

    # Extract keywords from title (first few significant words)
    keywords = [w.lower() for w in title.split()[:5] if len(w) > 3]

    best_session = None
    best_score = 0

    # Search sessions modified within 7 days of target date
    for session in project_dir.glob('*.jsonl'):
        session_time = datetime.fromtimestamp(session.stat().st_mtime)
        days_diff = abs((target_date - session_time).days)

        if days_diff <= 7:
            # Count keyword matches in session
            try:
                with open(session, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    score = sum(content.count(kw) for kw in keywords)

                    if score > best_score:
                        best_score = score
                        best_session = session
            except:
                continue

    return best_session.stem if best_session else None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 reextract_one_conv.py <conv_id>")
        sys.exit(1)

    conv_id = sys.argv[1]

    # Load conversation metadata from index.json
    index_path = Path('chats/index.json')
    with open(index_path) as f:
        index = json.load(f)

    if conv_id not in index['conversations']:
        print(f"❌ Conversation ID not found: {conv_id}")
        sys.exit(1)

    conv_data = index['conversations'][conv_id]
    title = conv_data['title']
    date = conv_data['date']
    target_file = Path(conv_data['file'])

    print(f"📖 Re-extracting: {title[:60]}")
    print(f"   Date: {date}")
    print(f"   Target: {target_file.name}")
    print()

    # Find best matching session
    print(f"🔍 Searching sessions around {date}...")
    session_id = find_best_session(date, title)

    if not session_id:
        print("❌ No matching session found")
        sys.exit(1)

    print(f"✅ Found session: {session_id}")
    print()

    # Run chat_archiver to extract (full session)
    cmd = [
        'python3',
        'scripts/services/chat_archiver.py',
        '--session-id', session_id
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        print(f"❌ Extraction failed:")
        print(result.stderr)
        sys.exit(1)

    # Find the extracted file (most recent)
    chats_dir = Path('chats')
    md_files = sorted(chats_dir.glob('2025-*/*.md'), key=lambda p: p.stat().st_mtime, reverse=True)

    if not md_files:
        print("❌ No file created by extraction")
        sys.exit(1)

    extracted_file = md_files[0]

    # Move to target location
    target_file.parent.mkdir(parents=True, exist_ok=True)
    extracted_file.replace(target_file)

    print(f"✅ Extracted to: {target_file}")

    return 0

if __name__ == '__main__':
    sys.exit(main())
