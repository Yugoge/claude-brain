#!/usr/bin/env python3
"""
Question classification module
Classifies questions into types A/B/C/D for appropriate Rem handling
"""

import re

class QuestionClassifier:
    """Classify questions for Rem update or creation decisions."""

    def __init__(self):
        # Compile regex patterns once for performance
        self.patterns = {
            'type_a': re.compile(
                r'(clarif|explain|what.*mean|什么意思|解释|说明)',
                re.IGNORECASE
            ),
            'type_b': re.compile(
                r'(what about|how about|那么.*怎么|what if|extend)',
                re.IGNORECASE
            ),
            'type_c': re.compile(
                r'(compare|differ|vs\.|versus|区别|对比|comparison)',
                re.IGNORECASE
            ),
            'type_d': re.compile(
                r'(in practice|practical|how to use|实践|应用|real.world)',
                re.IGNORECASE
            )
        }

    def classify_question(self, text):
        """
        Classify question into type A/B/C/D.
        Returns: question type and action.
        """
        # Check patterns in order of priority
        if self.patterns['type_a'].search(text):
            return 'A', 'update'  # Clarification - update existing Rem

        if self.patterns['type_c'].search(text):
            return 'C', 'create'  # Comparison - create comparison Rem

        if self.patterns['type_d'].search(text):
            return 'D', 'create'  # Application - create practical Rem

        if self.patterns['type_b'].search(text):
            return 'B', 'create'  # Extension - create new Rem

        # Default to extension type
        return 'B', 'create'

    def map_clarification_to_section(self, clarification_type):
        """
        Map clarification type to target Rem section.
        """
        mapping = {
            'definition': '## Core Memory Points',
            'example': '## Usage Scenario',
            'usage': '## Usage Scenario',
            'explanation': '## Core Memory Points',
            'detail': '## Details',
            'context': '## Context'
        }

        return mapping.get(clarification_type, '## Core Memory Points')

    def extract_clarification_content(self, question, answer):
        """
        Extract 2-3 concise sentences (<100 tokens) from answer.
        """
        # Simple extraction - take first 2-3 sentences
        sentences = answer.split('. ')[:3]
        clarification = '. '.join(sentences)

        # Truncate if too long
        if len(clarification) > 300:  # Approximate token limit
            clarification = clarification[:297] + '...'

        return clarification

    def batch_classify(self, questions):
        """
        Classify multiple questions at once.
        Returns list of (question, type, action) tuples.
        """
        results = []
        for q in questions:
            q_type, action = self.classify_question(q)
            results.append((q, q_type, action))

        return results