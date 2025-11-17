#!/usr/bin/env python3
"""
FSRS parameter presets.

Default: Trained on 10,000+ reviews (general population)
Conservative: Lower stability increase (for difficult material)
Aggressive: Higher stability increase (for easy material)
"""

from typing import Dict

PARAMETER_PRESETS = {
    "default": {
        "w": [
            0.4072, 1.1829, 3.1262, 15.4722,
            7.2102, 0.5316, 1.0651, 0.0234,
            1.616, 0.1544, 1.0826, 1.9813,
            0.0953, 0.2975, 2.2042, 0.2407,
            2.9466, 0.5034
        ],
        "desired_retention": 0.9,
        "maximum_interval": 36500,
        "description": "Trained on 10,000+ reviews, suitable for most users"
    },
    "conservative": {
        "w": [
            0.3, 0.9, 2.5, 12.0,
            8.0, 0.6, 1.2, 0.1,
            1.4, 0.2, 1.0, 1.5,
            0.1, 0.3, 2.0, 0.3,
            2.5, 0.6
        ],
        "desired_retention": 0.95,
        "maximum_interval": 18250,
        "description": "Conservative scheduling for difficult material"
    },
    "aggressive": {
        "w": [
            0.5, 1.4, 3.5, 18.0,
            6.5, 0.45, 0.95, 0.01,
            1.8, 0.1, 1.15, 2.2,
            0.08, 0.25, 2.4, 0.2,
            3.2, 0.45
        ],
        "desired_retention": 0.85,
        "maximum_interval": 36500,
        "description": "Aggressive scheduling for easy material"
    }
}


def load_preset(name: str = "default") -> Dict:
    """
    Load parameter preset.

    Args:
        name: Preset name ("default", "conservative", "aggressive")

    Returns:
        Parameter dictionary with w, desired_retention, maximum_interval

    Raises:
        ValueError: If preset name is unknown
    """
    if name not in PARAMETER_PRESETS:
        raise ValueError(
            f"Unknown preset: {name}. "
            f"Available presets: {', '.join(PARAMETER_PRESETS.keys())}"
        )
    return PARAMETER_PRESETS[name]


def list_presets() -> Dict[str, str]:
    """
    List all available presets.

    Returns:
        Dictionary mapping preset name to description
    """
    return {
        name: params["description"]
        for name, params in PARAMETER_PRESETS.items()
    }


if __name__ == "__main__":
    # Display available presets
    print("Available FSRS Parameter Presets")
    print("=" * 50)
    for name, description in list_presets().items():
        print(f"\n{name}:")
        print(f"  {description}")
        preset = load_preset(name)
        print(f"  Desired Retention: {preset['desired_retention']}")
        print(f"  Maximum Interval: {preset['maximum_interval']} days")
