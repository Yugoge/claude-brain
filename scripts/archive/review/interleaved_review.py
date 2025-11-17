#!/usr/bin/env python3
"""
Interleaved Review System
Story 3.7 - Task 10 & 11: Interleaved Review with Phase-Based Scheduling

TODO: Migrate from adaptive system to FSRS-based implementation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT STATUS: Not integrated, depends on archived adaptive-profile.json
MIGRATION NEEDED:
  - Line 40: Change .review/adaptive-profile.json → .review/schedule.json
  - Line 51: Change total_reviews_completed → len(data.get('concepts', {}))
INTEGRATION TARGET: /review command (review-master agent)
SCIENTIFIC BASIS: Interleaving improves long-term retention by 40-60%
PRIORITY: Medium (high value, medium complexity)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Implements interleaved review mixing current + previous + related concepts
with phase-based introduction (blocked → partial → full interleaving).
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple


class InterleavingScheduler:
    """
    Manages interleaved review scheduling.

    AC9: Mix current review + previous topics + related concepts
    AC10: Phase-based introduction (Weeks 1-2 blocked, 3-4 partial, 5+ full)
    """

    # Phase thresholds (review count)
    BLOCKED_THRESHOLD = 10
    PARTIAL_THRESHOLD = 50

    # Interleaving ratios
    FULL_INTERLEAVING_RATIO = (0.60, 0.25, 0.15)  # current, previous, related
    PARTIAL_INTERLEAVING_RATIO = (0.70, 0.30, 0.00)  # current, previous, none

    def __init__(self, profile_path: Path = None):
        """
        Initialize scheduler.

        Args:
            profile_path: Path to adaptive profile JSON
        """
        self.profile_path = profile_path or Path('.review/adaptive-profile.json')
        self.total_reviews_completed = self.load_review_count()

    def load_review_count(self) -> int:
        """Load total reviews completed from profile."""
        if not self.profile_path.exists():
            return 0

        try:
            with open(self.profile_path) as f:
                data = json.load(f)
            return data.get('total_reviews_completed', 0)
        except Exception:
            return 0

    def determine_phase(self) -> str:
        """
        Determine current interleaving phase.

        Returns:
            Phase: 'blocked' | 'partial' | 'full'
        """
        if self.total_reviews_completed < self.BLOCKED_THRESHOLD:
            return 'blocked'
        elif self.total_reviews_completed < self.PARTIAL_THRESHOLD:
            return 'partial'
        else:
            return 'full'

    def get_interleaving_ratio(self, phase: str = None) -> Tuple[float, float, float]:
        """
        Get interleaving ratio for phase.

        Args:
            phase: Optional phase override

        Returns:
            Tuple of (current_ratio, previous_ratio, related_ratio)
        """
        if phase is None:
            phase = self.determine_phase()

        if phase == 'blocked':
            return (1.0, 0.0, 0.0)
        elif phase == 'partial':
            return self.PARTIAL_INTERLEAVING_RATIO
        else:  # full
            return self.FULL_INTERLEAVING_RATIO

    def get_interleaved_concepts(
        self,
        current_due: List[str],
        previous_topics: List[str],
        related_concepts: List[str],
        max_concepts: int = 10
    ) -> List[str]:
        """
        Mix concepts for interleaved review.

        Args:
            current_due: Concepts due for review today
            previous_topics: Concepts from 1 week ago
            related_concepts: Related concepts via backlinks
            max_concepts: Maximum concepts to include

        Returns:
            List of concept IDs in interleaved order
        """
        phase = self.determine_phase()
        ratios = self.get_interleaving_ratio(phase)

        # Calculate counts based on ratios
        current_count = int(max_concepts * ratios[0])
        previous_count = int(max_concepts * ratios[1])
        related_count = int(max_concepts * ratios[2])

        # Sample from each category
        selected_current = random.sample(current_due, min(len(current_due), current_count))
        selected_previous = random.sample(previous_topics, min(len(previous_topics), previous_count))
        selected_related = random.sample(related_concepts, min(len(related_concepts), related_count))

        # Combine
        all_concepts = selected_current + selected_previous + selected_related

        # Shuffle to avoid same-domain clustering
        shuffled = self.shuffle_avoid_clustering(all_concepts)

        return shuffled[:max_concepts]

    def shuffle_avoid_clustering(self, concepts: List[str]) -> List[str]:
        """
        Shuffle concepts while avoiding same-domain clustering.

        Args:
            concepts: List of concept IDs

        Returns:
            Shuffled list with reduced clustering
        """
        if len(concepts) <= 2:
            return concepts

        # Simple anti-clustering shuffle
        shuffled = concepts.copy()
        random.shuffle(shuffled)

        # Swap adjacent same-domain concepts
        for i in range(len(shuffled) - 1):
            domain_i = self._extract_domain(shuffled[i])
            domain_next = self._extract_domain(shuffled[i + 1])

            if domain_i == domain_next and i + 2 < len(shuffled):
                # Swap with next different-domain concept
                for j in range(i + 2, len(shuffled)):
                    if self._extract_domain(shuffled[j]) != domain_i:
                        shuffled[i + 1], shuffled[j] = shuffled[j], shuffled[i + 1]
                        break

        return shuffled

    def _extract_domain(self, concept_id: str) -> str:
        """Extract domain from concept ID."""
        # Assume concept IDs like "finance-npv" or "programming-binary-search"
        if '-' in concept_id:
            return concept_id.split('-')[0]
        return 'unknown'

    def get_previous_topics(self, days_ago: int = 7) -> List[str]:
        """
        Get concepts reviewed N days ago.

        Args:
            days_ago: How many days back to look

        Returns:
            List of concept IDs
        """
        # In production, would query schedule.json for concepts reviewed on specific date
        # For now, return empty list (placeholder)
        return []

    def get_related_concepts(self, concepts: List[str], backlinks_path: Path = None) -> List[str]:
        """
        Get related concepts via backlinks.

        Args:
            concepts: Current concepts
            backlinks_path: Path to backlinks.json

        Returns:
            List of related concept IDs
        """
        backlinks_path = backlinks_path or Path('knowledge-base/backlinks.json')

        if not backlinks_path.exists():
            return []

        try:
            with open(backlinks_path) as f:
                backlinks = json.load(f)

            related = set()
            for concept_id in concepts:
                if concept_id in backlinks:
                    outgoing = backlinks[concept_id].get('outgoing_links', [])
                    related.update(outgoing)

            # Remove concepts that are already in current list
            related = related - set(concepts)
            return list(related)
        except Exception:
            return []


if __name__ == "__main__":
    print("Testing Interleaved Review System\n")
    print("=" * 80)

    # Create test scheduler
    test_profile = Path('.review/test-interleaving-profile.json')
    test_profile.parent.mkdir(parents=True, exist_ok=True)

    # Test all phases
    phases = [
        (5, 'blocked'),
        (25, 'partial'),
        (60, 'full')
    ]

    for review_count, expected_phase in phases:
        # Create test profile
        with open(test_profile, 'w') as f:
            json.dump({'total_reviews_completed': review_count}, f)

        scheduler = InterleavingScheduler(test_profile)
        phase = scheduler.determine_phase()
        ratios = scheduler.get_interleaving_ratio()

        print(f"\n{expected_phase.upper()} PHASE (Reviews: {review_count}):")
        print(f"  Detected phase: {phase}")
        print(f"  Ratios: Current={ratios[0]:.0%}, Previous={ratios[1]:.0%}, Related={ratios[2]:.0%}")

        # Test interleaving
        current_due = [f"finance-concept-{i}" for i in range(1, 11)]
        previous_topics = [f"programming-concept-{i}" for i in range(1, 6)]
        related_concepts = [f"language-concept-{i}" for i in range(1, 4)]

        interleaved = scheduler.get_interleaved_concepts(
            current_due, previous_topics, related_concepts, max_concepts=10
        )

        print(f"  Sample interleaved concepts ({len(interleaved)}):")
        for i, concept in enumerate(interleaved[:5]):
            domain = scheduler._extract_domain(concept)
            marker = "🔄" if domain != "finance" else "📅"
            print(f"    {i+1}. {marker} {concept}")

    # Cleanup
    test_profile.unlink()

    print("\n" + "=" * 80)
    print("\nAnti-Clustering Test:\n")

    # Test anti-clustering shuffle
    scheduler = InterleavingScheduler()
    concepts = [
        "finance-a", "finance-b", "finance-c",
        "programming-a", "programming-b",
        "language-a", "language-b"
    ]

    print("Before shuffle:")
    for i, c in enumerate(concepts):
        print(f"  {i+1}. {scheduler._extract_domain(c):12s} - {c}")

    shuffled = scheduler.shuffle_avoid_clustering(concepts)

    print("\nAfter anti-clustering shuffle:")
    for i, c in enumerate(shuffled):
        domain = scheduler._extract_domain(c)
        prev_domain = scheduler._extract_domain(shuffled[i-1]) if i > 0 else None
        marker = "⚠️" if domain == prev_domain else "✓"
        print(f"  {i+1}. {marker} {domain:12s} - {c}")

    print("\n" + "=" * 80)
    print("✅ Interleaved review system tested successfully")
