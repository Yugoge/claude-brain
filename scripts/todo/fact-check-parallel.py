#!/usr/bin/env python3
"""
Generate workflow checklist for dual-track /fact-check command.
"""

import json


def main():
    todos = [
        {
            "content": "Step 1: Parse claim and generate hypotheses",
            "activeForm": "Step 1: Parsing claim and generating hypotheses",
            "status": "pending"
        },
        {
            "content": "Step 2: Track A - Consult journalist as advocate for hypothesis A",
            "activeForm": "Step 2: Track A - Consulting journalist as advocate for hypothesis A",
            "status": "pending"
        },
        {
            "content": "Step 3: Track B - Consult journalist as advocate for hypothesis B",
            "activeForm": "Step 3: Track B - Consulting journalist as advocate for hypothesis B",
            "status": "pending"
        },
        {
            "content": "Step 4: Track C - Consult journalist as advocate for hypothesis C",
            "activeForm": "Step 4: Track C - Consulting journalist as advocate for hypothesis C",
            "status": "pending"
        },
        {
            "content": "Step 5: Gather evidence for each hypothesis (parallel)",
            "activeForm": "Step 5: Gathering evidence for each hypothesis (parallel)",
            "status": "pending"
        },
        {
            "content": "Step 6: Format evidence comparison matrix",
            "activeForm": "Step 6: Formatting evidence comparison matrix",
            "status": "pending"
        },
        {
            "content": "Step 7: Analyze disagreements (fact/interpretation/value layers)",
            "activeForm": "Step 7: Analyzing disagreements (fact/interpretation/value layers)",
            "status": "pending"
        },
        {
            "content": "Step 8: Present findings with user-guided interpretation",
            "activeForm": "Step 8: Presenting findings with user-guided interpretation",
            "status": "pending"
        },
        {
            "content": "Step 9: Multi-turn clarification loop",
            "activeForm": "Step 9: Multi-turn clarification loop",
            "status": "pending"
        },
        {
            "content": "Step 10: Offer archival after conclusion",
            "activeForm": "Step 10: Offering archival after conclusion",
            "status": "pending"
        }
    ]

    print(json.dumps(todos, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
