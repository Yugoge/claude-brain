#!/usr/bin/env python3
"""
Generate workflow checklist for /fact-check command
"""

import json

def main():
    todos = [
        {
            "content": "Step 1: Parse Input",
            "activeForm": "Step 1: Parsing Input",
            "status": "pending"
        },
        {
            "content": "Step 2: Dual Journalist Consultation (Pro/Con Verification)",
            "activeForm": "Step 2: Dual Journalist Consultation (Pro/Con Verification)",
            "status": "pending"
        },
        {
            "content": "Step 3: Validate and Parse Dual Journalist Responses",
            "activeForm": "Step 3: Validate and Parse Dual Journalist Responses",
            "status": "pending"
        },
        {
            "content": "Step 4: Synthesize Dual Perspectives and Respond Naturally",
            "activeForm": "Step 4: Synthesize Dual Perspectives and Respond Naturally",
            "status": "pending"
        },
        {
            "content": "Step 5: Multi-Turn Analysis Loop",
            "activeForm": "Step 5: Multi-Turn Analysis Loop",
            "status": "pending"
        },
        {
            "content": "Step 6: Natural Conclusion Detection",
            "activeForm": "Step 6: Natural Conclusion Detection",
            "status": "pending"
        },
        {
            "content": "Step 7: Post-Analysis Archival Prompt",
            "activeForm": "Step 7: Post-Analysis Archival Prompt",
            "status": "pending"
        },
        {
            "content": "Step 8: Handle Archival Response",
            "activeForm": "Step 8: Handle Archival Response",
            "status": "pending"
        }
    ]

    print(json.dumps(todos, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
