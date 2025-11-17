#!/usr/bin/env python3
"""
Concept extraction module
Extracts concepts from conversation and checks for technical content
"""

import time
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from utils.token_estimation import estimate_tokens, check_token_limit, format_token_count

class ConceptExtractor:
    """Extract concepts from conversation content."""

    # Token limits
    MAX_CONVERSATION_TOKENS = 150000  # 150k tokens
    WARNING_THRESHOLD = 100000         # Warn at 100k

    def __init__(self):
        self.technical_indicators = [
            'error', 'function', 'class', 'algorithm', 'data', 'code',
            'implement', 'design', 'pattern', 'method', 'variable',
            'database', 'api', 'framework', 'library', 'module',
            '错误', '函数', '算法', '数据', '代码', '实现', '设计'
        ]

        # Cache for duplicate detection
        self.kb_dir = Path(__file__).parent.parent.parent / "knowledge-base"

    def should_extract(self, conversation_turns=None):
        """
        Check if there's content worth extracting.
        Early exit optimization for performance.
        """
        # For demo purposes, return True
        # In real implementation, would analyze conversation
        return True

    def has_technical_content(self, text):
        """Check if text contains technical indicators."""
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in self.technical_indicators)

    def check_conversation_size(self, conversation_turns: Optional[List[Dict]] = None) -> int:
        """
        Check conversation size and validate against token limits.

        Args:
            conversation_turns: List of conversation turns (optional, for demo uses estimate)

        Returns:
            Estimated token count

        Raises:
            ValueError: If conversation exceeds MAX_CONVERSATION_TOKENS
        """
        if conversation_turns is None:
            # Demo mode: return safe estimate
            return 5000

        # Calculate actual token count
        total_tokens = 0
        for turn in conversation_turns:
            content = turn.get('content', '')
            if isinstance(content, str):
                total_tokens += estimate_tokens(content)

        # Check limit
        if total_tokens > self.MAX_CONVERSATION_TOKENS:
            raise ValueError(
                f"Conversation too large: {format_token_count(total_tokens)}\n\n"
                f"🔴 SOLUTION: Split this session into smaller conversations\n"
                f"   Current size: {format_token_count(total_tokens)} "
                f"({total_tokens/self.MAX_CONVERSATION_TOKENS:.0%} of limit)\n"
                f"   Maximum safe size: {format_token_count(self.MAX_CONVERSATION_TOKENS)}\n"
                f"   Recommended: Split into {(total_tokens // self.MAX_CONVERSATION_TOKENS) + 1} sessions"
            )

        # Warn if approaching limit
        if total_tokens > self.WARNING_THRESHOLD:
            percentage = (total_tokens / self.MAX_CONVERSATION_TOKENS) * 100
            print(f"⚠️  Warning: Large conversation ({format_token_count(total_tokens)}, {percentage:.0f}% of limit)")

        return total_tokens

    def check_duplicate_concepts(self, candidate_concepts: List[Dict]) -> List[Dict]:
        """
        Check for duplicate concepts in knowledge base.

        Uses simple title similarity to detect potential duplicates.
        Warns user but doesn't block extraction (user can decide).

        Args:
            candidate_concepts: List of concept dicts with 'title' and 'content'

        Returns:
            List of dicts with 'concept' and 'similar_to' (if duplicates found)
        """
        duplicates = []

        if not self.kb_dir.exists():
            return duplicates

        # Scan all Rem files for title comparison
        existing_titles = []
        for md_file in self.kb_dir.rglob('*.md'):
            # Skip templates and index
            if '_template' in str(md_file) or '_index' in str(md_file):
                continue

            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    # Read first 10 lines to find title in frontmatter
                    for i, line in enumerate(f):
                        if i > 10:
                            break
                        if line.startswith('title:'):
                            title = line.replace('title:', '').strip().strip('"\'')
                            existing_titles.append({
                                'title': title.lower(),
                                'file': str(md_file)
                            })
                            break
            except Exception:
                continue

        # Check each candidate against existing titles
        for concept in candidate_concepts:
            concept_title = concept.get('title', '').lower()

            for existing in existing_titles:
                existing_title = existing['title']

                # Simple similarity: check if titles overlap significantly
                # (More sophisticated: use TF-IDF, but this is fast enough)
                words_candidate = set(concept_title.split())
                words_existing = set(existing_title.split())

                if not words_candidate or not words_existing:
                    continue

                # Jaccard similarity
                intersection = len(words_candidate & words_existing)
                union = len(words_candidate | words_existing)
                similarity = intersection / union if union > 0 else 0

                # Flag as potential duplicate if >60% similar
                if similarity > 0.6:
                    duplicates.append({
                        'concept': concept['title'],
                        'similar_to': existing['title'],
                        'similarity': similarity,
                        'existing_file': existing['file']
                    })

        return duplicates

    def extract_concepts(self, session_type="learn", conversation_turns=None):
        """
        Extract concepts from the conversation.

        Args:
            session_type: Type of session ('learn', 'review', 'ask')
            conversation_turns: List of conversation turns (optional)

        Returns:
            List of concept dictionaries

        Raises:
            ValueError: If conversation too large
        """
        # CRITICAL: Check conversation size before extraction
        token_count = self.check_conversation_size(conversation_turns)
        print(f"📊 Conversation size: {format_token_count(token_count)}")

        # Demo implementation - would extract from actual conversation
        concepts = []

        if session_type == "review":
            # Extract from review session
            concepts.append({
                'title': 'Review Session Concept',
                'type': 'review',
                'domain': 'general',
                'content': 'Concept extracted from review session',
                'tokens': 120
            })
        else:
            # Extract from learn session
            concepts.append({
                'title': 'Learning Session Concept',
                'type': 'learn',
                'domain': 'programming',
                'content': 'Concept extracted from learning session',
                'tokens': 100
            })

        # Check for duplicates (non-blocking, just warns)
        duplicates = self.check_duplicate_concepts(concepts)
        if duplicates:
            print(f"\n⚠️  Potential duplicate concepts detected:")
            for dup in duplicates:
                print(f"   • '{dup['concept']}' similar to existing '{dup['similar_to']}'")
                print(f"     Similarity: {dup['similarity']:.0%} | File: {dup['existing_file']}")
            print(f"\n   Review these before approving extraction.\n")

        return concepts

    def filter_fsrs_tests(self, conversation_turns):
        """
        Filter out FSRS test dialogues to avoid duplicate Rems.
        Returns filtered conversation.
        """
        # Pattern matching for FSRS tests
        fsrs_patterns = [
            "Rate your recall:",
            "How well did you remember",
            "FSRS rating",
            "Review quality:"
        ]

        filtered = []
        for turn in conversation_turns:
            # Check if this is a test turn
            is_test = any(pattern in turn.get('content', '')
                         for pattern in fsrs_patterns)
            if not is_test:
                filtered.append(turn)

        return filtered

    def classify_concepts(self, concepts):
        """
        Classify concepts by domain and type.
        """
        for concept in concepts:
            # Domain detection
            if not concept.get('domain'):
                concept['domain'] = self.detect_domain(concept['content'])

            # Type classification
            if not concept.get('type'):
                concept['type'] = 'general'

        return concepts

    def detect_domain(self, content):
        """Detect domain from content."""
        domain_keywords = {
            'programming': ['code', 'function', 'algorithm', 'programming'],
            'finance': ['option', 'stock', 'trading', 'delta', 'gamma'],
            'language': ['语言', 'grammar', 'vocabulary', 'pronunciation'],
            'science': ['physics', 'chemistry', 'biology', 'research']
        }

        content_lower = content.lower()
        for domain, keywords in domain_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return domain

        return 'general'