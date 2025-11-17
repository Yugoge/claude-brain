#!/usr/bin/env python3
"""
Batch Conversation Extractor
Intelligently extracts Claude Code conversations by matching first/last user messages
from manual conversation files.

Uses "save" keyword as a strong delimiter for conversation boundaries.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from datetime import datetime

# Paths
CHATS_DIR = Path("/root/knowledge-system/chats")
MATCHED_DIR = CHATS_DIR / "matched-originals"
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects" / "-root-knowledge-system"


def extract_user_messages_from_manual(md_file: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract first and last User messages from PURE conversation part of manual file.
    Excludes post-archival content like "## Extracted Concepts".

    Returns:
        (first_message, last_message) or (None, None) if not found
    """
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract ONLY the conversation section, BEFORE "## Extracted Concepts" or "## Concepts Extracted"
    # This is critical to avoid matching archival metadata
    conversation_start = re.search(r'## (?:Full )?Conversation\s*\n', content)
    conversation_end = re.search(r'##\s*(?:Extracted )?Concepts?(?:\s+Extracted)?', content)

    if conversation_start:
        start_pos = conversation_start.end()
        end_pos = conversation_end.start() if conversation_end else len(content)
        conversation_content = content[start_pos:end_pos]
    else:
        # Fallback: try to find conversation without section headers
        conversation_content = content

    # Find all User message sections (### User followed by content until next ### header)
    user_sections = re.findall(r'### User\s*\n+(.*?)(?=\n### (?:Assistant|User)|$)', conversation_content, re.DOTALL)

    if not user_sections:
        return None, None

    # Clean up messages (remove extra whitespace, but keep content)
    user_messages = [msg.strip() for msg in user_sections if msg.strip()]

    if not user_messages:
        return None, None

    first_msg = user_messages[0]
    last_msg = user_messages[-1]

    return first_msg, last_msg


def find_save_delimiter(messages: List[str]) -> Optional[str]:
    """
    Find a message containing 'save' keyword as a strong delimiter.

    Prioritizes messages with just "save" or "继续" as they mark conversation boundaries.
    """
    for msg in messages:
        msg_lower = msg.lower().strip()
        # Look for save-related keywords
        if msg_lower in ['save', '保存', '继续', 'continue']:
            return msg
        if 'save' in msg_lower and len(msg) < 50:  # Short messages with "save"
            return msg
    return None


