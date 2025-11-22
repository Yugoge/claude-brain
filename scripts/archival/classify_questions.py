#!/usr/bin/env python3
"""
Classify user questions in review sessions

Analyzes review session conversations to classify user questions as:
- Type A (Clarification): Update existing Rem
- Type B (Extension): Create new Rem (extension)
- Type C (Comparison): Create new Rem (comparison)
- Type D (Application): Create new Rem (application)

Provides JSON suggestions for AI to review and make final decisions.

Usage:
    python scripts/archival/classify_questions.py \
        --archived-file chats/2025-11/conversation.md \
        --rems-reviewed '["rem-id-1", "rem-id-2"]'
"""

import json
import argparse
import sys
import re
from pathlib import Path
from typing import List, Dict, Optional

# Project root
ROOT = Path(__file__).parent.parent.parent


def parse_conversation(archived_file: Path) -> List[Dict]:
    """
    Parse conversation into turns.

    Returns:
        List of turns: [{"role": "user|assistant", "content": "...", "turn": N}]
    """
    with open(archived_file, 'r', encoding='utf-8') as f:
        content = f.read()

    turns = []
    current_role = None
    current_content = []
    turn_number = 0

    for line in content.split('\n'):
        # Detect role headers
        if line.startswith('### User'):
            if current_role and current_content:
                turns.append({
                    "role": current_role,
                    "content": '\n'.join(current_content).strip(),
                    "turn": turn_number
                })
                turn_number += 1
            current_role = "user"
            current_content = []
        elif line.startswith('### Assistant') or line.startswith('### Subagent'):
            if current_role and current_content:
                turns.append({
                    "role": current_role,
                    "content": '\n'.join(current_content).strip(),
                    "turn": turn_number
                })
                turn_number += 1
            current_role = "assistant"
            current_content = []
        else:
            # Skip frontmatter
            if line.strip() and not line.startswith('---'):
                current_content.append(line)

    # Add last turn
    if current_role and current_content:
        turns.append({
            "role": current_role,
            "content": '\n'.join(current_content).strip(),
            "turn": turn_number
        })

    return turns


def detect_rem_reference(text: str) -> Optional[str]:
    """
    Detect Rem reference in text.

    Looks for patterns like:
    - [[rem-id]]
    - "about {rem-id}"
    - "regarding {rem-id}"

    Returns: rem_id if found, None otherwise
    """
    # Pattern 1: [[rem-id]]
    wikilink_match = re.search(r'\[\[([^\]]+)\]\]', text)
    if wikilink_match:
        return wikilink_match.group(1)

    # Pattern 2: Common phrases + potential rem-id words
    # Look for hyphenated words after "about", "regarding", etc.
    phrase_patterns = [
        r'(?:about|regarding|concerning)\s+([a-z]+-[a-z-]+)',
        r'(?:the|this)\s+([a-z]+-[a-z-]+)\s+(?:concept|topic|idea)',
    ]

    for pattern in phrase_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).lower()

    return None


def classify_question_type(question: str) -> tuple:
    """
    Classify question type using pattern matching.

    Returns: (type, confidence)
        type: "A" | "B" | "C" | "D" | "unknown"
        confidence: 0.0 - 1.0
    """
    question_lower = question.lower()

    # Type A: Clarification patterns
    type_a_patterns = [
        (r'can you clarify', 0.95),
        (r'could you clarify', 0.95),
        (r'explain (?:more|again|in detail|further|better)', 0.90),
        (r'what (?:do you|does that|does this) mean', 0.90),
        (r"i don'?t (?:understand|get)", 0.85),
        (r'could you elaborate', 0.85),
        (r'what (?:is|does) (?:that|this) (?:mean|refer to)', 0.85),
        (r'help me understand', 0.80),
    ]

    for pattern, conf in type_a_patterns:
        if re.search(pattern, question_lower):
            return ("A", conf)

    # Type B: Extension patterns
    type_b_patterns = [
        (r'what about', 0.85),
        (r'what if', 0.85),
        (r'(?:also|additionally),?\s+(?:what|how)', 0.80),
        (r'another (?:thing|question|aspect)', 0.75),
    ]

    for pattern, conf in type_b_patterns:
        if re.search(pattern, question_lower):
            return ("B", conf)

    # Type C: Comparison patterns
    type_c_patterns = [
        (r'\s+vs\.?\s+', 0.95),
        (r'\s+versus\s+', 0.95),
        (r'compare (?:and contrast )?', 0.90),
        (r'difference (?:between|among)', 0.90),
        (r'how (?:does|do) .+ differ', 0.85),
        (r'(?:similar|different) (?:to|from)', 0.80),
    ]

    for pattern, conf in type_c_patterns:
        if re.search(pattern, question_lower):
            return ("C", conf)

    # Type D: Application patterns
    type_d_patterns = [
        (r'in practice', 0.90),
        (r'how (?:to|do (?:I|you)) (?:use|apply)', 0.90),
        (r'real world (?:example|application|use)', 0.85),
        (r'practical (?:example|application|use)', 0.85),
        (r'when (?:would|should) (?:I|you) use', 0.80),
    ]

    for pattern, conf in type_d_patterns:
        if re.search(pattern, question_lower):
            return ("D", conf)

    return ("unknown", 0.0)


