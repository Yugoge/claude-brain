#!/usr/bin/env python3
"""
Workflow Orchestrator for /save Step 3.5
Enforces Domain Tutor Enrichment execution.

Usage:
    python scripts/archival/workflow_orchestrator.py \\
        --domain programming \\
        --isced-path "06.../0611-computer-use" \\
        --candidate-rems candidate_rems.json

Outputs: enriched_rems.json with typed_relations added
"""

import json
import sys
import argparse
from pathlib import Path

# Add scripts to path
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "scripts"))

from archival.get_domain_concepts import extract_domain_concepts, load_backlinks


def load_candidate_rems(file_path):
    """Load candidate Rems from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_tutor_prompt(domain, existing_concepts, candidate_rems):
    """
    Build minimal tutor prompt with existing concepts context.

    Returns: JSON-formatted prompt string
    """
    existing_list = [{"id": c["id"], "title": c["title"]} for c in existing_concepts]

    candidates_summary = []
    for rem in candidate_rems:
        candidates_summary.append({
            "concept_id": rem["id"],
            "title": rem["title"],
            "core_points": rem.get("core_points", [])
        })

    prompt = f"""Domain expert: {domain}

**Existing Concepts** ({len(existing_list)}):
{json.dumps(existing_list, indent=2, ensure_ascii=False)}

**Candidate Rems** ({len(candidates_summary)}):
{json.dumps(candidates_summary, indent=2, ensure_ascii=False)}

**Task**: Return JSON with typed_relations for each Rem.

**Rules**:
1. ONLY link to concepts in existing list
2. Use specific types: synonym, prerequisite_of, contrasts_with, etc.
3. Empty array if no relations found

**Output Format**:
{{
  "concept_extraction_guidance": {{
    "rem_suggestions": [
      {{
        "concept_id": "rem-id",
        "typed_relations": [
          {{"to": "existing-id", "type": "relation-type", "rationale": "why"}}
        ]
      }}
    ]
  }}
}}
"""
    return prompt


def merge_tutor_suggestions(candidate_rems, tutor_response_json):
    """
    Merge tutor's typed_relations into candidate Rems.

    Args:
        candidate_rems: Original candidate Rems list
        tutor_response_json: Parsed tutor JSON response

    Returns: Enriched Rems with typed_relations field
    """
    enriched = []

    # Extract tutor suggestions
    guidance = tutor_response_json.get("concept_extraction_guidance", {})
    suggestions = guidance.get("rem_suggestions", [])

    # Build lookup map
    tutor_map = {s["concept_id"]: s for s in suggestions}

    for rem in candidate_rems:
        rem_id = rem["id"]
        enriched_rem = rem.copy()

        # Add typed_relations from tutor
        if rem_id in tutor_map:
            tutor_data = tutor_map[rem_id]
            enriched_rem["typed_relations"] = tutor_data.get("typed_relations", [])
        else:
            enriched_rem["typed_relations"] = []

        enriched.append(enriched_rem)

    return enriched


def main():
    parser = argparse.ArgumentParser(description='Orchestrate Step 3.5 Domain Tutor Enrichment')
    parser.add_argument('--domain', required=True, help='Domain: programming|language|finance|science')
    parser.add_argument('--isced-path', required=True, help='ISCED detailed path (e.g., 0611-computer-use)')
    parser.add_argument('--candidate-rems', required=True, help='JSON file with candidate Rems')
    parser.add_argument('--output', default='enriched_rems.json', help='Output file path')
    parser.add_argument('--tutor-response', help='Manual tutor JSON response file (skip Task call)')

    args = parser.parse_args()

    try:
        # Load candidate Rems
        candidate_rems = load_candidate_rems(args.candidate_rems)
        print(f"✓ Loaded {len(candidate_rems)} candidate Rems", file=sys.stderr)

        # Load existing concepts
        backlinks = load_backlinks()
        existing_concepts = extract_domain_concepts(backlinks, args.isced_path)
        print(f"✓ Found {len(existing_concepts)} existing concepts in {args.isced_path}", file=sys.stderr)

        # Build tutor prompt
        tutor_prompt = build_tutor_prompt(args.domain, existing_concepts, candidate_rems)

        if args.tutor_response:
            # Manual mode: use provided tutor response
            with open(args.tutor_response, 'r', encoding='utf-8') as f:
                tutor_json = json.load(f)
            print(f"✓ Loaded tutor response from {args.tutor_response}", file=sys.stderr)
        else:
            # Automated mode: output prompt for main agent to call Task tool
            print("\n📋 TUTOR PROMPT (pass to Task tool):\n", file=sys.stderr)
            print(tutor_prompt, file=sys.stderr)
            print("\n⚠️  Main agent: Call Task tool with above prompt, save response to tutor_response.json", file=sys.stderr)
            print("Then re-run with: --tutor-response tutor_response.json\n", file=sys.stderr)
            return 0

        # Merge tutor suggestions
        enriched_rems = merge_tutor_suggestions(candidate_rems, tutor_json)
        print(f"✓ Enriched {len(enriched_rems)} Rems with typed_relations", file=sys.stderr)

        # Count relations added
        total_relations = sum(len(r.get("typed_relations", [])) for r in enriched_rems)
        print(f"✓ Total typed_relations added: {total_relations}", file=sys.stderr)

        # Save enriched Rems
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(enriched_rems, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved enriched Rems to: {args.output}", file=sys.stderr)
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
