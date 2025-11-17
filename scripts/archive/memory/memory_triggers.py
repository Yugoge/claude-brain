#!/usr/bin/env python3
"""
Auto-trigger logic for memory creation.

Automatically saves important concepts to memory based on specific triggers.

Integrated with UnifiedMemory for comprehensive auto-save functionality.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import re

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_memory_utils import AgentMemory
from unified_memory import UnifiedMemory


class MemoryTriggers:
    """Auto-trigger logic for memory creation."""

    def __init__(self, agent_memory: Optional[AgentMemory] = None):
        """
        Initialize memory triggers.

        Args:
            agent_memory: Optional AgentMemory instance
        """
        self.memory = agent_memory or AgentMemory()
        self.unified = UnifiedMemory()  # Unified memory interface

        # Trigger keywords for importance markers
        self.importance_markers = [
            "remember this",
            "important",
            "don't forget",
            "key point",
            "crucial",
            "critical",
            "note that",
            "keep in mind"
        ]

        # Correction indicators
        self.correction_markers = [
            "no, actually",
            "that's wrong",
            "that's incorrect",
            "not quite",
            "correction:",
            "let me correct",
            "actually, it's"
        ]

        # Preference indicators
        self.preference_markers = [
            "i prefer",
            "too hard",
            "too easy",
            "too fast",
            "too slow",
            "make it easier",
            "make it harder",
            "i like",
            "i don't like"
        ]

    def check_triggers(self, context: Dict) -> List[str]:
        """
        Check all triggers and save to memory if conditions met.

        Args:
            context: Dictionary with conversation context

        Returns:
            List of triggered actions
        """
        triggered_actions = []

        # Trigger 1: New concept detected
        if context.get("new_concept"):
            self._trigger_new_concept(context)
            triggered_actions.append("new_concept")

        # Trigger 2: Explicit importance marker
        if self._detect_importance_marker(context.get("user_message", "")):
            self._trigger_importance_marker(context)
            triggered_actions.append("importance_marker")

        # Trigger 3: Repeated discussion (mentioned 3+ times)
        if context.get("mention_count", 0) >= 3:
            self._trigger_repeated_mention(context)
            triggered_actions.append("repeated_mention")

        # Trigger 4: User correction
        if self._detect_correction(context.get("user_message", "")):
            self._trigger_user_correction(context)
            triggered_actions.append("user_correction")

        # Trigger 5: Preference feedback
        pref = self._extract_preference(context.get("user_message", ""))
        if pref:
            self._trigger_preference_update(pref)
            triggered_actions.append("preference_update")

        # Trigger 6: Struggle detected
        if context.get("struggle_detected"):
            self._trigger_struggle(context)
            triggered_actions.append("struggle")

        # Trigger 7: Poor review performance
        if context.get("review_incorrect"):
            self._trigger_review_failure(context)
            triggered_actions.append("review_failure")

        # Trigger 8: Conversation archival
        if context.get("archival_event"):
            self._trigger_archival(context)
            triggered_actions.append("archival")

        return triggered_actions

    def _detect_importance_marker(self, message: str) -> bool:
        """Detect explicit importance markers in user message."""
        message_lower = message.lower()
        return any(marker in message_lower for marker in self.importance_markers)

    def _detect_correction(self, message: str) -> bool:
        """Detect user correction indicators."""
        message_lower = message.lower()
        return any(marker in message_lower for marker in self.correction_markers)

    def _extract_preference(self, message: str) -> Optional[Dict]:
        """Extract preference from user message."""
        message_lower = message.lower()

        # Check for preference markers
        for marker in self.preference_markers:
            if marker in message_lower:
                # Extract preference type and value
                if "too hard" in message_lower or "make it easier" in message_lower:
                    return {"key": "difficulty", "value": "easy"}
                elif "too easy" in message_lower or "make it harder" in message_lower:
                    return {"key": "difficulty", "value": "hard"}
                elif "too fast" in message_lower:
                    return {"key": "learning_pace", "value": "slow"}
                elif "too slow" in message_lower:
                    return {"key": "learning_pace", "value": "fast"}
                elif "i prefer" in message_lower:
                    # Generic preference - extract from context
                    return {"key": "preference", "value": message}

        return None

    # Trigger implementations

    def _trigger_new_concept(self, context: Dict) -> bool:
        """Trigger 1: Save new concept to memory."""
        try:
            concept_name = context.get("concept_name")
            domain = context.get("domain", "general")
            metadata = {
                "source": "auto-trigger",
                "reason": "new_concept",
                "timestamp": datetime.now().isoformat()
            }

            success = self.memory.save_concept(concept_name, domain, metadata)
            if success:
                print(f"✅ Auto-saved new concept: {concept_name}")
            return success

        except Exception as e:
            print(f"⚠️  Auto-trigger error (new_concept): {e}")
            return False

    def _trigger_importance_marker(self, context: Dict) -> bool:
        """Trigger 2: Save user-flagged important content."""
        try:
            user_message = context.get("user_message", "")
            domain = context.get("domain", "general")

            # Save as high-importance observation
            concept_name = context.get("concept_name", "important_note")

            # Check if concept exists, if not create it
            existing = self.memory.get_concept(concept_name)
            if not existing:
                self.memory.save_concept(concept_name, domain, {
                    "user_flagged": True,
                    "auto_trigger": True,
                    "importance": "high"
                })

            # Add observation
            self.memory.add_observation(
                concept_name,
                f"User flagged as important: {user_message[:200]}"
            )
            print(f"✅ Auto-saved user-flagged content to: {concept_name}")
            return True

        except Exception as e:
            print(f"⚠️  Auto-trigger error (importance_marker): {e}")
            return False

    def _trigger_repeated_mention(self, context: Dict) -> bool:
        """Trigger 3: Update importance for repeatedly mentioned concept."""
        try:
            concept_name = context.get("concept_name")
            mention_count = context.get("mention_count", 0)

            # Add observation about repeated mention
            self.memory.add_observation(
                concept_name,
                f"Mentioned {mention_count} times - high importance indicator"
            )
            print(f"✅ Auto-updated importance for: {concept_name} ({mention_count} mentions)")
            return True

        except Exception as e:
            print(f"⚠️  Auto-trigger error (repeated_mention): {e}")
            return False

    def _trigger_user_correction(self, context: Dict) -> bool:
        """Trigger 4: Save user correction."""
        try:
            correction = context.get("correction", context.get("user_message", ""))
            domain = context.get("domain", "general")

            # Save as correction observation
            self.memory.save_concept(
                "user_corrections",
                "context",
                {
                    "correction": correction,
                    "timestamp": datetime.now().isoformat()
                }
            )
            print(f"✅ Auto-saved user correction")
            return True

        except Exception as e:
            print(f"⚠️  Auto-trigger error (user_correction): {e}")
            return False

    def _trigger_preference_update(self, preference: Dict) -> bool:
        """Trigger 5: Update user preference."""
        try:
            key = preference.get("key")
            value = preference.get("value")

            success = self.memory.update_preference(key, value)
            if success:
                print(f"✅ Auto-updated preference: {key} = {value}")
            return success

        except Exception as e:
            print(f"⚠️  Auto-trigger error (preference_update): {e}")
            return False

    def _trigger_struggle(self, context: Dict) -> bool:
        """Trigger 6: Track concept struggle."""
        try:
            concept_name = context.get("concept_name")
            difficulty_score = context.get("difficulty_score", 0.8)
            domain = context.get("domain", "general")

            success = self.memory.track_struggle(concept_name, difficulty_score, domain)
            if success:
                print(f"✅ Auto-tracked struggle: {concept_name} (difficulty={difficulty_score})")
            return success

        except Exception as e:
            print(f"⚠️  Auto-trigger error (struggle): {e}")
            return False

    def _trigger_review_failure(self, context: Dict) -> bool:
        """Trigger 7: Track poor review performance."""
        try:
            concept_name = context.get("concept_name")
            domain = context.get("domain", "general")

            # Save as struggle
            success = self.memory.track_struggle(concept_name, difficulty=0.9, domain=domain)

            # Add review failure observation
            self.memory.add_observation(
                concept_name,
                f"Review incorrect: {datetime.now().isoformat()}"
            )

            if success:
                print(f"✅ Auto-tracked review failure: {concept_name}")
            return success

        except Exception as e:
            print(f"⚠️  Auto-trigger error (review_failure): {e}")
            return False

    def _trigger_archival(self, context: Dict) -> bool:
        """Trigger 8: Save concepts from archived conversation."""
        try:
            concepts = context.get("concepts", [])
            conversation_id = context.get("conversation_id")

            saved_count = 0
            for concept in concepts:
                success = self.memory.save_concept(
                    concept.get("name"),
                    concept.get("domain", "general"),
                    {
                        "source": "archived-conversation",
                        "conversation_id": conversation_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                if success:
                    saved_count += 1

            print(f"✅ Auto-saved {saved_count}/{len(concepts)} concepts from archival")
            return saved_count > 0

        except Exception as e:
            print(f"⚠️  Auto-trigger error (archival): {e}")
            return False

    # ========== Unified Memory Auto-Save Triggers ==========

    def after_ask_session(
        self,
        question: str,
        answer: str,
        concepts: List[str],
        domain: Optional[str] = None
    ) -> bool:
        """
        Auto-save trigger after /ask session.

        Args:
            question: User question
            answer: Answer provided
            concepts: Concepts discussed
            domain: Optional domain

        Returns:
            True if successful, False otherwise
        """
        try:
            self.unified.after_ask_session(question, answer, concepts, domain)
            print(f"✅ Auto-saved {len(concepts)} concepts from /ask session")
            return True
        except Exception as e:
            print(f"⚠️  Auto-trigger error (after_ask_session): {e}")
            return False

    def after_learning_session(
        self,
        material: str,
        concepts_learned: List[str],
        preferences: Optional[Dict] = None,
        domain: Optional[str] = None
    ) -> bool:
        """
        Auto-save trigger after learning session.

        Args:
            material: Learning material name
            concepts_learned: Concepts learned
            preferences: User preferences observed
            domain: Optional domain

        Returns:
            True if successful, False otherwise
        """
        try:
            self.unified.after_learning_session(
                material, concepts_learned, preferences, domain
            )
            print(f"✅ Auto-saved learning session: {len(concepts_learned)} concepts")
            return True
        except Exception as e:
            print(f"⚠️  Auto-trigger error (after_learning_session): {e}")
            return False

    def after_review_session(
        self,
        concept: str,
        performance: Dict,
        domain: Optional[str] = None
    ) -> bool:
        """
        Auto-save trigger after review session.

        Args:
            concept: Concept reviewed
            performance: Performance data (correct, rating, etc.)
            domain: Optional domain

        Returns:
            True if successful, False otherwise
        """
        try:
            self.unified.after_review_session(concept, performance, domain)
            if not performance.get("correct", True):
                print(f"✅ Auto-tracked struggle from review: {concept}")
            return True
        except Exception as e:
            print(f"⚠️  Auto-trigger error (after_review_session): {e}")
            return False

    def after_archival(
        self,
        conversation_id: str,
        concepts_extracted: List[str],
        domain: Optional[str] = None
    ) -> bool:
        """
        Auto-save trigger after conversation archival.

        Args:
            conversation_id: Conversation ID
            concepts_extracted: Concepts extracted from conversation
            domain: Optional domain

        Returns:
            True if successful, False otherwise
        """
        try:
            self.unified.after_archival(conversation_id, concepts_extracted, domain)
            print(f"✅ Auto-saved archival: {len(concepts_extracted)} concepts")
            return True
        except Exception as e:
            print(f"⚠️  Auto-trigger error (after_archival): {e}")
            return False


def main():
    """CLI interface for memory triggers."""
    import argparse

    parser = argparse.ArgumentParser(description="Memory Auto-Triggers")
    parser.add_argument("command", choices=["test", "check"])
    parser.add_argument("--message", help="User message to analyze")
    parser.add_argument("--concept", help="Concept name")
    parser.add_argument("--domain", default="general", help="Domain")

    args = parser.parse_args()
    triggers = MemoryTriggers()

    if args.command == "test":
        # Test trigger detection
        context = {
            "user_message": args.message or "Remember this: Python uses duck typing",
            "concept_name": args.concept or "test-concept",
            "domain": args.domain,
            "new_concept": True
        }

        print(f"\n🔍 Testing triggers with context:\n{context}\n")
        triggered = triggers.check_triggers(context)
        print(f"\n✅ Triggered: {', '.join(triggered) if triggered else 'None'}")

    elif args.command == "check":
        # Check specific message for markers
        message = args.message or ""
        print(f"\n🔍 Analyzing message: '{message}'\n")
        print(f"Importance marker: {triggers._detect_importance_marker(message)}")
        print(f"Correction marker: {triggers._detect_correction(message)}")

        pref = triggers._extract_preference(message)
        if pref:
            print(f"Preference: {pref}")


if __name__ == "__main__":
    main()
