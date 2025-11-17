#!/usr/bin/env python3
"""
Batch re-extract all 15 conversations from index.json using fixed chat_archiver.

This script:
1. Reads the official conversation list from chats/index.json
2. Searches for each conversation in JSONL session files
3. Extracts with the fixed chat_archiver (BUG 4 fix applied)
4. Renames output to match index.json paths exactly
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import subprocess
import shutil

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

def find_session_for_conversation(date: str, title_keywords: list) -> tuple:
    """
    Find the JSONL session file containing a conversation.

    Returns: (session_file, first_user_message, last_user_message) or None
    """
    project_dir = Path.home() / '.claude/projects/-root-knowledge-system'

    # Convert date to datetime for comparison
    target_date = datetime.strptime(date, '%Y-%m-%d').date()

    # Search sessions modified around that date (±2 days)
    candidate_sessions = []
    for session in project_dir.glob('*.jsonl'):
        mtime = datetime.fromtimestamp(session.stat().st_mtime).date()
        days_diff = abs((mtime - target_date).days)
        if days_diff <= 7:  # Within a week
            candidate_sessions.append(session)

    print(f'  🔍 Searching {len(candidate_sessions)} sessions for {date}...')

    # Search for keywords in each session
    for session in candidate_sessions:
        try:
            with open(session, 'r', encoding='utf-8') as f:
                content = f.read()
                # Check if all keywords present
                if all(keyword.lower() in content.lower() for keyword in title_keywords[:2]):
                    print(f'  ✅ Found in: {session.name}')

                    # Extract first and last user messages
                    first_msg, last_msg = extract_boundary_messages(session, content)
                    return (session, first_msg, last_msg)
        except Exception as e:
            continue

    print(f'  ❌ Not found')
    return None

def extract_boundary_messages(session_path: Path, content: str) -> tuple:
    """Extract first and last user messages from session content."""
    import json

    user_messages = []

    with open(session_path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if event.get('type') == 'user' and not event.get('isMeta'):
                    msg_content = event['message'].get('content', '')
                    # Extract text (simple version)
                    if isinstance(msg_content, str):
                        text = msg_content
                    elif isinstance(msg_content, list):
                        text_parts = []
                        for item in msg_content:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                text_parts.append(item.get('text', ''))
                        text = ' '.join(text_parts)
                    else:
                        text = str(msg_content)

                    # Clean and truncate
                    text = text.strip()[:200]
                    if text and not text.startswith('[{'):  # Skip tool_result format
                        user_messages.append(text)
            except:
                continue

    if len(user_messages) >= 2:
        return (user_messages[0], user_messages[-1])
    elif len(user_messages) == 1:
        return (user_messages[0], user_messages[0])
    else:
        return ('', '')

def extract_conversation(session_id: str, first_msg: str, last_msg: str, expected_path: Path):
    """Run chat_archiver to extract conversation."""

    cmd = [
        'python3',
        '/root/knowledge-system/scripts/services/chat_archiver.py',
        '--session-id', session_id,
        '--first-message', first_msg,
        '--last-message', last_msg
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode == 0:
        # Find the extracted file (chat_archiver creates with timestamp)
        chats_dir = Path('/root/knowledge-system/chats')

        # The most recently created .md file
        md_files = sorted(chats_dir.glob('2025-*/*.md'), key=lambda p: p.stat().st_mtime, reverse=True)

        if md_files:
            extracted_file = md_files[0]

            # Rename to expected path
            expected_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(extracted_file), str(expected_path))

            print(f'  ✅ Extracted: {expected_path.name}')
            return True
        else:
            print(f'  ⚠️  Extraction produced no file')
            return False
    else:
        print(f'  ❌ Extraction failed: {result.stderr[:200]}')
        return False

def main():
    # Load index.json
    index_path = Path('/root/knowledge-system/chats/index.json')
    with open(index_path) as f:
        index = json.load(f)

    conversations = index['conversations']
    total = len(conversations)

    print(f'📚 Batch Re-extraction of {total} Conversations')
    print(f'=' * 60)
    print()

    success_count = 0
    failed = []

    for i, (conv_id, conv_data) in enumerate(conversations.items(), 1):
        title = conv_data['title']
        date = conv_data['date']
        file_path = Path('/root/knowledge-system') / conv_data['file']

        print(f'\n[{i}/{total}] {title[:60]}')
        print(f'  Date: {date}')

        # Extract keywords from title
        keywords = [word for word in title.split() if len(word) > 3][:3]

        # Find session
        result = find_session_for_conversation(date, keywords)

        if result:
            session_file, first_msg, last_msg = result
            session_id = session_file.stem

            # Extract conversation
            if extract_conversation(session_id, first_msg, last_msg, file_path):
                success_count += 1
            else:
                failed.append(conv_id)
        else:
            failed.append(conv_id)

    print()
    print('=' * 60)
    print(f'✅ Successfully extracted: {success_count}/{total}')

    if failed:
        print(f'❌ Failed: {len(failed)}')
        print(f'   {", ".join(failed)}')
    else:
        print('🎉 All conversations extracted successfully!')

    return 0 if not failed else 1

if __name__ == '__main__':
    sys.exit(main())
