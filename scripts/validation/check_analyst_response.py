#!/usr/bin/env python3
"""Validate analyst JSON response quality."""

import sys
import json


def validate_analyst_response(json_str, min_confidence=70, min_sources=5):
    """
    Check if analyst response meets quality thresholds.

    Args:
        json_str: JSON string from analyst
        min_confidence: Minimum confidence threshold (0-100)
        min_sources: Minimum number of sources required

    Returns:
        dict: {"valid": bool, "needs_escalation": bool, "reason": str}
    """
    try:
        data = json.loads(json_str)
        confidence = data.get("confidence", 0)
        sources = data.get("sources", [])

        if confidence < min_confidence:
            return {
                "valid": False,
                "needs_escalation": True,
                "reason": f"Low confidence: {confidence} < {min_confidence}"
            }

        if len(sources) < min_sources:
            return {
                "valid": False,
                "needs_escalation": True,
                "reason": f"Insufficient sources: {len(sources)} < {min_sources}"
            }

        return {"valid": True, "needs_escalation": False, "reason": "OK"}

    except Exception as e:
        return {"valid": False, "needs_escalation": True, "reason": str(e)}


if __name__ == "__main__":
    result = validate_analyst_response(
        sys.stdin.read(),
        min_confidence=int(sys.argv[1]) if len(sys.argv) > 1 else 70,
        min_sources=int(sys.argv[2]) if len(sys.argv) > 2 else 5
    )
    print(json.dumps(result))
