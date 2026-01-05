#!/usr/bin/env python3
"""
Chat Archiver - Claude Code Conversation Extraction Service
Extracts conversations from Claude Code's native JSONL storage for /save command.

Features:
- Direct extraction from ~/.claude/projects/
- Project-specific filtering (only knowledge-system conversations)
- Rich metadata extraction (tokens, costs, models)
- /save-compatible frontmatter format
- Filters prompts, keeps only User/Assistant dialogue

🔧 BUG FIXES (2025-11-07 & 2025-11-08):
========================================
BUG 8 (P0): Imprecise First-Message Matching (Greedy Strategy) - CRITICAL
  - Problem: Substring matching too loose + greedy first-match strategy
    * Common words match many conversations, stops at first match (wrong one)
    * No scoring mechanism to find BEST match
    * Common words matched wrong sessions (2 messages) instead of intended (242 messages)
  - Impact: Historical conversations (french-1453) consistently matched wrong sessions
  - Root Cause: parse_conversation() uses "pattern in content" which matches any occurrence
  - Fix: Implemented intelligent match scoring system:
    * Exact match: 100 points
    * Prefix match: 80 points
    * Fuzzy match (>90% similarity): 60-80 points
    * Substring match: 40 points
    * Date proximity bonus: +20 points (same day), +10 (within 1 day), +5 (within 3 days)
    * Evaluates ALL candidates, returns highest score (minimum threshold: 40)
  - Usage: python chat_archiver.py --first-message "..." --last-message "..." --oldest-first
    * Automatically scores all matching conversations
    * Shows top 3 candidates with scores
    * Selects best match instead of first match
  - Benefit: Robust matching even with ambiguous search terms

BUG 9 (P1): No Date Range Filtering
  - Problem: Cannot narrow search to specific date ranges
  - Impact: Increased false positives when common phrases used across many dates
  - Fix: Added --date-from and --date-to parameters
  - Usage: python chat_archiver.py --first-message "..." --date-from "2025-10-29" --date-to "2025-10-31"
  - Benefit: Combined with scoring system, provides precise historical extraction

BUG 7 (P1): Intelligent Tiered Matching Strategy - ENHANCED BY BUG 13
  - Problem: When sessions are split/reorganized (Happy remote operation), exact first+last
    match may fail, requiring manual fallback to first-message-only
  - Impact: Required manual debugging and multiple extraction attempts
  - Fix: Automatic tiered matching with intelligent fallback:
    * Tier 1: first+last message match (most precise, tries first)
    * Tier 2: first-message-only (auto-fallback when Tier 1 fails)
  - Usage: python chat_archiver.py --first-message "..." --last-message "..." --oldest-first
    * If both messages provided: tries Tier 1, auto-falls-back to Tier 2 if needed
    * If only first-message: directly uses Tier 2
  - Benefit: No manual intervention needed, handles split sessions automatically
  - Status: SUPERSEDED by BUG 13 (now 5 tiers instead of 2)

BUG 6 (P1): Newest Conversations Override Historical Matches
  - Problem: When searching with first/last-message, newest conversations were prioritized
  - Impact: Historical conversations (e.g., french-1453 from 2025-10-30) were skipped if
    recent conversations (2025-11-07+) also contained matching text
  - Fix: Added --oldest-first flag to prioritize historical data during extraction
  - Usage: python chat_archiver.py --first-message "..." --last-message "..." --oldest-first

========================================
BUG 1 (P1): Incorrect Subagent Label Mapping
  - Problem: Non-classification-expert outputs were incorrectly labeled
  - Fix: Added strict JSON schema validation (validate_classification_expert_json)
  - Impact: Now validates required fields (domain, confidence, isced, dewey, message)

BUG 2 (P2): Unfiltered Tool Error Outputs
  - Problem: Bash errors (command not found, etc.) appeared in archives
  - Fix: Enhanced is_tool_result_content() with comprehensive error patterns
  - Impact: Filters 20+ error patterns including bash, python, npm, git errors

BUG 11 (P0): User-Subagent Dialogue Over-Filtering - CRITICAL [FIXED 2025-11-08]
  - Problem: BUG 3 fix was too aggressive - filtered ALL depth>0 user messages
  - Impact: Lost valuable Socratic dialogues (e.g., user ↔ language-tutor 42-turn sessions)
    * french-1453 learning: Only 10 messages extracted instead of 42 turns
    * User responses to subagent teaching were all filtered out
  - Root Cause: depth > 0 filter removed both nested calls AND direct user-subagent interaction
  - Fix: Changed filter from depth > 0 to depth >= 3
    * Now KEEPS depth=0 (main conversation)
    * Now KEEPS depth=1 (direct subagent invocation)
    * Now KEEPS depth=2 (user ↔ subagent Socratic dialogue - the conversation itself!)
    * Only FILTERS depth>=3 (truly nested subagent calls, subagent→subagent)
  - Usage: No parameter change needed - automatically includes user-subagent dialogues
  - Benefit: Complete learning sessions preserved (340 dialogue messages + 9 invocation messages)

BUG 12 (P0): Depth Calculation Broken - All Subagent Messages Depth=0 - CRITICAL [FIXED 2025-11-08]
  - Problem: Depth calculation relied on unreliable `isSidechain` flag, causing all subagent messages to be depth=0
  - Impact: 349 language-tutor messages in french-1453 all marked depth=0 (should be depth=1/2)
    * Depth distribution was 404 depth=0, 0 depth=1, 0 depth=2 (completely broken)
    * BUG 11 filter couldn't work because there were no depth>0 messages to filter
  - Root Cause: Only 2 messages in 404-message conversation had isSidechain=true (99.5% false negative rate)
    * language-tutor messages are isSidechain=false but correctly detected via content parsing
    * Old logic: depth calculation used isSidechain → broken depth values
  - Fix: Two-part fix:
    * Part 1 - Reordered logic: subagent_name propagation BEFORE depth calculation (lines 640-726)
    * Part 2 - New depth calculation based on subagent_name, NOT isSidechain:
      - Depth 0: No subagent_name (main conversation)
      - Depth 1: Has subagent_name, parent has NO subagent_name (direct invocation)
      - Depth 2: Has subagent_name, parent also has subagent_name (Socratic dialogue)
      - Depth 3+: Would be nested subagent calls (subagent calling another subagent)
  - Test Results (session b78c0a9f...):
    * Before fix: 404 depth=0, 0 depth=1, 0 depth=2
    * After fix: 55 depth=0, 9 depth=1, 340 depth=2 ✅
    * depth=2 messages are the Socratic dialogue (151 user + 189 language-tutor)
  - Usage: No parameter change needed - depth calculation now works correctly
  - Benefit: Accurate depth tracking enables proper filtering of nested calls while preserving dialogues

BUG 13 (P0): No Tiered Fallback for Repeated First/Last Patterns - CRITICAL [FIXED 2025-11-08]
  - Problem: When same first/last messages appear across 10+ days, no systematic fallback strategy
  - Impact: Extraction fails when:
    * Sessions are split/reorganized by Happy's remote operations
    * Same conversation pattern repeats across multiple dates
    * Last message is in a different session than first message
  - Root Cause: Only 2 tiers existed (first+last, first-only), no date-aware fallback
  - Fix: Implemented comprehensive 5-tier matching strategy with intelligent fallbacks:
    * Tier 0: --session-id <UUID> (most precise, bypasses all search)
    * Tier 1: first+last+date (precise extraction with date constraints)
    * Tier 2: first+last (no date - handles split sessions across dates)
    * Tier 3: first+date (last might be split to different session)
    * Tier 4: first+oldest (insurance mode for 10-day repeated patterns)
  - Usage examples:
    * Tier 0: python chat_archiver.py --session-id abc123
    * Tier 1: python chat_archiver.py --first-message "continue" --last-message "done" --date-from 2025-10-30 --date-to 2025-10-31
    * Tier 2: Auto-fallback when Tier 1 finds no date match
    * Tier 3: Auto-fallback when last message not found in date range (split sessions)
    * Tier 4: Auto-fallback when all else fails, finds oldest matching first message
  - Benefit: Robust extraction handles all edge cases (split sessions, repeated patterns, remote reorganization)
  - Test Scenario: 10-day period with repeated first messages - Tier 4 correctly extracts oldest match

BUG 10 (P1): Command-Args Content Filtering
  - Problem: <command-args> tags were completely filtered out, losing user input in slash commands
  - Impact: Slash command arguments like "/learn [topic]" had the argument removed
  - Fix: Modified filter_user_content() to EXTRACT <command-args> content instead of removing it
  - Status: ALREADY FIXED in previous version (lines 717-726)

BUG 3 (P0): Subagent Internal Dialogue Leakage - SUPERSEDED BY BUG 11
  - Problem: User/Assistant exchanges within subagent trees leaked to main dialogue
  - Fix: Added depth tracking to build_conversation_threads()
  - Impact: Filters messages based on depth:
    * Depth 0: Main conversation (always included)
    * Depth 1: Direct subagent responses (included if include_subagents=True)
    * Depth 1 User messages: NOW INCLUDED (BUG 11 fix) - user responses to subagent
    * Depth 2+: Nested subagent calls (excluded)

BUG 4 (P0): Tool Result Content Leaking into User Messages - CRITICAL
  - Problem: User messages contained file content from Read tool, bash output, etc.
  - Root Cause: extract_text_from_content() was extracting tool_result content
  - Fix: Skip tool_result items entirely in extract_text_from_content()
  - Impact: User messages now only contain actual user input, not tool outputs

BUG 5 (P1): User Option Selections Misclassified as Subagent Messages
  - Problem: When assistant provides <options> tags and user selects one, the user's
    selection was incorrectly marked as coming from a subagent (e.g., analyst)
  - Root Cause: Subagent attribution was inherited from parent threads without
    checking if the user message was an option selection
  - Fix: Added extract_options_from_content() and option matching in build_conversation_threads()
  - Impact: User messages that exactly match provided options are correctly attributed
    to the user, not to subagents

VALIDATION:
  - Added validate_archived_conversation() to check quality after archiving
  - Automatically detects all three bug patterns in output
  - Reports stats: depth distribution, subagent attribution

Usage:
    # Called by /save command (extracts most recent conversation)
    python scripts/services/chat_archiver.py

    # Manual extraction of specific session
    python scripts/services/chat_archiver.py --session-id <UUID>
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
CHATS_DIR = PROJECT_ROOT / "chats"
CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Auto-detect project encoded name from absolute path
# Claude Code encodes project paths by replacing / with - and removing leading /
# Example: /home/user/knowledge-system -> -home-user-knowledge-system
def get_project_encoded_name() -> str:
    """
    Automatically detect Claude Code's encoded project name from current project path.

    Claude Code encoding rules:
    - Remove leading /
    - Replace all / with -

    Examples:
        /home/user/knowledge-system -> -home-user-knowledge-system
        /root/knowledge-system -> -root-knowledge-system
        /Users/alice/projects/kb -> -Users-alice-projects-kb
    """
    absolute_path = PROJECT_ROOT.resolve()
    # Remove leading / and replace all / with -
    encoded = str(absolute_path).lstrip('/').replace('/', '-')
    return f"-{encoded}"

PROJECT_ENCODED_NAME = get_project_encoded_name()


def extract_text_from_content(content) -> str:
    """
    Extract text from Claude message content (handles multiple formats).

    🔧 BUG 4 FIX: Skip tool_result items entirely - they contain tool outputs
    (file content, command results, etc.) which should NOT appear in user messages.
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                # 🔧 BUG 4 FIX: SKIP tool_result entirely
                # tool_result contains tool outputs (Read file content, Bash output, etc.)
                # These should NEVER appear in user/assistant dialogue
                if item.get('type') == 'tool_result':
                    continue  # Skip this item completely
                # Handle regular text format
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


