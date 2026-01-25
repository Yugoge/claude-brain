#!/usr/bin/env python3
"""
Workflow Orchestrator for /save Step 3.5
Enforces Domain Tutor Enrichment execution.

Usage:
    source venv/bin/activate && source venv/bin/activate && python scripts/archival/workflow_orchestrator.py \\
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
from archival.relation_types import ALL_TYPES, PAIRED_TYPES, SYMMETRIC_TYPES, LEXICAL_TYPES


def validate_rem_id(rem_id):
    """
    Validate rem_id format (kebab-case, lowercase, no spaces).

    Returns: (is_valid, error_message)
    """
    import re

    if not rem_id:
        return (False, "rem_id is empty")

    if ' ' in rem_id:
        return (False, f"contains spaces (use hyphens)")

    if rem_id != rem_id.lower():
        return (False, f"contains uppercase (use lowercase)")

    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', rem_id):
        return (False, f"invalid format (use kebab-case: a-z, 0-9, hyphens only)")

    if len(rem_id) > 100:
        return (False, f"too long (max 100 chars, got {len(rem_id)})")

    return (True, None)


def load_candidate_rems(file_path=None, json_string=None):
    """
    Load and validate candidate Rems from JSON file or inline JSON string.

    Args:
        file_path: Path to JSON file (legacy)
        json_string: Inline JSON string (preferred)

    Returns: List of candidate Rems
    """
    if json_string:
        rems = json.loads(json_string)
    elif file_path:
        with open(file_path, 'r', encoding='utf-8') as f:
            rems = json.load(f)
    else:
        raise ValueError("Must provide either file_path or json_string")

    # Validate rem_id format for all candidate Rems
    errors = []
    for i, rem in enumerate(rems):
        rem_id = rem.get("rem_id", "")
        is_valid, error_msg = validate_rem_id(rem_id)
        if not is_valid:
            errors.append(f"Rem #{i+1} '{rem_id}': {error_msg}")

    if errors:
        raise ValueError(f"Invalid candidate Rems:\n" + "\n".join(f"  - {e}" for e in errors))

    return rems


def build_tutor_prompt(domain, existing_concepts, candidate_rems):
    """
    Build minimal tutor prompt with support for inter-candidate relations.

    Returns: JSON-formatted prompt string
    """
    existing_list = [{"rem_id": c["rem_id"], "title": c["title"]} for c in existing_concepts]

    candidates_summary = []
    for rem in candidate_rems:
        candidates_summary.append({
            "concept_id": rem["rem_id"],
            "title": rem["title"],
            "core_points": rem.get("core_points", [])
        })

    # Extract valid IDs: BOTH existing concepts AND candidate Rems
    existing_ids = [c["rem_id"] for c in existing_concepts]
    candidate_ids = [r["rem_id"] for r in candidate_rems]
    all_valid_ids = existing_ids + candidate_ids  # Support inter-candidate relations

    # Include core_points for deduplication
    existing_list_detailed = []
    for c in existing_concepts:
        existing_list_detailed.append({
            "rem_id": c["rem_id"],
            "title": c["title"],
            "core_points": c.get("core_points", [])[:3]  # First 3 points for comparison
        })

    prompt = f"""Domain expert: {domain}

**CRITICAL**: Use EXACT concept_id values from the lists below. DO NOT create new IDs.

**Existing Concepts** ({len(existing_list_detailed)}):
{json.dumps(existing_list_detailed, indent=2, ensure_ascii=False)}

**Candidate Rems** ({len(candidates_summary)}) - NEW in this session:
{json.dumps(candidates_summary, indent=2, ensure_ascii=False)}

**Valid rem_id values** (use these EXACTLY in "to" fields of typed_relations):
{json.dumps(all_valid_ids, ensure_ascii=False)}

**Tasks**:
1. Deduplication: Check if each candidate duplicates existing Rem content (semantic comparison, not title matching)
2. Typed Relations: For new Rems only, suggest pedagogically relevant relations

**Rules**:
1. Use "concept_id" from Candidate Rems list (the new concepts being created)
2. In "to" field, reference IDs from:
   - Existing concepts (pedagogical relations to prior knowledge)
   - Other candidate Rems (inter-concept relations in this batch)
