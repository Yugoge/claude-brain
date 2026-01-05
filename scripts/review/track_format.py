#!/usr/bin/env python3
"""
Track Question Format History

Append question format to session history for diversity tracking.
Root cause fix: commit 3ed6b6f - stateless architecture requires external state

Usage:
    python scripts/review/track_format.py <format>

    format: short-answer | multiple-choice | cloze | problem-solving

Output: JSON confirmation
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def track_format(question_format):
    """
    Append format to history file.

    Args:
        question_format: One of 4 valid formats

    Returns:
        Dict with updated history
    """
    valid_formats = ['short-answer', 'multiple-choice', 'cloze', 'problem-solving']

    if question_format not in valid_formats:
        return {
            'success': False,
            'error': f'Invalid format: {question_format}. Must be one of: {", ".join(valid_formats)}'
        }

    format_file = Path('.review/format_history.json')

    # Load existing history
    if format_file.exists():
        try:
            with open(format_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {'recent_formats': []}
    else:
        data = {'recent_formats': []}

    # Append new format with timestamp
    data['recent_formats'].append({
        'format': question_format,
        'timestamp': datetime.now().isoformat()
    })

    # Keep last 20 formats (5 shown to agent, 20 stored for analytics)
    data['recent_formats'] = data['recent_formats'][-20:]

    # Ensure .review directory exists
    format_file.parent.mkdir(parents=True, exist_ok=True)

    # Write atomically
    temp_file = format_file.with_suffix('.tmp')
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    temp_file.replace(format_file)

    # Extract format strings for display (last 5)
    recent_format_strings = [f['format'] for f in data['recent_formats'][-5:]]

    return {
        'success': True,
        'format': question_format,
        'recent_formats': recent_format_strings,
        'total_tracked': len(data['recent_formats'])
    }

def main():
    if len(sys.argv) != 2:
        print(json.dumps({
            'success': False,
            'error': 'Usage: python track_format.py <format>'
        }), file=sys.stderr)
        sys.exit(1)

    question_format = sys.argv[1]
    result = track_format(question_format)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if not result['success']:
        sys.exit(1)

if __name__ == '__main__':
    main()