def filter_assistant_content(content) -> str:
    """
    Filter assistant content to remove tool-use blocks and system-reminders.
    Keep only the actual dialogue text.
    """
    if isinstance(content, str):
        # Simple string content - remove tags
        text = content
        text = re.sub(r'<system-reminder>.*?</system-reminder>', '', text, flags=re.DOTALL)
        text = re.sub(r'<SILENT_CONSULTATION_MODE>.*?</SILENT_CONSULTATION_MODE>', '', text, flags=re.DOTALL)
        # Remove standalone tags
        text = re.sub(r'^\s*<SILENT_CONSULTATION_MODE>\s*$', '', text, flags=re.MULTILINE)
        return text.strip()

    elif isinstance(content, list):
        filtered_parts = []
        for item in content:
            if isinstance(item, dict):
                item_type = item.get('type')

                # Keep only text blocks, skip tool_use
                if item_type == 'text':
                    text = item.get('text', '')
                    # Remove <system-reminder> tags and content
                    text = re.sub(r'<system-reminder>.*?</system-reminder>', '', text, flags=re.DOTALL)
                    # Remove SILENT_CONSULTATION_MODE tags
                    text = re.sub(r'<SILENT_CONSULTATION_MODE>.*?</SILENT_CONSULTATION_MODE>', '', text, flags=re.DOTALL)
                    text = re.sub(r'^\s*<SILENT_CONSULTATION_MODE>\s*$', '', text, flags=re.MULTILINE)
                    if text.strip():
                        filtered_parts.append(text)
                # Skip tool_use blocks entirely
                elif item_type == 'tool_use':
                    continue

        return '\n'.join(filtered_parts)

    elif isinstance(content, dict):
        # Single dict content
        if 'text' in content:
            text = content['text']
            text = re.sub(r'<system-reminder>.*?</system-reminder>', '', text, flags=re.DOTALL)
            text = re.sub(r'<SILENT_CONSULTATION_MODE>.*?</SILENT_CONSULTATION_MODE>', '', text, flags=re.DOTALL)
            text = re.sub(r'^\s*<SILENT_CONSULTATION_MODE>\s*$', '', text, flags=re.MULTILINE)
            return text.strip()
        elif 'content' in content:
            return filter_assistant_content(content['content'])

    return ""


def is_tool_result_content(content: str) -> bool:
    """
    Detect if content is a tool result (should not be included in conversation archive).

    Tool results are typically:
    - JSON objects with tool-specific schemas
    - Error messages from tool execution (Bash errors, command not found, etc.)
    - File system responses
    - PDF extraction results

    Returns:
        True if content appears to be a tool result, False otherwise
    """
    if not content or not content.strip():
        return False

    content_stripped = content.strip()

    # Pattern 1: JSON tool results
    if content_stripped.startswith('{') and content_stripped.endswith('}'):
        try:
            data = json.loads(content_stripped)
            # Common tool result fields
            if any(key in data for key in ['type', 'success', 'error', 'result',
                                           'pages_extracted', 'temp_file', 'file_size_mb']):
                return True
        except json.JSONDecodeError:
            pass

    # Pattern 2: Tool use errors
    if '<tool_use_error>' in content_stripped:
        return True

    # Pattern 3: File read notifications
    if re.match(r'^PDF file read: .+\.pdf \(\d+\.?\d*[KM]B\)$', content_stripped):
        return True

    # Pattern 4: Common tool result patterns
    tool_result_patterns = [
        r'^File does not exist\.$',
        r'^No files found$',
        r'^Directory created: ',
        r'^File written: ',
        r'^Command executed: ',
    ]

    for pattern in tool_result_patterns:
        if re.match(pattern, content_stripped):
            return True

    # 🔧 BUG 2 FIX: Comprehensive Bash/tool error filtering
    # These patterns catch command errors that shouldn't appear in archives
    error_patterns = [
        r'/bin/bash: line \d+:.*command not found',  # Command not found
        r'/bin/bash:.*No such file or directory',     # File not found
        r'bash:.*command not found',                  # Alternative bash error format
        r'python: command not found',                 # Python not found
        r'python3: command not found',                # Python3 not found
        r'npm: command not found',                    # NPM not found
        r'node: command not found',                   # Node not found
        r'git: command not found',                    # Git not found
        r'error: command .*not found',                # Generic command not found
        r'ERROR:.*',                                  # Generic ERROR prefix
        r'Error:.*',                                  # Generic Error prefix
        r'.*: No such file or directory',             # File not found (any command)
        r'.*: permission denied',                     # Permission errors
        r'.*: cannot access.*',                       # Access errors
        r'usage: .*',                                 # Usage messages (help text)
        r'^ls: cannot access',                        # ls errors
        r'^cat: .*: No such file',                    # cat errors
        r'^grep: .*: No such file',                   # grep errors
        r'^find: .*: No such file',                   # find errors
        r'Traceback \(most recent call last\):',     # Python tracebacks
        r'^\s*File ".*", line \d+',                   # Python traceback lines
        r'^\s*\w+Error: .*',                          # Python exception lines
    ]

    for pattern in error_patterns:
        if re.search(pattern, content_stripped, re.MULTILINE | re.IGNORECASE):
            return True

    return False