def search_message_in_jsonl(jsonl_file: Path, search_text: str, max_chars: int = 80) -> List[int]:
    """
    Search for a message in a JSONL file using grep for speed.

    Args:
        jsonl_file: Path to JSONL file
        search_text: Text to search for
        max_chars: Maximum characters to use for matching (default: 80)

    Returns:
        List of line numbers (1-indexed) where the message appears
    """
    import subprocess

    # Prepare search pattern (use first max_chars, take first few meaningful words)
    search_pattern = search_text[:max_chars].strip()

    # Extract key words (Chinese and English) for grep search
    # Take first 3-5 words or first 30 chars, whichever is shorter
    words = search_pattern.split()[:5]
    if words:
        grep_pattern = ' '.join(words)[:30]
    else:
        grep_pattern = search_pattern[:30]

    matching_lines = []

    try:
        # Use grep to quickly find candidate lines
        result = subprocess.run(
            ['grep', '-n', grep_pattern, str(jsonl_file)],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Parse grep output (format: "line_number:content")
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    line_num_str = line.split(':', 1)[0]
                    try:
                        matching_lines.append(int(line_num_str))
                    except ValueError:
                        pass

    except subprocess.TimeoutExpired:
        print(f"    Warning: grep timeout for {jsonl_file.name}")
    except Exception as e:
        pass  # Silently skip errors

    return matching_lines


def extract_text_from_content(content) -> str:
    """Extract text from various content formats"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                # Handle tool_result format
                if item.get('type') == 'tool_result':
                    result_content = item.get('content', '')
                    # Recursively extract if content is nested
                    if isinstance(result_content, (list, dict)):
                        text_parts.append(extract_text_from_content(result_content))
                    else:
                        text_parts.append(str(result_content))
                # Handle text format
                elif item.get('type') == 'text':
                    text_parts.append(str(item.get('text', '')))
                elif 'text' in item:
                    text_parts.append(str(item['text']))
            elif isinstance(item, str):
                text_parts.append(item)
        # Filter out empty strings and join
        return '\n'.join(part for part in text_parts if part)
    elif isinstance(content, dict):
        if 'text' in content:
            return str(content['text'])
        elif 'content' in content:
            return extract_text_from_content(content['content'])
    return ""


def find_session_for_conversation(first_msg: str, last_msg: str) -> Optional[Tuple[str, int, int]]:
    """
    Find the session ID and line range for a conversation.

    Args:
        first_msg: First user message
        last_msg: Last user message

    Returns:
        (session_id, first_line, last_line) or None if not found
    """
    all_jsonl_files = list(CLAUDE_PROJECTS_DIR.glob("*.jsonl"))

    # Search for sessions containing both messages
    candidates = []

    for jsonl_file in all_jsonl_files:
        session_id = jsonl_file.stem

        # Search for first message
        first_lines = search_message_in_jsonl(jsonl_file, first_msg, max_chars=100)

        if not first_lines:
            continue

        # Search for last message
        last_lines = search_message_in_jsonl(jsonl_file, last_msg, max_chars=100)

        if not last_lines:
            continue

        # Check if last message appears after first message
        for first_line in first_lines:
            for last_line in last_lines:
                if last_line >= first_line:
                    candidates.append((session_id, first_line, last_line, jsonl_file))

    if not candidates:
        return None

    # If multiple candidates, choose the one with the smallest range
    # (most likely to be the correct conversation)
    candidates.sort(key=lambda x: x[2] - x[1])

    session_id, first_line, last_line, jsonl_file = candidates[0]

    # Get file modification date for verification
    file_date = datetime.fromtimestamp(jsonl_file.stat().st_mtime).strftime('%Y-%m-%d')

    return session_id, first_line, last_line


def extract_conversation(manual_file: Path, session_id: str, first_msg: str, last_msg: str) -> bool:
    """
    Extract a conversation using chat_archiver.py with range parameters.

    Returns:
        True if extraction succeeded, False otherwise
    """
    # Prepare search strings (use first 80 chars for matching)
    first_search = first_msg[:80].strip()
    last_search = last_msg[:80].strip()

    # Call chat_archiver.py
    try:
        result = subprocess.run([
            'python3', 'scripts/services/chat_archiver.py',
            '--session-id', session_id,
            '--first-message', first_search,
            '--last-message', last_search
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Check output for success
            if "✅ Saved:" in result.stdout:
                return True

        # Print error for debugging
        print(f"    ⚠️  Extraction failed for {manual_file.name}")
        print(f"       stdout: {result.stdout[:200]}")
        if result.stderr:
            print(f"       stderr: {result.stderr[:200]}")

        return False

    except subprocess.TimeoutExpired:
        print(f"    ❌ Timeout extracting {manual_file.name}")
        return False
    except Exception as e:
        print(f"    ❌ Error extracting {manual_file.name}: {e}")
        return False


def batch_extract_all_conversations():
    """
    Main function: Extract conversations using session mapping from previous agent.
    """
    print("=" * 80)
    print("Batch Conversation Extraction (Using Session Mapping)")
    print("=" * 80)
    print()

    # Read session mapping from previous agent
    mapping_file = Path("/tmp/session_mapping_correct.txt")

    if not mapping_file.exists():
        print("❌ Session mapping file not found at /tmp/session_mapping_correct.txt")
        print("   Previous agent should have created this file.")
        return None, None

    # Parse mapping: filename -> session_id
    session_mapping = {}
    with open(mapping_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or '|' not in line:
                continue
            filename, session_id = line.split('|', 1)
            session_mapping[filename] = session_id

    print(f"📁 Found {len(session_mapping)} conversations in session mapping")
    print()

    # Statistics
    stats = {
        'total': len(session_mapping),
        'success': 0,
        'not_found': 0,
        'failed': 0,
        'no_messages': 0
    }

    results = []

    # Process each mapped conversation
    for idx, (filename, session_id) in enumerate(session_mapping.items(), 1):
        print(f"[{idx}/{len(session_mapping)}] {filename}")
        print(f"    Session: {session_id}")

        # Find the manual file
        manual_file = None
        for month_dir in CHATS_DIR.glob("2025-*"):
            candidate = month_dir / filename
            if candidate.exists():
                manual_file = candidate
                break

        if not manual_file:
            print(f"    ⚠️  Manual file not found in chats/")
            stats['not_found'] += 1
            results.append({
                'file': filename,
                'status': 'not_found',
                'session': session_id
            })
            print()
            continue

        # Extract first and last messages from PURE conversation part
        first_msg, last_msg = extract_user_messages_from_manual(manual_file)

        if not first_msg or not last_msg:
            print(f"    ⚠️  Could not extract user messages")
            stats['no_messages'] += 1
            results.append({
                'file': filename,
                'status': 'no_messages',
                'session': session_id
            })
            print()
            continue

        print(f"    First: {first_msg[:60]}...")
        print(f"    Last:  {last_msg[:60]}...")

        # Extract conversation using the mapped session_id
        success = extract_conversation(manual_file, session_id, first_msg, last_msg)

        if success:
            print(f"    ✅ Extracted successfully")
            stats['success'] += 1
            results.append({
                'file': filename,
                'status': 'success',
                'session': session_id
            })
        else:
            print(f"    ❌ Extraction failed")
            stats['failed'] += 1
            results.append({
                'file': filename,
                'status': 'failed',
                'session': session_id
            })

        print()

    # Print summary
    print("=" * 80)
    print("Extraction Summary")
    print("=" * 80)
    print(f"Total conversations:        {stats['total']}")
    print(f"✅ Successfully extracted:  {stats['success']}")
    print(f"❌ Not found in JSONL:      {stats['not_found']}")
    print(f"❌ Extraction failed:       {stats['failed']}")
    print(f"⚠️  No messages extracted:  {stats['no_messages']}")
    print()

    # Print details for not found conversations
    if stats['not_found'] > 0:
        print("=" * 80)
        print("Conversations NOT FOUND in Claude Code JSONL:")
        print("=" * 80)
        for result in results:
            if result['status'] == 'not_found':
                print(f"\n📄 {result['file']}")
                print(f"   First message: {result['first_msg']}")
                print(f"   Last message:  {result['last_msg']}")
        print()

    # Save results to JSON
    results_file = CHATS_DIR / "extraction_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'statistics': stats,
            'results': results
        }, f, indent=2, ensure_ascii=False)

    print(f"📊 Results saved to: {results_file}")
    print()

    return stats, results


if __name__ == "__main__":
    batch_extract_all_conversations()