3. Prioritize:
   - Strong conceptual relations (prerequisite_of, uses, defines, triggers)
   - Relations within same topic/conversation
   - Inter-candidate relations when concepts are tightly coupled
4. DO NOT create composite, normalized, or descriptive IDs
5. Use ONLY these relation types (from RELATION_TYPES.md standard):
   {json.dumps(sorted(ALL_TYPES), ensure_ascii=False)}

   Paired types (use correct direction):
   {json.dumps({k: v for k, v in sorted(PAIRED_TYPES.items())}, indent=2, ensure_ascii=False)}

   Symmetric types (bidirectional allowed):
   {json.dumps(sorted(SYMMETRIC_TYPES), ensure_ascii=False)}

   Lexical types (language-specific):
   {json.dumps(sorted(LEXICAL_TYPES), ensure_ascii=False)}

6. Use field name 'type' (NOT 'relation_type') in your JSON response
7. Empty array if no strong pedagogical relations exist

**Output Format**:
{{
  "concept_extraction_guidance": {{
    "rem_suggestions": [
      {{
        "concept_id": "exact-id-from-valid-list",
        "deduplication_status": "new|duplicate_of:existing-rem-id|update_to:existing-rem-id",
        "deduplication_rationale": "brief explanation",
        "typed_relations": [
          {{"to": "exact-id-from-valid-list", "type": "relation-type", "rationale": "brief reason"}}
        ]
      }}
    ]
  }}
}}

