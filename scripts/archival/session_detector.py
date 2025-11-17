#!/usr/bin/env python3
"""
Session detection module
Detects whether the session is a review or learning session
"""

import json
import time
from pathlib import Path
from datetime import datetime

class SessionDetector:
    """Detect session type and load relevant data with confidence scoring."""

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.8    # Strong indicators present
    MEDIUM_CONFIDENCE = 0.5  # Some indicators present
    LOW_CONFIDENCE = 0.3     # Weak indicators

    def __init__(self):
        self.history_file = Path('.review/history.json')
        self.session_type = "learn"
        self.rems_reviewed = []
        self.confidence_score = 1.0  # Default: high confidence

    def calculate_confidence(self, conversation_turns=None) -> float:
        """
        Calculate confidence score for session type detection.

        Uses multiple heuristics:
        - FSRS pattern presence (rating prompts, review dates)
        - Turn count (more turns = more reliable)
        - Technical keyword density
        - Multiple Rem ID references

        Args:
            conversation_turns: Optional conversation history

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if conversation_turns is None:
            # No conversation data, rely only on history file
            return 0.7 if self.history_file.exists() else 0.5

        confidence = 0.0
        total_weight = 0.0

        # Indicator 1: Turn count (longer conversations more reliable)
        turn_count = len(conversation_turns)
        if turn_count >= 10:
            confidence += 0.3
        elif turn_count >= 5:
            confidence += 0.2
        elif turn_count >= 3:
            confidence += 0.1
        total_weight += 0.3

        # Indicator 2: FSRS patterns (strong indicator for review sessions)
        fsrs_patterns = [
            "rate your recall",
            "how well did you remember",
            "fsrs rating",
            "review quality",
            "next review",
            "stability"
        ]

        fsrs_matches = 0
        technical_keywords = 0
        rem_id_references = 0

        for turn in conversation_turns:
            content = turn.get('content', '').lower()

            # Count FSRS patterns
            for pattern in fsrs_patterns:
                if pattern in content:
                    fsrs_matches += 1

            # Count technical keywords
            tech_keywords = ['function', 'class', 'algorithm', 'implement', 'code']
            for keyword in tech_keywords:
                if keyword in content:
                    technical_keywords += 1

            # Count Rem ID references ([[rem-id]] pattern)
            import re
            rem_refs = re.findall(r'\[\[([a-z0-9\-]+)\]\]', content)
            rem_id_references += len(rem_refs)

        # Indicator 2 weight: FSRS patterns
        if fsrs_matches >= 5:
            confidence += 0.3
        elif fsrs_matches >= 2:
            confidence += 0.2
        elif fsrs_matches >= 1:
            confidence += 0.1
        total_weight += 0.3

        # Indicator 3: Technical content density
        if technical_keywords >= 10:
            confidence += 0.2
        elif technical_keywords >= 5:
            confidence += 0.15
        elif technical_keywords >= 2:
            confidence += 0.1
        total_weight += 0.2

        # Indicator 4: Multiple Rem references (indicates review session)
        if rem_id_references >= 5:
            confidence += 0.2
        elif rem_id_references >= 2:
            confidence += 0.1
        total_weight += 0.2

        # Normalize confidence score
        if total_weight > 0:
            confidence = confidence / total_weight
        else:
            confidence = 0.5  # Default: medium confidence

        return min(1.0, max(0.0, confidence))

    def detect_session_type(self, conversation_turns=None):
        """
        Detect if this is a review or learning session with confidence scoring.

        Args:
            conversation_turns: Optional conversation history for heuristics

        Returns:
            Tuple of (session_type, rems_reviewed, confidence_score)
        """
        # Performance tracking
        start_time = time.time()

        # Lazy loading - only read if file exists
        if not self.history_file.exists():
            self.confidence_score = self.calculate_confidence(conversation_turns)
            return self.session_type, self.rems_reviewed, self.confidence_score

        try:
            with open(self.history_file) as f:
                history = json.load(f)

            # Check if last review was today
            today = datetime.now().strftime('%Y-%m-%d')

            if history.get('sessions'):
                last_session = history['sessions'][-1]
                if last_session.get('date') == today:
                    self.session_type = "review"
                    self.rems_reviewed = last_session.get('concepts_reviewed', [])

            load_time = time.time() - start_time
            if self.session_type == "review":
                print(f"⏱️  Loaded review history in {load_time:.2f}s")

        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  Error reading history: {e}")
            # Lower confidence if file read failed
            self.confidence_score = 0.4

        # Calculate confidence score based on multiple indicators
        self.confidence_score = self.calculate_confidence(conversation_turns)

        # Warn user if confidence is low
        if self.confidence_score < self.MEDIUM_CONFIDENCE:
            print(f"\n⚠️  Session type detection confidence: {self.confidence_score:.0%} (LOW)")
            print(f"   Detected as: {self.session_type}")
            print(f"   If this seems incorrect, please confirm before proceeding.\n")
        elif self.confidence_score < self.HIGH_CONFIDENCE:
            print(f"ℹ️  Session type confidence: {self.confidence_score:.0%} (MEDIUM)")

        return self.session_type, self.rems_reviewed, self.confidence_score

    def get_session_metadata(self):
        """Get metadata for the current session with confidence."""
        return {
            "type": self.session_type,
            "rems_reviewed": self.rems_reviewed,
            "timestamp": datetime.now().isoformat(),
            "fsrs_progress_saved": self.session_type == "review",
            "confidence_score": self.confidence_score,
            "confidence_level": (
                "HIGH" if self.confidence_score >= self.HIGH_CONFIDENCE
                else "MEDIUM" if self.confidence_score >= self.MEDIUM_CONFIDENCE
                else "LOW"
            )
        }