def validate_classification_expert_json(data: dict) -> bool:
    """
    �� BUG 1 FIX: Strict validation for classification-expert JSON output.

    classification-expert returns JSON with this EXACT schema:
    {
        "domain": str,           # Primary domain name
        "confidence": str,       # "high", "medium", or "low"
        "isced": {...},         # UNESCO ISCED classification
        "dewey": {...},         # Dewey Decimal classification
        "message": str          # Explanation message
    }

    Returns:
        True if this is valid classification-expert output
    """
    # Required top-level keys
    required_keys = {'domain', 'confidence', 'isced', 'dewey', 'message'}
    if not all(key in data for key in required_keys):
        return False

    # Validate data types
    if not isinstance(data['domain'], str):
        return False
    if not isinstance(data['message'], str):
        return False

    # Confidence must be one of: high, medium, low
    if data['confidence'] not in ['high', 'medium', 'low']:
        return False

    # isced must be a dict with required fields
    if not isinstance(data['isced'], dict):
        return False
    isced_required = {'code', 'name', 'broad_field', 'narrow_field'}
    if not all(key in data['isced'] for key in isced_required):
        return False

    # dewey must be a dict with required fields
    if not isinstance(data['dewey'], dict):
        return False
    dewey_required = {'code', 'name', 'division', 'section'}
    if not all(key in data['dewey'] for key in dewey_required):
        return False

    return True


def extract_options_from_content(content) -> List[str]:
    """
    🔧 BUG 5 FIX: Extract option choices from assistant messages with <options> tags.

    When assistant provides options using XML tags like:
    <options>
    <option>Yes, I'm familiar with options</option>
    <option>I have some basic knowledge</option>
    </options>

    This function extracts the option text to help identify user selections.

    Returns:
        List of option texts (cleaned, without XML tags)
    """
    options = []

    # Extract text content first
    text = extract_text_from_content(content)

    if not text or '<options>' not in text:
        return options

    # Extract options using regex
    # Match content between <options>...</options>
    options_match = re.search(r'<options>(.*?)</options>', text, re.DOTALL)
    if options_match:
        options_block = options_match.group(1)

        # Extract individual <option> entries
        option_matches = re.findall(r'<option>(.*?)</option>', options_block, re.DOTALL)
        for opt_text in option_matches:
            # Clean up the text
            cleaned = opt_text.strip()
            if cleaned:
                options.append(cleaned)

    return options


def detect_subagent_name(content: str, is_sidechain: bool = False, role: str = None) -> Optional[str]:
    """
    Detect if content is from a subagent and extract the agent name.

    CRITICAL: Only mark as subagent if it's truly FROM a subagent (sidechain=True).
    User messages containing prompts/agent names should NOT be marked as subagent.

    Detection patterns (STRICT):
    - Sidechain messages with Task tool invocations
    - Sidechain assistant responses with SILENT_CONSULTATION_MODE
    - Explicit "I am the X agent" statements in assistant messages
    - EXCEPTION: Classification JSON from classification-expert (stored as user messages)

    Returns:
        Agent name (e.g., "analyst", "language-tutor") or None if not a subagent
    """
    text = extract_text_from_content(content)

    # ✅ EXCEPTION: Detect classification-expert JSON output (stored as user type)
    # 🔧 BUG 1 FIX: Enhanced validation to prevent false positives
    if role == 'user' and text.strip().startswith('{'):
        try:
            data = json.loads(text.strip())
            # Use strict schema validation
            if validate_classification_expert_json(data):
                return 'classification-expert'
        except (json.JSONDecodeError, TypeError):
            pass

    # ❌ REJECT: User messages are NEVER subagents (even if containing agent names)
    if role == 'user':
        return None

    # ❌ REJECT: System messages (not subagents)
    if 'Todos have been modified successfully' in text:
        return None
    if 'Successfully changed chat title' in text:
        return None

    # ✅ Pattern 1: Sidechain + Task tool invocation (main assistant calling subagent)
    if is_sidechain and role == 'assistant':
        # First check if this is a Task tool invocation (before subagent responds)
        subagent_match = re.search(r'subagent_type["\']?\s*[:=]\s*["\']([a-z-]+)["\']', text)
        if subagent_match:
            return subagent_match.group(1)

        # If no Task tool pattern, continue to check other patterns below
        # DON'T return None here - let other patterns be checked

    # ✅ Pattern 2: SILENT_CONSULTATION_MODE (consultant agent response)
    # Detects consultant agents (language-tutor, finance-tutor, etc.)
    # Only in assistant messages, not user prompts
    if role == 'assistant' and 'SILENT_CONSULTATION_MODE' in text:
        # Look for common agent names in consultation mode
        for agent in ['language-tutor', 'finance-tutor', 'programming-tutor',
                      'book-tutor', 'classification-expert']:
            if agent in text.lower():
                return agent
        # If no specific agent found, don't mark as subagent
        return None

    # ✅ Pattern 3: Consultant agents invoked via Task tool or slash commands
    # These include analyst (/ask), review-master (/review), and other consultants
    # Detect by typical opening phrases in sidechain assistant messages
    if role == 'assistant' and is_sidechain:
        # Analyst patterns
        if any(phrase in text for phrase in [
            "I'll search for", "I'll research", "I'll help you understand",
            "I'll analyze", "Based on my research", "Based on my analysis"
        ]):
            return 'analyst'

        # Review-master patterns
        if any(phrase in text for phrase in [
            "Let's begin your review session", "FSRS review session",
            "Rate your recall"
        ]):
            return 'review-master'

        # Knowledge-indexer patterns
        if "backlinks" in text.lower() and "knowledge graph" in text.lower():
            return 'knowledge-indexer'

    # DISABLED:     # ✅ Pattern 3: Explicit agent statements (only in assistant messages)
    # DISABLED:     if role == 'assistant':
    # DISABLED:         agent_statement = re.search(r'I am the ([a-z-]+) agent', text, re.IGNORECASE)
    # DISABLED:         if agent_statement:
    # DISABLED:             return agent_statement.group(1)

    # ❌ NOT a subagent
    return None


def demote_headings_in_content(content: str, levels: int = 1) -> str:
    """
    Demote all markdown headings by N levels to prevent heading hierarchy conflicts.

    Example: If message role is ### User (H3), then content headings should start at H4.
    # Title → ## Title
    ## Section → ### Section
    ### Subsection → #### Subsection

    Args:
        content: Markdown content
        levels: Number of levels to demote (default: 1)

    Returns:
        Content with demoted headings
    """
    if not content:
        return content

    lines = content.split('\n')
    demoted_lines = []

    for line in lines:
        # Match markdown headings (# at start of line)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            current_hashes = heading_match.group(1)
            heading_text = heading_match.group(2)

            # Add N more hashes (max 6)
            new_level = min(len(current_hashes) + levels, 6)
            new_hashes = '#' * new_level

            demoted_lines.append(f"{new_hashes} {heading_text}")
        else:
            demoted_lines.append(line)

    return '\n'.join(demoted_lines)