**Deduplication Decision Guide**:
- "new": Genuinely new concept, no semantic overlap with existing Rems
- "duplicate_of:rem-id": Same content as existing Rem (recommend skip/merge)
- "update_to:rem-id": Adds clarification/extension to existing Rem (recommend update existing Rem's core points)
"""
    return prompt


def validate_tutor_response(tutor_response_json, valid_ids):
    """
    Validate that tutor response only uses IDs from valid_ids set
    and uses only standard relation types.

    Returns: (is_valid, error_messages)
    """
    errors = []
    guidance = tutor_response_json.get("concept_extraction_guidance", {})
    suggestions = guidance.get("rem_suggestions", [])

    valid_ids_set = set(valid_ids)

    for suggestion in suggestions:
        concept_id = suggestion.get("concept_id")

        # NOTE: Do NOT validate concept_id itself - these are NEW candidate Rems being created
        # Only validate that typed_relations reference existing concepts

        # Check all "to" fields are valid and relation types are standard
        for relation in suggestion.get("typed_relations", []):
            to_id = relation.get("to")
            rel_type = relation.get("type")

            # Validate concept ID
            if to_id not in valid_ids_set:
                errors.append(f"Invalid 'to' ID in {concept_id}: '{to_id}' not in valid ID list")

            # Validate relation type
            if rel_type and rel_type not in ALL_TYPES:
                valid_types_list = sorted(ALL_TYPES)
                errors.append(
                    f"Invalid relation type in {concept_id}: '{rel_type}' not in standard types.\n"
                    f"   Valid types: {', '.join(valid_types_list[:10])}... (see ALL_TYPES)"
                )

    return (len(errors) == 0, errors)


def auto_generate_output_paths(enriched_rems, isced_path):
    """
    Auto-generate output_path for Rems that are missing it.

    Args:
        enriched_rems: List of Rems (may have missing output_path)
        isced_path: ISCED path for directory

    Returns: Rems with output_path populated
    """
    import subprocess

    for rem in enriched_rems:
        if not rem.get('output_path'):
            # Get next available number
            result = subprocess.run(
                ['python3', 'scripts/utilities/get-next-number.py', '--directory', f'knowledge-base/{isced_path}'],
                capture_output=True,
                text=True,
                cwd=ROOT
            )

            if result.returncode == 0:
                next_num = result.stdout.strip()
                rem['output_path'] = f"knowledge-base/{isced_path}/{next_num}-{rem['rem_id']}.md"
                print(f"  ✓ Generated output_path: {rem['rem_id']} → {next_num}", file=sys.stderr)
            else:
                print(f"  ⚠️  Failed to generate number for {rem['rem_id']}: {result.stderr}", file=sys.stderr)
                # Leave output_path empty - will be caught by validation

    return enriched_rems


def merge_tutor_suggestions(candidate_rems, tutor_response_json):
    """
    Merge tutor's typed_relations into candidate Rems.

    Normalizes field names: accepts both 'type' and 'relation_type' from tutors.

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
        rem_id = rem["rem_id"]
        enriched_rem = rem.copy()

        # Add typed_relations from tutor
        if rem_id in tutor_map:
            tutor_data = tutor_map[rem_id]
            typed_relations = tutor_data.get("typed_relations", [])

            # Normalize field names: accept both 'type' and 'relation_type'
            normalized_relations = []
            for rel in typed_relations:
                normalized_rel = rel.copy()
                # If tutor used 'relation_type', rename to 'type'
                if 'relation_type' in normalized_rel and 'type' not in normalized_rel:
                    normalized_rel['type'] = normalized_rel.pop('relation_type')
                normalized_relations.append(normalized_rel)

            enriched_rem["typed_relations"] = normalized_relations
        else:
            enriched_rem["typed_relations"] = []

        enriched.append(enriched_rem)

    return enriched


def main():
    parser = argparse.ArgumentParser(description='Orchestrate Step 3.5 Domain Tutor Enrichment')
    parser.add_argument('--domain', required=True, help='Domain: programming|language|finance|science')
    parser.add_argument('--isced-path', required=True, help='ISCED detailed path (e.g., 0611-computer-use)')

    # Input modes (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--candidate-rems', help='JSON file with candidate Rems (legacy)')
    input_group.add_argument('--candidate-rems-json', help='Inline JSON string with candidate Rems (preferred)')

    parser.add_argument('--output', default='/tmp/enriched_rems.json', help='Output file path')

    # Tutor response modes (optional, mutually exclusive)
    tutor_group = parser.add_mutually_exclusive_group()
    tutor_group.add_argument('--tutor-response', help='Tutor JSON response file (legacy)')
    tutor_group.add_argument('--tutor-response-json', help='Inline tutor JSON response (preferred)')

    # Automation mode
    parser.add_argument('--auto-mode', action='store_true',
                        help='Automated mode: output prompt for main agent to call Task tool, then exit. Main agent should merge results.')

    # Quiet mode
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress non-critical output')

    args = parser.parse_args()

    try:
        # Load candidate Rems (from file or inline JSON)
        candidate_rems = load_candidate_rems(
            file_path=args.candidate_rems,
            json_string=args.candidate_rems_json
        )
        if not args.quiet:
            print(f"✓ Loaded {len(candidate_rems)} candidate Rems", file=sys.stderr)

        # Load existing concepts
        backlinks = load_backlinks()
        existing_concepts = extract_domain_concepts(backlinks, args.isced_path)
        if not args.quiet:
            print(f"✓ Found {len(existing_concepts)} existing concepts in {args.isced_path}", file=sys.stderr)

        # Build tutor prompt
        tutor_prompt = build_tutor_prompt(args.domain, existing_concepts, candidate_rems)

        if args.tutor_response or args.tutor_response_json:
            # Manual mode: use provided tutor response (from file or inline JSON)
            if args.tutor_response_json:
                tutor_json = json.loads(args.tutor_response_json)
                if not args.quiet:
                    print(f"✓ Loaded tutor response from inline JSON", file=sys.stderr)
            else:
                with open(args.tutor_response, 'r', encoding='utf-8') as f:
                    tutor_json = json.load(f)
                if not args.quiet:
                    print(f"✓ Loaded tutor response from {args.tutor_response}", file=sys.stderr)

            # Validate tutor response IDs (includes both existing and candidate IDs)
            existing_ids = [c["rem_id"] for c in existing_concepts]
            candidate_ids = [r["rem_id"] for r in candidate_rems]
            all_valid_ids = existing_ids + candidate_ids
            is_valid, errors = validate_tutor_response(tutor_json, all_valid_ids)

            if not is_valid:
                print(f"\n❌ Tutor response validation failed:", file=sys.stderr)
                for error in errors[:10]:  # Show first 10 errors
                    print(f"   - {error}", file=sys.stderr)
                if len(errors) > 10:
                    print(f"   ... and {len(errors) - 10} more errors", file=sys.stderr)
                print("\n⚠️  Tutor must use EXACT IDs from the provided lists.", file=sys.stderr)
                return 1

            if not args.quiet:
                print(f"✓ Tutor response validated (all IDs match)", file=sys.stderr)
        else:
            # Automated mode: output prompt for main agent to call Task tool
            if args.auto_mode:
                # Output prompt in machine-readable format for automation
                print(tutor_prompt)
            else:
                # Interactive mode: show instructions
                print("\n📋 TUTOR PROMPT (pass to Task tool):\n", file=sys.stderr)
                print(tutor_prompt, file=sys.stderr)
                print("\n⚠️  Main agent: Call Task tool with above prompt, save response to tutor_response.json", file=sys.stderr)
                print("Then re-run with: --tutor-response tutor_response.json\n", file=sys.stderr)
            return 0

        # Merge tutor suggestions
        enriched_rems = merge_tutor_suggestions(candidate_rems, tutor_json)
        if not args.quiet:
            print(f"✓ Enriched {len(enriched_rems)} Rems with typed_relations", file=sys.stderr)

        # Count relations added
        total_relations = sum(len(r.get("typed_relations", [])) for r in enriched_rems)
        if not args.quiet:
            print(f"✓ Total typed_relations added: {total_relations}", file=sys.stderr)

        # STEP 3.6: Validate hierarchical consistency
        if not args.quiet:
            print("\n🔍 Validating hierarchical consistency...", file=sys.stderr)
        from archival.validate_hierarchical_consistency import (
            build_relation_map, validate_proposed_relations, detect_cycles
        )

        existing_relations = build_relation_map(backlinks)
        is_valid, errors = validate_proposed_relations(enriched_rems, existing_relations)
        cycles = detect_cycles(enriched_rems)

        if not is_valid or cycles:
            print(f"\n❌ VALIDATION FAILED: Hierarchical contradictions detected!", file=sys.stderr)
            print(f"   Contradictions: {len(errors)}", file=sys.stderr)
            print(f"   Cycles: {len(cycles)}", file=sys.stderr)

            # Print details (show all, not truncated)
            if errors:
                print(f"\n   Contradictions found ({len(errors)}):", file=sys.stderr)
                for error in errors:
                    print(f"     • {error.from_rem} ⟷ {error.to_rem} [{error.rel_type}]", file=sys.stderr)

            if cycles:
                print(f"\n   Prerequisite cycles ({len(cycles)}):", file=sys.stderr)
                for i, cycle in enumerate(cycles, 1):
                    print(f"     {i}. {' → '.join(cycle + [cycle[0]])}", file=sys.stderr)

            print("\n⚠️  These relations will be REMOVED to maintain graph consistency.", file=sys.stderr)
            print("   Re-run /save or adjust tutor logic to avoid contradictions.\n", file=sys.stderr)

            # Remove problematic relations
            from collections import defaultdict
            problem_pairs = defaultdict(set)
            for error in errors:
                problem_pairs[error.from_rem].add((error.to_rem, error.rel_type))

            for rem in enriched_rems:
                if rem['rem_id'] in problem_pairs:
                    rem['typed_relations'] = [
                        rel for rel in rem.get('typed_relations', [])
                        if (rel['to'], rel['type']) not in problem_pairs[rem['rem_id']]
                    ]

            # Recalculate total after cleanup
            total_relations = sum(len(r.get("typed_relations", [])) for r in enriched_rems)
            if not args.quiet:
                print(f"✓ Cleaned relations count: {total_relations}", file=sys.stderr)
        else:
            if not args.quiet:
                print(f"✅ Validation passed: No contradictions detected", file=sys.stderr)

        # Auto-generate missing output_path values
        if not args.quiet:
            print("  Auto-generating missing output paths...", file=sys.stderr)
        enriched_rems = auto_generate_output_paths(enriched_rems, args.isced_path)

        # Build complete output structure (with session_metadata wrapper)
        output_data = {
            "session_metadata": {
                "domain": args.domain,
                "isced_path": args.isced_path,
                "timestamp": None,  # Will be filled by save_post_processor
                "agent": "main"
            },
            "rems": enriched_rems,
            "rems_to_update": []
        }

        # Save enriched Rems with session_metadata wrapper
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        if not args.quiet:
            print(f"✅ Saved enriched Rems to: {args.output}", file=sys.stderr)
        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
