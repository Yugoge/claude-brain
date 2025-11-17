#!/usr/bin/env python3
"""
Unit tests for FSRS parameter presets.
"""

import pytest
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from fsrs_parameters import load_preset, list_presets, PARAMETER_PRESETS
from fsrs_algorithm import FSRSAlgorithm


class TestFSRSParameters:
    """Test suite for FSRS parameter presets."""

    def test_default_preset_exists(self):
        """Test that default preset exists."""
        preset = load_preset("default")
        assert preset is not None
        assert "w" in preset
        assert "desired_retention" in preset
        assert "maximum_interval" in preset
        assert "description" in preset

    def test_all_presets_have_18_parameters(self):
        """Test that all presets have exactly 18 w parameters."""
        for name in PARAMETER_PRESETS:
            preset = load_preset(name)
            assert len(preset["w"]) == 18, f"Preset {name} has {len(preset['w'])} parameters"

    def test_conservative_preset(self):
        """Test conservative preset properties."""
        preset = load_preset("conservative")

        # Conservative should have higher retention target
        assert preset["desired_retention"] >= 0.9

        # Conservative should have shorter maximum interval
        assert preset["maximum_interval"] < 36500

    def test_aggressive_preset(self):
        """Test aggressive preset properties."""
        preset = load_preset("aggressive")

        # Aggressive should have lower retention target (trade retention for less reviews)
        assert preset["desired_retention"] <= 0.9

        # Aggressive should have longer maximum interval
        assert preset["maximum_interval"] == 36500

    def test_list_presets(self):
        """Test listing all presets."""
        presets = list_presets()

        assert "default" in presets
        assert "conservative" in presets
        assert "aggressive" in presets

        # All presets should have descriptions
        for name, description in presets.items():
            assert isinstance(description, str)
            assert len(description) > 0

    def test_invalid_preset_raises_error(self):
        """Test that loading invalid preset raises ValueError."""
        with pytest.raises(ValueError):
            load_preset("nonexistent")

    def test_presets_work_with_fsrs_algorithm(self):
        """Test that all presets can be used with FSRSAlgorithm."""
        for name in PARAMETER_PRESETS:
            preset = load_preset(name)

            # Create FSRS instance with preset
            fsrs = FSRSAlgorithm(preset)

            # Test that it works for basic review
            state = fsrs.review({}, rating=3)

            assert "difficulty" in state
            assert "stability" in state
            assert "interval" in state

    def test_default_preset_values(self):
        """Test default preset has expected values."""
        preset = load_preset("default")

        assert preset["desired_retention"] == 0.9
        assert preset["maximum_interval"] == 36500

        # Check first few w parameters match research values
        assert abs(preset["w"][0] - 0.4072) < 0.01
        assert abs(preset["w"][1] - 1.1829) < 0.01

    def test_preset_parameters_are_valid(self):
        """Test that all preset parameters are valid numbers."""
        for name in PARAMETER_PRESETS:
            preset = load_preset(name)

            # All w parameters should be positive numbers
            for i, w in enumerate(preset["w"]):
                assert isinstance(w, (int, float)), f"w[{i}] in {name} is not a number"
                assert w >= 0, f"w[{i}] in {name} is negative"

            # Retention should be between 0 and 1
            assert 0 < preset["desired_retention"] <= 1

            # Maximum interval should be positive
            assert preset["maximum_interval"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