def build_conversation_threads(jsonl_file: Path) -> Dict[str, Dict]:
    """
    🔧 BUG 3 FIX: Build conversation thread map with DEPTH TRACKING.
    🔧 BUG 5 FIX: Track options provided by assistant to prevent misclassifying option selections.

    This function now tracks conversation depth to distinguish:
    - Depth 0: Main conversation (User ↔ Assistant)
    - Depth 1+: Subagent threads (sidechains)

    The depth tracking is critical to prevent subagent internal dialogues
    from leaking into the main conversation archive.

    First pass through the conversation to:
    1. Map all UUIDs to their messages
    2. Identify subagent conversation threads (starting from Task tool invocations)
    3. Extract subagent_type from Task tool calls
    4. Track parent-child relationships
    5. 🆕 Calculate conversation depth (0=main, 1+=subagent)
    6. 🆕 Extract options from assistant messages to identify user option selections

    Returns:
        Dict mapping UUID -> {
            'type': 'user' | 'assistant',
            'parent_uuid': str | None,
            'is_sidechain': bool,
            'subagent_name': str | None (detected or inherited from parent),
            'depth': int (0=main conversation, 1+=subagent depth),
            'raw_content': Any,
            'options': List[str] (for assistant messages with <options> tags)
        }
    """
    uuid_map = {}

    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
                event_type = event.get('type')

                if event_type in ['user', 'assistant']:
                    uuid = event['uuid']
                    parent_uuid = event.get('parentUuid')
                    is_sidechain = event.get('isSidechain', False)

                    if event_type == 'user':
                        raw_content = event['message']['content']
                    else:  # assistant
                        raw_content = event['message']['content']

                    # Detect subagent for this message (pass role to prevent misidentification)
                    subagent_name = detect_subagent_name(raw_content, is_sidechain, role=event_type)

                    # ✅ ENHANCED: Extract subagent_type from Task tool invocations
                    # When main assistant calls Task tool, record it for propagation to child messages
                    task_subagent_type = None
                    if event_type == 'assistant' and isinstance(raw_content, list):
                        for item in raw_content:
                            if isinstance(item, dict) and item.get('type') == 'tool_use' and item.get('name') == 'Task':
                                task_input = item.get('input', {})
                                task_subagent_type = task_input.get('subagent_type')
                                if task_subagent_type:
                                    # Record this for child sidechain messages
                                    subagent_name = task_subagent_type
                                    break

                    # 🔧 BUG 5 FIX: Extract options from assistant messages
                    options = []
                    if event_type == 'assistant':
                        options = extract_options_from_content(raw_content)

                    uuid_map[uuid] = {
                        'type': event_type,
                        'parent_uuid': parent_uuid,
                        'is_sidechain': is_sidechain,
                        'subagent_name': subagent_name,
                        'depth': 0,  # Will be calculated in second pass
                        'raw_content': raw_content,
                        'options': options  # 🔧 BUG 5 FIX: Store options for later checking
                    }

            except (json.JSONDecodeError, KeyError):
                continue

    # Second pass: Propagate subagent names FIRST, then calculate depth
    # 🔧 BUG 12 FIX: Reordered logic - subagent_name propagation must happen BEFORE depth calculation
    #
    # CRITICAL: Depth calculation depends on subagent_name being fully propagated.
    # Old ordering caused incomplete propagation → wrong depth values.

    # Step 1: Propagate subagent names down conversation threads
    # 🔧 BUG 5 FIX: Check for option selections to prevent misclassification
    for uuid, msg_data in uuid_map.items():
        # Skip if already has subagent_name (detected in first pass)
        if msg_data['subagent_name']:
            continue

        # Walk up parent chain to find first ancestor with subagent_name
        # Subagent responses can be great-grandchildren of Task invocations:
        # Task(analyst) → Tool result (user) → User prompt (user) → Analyst response (assistant)
        if msg_data['parent_uuid']:
            current_uuid = msg_data['parent_uuid']
            visited_ancestors = set()  # Prevent infinite loops

            while current_uuid and current_uuid not in visited_ancestors:
                visited_ancestors.add(current_uuid)
                ancestor = uuid_map.get(current_uuid)
                if ancestor and ancestor.get('subagent_name'):
                    # 🔧 BUG 14 FIX: User messages can NEVER inherit subagent_name
                    # User messages are ALWAYS from the user, regardless of conversation thread
                    # The ONLY exception is classification-expert (detected separately in detect_subagent_name)
                    if msg_data['type'] == 'user':
                        break  # Don't inherit for user messages

                    # 🔧 BUG 5 FIX: Don't inherit subagent name if current message is option selection
                    # Check if this user message matches any option from the parent
                    if msg_data['type'] == 'user' and ancestor.get('options'):
                        user_text = extract_text_from_content(msg_data['raw_content']).strip()
                        is_option_selection = any(user_text == opt.strip() for opt in ancestor['options'])
                        if is_option_selection:
                            # Don't inherit - this is user's own selection
                            break

                    # Found an ancestor with subagent_name - inherit it (assistant messages only)
                    msg_data['subagent_name'] = ancestor['subagent_name']
                    break
                # Continue walking up the chain
                current_uuid = ancestor.get('parent_uuid') if ancestor else None

    # Step 2: Clear subagent attribution for option selections
    # 🔧 BUG 5 FIX: Check if user is selecting an option from parent assistant
    for uuid, msg_data in uuid_map.items():
        if msg_data['type'] == 'user' and msg_data['parent_uuid']:
            parent = uuid_map.get(msg_data['parent_uuid'])
            if parent and parent.get('options'):
                # Extract user's text content
                user_text = extract_text_from_content(msg_data['raw_content']).strip()

                # Check if user's message exactly matches one of the provided options
                for option in parent['options']:
                    if user_text == option.strip():
                        # This is an option selection - clear any subagent attribution
                        msg_data['subagent_name'] = None
                        break

    # Step 3: Calculate depth based on subagent_name (NOW fully propagated)
    # 🔧 BUG 12 FIX: Depth calculation based on subagent_name, NOT isSidechain
    #
    # PROBLEM DIAGNOSIS:
    # - isSidechain is unreliable: only 2 messages marked as isSidechain=true
    # - language-tutor's 349 messages are isSidechain=false but correctly detected as subagent
    # - Old logic relied on isSidechain → all subagent messages got depth=0
    #
    # NEW LOGIC (based on subagent_name):
    # - Depth 0: No subagent_name (main conversation)
    # - Depth 1: Has subagent_name (direct subagent call)
    # - Depth 2: Has subagent_name AND parent has subagent_name (nested subagent)
    for uuid, msg_data in uuid_map.items():
        depth = 0

        # Check if this message has a subagent
        if msg_data.get('subagent_name'):
            # Default: depth=1 for any subagent message
            depth = 1

            # Check if parent also has subagent (nested call)
            parent_uuid = msg_data.get('parent_uuid')
            if parent_uuid:
                parent = uuid_map.get(parent_uuid)
                if parent and parent.get('subagent_name'):
                    # Parent is also subagent → nested call → depth=2
                    depth = 2

        # If no subagent_name, depth remains 0 (main conversation)
        msg_data['depth'] = depth

    return uuid_map


def filter_user_content(content) -> str:
    """
    Filter user content to remove command prompts and system warnings.
    Keep only the actual user input.

    CRITICAL: Extracts content from <command-args> tags (where actual user input lives for slash commands)

    Removes:
    - <command-message>...</command-message> tags
    - <command-name>...</command-name> tags
    - <system-reminder>...</system-reminder> tags
    - Warning prompts starting with **⚠️ or **CRITICAL**
    - <user-prompt-submit-hook>...</user-prompt-submit-hook> tags
    - <session-start-hook>...</session-start-hook> tags
    """
    # First extract text from the content structure
    text = extract_text_from_content(content)

    # ✅ CRITICAL FIX: Extract command-args content BEFORE removing tags
    # For slash commands like /ask, the actual user input is inside <command-args>
    command_args_match = re.search(r'<command-args>(.*?)</command-args>', text, flags=re.DOTALL)
    if command_args_match:
        # If command-args exists, use its content as the primary user input
        user_input = command_args_match.group(1).strip()
    else:
        # Otherwise use the full text (for regular messages without slash commands)
        user_input = text

    # Now remove all meta tags from user_input
    user_input = re.sub(r'<command-message>.*?</command-message>', '', user_input, flags=re.DOTALL)
    user_input = re.sub(r'<command-name>.*?</command-name>', '', user_input, flags=re.DOTALL)
    user_input = re.sub(r'<system-reminder>.*?</system-reminder>', '', user_input, flags=re.DOTALL)
    user_input = re.sub(r'<user-prompt-submit-hook>.*?</user-prompt-submit-hook>', '', user_input, flags=re.DOTALL)
    user_input = re.sub(r'<session-start-hook>.*?</session-start-hook>', '', user_input, flags=re.DOTALL)

    # Remove warning prompts (lines starting with **⚠️)
    user_input = re.sub(r'^\*\*⚠️.*?$', '', user_input, flags=re.MULTILINE)

    # Remove CRITICAL prompts (lines starting with **CRITICAL**)
    user_input = re.sub(r'^\*\*CRITICAL\*\*:.*?$', '', user_input, flags=re.MULTILINE)

    # Remove IMPORTANT prompts (lines starting with **IMPORTANT**)
    user_input = re.sub(r'^\*\*IMPORTANT\*\*:.*?$', '', user_input, flags=re.MULTILINE)

    # Remove multiple consecutive blank lines
    user_input = re.sub(r'\n\s*\n\s*\n+', '\n\n', user_input)

    # Strip leading/trailing whitespace
    user_input = user_input.strip()

    # Filter out system messages (todo notifications, title changes, etc.)
    if 'Todos have been modified successfully' in user_input:
        return ''
    if 'Successfully changed chat title' in user_input:
        return ''
    if user_input.startswith('Todos have been'):
        return ''

    return user_input