def extract_clarification_content(assistant_response: str, max_sentences: int = 3) -> str:
    """
    Extract clarification content from assistant response.

    Takes first N sentences as clarification text.
    Aims for <100 tokens.
    """
    # Split into sentences (simple approach)
    sentences = re.split(r'[.!?]+\s+', assistant_response)

    # Take first max_sentences
    clarification = '. '.join(sentences[:max_sentences]).strip()

    # Add period if missing
    if clarification and not clarification[-1] in '.!?':
        clarification += '.'

    return clarification


def infer_target_section(question: str, clarification: str) -> str:
    """
    Infer which Rem section to update based on question content.

    Returns: "## Core Memory Points" | "## Usage Scenario" | "## My Mistakes"
    """
    question_lower = question.lower()
    clarification_lower = clarification.lower()

    # Usage/example indicators
    usage_keywords = ['example', 'usage', 'use case', 'in practice', 'how to use', 'when to use']
    if any(kw in question_lower or kw in clarification_lower for kw in usage_keywords):
        return "## Usage Scenario"

    # Mistake/correction indicators
    mistake_keywords = ['mistake', 'error', 'wrong', 'incorrect', 'correction', 'actually']
    if any(kw in question_lower or kw in clarification_lower for kw in mistake_keywords):
        return "## My Mistakes"

    # Default: Core Memory Points (for definition clarifications)
    return "## Core Memory Points"


def classify_review_questions(
    archived_file: Path,
    rems_reviewed: List[str]
) -> Dict:
    """
    Classify all questions in a review session.

    Args:
        archived_file: Path to archived conversation
        rems_reviewed: List of Rem IDs that were reviewed

    Returns:
        {
            "type_a": [{question, turn, rem_id, clarification_text, target_section, confidence}],
            "type_bcd": [{question, turn, type, confidence}],
            "statistics": {total_questions, classified, unclassified}
        }
    """
    turns = parse_conversation(archived_file)

    type_a = []
    type_bcd = []

    for i, turn in enumerate(turns):
        if turn['role'] != 'user':
            continue

        question = turn['content']

        # Skip very short messages (likely not questions)
        if len(question.strip()) < 10:
            continue

        # Classify question
        q_type, confidence = classify_question_type(question)

        if q_type == "unknown":
            continue

        if q_type == "A":
            # Type A: Clarification - try to detect which Rem
            rem_id = detect_rem_reference(question)

            # If no explicit reference, try to infer from reviewed Rems context
            if not rem_id and rems_reviewed:
                # Use the most recent Rem as a guess (low confidence)
                rem_id = rems_reviewed[-1] if rems_reviewed else None
                confidence *= 0.7  # Reduce confidence for inference

            # Extract clarification from next assistant response
            clarification_text = ""
            if i + 1 < len(turns) and turns[i + 1]['role'] == 'assistant':
                clarification_text = extract_clarification_content(turns[i + 1]['content'])

            # Infer target section
            target_section = infer_target_section(question, clarification_text)

            type_a.append({
                "question": question[:200],  # Truncate for preview
                "turn": turn['turn'],
                "rem_id": rem_id,
                "clarification_text": clarification_text,
                "target_section": target_section,
                "confidence": confidence
            })
        else:
            # Type B/C/D: New concept
            type_bcd.append({
                "question": question[:200],
                "turn": turn['turn'],
                "type": q_type,
                "confidence": confidence
            })

    return {
        "type_a": type_a,
        "type_bcd": type_bcd,
        "statistics": {
            "total_questions": len([t for t in turns if t['role'] == 'user']),
            "type_a_classified": len(type_a),
            "type_bcd_classified": len(type_bcd),
            "unclassified": len([t for t in turns if t['role'] == 'user']) - len(type_a) - len(type_bcd)
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description='Classify questions in review session',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--archived-file',
        required=True,
        help='Path to archived conversation file'
    )

    parser.add_argument(
        '--rems-reviewed',
        default='[]',
        help='JSON list of reviewed Rem IDs'
    )

    parser.add_argument(
        '--output',
        help='Output JSON file (default: stdout)'
    )

    args = parser.parse_args()

    try:
        # Parse arguments
        archived_file = Path(args.archived_file)
        if not archived_file.exists():
            print(f"❌ File not found: {archived_file}", file=sys.stderr)
            return 1

        rems_reviewed = json.loads(args.rems_reviewed)

        # Classify questions
        result = classify_review_questions(archived_file, rems_reviewed)

        # Output
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"✅ Classification saved to {output_path}", file=sys.stderr)
        else:
            # Print to stdout (for piping to other scripts)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        # Print statistics to stderr
        stats = result['statistics']
        print(f"\n📊 Classification Statistics:", file=sys.stderr)
        print(f"   Total questions: {stats['total_questions']}", file=sys.stderr)
        print(f"   Type A (Clarification): {stats['type_a_classified']}", file=sys.stderr)
        print(f"   Type B/C/D (New): {stats['type_bcd_classified']}", file=sys.stderr)
        print(f"   Unclassified: {stats['unclassified']}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
