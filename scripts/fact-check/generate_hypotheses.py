#!/usr/bin/env python3
"""
Generate opposing hypotheses from a claim for parallel fact-checking.
Outputs 2-3 alternative interpretations to prevent single-narrative bias.
"""

import json
import sys


def generate_hypotheses(claim: str) -> dict:
    """
    Auto-generate opposing hypotheses from user's claim.

    Returns dict with:
    - hypotheses: List of 2-3 opposing interpretations
    - search_strategies: Suggested queries for each hypothesis
    """

    # Simple heuristic: detect claim structure and generate opposites
    # For production, this could use NLP, but keeping minimal

    hypotheses = {
        "original_claim": claim,
        "hypotheses": [
            {
                "id": "hypothesis_A",
                "statement": f"Claim is accurate: {claim}",
                "role": "advocate_for_A",
                "search_focus": "Evidence supporting the claim"
            },
            {
                "id": "hypothesis_B",
                "statement": f"Claim is inaccurate or misleading",
                "role": "advocate_for_B",
                "search_focus": "Counter-evidence and alternative explanations"
            },
            {
                "id": "hypothesis_C",
                "statement": "Claim requires reframing or additional context",
                "role": "advocate_for_C",
                "search_focus": "Alternative framings and missing nuance"
            }
        ],
        "search_strategies": {
            "A": [
                f'"{claim}" evidence',
                f'"{claim}" academic research',
                f'"{claim}" statistics'
            ],
            "B": [
                f'"{claim}" debunked',
                f'"{claim}" counter evidence',
                f'"{claim}" criticism'
            ],
            "C": [
                f'"{claim}" context',
                f'"{claim}" nuance',
                f'"{claim}" alternative explanation'
            ]
        }
    }

    return hypotheses


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: generate_hypotheses.py <claim>",
            "example": "generate_hypotheses.py 'Qing Dynasty suppressed Han literacy'"
        }, indent=2))
        sys.exit(1)

    claim = " ".join(sys.argv[1:])
    result = generate_hypotheses(claim)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