def score_message_match(user_message: str, search_pattern: str,
                       file_mtime: datetime, target_date: Optional[datetime] = None) -> float:
    """
    🔧 BUG 8 FIX: Calculate match score to enable best-match selection.

    Scoring criteria (0-100 points):
    - Exact match: 100 points
    - Prefix match (80% of pattern): 80 points
    - Fuzzy match (>90% similarity): 60-80 points
    - Substring match: 40 points
    - Date proximity bonus: +20 points if within 1 day

    Args:
        user_message: The user message content to check
        search_pattern: The search pattern provided by user
        file_mtime: File modification time
        target_date: Optional target date for date proximity bonus

    Returns:
        Match score (0-100)
    """
    if not search_pattern or not user_message:
        return 0

    score = 0

    # Normalize both strings
    msg_norm = user_message.lower().strip()
    pattern_norm = search_pattern.lower().strip()

    # Exact match (100 points)
    if msg_norm == pattern_norm:
        score = 100

    # Prefix match (80 points)
    elif msg_norm.startswith(pattern_norm) or pattern_norm.startswith(msg_norm):
        score = 80

    # Fuzzy match using SequenceMatcher (60-80 points)
    else:
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, msg_norm, pattern_norm).ratio()

        if similarity > 0.9:
            # Very high similarity: 60-80 points
            score = 60 + (similarity - 0.9) * 200  # Maps 0.9-1.0 → 60-80
        elif similarity > 0.7:
            # Moderate similarity: 40-60 points
            score = 40 + (similarity - 0.7) * 100  # Maps 0.7-0.9 → 40-60
        elif pattern_norm in msg_norm or msg_norm in pattern_norm:
            # Substring match: 40 points
            score = 40
        else:
            # No match
            score = 0

    # Date proximity bonus (up to +20 points)
    if target_date and score > 0:
        days_diff = abs((file_mtime - target_date).days)
        if days_diff == 0:
            score += 20  # Same day
        elif days_diff <= 1:
            score += 10  # Within 1 day
        elif days_diff <= 3:
            score += 5   # Within 3 days

    return min(score, 100)  # Cap at 100


