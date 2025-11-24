#!/usr/bin/env python3
"""
Categorize disagreements into fact/interpretation/value layers.
Helps users understand where evidence conflicts vs where frameworks differ.
"""

import json
import sys


def categorize_disagreements(evidence_data: dict) -> dict:
    """
    Analyze evidence and categorize disagreements.

    Returns:
    {
        "factual_layer": {"consensus": [...], "disputed": [...]},
        "interpretation_layer": {"framework_A": "...", "framework_B": "..."},
        "value_layer": {"priority_A": "...", "priority_B": "..."}
    }
    """

    # Simple heuristic categorization
    # In production, could use semantic analysis

    aspects = evidence_data.get("aspects", [])
    hypotheses = evidence_data.get("hypotheses", {})

    consensus_facts = []
    disputed_facts = []
    frameworks = {}

    for aspect in aspects:
        # Collect evidence for this aspect across hypotheses
        evidence_items = []
        for hyp_id, hyp_data in hypotheses.items():
            aspect_data = hyp_data.get(aspect, {})
            if aspect_data.get("evidence"):
                evidence_items.append({
                    "hypothesis": hyp_id,
                    "evidence": aspect_data["evidence"],
                    "quality": aspect_data.get("quality", "unknown")
                })

        # Check if evidence agrees or conflicts
        if len(evidence_items) > 1:
            # Simple check: if all evidence similar, it's consensus
            # Otherwise, it's disputed
            unique_claims = set(item["evidence"][:50] for item in evidence_items)

            if len(unique_claims) == 1:
                consensus_facts.append({
                    "aspect": aspect,
                    "agreed_fact": evidence_items[0]["evidence"]
                })
            else:
                disputed_facts.append({
                    "aspect": aspect,
                    "conflicting_claims": [
                        {
                            "hypothesis": item["hypothesis"],
                            "claim": item["evidence"],
                            "quality": item["quality"]
                        }
                        for item in evidence_items
                    ]
                })

    # Extract interpretation frameworks
    for hyp_id, hyp_data in hypotheses.items():
        framework_desc = hyp_data.get("framework", "No explicit framework")
        frameworks[hyp_id] = framework_desc

    result = {
        "factual_layer": {
            "consensus": consensus_facts,
            "disputed": disputed_facts
        },
        "interpretation_layer": {
            "frameworks": frameworks,
            "note": "Different interpretations of same facts"
        },
        "value_layer": {
            "note": "User must decide which values to prioritize",
            "considerations": [
                "Which evidence quality threshold do you apply?",
                "Which aspects matter most to you?",
                "What are your prior assumptions?"
            ]
        },
        "meta_analysis": {
            "consensus_count": len(consensus_facts),
            "dispute_count": len(disputed_facts),
            "agreement_ratio": len(consensus_facts) / (len(consensus_facts) + len(disputed_facts)) if (consensus_facts or disputed_facts) else 0
        }
    }

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_disagreements.py <evidence_json_file>")
        sys.exit(1)

    if sys.argv[1] == "-":
        data = json.load(sys.stdin)
    else:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)

    analysis = categorize_disagreements(data)
    print(json.dumps(analysis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
