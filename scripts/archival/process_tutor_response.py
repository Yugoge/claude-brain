#!/usr/bin/env python3
"""
Process domain tutor consultation response
Extracts refined Rem suggestions from tutor's JSON output
"""
import sys
import json

def parse_tutor_response(tutor_response_json):
    """Parse tutor's JSON and extract refined Rem suggestions."""
    try:
        guidance = json.loads(tutor_response_json)['concept_extraction_guidance']

        refined_rems = []
        for suggestion in guidance['rem_suggestions']:
            rem = {
                'concept_id': suggestion['concept_id'],
                'title': suggestion['title'],
                'core_points': suggestion['core_content'].split('\n'),
                'usage_scenario': suggestion.get('usage_scenario_suggestion', ''),
                'common_mistakes_from_tutor': suggestion.get('common_mistakes_suggestion', []),
                'academic_source': suggestion.get('academic_source', '')
            }

            # v2.0: Support typed_relations (preferred)
            if 'typed_relations' in suggestion:
                rem['typed_relations'] = suggestion['typed_relations']
            # Fallback to v1.0: related_to (for backward compatibility)
            elif 'related_to' in suggestion:
                rem['related'] = suggestion['related_to']
            else:
                rem['typed_relations'] = []  # Empty if neither provided

            refined_rems.append(rem)

        return refined_rems

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Tutor consultation failed: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    # Read from stdin or command line arg
    if len(sys.argv) > 1:
        tutor_json = sys.argv[1]
    else:
        tutor_json = sys.stdin.read()

    result = parse_tutor_response(tutor_json)
    if result:
        print(json.dumps(result, indent=2))
    else:
        sys.exit(1)