def find_best_match_conversation(conversations: List[Path],
                                first_message: str,
                                last_message: Optional[str],
                                date_from: Optional[datetime],
                                date_to: Optional[datetime]) -> Optional[tuple]:
    """
    🔧 BUG 8 FIX: Evaluate all conversations and return the best match.

    Instead of stopping at the first match (greedy strategy), this function:
    1. Filters conversations by date range (if provided)
    2. Scores ALL matching conversations
    3. Returns the one with the highest score

    Args:
        conversations: List of JSONL file paths to evaluate
        first_message: Required first message pattern
        last_message: Optional last message pattern
        date_from: Optional start date filter
        date_to: Optional end date filter

    Returns:
        Tuple of (best_file, match_score) or None if no match found
    """
    if not first_message:
        return None

    candidates = []  # List of (file, score) tuples

    for conv_file in conversations:
        file_mtime = datetime.fromtimestamp(conv_file.stat().st_mtime)

        # 🔧 BUG 9 FIX: Date range filtering
        if date_from and file_mtime < date_from:
            continue
        if date_to and file_mtime > date_to:
            continue

        # Quick scan for first message in file
        first_msg_found = False
        first_msg_score = 0
        last_msg_score = 0

        try:
            with open(conv_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        event = json.loads(line)
                        if event.get('type') != 'user':
                            continue

                        # Skip meta messages
                        if event.get('isMeta', False):
                            continue

                        # Extract user content
                        raw_content = event['message']['content']
                        user_text = filter_user_content(raw_content)

                        if not user_text:
                            continue

                        # Score first message match
                        if not first_msg_found:
                            target_date = date_from if date_from else file_mtime
                            score = score_message_match(user_text, first_message, file_mtime, target_date)
                            if score > 0:
                                first_msg_found = True
                                first_msg_score = score

                                # If we need to match last message too, keep scanning
                                if last_message:
                                    continue
                                else:
                                    # First-only match - we're done
                                    break

                        # Score last message match (if needed and first found)
                        elif first_msg_found and last_message:
                            target_date = date_from if date_from else file_mtime
                            score = score_message_match(user_text, last_message, file_mtime, target_date)
                            if score > 0:
                                last_msg_score = score
                                # Keep scanning to find the LAST match

                    except (json.JSONDecodeError, KeyError):
                        continue

            # Calculate final score for this conversation
            if first_msg_found:
                if last_message:
                    # For first+last matching, use weighted average (first is more important)
                    if last_msg_score > 0:
                        final_score = (first_msg_score * 0.6 + last_msg_score * 0.4)
                    else:
                        # First matched but not last - low score
                        final_score = first_msg_score * 0.3
                else:
                    # First-only matching
                    final_score = first_msg_score

                candidates.append((conv_file, final_score))

        except Exception as e:
            print(f"⚠️  Error scanning {conv_file.name}: {e}", file=sys.stderr)
            continue

    # Find best candidate
    if not candidates:
        return None

    # Sort by score (descending)
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Debug: show top 3 candidates
    print(f"🔍 Found {len(candidates)} candidate(s):", file=sys.stderr)
    for i, (file, score) in enumerate(candidates[:3]):
        file_date = datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d')
        print(f"   {i+1}. {file.name[:40]}... (score: {score:.1f}, date: {file_date})", file=sys.stderr)

    # Return best match (minimum score threshold: 40)
    best_file, best_score = candidates[0]
    if best_score >= 40:
        return (best_file, best_score)
    else:
        return None


def parse_conversation(jsonl_file: Path, first_message: str = None, last_message: str = None, include_subagents: bool = True) -> Dict:
    """
    Parse a Claude Code JSONL conversation file with comprehensive attribution.

    This function uses two-pass processing:
    1. First pass: Build conversation thread map (UUID relationships, subagent detection)
    2. Second pass: Extract messages with accurate attribution

    Args:
        jsonl_file: Path to JSONL file
        first_message: Optional substring to match the first user message (for range extraction)
        last_message: Optional substring to match the last user message (for range extraction)
        include_subagents: Whether to include subagent messages (default: True)

    Returns:
        Dictionary with metadata, messages, and summaries
    """
    # First pass: Build conversation threads for accurate attribution
    uuid_map = build_conversation_threads(jsonl_file)

    messages = []
    summaries = []
    metadata = {
        'session_id': jsonl_file.stem,
        'file_path': str(jsonl_file),
        'file_size_kb': jsonl_file.stat().st_size / 1024,
        'modified_at': datetime.fromtimestamp(jsonl_file.stat().st_mtime).isoformat(),
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'total_cache_tokens': 0,
        'total_cost_usd': 0.0,
        'models_used': set(),
        'git_branches': set(),
        'working_directories': set()
    }

    # Range extraction flags
    in_range = (first_message is None)  # If no first_message specified, start immediately
    range_started = False

    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
                event_type = event.get('type')

                # Skip queue operations
                if event_type == 'queue-operation':
                    continue

                if event_type == 'user':
                    # Skip meta messages (slash command prompts)
                    if event.get('isMeta', False):
                        continue

                    # Extract and filter user content (remove prompt tags)
                    raw_content = event['message']['content']
                    filtered_content = filter_user_content(raw_content)

                    # Skip if content is empty after filtering
                    if not filtered_content:
                        continue

                    # 🔧 FIX: Filter out tool results (should not be in conversation archive)
                    if is_tool_result_content(filtered_content):
                        continue

                    # Skip messages that are pure prompts (analyst consultations, etc)
                    if '<SILENT_CONSULTATION_MODE>' in filtered_content:
                        continue
                    if filtered_content.strip().startswith('# Ask Command'):
                        continue
                    if filtered_content.strip().startswith('# /'):
                        continue

                    # Range extraction logic - IMPROVED MATCHING
                    if first_message and not in_range:
                        # Normalize both for better matching
                        # 🔧 FIX: Increase matching length from 200 to 500 chars
                        first_msg_norm = first_message.lower().strip()[:500]
                        content_norm = filtered_content.lower().strip()[:500]

                        # Check if this is the start of the range (more robust matching)
                        if (first_msg_norm in content_norm or
                            content_norm in first_msg_norm or
                            (len(first_msg_norm) > 50 and first_msg_norm[:50] in content_norm)):
                            in_range = True
                            range_started = True
                            print(f"✅ Found first message match at line {line_num}: {filtered_content[:100]}...", file=sys.stderr)

                    # Check if this is the end of the range
                    if last_message and in_range:
                        # 🔧 FIX: Increase matching length from 200 to 500 chars
                        last_msg_norm = last_message.lower().strip()[:500]
                        content_norm = filtered_content.lower().strip()[:500]

                        if (last_msg_norm in content_norm or
                            content_norm in last_msg_norm or
                            (len(last_msg_norm) > 50 and last_msg_norm[:50] in content_norm)):
                            print(f"✅ Found last message match at line {line_num}: {filtered_content[:100]}...", file=sys.stderr)
                            # 🔧 FIX: Get subagent attribution from UUID map
                            uuid = event['uuid']
                            thread_info = uuid_map.get(uuid, {})
                            subagent_name = thread_info.get('subagent_name')
                            is_sidechain = event.get('isSidechain', False)
                            depth = thread_info.get('depth', 0)

                            # 🔧 BUG 11 & 12 FIX: Allow depth=0/1/2, only filter depth>=3
                            # depth=0: main, depth=1: invocation, depth=2: Socratic dialogue
                            if depth >= 3:
                                break

                            # Skip if it's a subagent and we're excluding them
                            if not (not include_subagents and subagent_name):
                                # Include this message, then stop
                                msg_data = {
                                    'role': 'user',
                                    'content': filtered_content,
                                    'timestamp': event['timestamp'],
                                    'uuid': uuid,
                                    'parent_uuid': event.get('parentUuid'),
                                    'cwd': event.get('cwd'),
                                    'git_branch': event.get('gitBranch'),
                                    'is_sidechain': is_sidechain,
                                    'subagent_name': subagent_name,
                                    'depth': depth
                                }

                                # Track metadata
                                if msg_data['cwd']:
                                    metadata['working_directories'].add(msg_data['cwd'])
                                if msg_data['git_branch']:
                                    metadata['git_branches'].add(msg_data['git_branch'])

                                messages.append(msg_data)
                            break  # Stop processing after last_message

                    # Only add message if we're in range
                    if not in_range:
                        continue

                    # 🔧 FIX: Get subagent attribution from UUID map (thread-aware)
                    uuid = event['uuid']
                    thread_info = uuid_map.get(uuid, {})
                    subagent_name = thread_info.get('subagent_name')
                    is_sidechain = event.get('isSidechain', False)
                    depth = thread_info.get('depth', 0)

                    # 🔧 BUG 11 & 12 FIX: Preserve user-subagent Socratic dialogue while filtering nested calls
                    #
                    # KEEP:
                    # - depth=0: Main conversation (user ↔ assistant)
                    # - depth=1: Direct subagent invocation (Task tool call responses)
                    # - depth=2: User ↔ subagent Socratic dialogue (e.g., language-tutor teaching)
                    #
                    # FILTER:
                    # - depth>=3: Truly nested subagent calls (subagent→subagent)
                    #
                    # BUG 3 was overly aggressive (filtered ALL depth>0), losing valuable Socratic dialogues.
                    # BUG 12 fixed depth calculation so depth=2 now correctly represents Socratic dialogue.
                    # This allows depth=0/1/2 messages (full learning sessions) while filtering depth>=3 (nested calls).
                    if depth >= 3:
                        continue

                    # Skip subagent messages if include_subagents=False
                    if not include_subagents and subagent_name:
                        continue

                    msg_data = {
                        'role': 'user',
                        'content': filtered_content,
                        'timestamp': event['timestamp'],
                        'uuid': uuid,
                        'parent_uuid': event.get('parentUuid'),
                        'cwd': event.get('cwd'),
                        'git_branch': event.get('gitBranch'),
                        'is_sidechain': is_sidechain,
                        'subagent_name': subagent_name,  # From thread tracking
                        'depth': depth
                    }

                    # Track metadata
                    if msg_data['cwd']:
                        metadata['working_directories'].add(msg_data['cwd'])
                    if msg_data['git_branch']:
                        metadata['git_branches'].add(msg_data['git_branch'])

                    messages.append(msg_data)

                elif event_type == 'assistant':
                    # Only add assistant message if we're in range
                    if not in_range:
                        continue

                    msg_info = event['message']
                    usage = msg_info.get('usage', {})

                    # Accumulate token usage
                    metadata['total_input_tokens'] += usage.get('input_tokens', 0)
                    metadata['total_output_tokens'] += usage.get('output_tokens', 0)
                    metadata['total_cache_tokens'] += usage.get('cache_read_input_tokens', 0)

                    model = msg_info.get('model', 'unknown')
                    metadata['models_used'].add(model)

                    # Extract content and filter out tool-use, system-reminders
                    raw_content = msg_info['content']
                    filtered_content = filter_assistant_content(raw_content)

                    # 🔧 FIX: Get subagent attribution from UUID map (thread-aware)
                    uuid = event['uuid']
                    thread_info = uuid_map.get(uuid, {})
                    subagent_name = thread_info.get('subagent_name')
                    is_sidechain = event.get('isSidechain', False)
                    depth = thread_info.get('depth', 0)

                    # 🔧 BUG 11 & 12 FIX: Filter out truly nested subagent calls (depth >= 3)
                    # Include depth 0 (main), depth 1 (invocation), depth 2 (Socratic dialogue)
                    if depth >= 3:
                        continue

                    # Skip subagent messages if include_subagents=False
                    if not include_subagents and subagent_name:
                        continue

                    msg_data = {
                        'role': 'assistant',
                        'content': filtered_content,
                        'timestamp': event['timestamp'],
                        'uuid': uuid,
                        'parent_uuid': event.get('parentUuid'),
                        'model': model,
                        'usage': usage,
                        'request_id': event.get('requestId'),
                        'is_sidechain': is_sidechain,
                        'subagent_name': subagent_name,  # 🔧 NOW INCLUDES SUBAGENT ATTRIBUTION!
                        'depth': depth
                    }

                    messages.append(msg_data)

                elif event_type == 'summary':
                    summaries.append({
                        'summary': event.get('summary', ''),
                        'leaf_uuid': event.get('leafUuid')
                    })

            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  Warning: Line {line_num} in {jsonl_file.name}: {e}", file=sys.stderr)
                continue

    # Convert sets to lists for JSON serialization
    metadata['models_used'] = list(metadata['models_used'])
    metadata['git_branches'] = list(metadata['git_branches'])
    metadata['working_directories'] = list(metadata['working_directories'])

    return {
        'metadata': metadata,
        'messages': messages,
        'summaries': summaries
    }


def validate_archived_conversation(conversation: Dict) -> Dict[str, any]:
    """
    🔧 VALIDATION: Verify quality of archived conversation.

    Checks for:
    - No tool errors in messages (BUG 2 check)
    - No misattributed subagents (BUG 1 check)
    - No internal subagent dialogues (BUG 3 check)

    Returns:
        Dict with validation results:
        {
            'is_valid': bool,
            'warnings': List[str],
            'errors': List[str],
            'stats': Dict[str, int]
        }
    """
    warnings = []
    errors = []
    stats = {
        'total_messages': len(conversation['messages']),
        'user_messages': 0,
        'assistant_messages': 0,
        'subagent_messages': 0,
        'depth_0_messages': 0,
        'depth_1_messages': 0,
        'depth_2plus_messages': 0,
    }

    for i, msg in enumerate(conversation['messages']):
        role = msg['role']
        content = msg.get('content', '')
        depth = msg.get('depth', 0)
        subagent_name = msg.get('subagent_name')

        # Track stats
        if role == 'user':
            stats['user_messages'] += 1
        else:
            stats['assistant_messages'] += 1

        if subagent_name:
            stats['subagent_messages'] += 1

        if depth == 0:
            stats['depth_0_messages'] += 1
        elif depth == 1:
            stats['depth_1_messages'] += 1
        else:
            stats['depth_2plus_messages'] += 1

        # BUG 2 CHECK: Tool errors in content
        if is_tool_result_content(content):
            errors.append(f"Message {i} ({role}): Contains tool result/error content")

        # BUG 3 CHECK: Internal subagent dialogues
        # 🔧 BUG 11 & 12 FIX: Updated validation to match new depth filter (depth >= 3)
        # We now ALLOW depth=0/1/2 (main, invocation, Socratic dialogue)
        # We only REJECT depth >= 3 (truly nested subagent calls)
        if depth >= 3:
            errors.append(f"Message {i} ({role}): Depth {depth} >= 3 (nested subagent, should be filtered)")

        # BUG 1 CHECK: Misattributed classification-expert
        if subagent_name == 'classification-expert' and role == 'user':
            # Verify it's actually valid classification JSON
            if content.strip().startswith('{'):
                try:
                    data = json.loads(content.strip())
                    if not validate_classification_expert_json(data):
                        warnings.append(f"Message {i}: Marked as classification-expert but JSON schema doesn't match")
                except json.JSONDecodeError:
                    warnings.append(f"Message {i}: Marked as classification-expert but not valid JSON")
            else:
                errors.append(f"Message {i}: Marked as classification-expert but content is not JSON")

        # Check for common error patterns that should be filtered
        error_indicators = [
            'command not found',
            '/bin/bash: line',
            'No such file or directory',
            'Traceback (most recent call last)',
            'permission denied',
        ]
        for indicator in error_indicators:
            if indicator.lower() in content.lower():
                warnings.append(f"Message {i} ({role}): Contains error indicator: '{indicator}'")

    is_valid = len(errors) == 0

    return {
        'is_valid': is_valid,
        'warnings': warnings,
        'errors': errors,
        'stats': stats
    }


def export_to_markdown(conversation: Dict, output_file: Path):
    """
    Export conversation to markdown format with /save-compatible structure.

    Generates placeholder format that /save will enrich with:
    - Summary (from active context)
    - Rems extracted (with hyperlinks)
    - Tags and domain classification
    """
    metadata = conversation['metadata']
    messages = conversation['messages']
    summaries = conversation['summaries']

    # Determine date from first message or file modification
    if messages:
        first_timestamp = datetime.fromisoformat(messages[0]['timestamp'].replace('Z', '+00:00'))
        date_str = first_timestamp.strftime('%Y-%m-%d')
        time_str = first_timestamp.strftime('%H:%M:%S')
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')
        time_str = datetime.now().strftime('%H:%M:%S')

    # Build placeholder format
    frontmatter = f"""---
id: conversation-{date_str}
title: "Conversation - {date_str}"
date: {date_str}
agent: main
domain: general
tags: []
rems_extracted: []
turns: {len(messages)}
archived_by: chat-archiver
archived_at: {date_str}
---

"""

    # Build markdown content
    md_content = frontmatter

    # Title
    md_content += f"# Conversation - {date_str}\n\n"

    # Metadata block
    md_content += f"**Date**: {date_str}\n"
    md_content += f"**Agent**: main\n"
    md_content += f"**Domain**: general\n\n"

    # Metadata section
    md_content += "## Metadata\n\n"
    md_content += "- **Rems Extracted**: *(Will be extracted by /save)*\n"
    md_content += f"- **Total Turns**: {len(messages)}\n"
    md_content += "- **Tags**: *(Will be added by /save)*\n\n"

    # Summary section
    md_content += "## Summary\n\n"
    md_content += "*(Summary will be generated by /save from active context)*\n\n"

    # Rems Extracted section
    md_content += "## Rems Extracted\n\n"
    md_content += "This conversation led to the creation of these knowledge Rems:\n\n"
    md_content += "*(Rems will be listed by /save command)*\n\n"

    # Full Conversation section
    md_content += "## Full Conversation\n\n"

    # Add all messages
    for msg in messages:
        role = msg['role'].title()
        content = msg['content']

        # Skip empty messages
        if not content.strip():
            continue

        # 🔧 BUG 14 PART 2 FIX: Detect Task prompts (sidechain user with no parent)
        # When assistant calls Task tool, Claude Code creates a sidechain user message
        # with the prompt content. This should be labeled "Assistant → Subagent".
        is_task_prompt = (
            msg['role'] == 'user' and
            msg.get('is_sidechain') and
            msg.get('parent_uuid') is None
        )

        # 🔧 BUG 15 FIX: Detect JSON responses from consultant subagents
        # These are labeled "Subagent → Assistant" (returning JSON to main agent)
        is_json_response = False
        if msg['role'] == 'assistant':
            # Check if content is JSON (consultant subagent response)
            content_stripped = content.strip()

            # Strip markdown code fences if present (```json...```)
            content_for_check = content_stripped
            if content_stripped.startswith('```'):
                lines = content_stripped.split('\n')
                # Remove opening fence (```json or ```)
                if lines[0].startswith('```'):
                    lines = lines[1:]
                # Remove closing fence (```)
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content_for_check = '\n'.join(lines).strip()

            # Now check if it's JSON
            if content_for_check.startswith('{') and content_for_check.endswith('}'):
                try:
                    parsed_json = json.loads(content_for_check)
                    # Verify it's actually a subagent response (has typical JSON consultant fields)
                    consultant_indicators = [
                        'strategy', 'rationale', 'content', 'confidence',  # analyst/tutor responses
                        'domain', 'isced', 'dewey', 'message'  # classification-expert
                    ]
                    if any(key in parsed_json for key in consultant_indicators):
                        is_json_response = True
                except json.JSONDecodeError:
                    pass

        # Determine header based on message type
        if is_task_prompt:
            # Task prompt: Main agent calling subagent
            md_content += f"### Assistant → Subagent\n\n"
        elif is_json_response:
            # JSON response: Subagent returning JSON to main agent
            subagent_name = msg.get('subagent_name')
            if subagent_name:
                subagent_label = subagent_name.replace('-', ' ').title()
                md_content += f"### Subagent ({subagent_label}) → Assistant\n\n"
            else:
                md_content += f"### Subagent → Assistant\n\n"
        elif msg.get('subagent_name') and msg['role'] == 'user':
            # User message from subagent (e.g., classification-expert)
            subagent_label = msg['subagent_name'].replace('-', ' ').title()
            md_content += f"### Subagent: {subagent_label}\n\n"
        else:
            # Regular user/assistant message
            md_content += f"### {role}\n\n"

        # Demote headings in content to maintain hierarchy
        demoted_content = demote_headings_in_content(content, levels=3)
        md_content += f"{demoted_content}\n\n"

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return output_file


def find_project_conversations(oldest_first: bool = False) -> List[Path]:
    """
    Find all conversation files for the knowledge-system project.

    Args:
        oldest_first: If True, return oldest conversations first (for historical extraction).
                     If False, return newest first (default, for recent extraction).

    🔧 BUG 6 FIX: Allow prioritizing oldest conversations for historical data extraction.
    """
    project_dir = CLAUDE_PROJECTS_DIR / PROJECT_ENCODED_NAME

    if not project_dir.exists():
        print(f"❌ Project directory not found: {project_dir}", file=sys.stderr)
        return []

    all_jsonl = list(project_dir.glob('*.jsonl'))

    # Sort by modification time
    # 🔧 BUG 6 FIX: reverse=not oldest_first (oldest_first=True means ascending time order)
    return sorted(all_jsonl, key=lambda p: p.stat().st_mtime, reverse=not oldest_first)


def extract_and_save(jsonl_file: Path, quiet: bool = False, first_message: str = None, last_message: str = None, include_subagents: bool = True) -> Optional[Path]:
    """
    Extract a conversation and save to chats folder.

    Args:
        jsonl_file: Path to JSONL file
        quiet: Suppress output messages
        first_message: Optional substring to match first user message (for range extraction)
        last_message: Optional substring to match last user message (for range extraction)
        include_subagents: Whether to include subagent messages (default: True)

    Returns:
        Path to saved markdown file, or None if failed
    """
    try:
        # Parse conversation (with optional range extraction)
        conversation = parse_conversation(jsonl_file, first_message, last_message, include_subagents)

        if not conversation['messages']:
            if not quiet:
                print(f"⚠️  Skipping {jsonl_file.name}: No messages found", file=sys.stderr)
            else:
                # In quiet mode, still report to stderr (orchestrator checks this)
                print(f"⚠️  No messages found in {jsonl_file.name}", file=sys.stderr)
            return None

        # Generate output filename
        metadata = conversation['metadata']
        if conversation['messages']:
            first_timestamp = datetime.fromisoformat(
                conversation['messages'][0]['timestamp'].replace('Z', '+00:00')
            )
        else:
            first_timestamp = datetime.now()

        month_dir = CHATS_DIR / first_timestamp.strftime("%Y-%m")
        date_str = first_timestamp.strftime("%Y-%m-%d")
        time_str = first_timestamp.strftime("%H%M%S")

        # Use summary as filename slug if available
        slug = "conversation"
        if conversation['summaries']:
            summary_text = conversation['summaries'][0]['summary']
            # Create slug from summary
            slug = re.sub(r'[^a-z0-9]+', '-', summary_text.lower())[:50]

        filename = f"claude-{date_str}-{time_str}-{slug}.md"
        output_file = month_dir / filename

        # 🔧 VALIDATION: Check quality before exporting
        validation = validate_archived_conversation(conversation)

        if not quiet:
            # Print validation results
            if not validation['is_valid']:
                print(f"⚠️  Validation FAILED with {len(validation['errors'])} errors:")
                for error in validation['errors'][:5]:  # Show first 5 errors
                    print(f"     - {error}")
                if len(validation['errors']) > 5:
                    print(f"     ... and {len(validation['errors']) - 5} more errors")

            if validation['warnings'] and not quiet:
                print(f"⚠️  Validation warnings: {len(validation['warnings'])}")
                for warning in validation['warnings'][:3]:  # Show first 3 warnings
                    print(f"     - {warning}")

        # Export to markdown
        export_to_markdown(conversation, output_file)

        if not quiet:
            print(f"✅ Saved: {output_file}")
            print(f"   Messages: {len(conversation['messages'])} ({metadata['total_input_tokens'] + metadata['total_output_tokens']} tokens)")
            print(f"   Validation: {'✓ Passed' if validation['is_valid'] else '✗ Failed'}")
            print(f"   Stats: {validation['stats']['depth_0_messages']} main, {validation['stats']['subagent_messages']} subagent messages")

        return output_file

    except Exception as e:
        if not quiet:
            print(f"❌ Error processing {jsonl_file.name}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        return None


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Chat Archiver - Extract Claude Code conversations for /save command"
    )
    parser.add_argument("--session-id", type=str, nargs='?',
                        help="Extract specific session by UUID (default: most recent)")
    parser.add_argument("--first-message", type=str,
                        help="Substring to match first user message (for range extraction)")
    parser.add_argument("--last-message", type=str,
                        help="Substring to match last user message (for range extraction)")
    parser.add_argument("--no-include-subagents", dest='include_subagents', action='store_false',
                        help="Exclude subagent messages from archive (default: include)")
    parser.add_argument("--include-subagents", dest='include_subagents', action='store_true',
                        help="Include subagent messages in archive (default)")
    parser.add_argument("--oldest-first", action='store_true',
                        help="🔧 BUG 6 FIX: Prioritize oldest conversations when searching (for historical extraction)")
    parser.add_argument("--date-from", type=str,
                        help="🔧 BUG 9 FIX: Filter conversations from this date (YYYY-MM-DD)")
    parser.add_argument("--date-to", type=str,
                        help="🔧 BUG 9 FIX: Filter conversations to this date (YYYY-MM-DD)")
    parser.set_defaults(include_subagents=True)

    args = parser.parse_args()

    # Ensure chats directory exists
    CHATS_DIR.mkdir(exist_ok=True)

    if args.session_id:
        # Extract specific session
        session_file = CLAUDE_PROJECTS_DIR / PROJECT_ENCODED_NAME / f"{args.session_id}.jsonl"
        if not session_file.exists():
            print(f"❌ Session not found: {args.session_id}")
            sys.exit(1)

        print(f"📖 Extracting session: {args.session_id}")
        if args.first_message or args.last_message:
            print(f"   Range: first=\"{args.first_message or 'START'}\" last=\"{args.last_message or 'END'}\"")
        if not args.include_subagents:
            print(f"   Excluding subagent messages")

        extract_and_save(session_file, first_message=args.first_message, last_message=args.last_message, include_subagents=args.include_subagents)

    else:
        # If first_message or last_message specified, search ALL conversations
        if args.first_message or args.last_message:
            # 🔧 BUG 8 FIX: Best-match selection strategy with scoring
            # 🔧 BUG 7 FIX: Intelligent tiered matching strategy (auto-fallback)
            # 🔧 BUG 9 FIX: Date range filtering support

            # 🔧 BUG 6 FIX: Use oldest_first flag to prioritize historical conversations
            conversations = find_project_conversations(oldest_first=args.oldest_first)
            if not conversations:
                print("❌ No conversations found", file=sys.stderr)
                sys.exit(1)

            if args.oldest_first:
                print(f"🔍 Searching {len(conversations)} conversations (oldest first)...", file=sys.stderr)
            else:
                print(f"🔍 Searching {len(conversations)} conversations (newest first)...", file=sys.stderr)

            # Parse date filters
            date_from = None
            date_to = None
            if args.date_from:
                try:
                    date_from = datetime.strptime(args.date_from, '%Y-%m-%d')
                    print(f"📅 Date filter: from {args.date_from}", file=sys.stderr)
                except ValueError:
                    print(f"❌ Invalid date format for --date-from: {args.date_from} (expected YYYY-MM-DD)", file=sys.stderr)
                    sys.exit(1)
            if args.date_to:
                try:
                    date_to = datetime.strptime(args.date_to, '%Y-%m-%d')
                    # Set to end of day
                    date_to = date_to.replace(hour=23, minute=59, second=59)
                    print(f"📅 Date filter: to {args.date_to}", file=sys.stderr)
                except ValueError:
                    print(f"❌ Invalid date format for --date-to: {args.date_to} (expected YYYY-MM-DD)", file=sys.stderr)
                    sys.exit(1)

            output_file = None

            # 🔧 BUG 13 FIX: 5-tier matching strategy for repeated patterns
            # Tier 0: --session-id (handled above, lines 1609-1622)
            # Tier 1: first+last+date (most precise)
            # Tier 2: first+last (no date - for split sessions)
            # Tier 3: first+date (last might be split)
            # Tier 4: first+oldest (insurance for 10-day repeated patterns)

            # 🔧 BUG 8 & 13: Tier 1 - first+last+date (most precise)
            if args.first_message and args.last_message and (date_from or date_to):
                print(f"🎯 Tier 1: first+last+date (most precise)...", file=sys.stderr)
                result = find_best_match_conversation(
                    conversations,
                    args.first_message,
                    args.last_message,
                    date_from,
                    date_to
                )

                if result:
                    best_file, best_score = result
                    print(f"✅ Tier 1 SUCCESS: score {best_score:.1f}", file=sys.stderr)
                    output_file = extract_and_save(best_file, quiet=False,
                                                  first_message=args.first_message,
                                                  last_message=args.last_message,
                                                  include_subagents=args.include_subagents)

            # 🔧 BUG 13: Tier 2 - first+last (no date constraint)
            # Use when Tier 1 fails OR when no date filters provided but both messages given
            if not output_file and args.first_message and args.last_message:
                print(f"🔄 Tier 2: first+last (no date)...", file=sys.stderr)
                result = find_best_match_conversation(
                    conversations,
                    args.first_message,
                    args.last_message,
                    None,  # No date constraint
                    None
                )

                if result:
                    best_file, best_score = result
                    print(f"✅ Tier 2 SUCCESS: score {best_score:.1f}", file=sys.stderr)
                    output_file = extract_and_save(best_file, quiet=False,
                                                  first_message=args.first_message,
                                                  last_message=args.last_message,
                                                  include_subagents=args.include_subagents)

            # 🔧 BUG 13: Tier 3 - first+date (last might be split across sessions)
            if not output_file and args.first_message and (date_from or date_to):
                print(f"🔄 Tier 3: first+date (last might be split)...", file=sys.stderr)
                result = find_best_match_conversation(
                    conversations,
                    args.first_message,
                    None,  # No last message requirement (might be split)
                    date_from,
                    date_to
                )

                if result:
                    best_file, best_score = result
                    print(f"✅ Tier 3 SUCCESS: score {best_score:.1f}", file=sys.stderr)
                    output_file = extract_and_save(best_file, quiet=False,
                                                  first_message=args.first_message,
                                                  last_message=None,  # Extract to end
                                                  include_subagents=args.include_subagents)

            # 🔧 BUG 13: Tier 4 - first+oldest (insurance mode for 10-day repeated patterns)
            # When all else fails, find oldest conversation with matching first message
            if not output_file and args.first_message:
                print(f"🔄 Tier 4: first+oldest (insurance mode)...", file=sys.stderr)
                # Re-scan with oldest-first priority if not already set
                if not args.oldest_first:
                    conversations = find_project_conversations(oldest_first=True)
                    print(f"   🔍 Re-scanning {len(conversations)} conversations (oldest first)...", file=sys.stderr)

                result = find_best_match_conversation(
                    conversations,
                    args.first_message,
                    None,  # No last message requirement
                    None,  # No date constraint (insurance mode)
                    None
                )

                if result:
                    best_file, best_score = result
                    print(f"✅ Tier 4 SUCCESS: score {best_score:.1f} (oldest match)", file=sys.stderr)
                    output_file = extract_and_save(best_file, quiet=False,
                                                  first_message=args.first_message,
                                                  last_message=None,  # Extract to end
                                                  include_subagents=args.include_subagents)

            if not output_file:
                print("❌ All tiers failed to extract conversation", file=sys.stderr)
                sys.exit(1)
            else:
                sys.exit(0)
        else:
            # Default behavior: Extract most recent and return file path (for /save)
            conversations = find_project_conversations(oldest_first=False)
            if not conversations:
                print("❌ No conversations found", file=sys.stderr)
                sys.exit(1)

            # Extract the most recent conversation (quiet mode - only print file path)
            output_file = extract_and_save(conversations[0], quiet=True,
                                          first_message=args.first_message,
                                          last_message=args.last_message,
                                          include_subagents=args.include_subagents)

        if output_file:
            # Print ONLY the file path to stdout (for /save to capture)
            print(str(output_file))
            sys.exit(0)
        else:
            print("❌ Failed to extract conversation", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
