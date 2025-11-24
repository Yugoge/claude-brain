#!/usr/bin/env python3
"""
Format evidence from multiple hypotheses into comparison table.
Ensures balanced presentation of conflicting evidence.
"""

import json
import sys


def format_matrix(evidence_data: dict) -> str:
    """
    Generate markdown table comparing evidence across hypotheses.

    Input format:
    {
        "aspects": ["Aspect 1", "Aspect 2", ...],
        "hypotheses": {
            "A": {"aspect1": {"evidence": "...", "source": "...", "quality": "..."}, ...},
            "B": {...},
            "C": {...}
        }
    }
    """

    aspects = evidence_data.get("aspects", [])
    hypotheses = evidence_data.get("hypotheses", {})

    # Generate table header
    header = "| Aspect | " + " | ".join([f"Hypothesis {h}" for h in hypotheses.keys()]) + " | Assessment |\n"
    separator = "|" + "|".join(["---"] * (len(hypotheses) + 2)) + "|\n"

    # Generate rows
    rows = []
    for aspect in aspects:
        row = f"| **{aspect}** | "

        evidence_cells = []
        for hyp_id, hyp_data in hypotheses.items():
            aspect_evidence = hyp_data.get(aspect, {})
            evidence_text = aspect_evidence.get("evidence", "No evidence found")
            source = aspect_evidence.get("source", "")
            quality = aspect_evidence.get("quality", "")

            cell = f"{evidence_text}"
            if source:
                cell += f" (Source: {source})"
            if quality:
                cell += f" [{quality}]"

            evidence_cells.append(cell)

        row += " | ".join(evidence_cells)
        row += " | *See analysis* |\n"
        rows.append(row)

    return header + separator + "".join(rows)


def main():
    if len(sys.argv) < 2:
        print("Usage: format_evidence_matrix.py <evidence_json_file>")
        print("Or pipe JSON via stdin")
        sys.exit(1)

    # Read from file or stdin
    if sys.argv[1] == "-":
        data = json.load(sys.stdin)
    else:
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)

    table = format_matrix(data)
    print(table)


if __name__ == "__main__":
    main()
