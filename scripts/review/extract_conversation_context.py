#!/usr/bin/env python3
"""
Extract key context from large conversation files using pattern matching.

Purpose: Fallback for review-master when conversation files exceed Read tool limits (>2000 lines)
Root Cause: Commit c11f968 added conversation_source but no fallback for large files
Strategy: Search for user questions and keywords instead of reading entire file

Usage:
    python extract_conversation_context.py <conversation_file_path>

Output: JSON with extracted questions and keywords
Exit Codes:
    0 = Success
    1 = File not found or invalid
    2 = Extraction failed
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Optional


def extract_user_questions(file_path: Path) -> List[str]:
    """
    Extract user questions from conversation file using pattern matching.

    Searches for:
    - Lines starting with "### User"
    - Lines starting with "**User**:"
    - Lines containing question marks in user sections

    Returns list of extracted questions (max 10 most relevant).
    """
    questions = []
    in_user_section = False
    current_question = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Detect user section markers
                if line.startswith('### User') or line.startswith('**User**'):
                    in_user_section = True
                    current_question = []
                    continue

                # Detect section end (next speaker)
                if line.startswith('### ') or line.startswith('**Assistant**') or line.startswith('**Agent**'):
                    if current_question:
                        questions.append(' '.join(current_question))
                        current_question = []
                    in_user_section = False
                    continue

                # Extract questions from user section
                if in_user_section and line:
                    # If line contains question mark, it's a question
                    if '?' in line or '什么' in line or '为什么' in line or '怎么' in line:
                        current_question.append(line)
                    # Also capture context lines (non-empty)
                    elif current_question:
                        current_question.append(line)

        # Add last question if exists
        if current_question:
            questions.append(' '.join(current_question))

        # Return top 10 most relevant (filter out very short questions)
        questions = [q for q in questions if len(q) > 20]
        return questions[:10]

    except Exception as e:
        print(f"Error extracting questions: {e}", file=sys.stderr)
        return []


def extract_key_topics(file_path: Path) -> List[str]:
    """
    Extract key topics from conversation metadata.

    Searches frontmatter for:
    - tags
    - title
    - domain
    - concepts extracted

    Returns list of key topics/concepts.
    """
    topics = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter (between --- delimiters)
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
        if not frontmatter_match:
            return []

        frontmatter = frontmatter_match.group(1)

        # Extract title
        title_match = re.search(r'title:\s*["\']?(.+?)["\']?\s*$', frontmatter, re.MULTILINE)
        if title_match:
            topics.append(title_match.group(1))

        # Extract domain
        domain_match = re.search(r'domain:\s*(\S+)', frontmatter)
        if domain_match:
            topics.append(domain_match.group(1))

        # Extract tags
        tags_match = re.search(r'tags:\s*\[(.*?)\]', frontmatter)
        if tags_match:
            tags = [tag.strip().strip('"\'') for tag in tags_match.group(1).split(',')]
            topics.extend(tags[:5])  # Top 5 tags

        # Extract concepts from body (wikilinks)
        concepts = re.findall(r'\[\[([^\]]+)\]\]', content)
        topics.extend(concepts[:5])  # Top 5 concepts

        return topics[:15]  # Max 15 topics

    except Exception as e:
        print(f"Error extracting topics: {e}", file=sys.stderr)
        return []


def extract_summary(file_path: Path) -> Optional[str]:
    """Extract summary section from conversation if available."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for summary section
        summary_match = re.search(r'## Summary\s*\n\s*(.+?)(?:\n\n|\n##)', content, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
            # Limit to 500 chars
            if len(summary) > 500:
                summary = summary[:500] + "..."
            return summary

        return None

    except Exception as e:
        print(f"Error extracting summary: {e}", file=sys.stderr)
        return None


def extract_conversation_context(file_path: str) -> Dict:
    """
    Main extraction function.

    Args:
        file_path: Path to conversation file

    Returns:
        Dict with extracted context:
        {
            "success": bool,
            "file_path": str,
            "line_count": int,
            "extraction_method": "search-based",
            "user_questions": List[str],
            "key_topics": List[str],
            "summary": Optional[str],
            "error": Optional[str]
        }
    """
    path = Path(file_path)

    # Validate file exists
    if not path.exists():
        return {
            "success": False,
            "file_path": file_path,
            "error": f"File not found: {file_path}"
        }

    # Count lines
    try:
        with open(path, 'r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f)
    except Exception as e:
        return {
            "success": False,
            "file_path": file_path,
            "error": f"Cannot read file: {e}"
        }

    # Extract context
    questions = extract_user_questions(path)
    topics = extract_key_topics(path)
    summary = extract_summary(path)

    return {
        "success": True,
        "file_path": file_path,
        "line_count": line_count,
        "extraction_method": "search-based",
        "user_questions": questions,
        "key_topics": topics,
        "summary": summary,
        "error": None
    }


def main():
    """CLI entry point."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <conversation_file_path>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Extract key context from conversation files too large for Read tool.", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    # Extract context
    result = extract_conversation_context(file_path)

    # Print JSON result
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Exit with appropriate code
    if result["success"]:
        sys.exit(0)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
