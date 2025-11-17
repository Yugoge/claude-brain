#!/usr/bin/env python3
"""
Unit tests for FSRS optimizer.
"""

import pytest
import sys
import os
import numpy as np

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from fsrs_optimizer import FSRSOptimizer, run_optimization
from fsrs_algorithm import FSRSAlgorithm


class TestFSRSOptimizer:
    """Test suite for FSRS optimizer."""

    def generate_synthetic_reviews(self, count: int = 50) -> list:
        """Generate synthetic review history for testing."""
        reviews = []
        concepts = ["concept_a", "concept_b", "concept_c", "concept_d"]

        for i in range(count):
            reviews.append({
                "concept": concepts[i % len(concepts)],
                "rating": np.random.choice([1, 2, 3, 4], p=[0.15, 0.15, 0.5, 0.2]),
                "elapsed_days": np.random.randint(1, 30),
                "difficulty": 5.0 + np.random.randn(),
                "stability": 10.0 + np.random.randn() * 3
            })

        return reviews

    def test_optimizer_initialization(self):
        """Test optimizer initialization."""
        reviews = self.generate_synthetic_reviews(10)
        optimizer = FSRSOptimizer(reviews)

        assert optimizer.history == reviews
        assert len(optimizer.default_params) == 18

    def test_should_optimize_insufficient_reviews(self):
        """Test that optimizer rejects insufficient review count."""
        reviews = self.generate_synthetic_reviews(20)  # Less than 30
        optimizer = FSRSOptimizer(reviews)

        should_run, reason = optimizer.should_optimize()

        assert not should_run
        assert "30+" in reason

    def test_should_optimize_insufficient_forgot_events(self):
        """Test that optimizer rejects insufficient forgot events."""
        reviews = []
        for i in range(40):
            reviews.append({
                "concept": f"concept_{i % 5}",
                "rating": 3,  # All "Good" - no forgot events
                "elapsed_days": 5,
                "difficulty": 5.0,
                "stability": 10.0
            })

        optimizer = FSRSOptimizer(reviews)
        should_run, reason = optimizer.should_optimize()

        assert not should_run
        assert "10+" in reason

    def test_should_optimize_insufficient_concepts(self):
        """Test that optimizer rejects insufficient concept diversity."""
        reviews = []
        for i in range(40):
            reviews.append({
                "concept": "concept_a",  # Only 1 concept
                "rating": np.random.choice([1, 2, 3, 4]),
                "elapsed_days": 5,
                "difficulty": 5.0,
                "stability": 10.0
            })

        optimizer = FSRSOptimizer(reviews)
        should_run, reason = optimizer.should_optimize()

        assert not should_run
        assert "3+" in reason

    def test_should_optimize_sufficient_data(self):
        """Test that optimizer accepts sufficient data."""
        reviews = []
        concepts = ["concept_a", "concept_b", "concept_c", "concept_d"]

        for i in range(50):
            reviews.append({
                "concept": concepts[i % len(concepts)],
                "rating": 1 if i % 4 == 0 else 3,  # 25% forgot rate
                "elapsed_days": 5,
                "difficulty": 5.0,
                "stability": 10.0
            })

        optimizer = FSRSOptimizer(reviews)
        should_run, reason = optimizer.should_optimize()

        assert should_run
        assert "Ready" in reason

    def test_loss_function_calculation(self):
        """Test that loss function calculates without errors."""
        reviews = self.generate_synthetic_reviews(30)
        optimizer = FSRSOptimizer(reviews)

        w = np.array(optimizer.default_params)
        loss = optimizer.loss_function(w)

        assert isinstance(loss, (float, np.floating))
        assert loss >= 0  # Loss should be non-negative

    def test_optimize_basic(self):
        """Test basic optimization run."""
        # Generate good synthetic data
        reviews = []
        concepts = ["concept_a", "concept_b", "concept_c", "concept_d"]

        for i in range(50):
            reviews.append({
                "concept": concepts[i % len(concepts)],
                "rating": 1 if i % 5 == 0 else 3,  # 20% forgot rate
                "elapsed_days": np.random.randint(1, 20),
                "difficulty": 5.0 + np.random.randn(),
                "stability": 10.0 + np.random.randn() * 2
            })

        optimizer = FSRSOptimizer(reviews)
        result = optimizer.optimize(max_iterations=50)

        assert "w" in result
        assert "loss" in result
        assert "baseline_loss" in result
        assert "improvement" in result
        assert "success" in result

        # Check that w parameters are reasonable
        assert len(result["w"]) == 18
        for w in result["w"]:
            assert isinstance(w, (float, int))

    def test_optimize_reduces_loss(self):
        """Test that optimization reduces loss."""
        reviews = self.generate_synthetic_reviews(50)
        optimizer = FSRSOptimizer(reviews)

        result = optimizer.optimize(max_iterations=100)

        # Optimized loss should be <= baseline loss
        assert result["loss"] <= result["baseline_loss"]

        # Improvement should be non-negative
        assert result["improvement"] >= 0

    def test_run_optimization_no_history(self):
        """Test run_optimization with no history file."""
        # This will fail gracefully if .review/history.json doesn't exist
        result = run_optimization("test_user")

        assert "optimized" in result
        # Should fail without history
        if not os.path.exists(".review/history.json"):
            assert not result["optimized"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
