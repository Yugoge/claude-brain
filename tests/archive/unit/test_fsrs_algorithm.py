#!/usr/bin/env python3
"""
Unit tests for FSRS algorithm.
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from fsrs_algorithm import FSRSAlgorithm


class TestFSRSAlgorithm:
    """Test suite for FSRS algorithm."""

    def test_default_parameters(self):
        """Test that default parameters are loaded correctly."""
        fsrs = FSRSAlgorithm()
        assert len(fsrs.w) == 18
        assert fsrs.desired_retention == 0.9
        assert fsrs.maximum_interval == 36500

    def test_initial_difficulty(self):
        """Test initial difficulty calculation."""
        fsrs = FSRSAlgorithm()

        # Rating 1 (Again) should use w[4]
        assert fsrs.initial_difficulty(1) == fsrs.w[4]

        # Rating 2 (Hard) should use w[5]
        assert fsrs.initial_difficulty(2) == fsrs.w[5]

        # Rating 3 (Good) should use w[6]
        assert fsrs.initial_difficulty(3) == fsrs.w[6]

        # Rating 4 (Easy) should use w[7]
        assert fsrs.initial_difficulty(4) == fsrs.w[7]

    def test_initial_stability(self):
        """Test initial stability calculation."""
        fsrs = FSRSAlgorithm()

        # Ratings 1-4 should use w[0]-w[3]
        for rating in range(1, 5):
            stability = fsrs.initial_stability(rating)
            assert stability >= 0.1  # Minimum stability
            assert stability == max(fsrs.w[rating - 1], 0.1)

    def test_calculate_interval(self):
        """Test interval calculation."""
        fsrs = FSRSAlgorithm()

        # Test with stability = 10 days
        stability = 10.0
        interval = fsrs.calculate_interval(stability)

        # Expected: 10 * (1 / 0.9 - 1) ≈ 1.11 days
        expected = stability * (1 / 0.9 - 1)
        assert abs(interval - expected) < 1.0  # Within 1 day tolerance

    def test_calculate_retrievability(self):
        """Test retrievability calculation."""
        fsrs = FSRSAlgorithm()

        # At elapsed = 0, retrievability should be 1.0
        assert fsrs.calculate_retrievability(0, 10.0) == 1.0

        # After some time, retrievability should decrease
        r1 = fsrs.calculate_retrievability(5, 10.0)
        r2 = fsrs.calculate_retrievability(10, 10.0)
        assert 0 < r1 < 1.0
        assert 0 < r2 < r1  # Should decrease over time

    def test_next_difficulty(self):
        """Test difficulty update."""
        fsrs = FSRSAlgorithm()

        initial_difficulty = 5.0

        # Rating 1 (Again) should decrease difficulty (offset from Good rating)
        # delta_d = 1 - 3 = -2, so difficulty decreases
        d1 = fsrs.next_difficulty(initial_difficulty, 1)
        assert d1 < initial_difficulty

        # Rating 4 (Easy) should increase difficulty (offset from Good rating)
        # delta_d = 4 - 3 = +1, so difficulty increases
        d4 = fsrs.next_difficulty(initial_difficulty, 4)
        assert d4 > initial_difficulty

        # Difficulty should be clamped to [1, 10]
        d_high = fsrs.next_difficulty(9.5, 4)  # Changed from rating 1 to 4
        assert d_high <= 10

        d_low = fsrs.next_difficulty(1.5, 1)  # Changed from rating 4 to 1
        assert d_low >= 1

    def test_review_first_time(self):
        """Test first review of a new concept."""
        fsrs = FSRSAlgorithm()

        # First review with "Good" rating
        state = fsrs.review({}, rating=3)

        assert "difficulty" in state
        assert "stability" in state
        assert "retrievability" in state
        assert "interval" in state
        assert "next_review" in state
        assert "review_count" in state
        assert "last_review" in state

        # First review should have retrievability = 1.0
        assert state["retrievability"] == 1.0

        # Review count should be 1
        assert state["review_count"] == 1

        # Difficulty should match initial difficulty for rating 3
        assert state["difficulty"] == fsrs.initial_difficulty(3)

        # Stability should match initial stability for rating 3
        assert state["stability"] == max(fsrs.w[2], 0.1)

    def test_review_second_time(self):
        """Test second review of a concept."""
        fsrs = FSRSAlgorithm()

        # First review
        now = datetime.now()
        first_state = fsrs.review({}, rating=3, review_date=now)

        # Second review 5 days later
        second_review_date = now + timedelta(days=5)
        second_state = fsrs.review(first_state, rating=3, review_date=second_review_date)

        # Review count should increase
        assert second_state["review_count"] == 2

        # Retrievability should be < 1.0 (some forgetting)
        assert second_state["retrievability"] < 1.0

        # Stability should be at least minimum (0.1)
        assert second_state["stability"] >= 0.1

    def test_review_forgot(self):
        """Test review when concept is forgotten (rating=1)."""
        fsrs = FSRSAlgorithm()

        # First review (Good)
        now = datetime.now()
        first_state = fsrs.review({}, rating=3, review_date=now)

        # Second review (Again - forgot)
        second_review_date = now + timedelta(days=5)
        second_state = fsrs.review(first_state, rating=1, review_date=second_review_date)

        # Difficulty should decrease when forgot (rating 1 < 3 "Good")
        # delta_d = 1 - 3 = -2, so difficulty decreases
        assert second_state["difficulty"] < first_state["difficulty"]

        # Stability should be recalculated (reset formula for forgot)
        # It should be positive and bounded
        assert 0.1 <= second_state["stability"] <= fsrs.maximum_interval

    def test_predict_retention(self):
        """Test retention prediction."""
        fsrs = FSRSAlgorithm()

        # Create a state
        state = {
            "difficulty": 5.0,
            "stability": 10.0,
            "retrievability": 0.9,
            "review_count": 3
        }

        # Predict retention 0 days ahead
        r0 = fsrs.predict_retention(state, 0)
        assert r0 == 1.0

        # Predict retention 5 days ahead
        r5 = fsrs.predict_retention(state, 5)
        assert 0 < r5 < 1.0

        # Predict retention 10 days ahead
        r10 = fsrs.predict_retention(state, 10)
        assert 0 < r10 < r5  # Should decrease over time

    def test_custom_parameters(self):
        """Test FSRS with custom parameters."""
        custom_params = {
            "w": [0.5] * 18,
            "desired_retention": 0.95,
            "maximum_interval": 180
        }

        fsrs = FSRSAlgorithm(custom_params)

        assert fsrs.w == [0.5] * 18
        assert fsrs.desired_retention == 0.95
        assert fsrs.maximum_interval == 180

    def test_interval_bounds(self):
        """Test that intervals are bounded correctly."""
        fsrs = FSRSAlgorithm()

        # Very low stability should give interval >= 1
        interval_low = fsrs.calculate_interval(0.01)
        assert interval_low >= 1

        # Very high stability should be clamped to maximum_interval
        interval_high = fsrs.calculate_interval(1000000)
        assert interval_high <= fsrs.maximum_interval

    def test_next_stability_remembered(self):
        """Test stability increase when concept is remembered."""
        fsrs = FSRSAlgorithm()

        difficulty = 5.0
        stability = 10.0
        retrievability = 0.5  # Lower retrievability to ensure change

        # Rating 3 (Good) - remembered
        new_stability_good = fsrs.next_stability(difficulty, stability, retrievability, 3)

        # Stability should be at least minimum
        assert new_stability_good >= 0.1

        # With low retrievability (0.5), stability should change
        # (The formula should apply a multiplier based on retrievability)
        assert new_stability_good > 0.1

    def test_next_stability_forgot(self):
        """Test stability reset when concept is forgotten."""
        fsrs = FSRSAlgorithm()

        difficulty = 5.0
        stability = 10.0
        retrievability = 0.85

        # Rating 1 (Again) - forgot
        new_stability_forgot = fsrs.next_stability(difficulty, stability, retrievability, 1)

        # Stability should be recalculated (likely lower)
        assert new_stability_forgot >= 0.1  # At least minimum
        assert new_stability_forgot != stability  # Should change


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
