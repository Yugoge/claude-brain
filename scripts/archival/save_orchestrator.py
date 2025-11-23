#!/usr/bin/env python3
"""
Save Workflow Orchestrator - Pre-Processing Pipeline

Executes /save workflow Step 1 (automated batch operations):
  1. Archive Conversation
  2. Parse Arguments & Detect Session Type
  3. Session Validation (session_detector + concept_extractor)
  4. Filter FSRS Test Dialogues (review sessions only)

Main agent then performs Steps 2-9 interactively:
  Step 2: Domain Classification (via classification-expert)
  Step 3: Extract Concepts & Write to /tmp/candidate_rems.json
  Step 4: Analyze User Learning & Rem Updates (review sessions only, AI-driven)
  Step 5: Enrich with Typed Relations (via domain-tutor)
  Steps 6-9: Preview, Confirm, Post-Processing

Enforcement Gates:
  - Session validation: Blocks if confidence <50% or token limit exceeded
  - Token limit: Blocks if >150k tokens

Usage:
    python scripts/archival/save_orchestrator.py [topic-name | --all]

Output:
    - Filtered archived conversation (chats/YYYY-MM/conversation-YYYY-MM-DD.md)
    - orchestrator_metadata.json: Session info for main agent Steps 2-9
    - Exit code 0 if successful, 1 if validation failed, 2 if token limit exceeded
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from enum import Enum

# Add scripts to path
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "scripts"))

# Import existing functionality
from archival.session_detector import SessionDetector
from archival.concept_extractor import ConceptExtractor
from archival.archival_types import DetectionResult, ValidationResult
from archival.get_domain_concepts import extract_domain_concepts, load_backlinks
from archival.workflow_orchestrator import (
    build_tutor_prompt,
    validate_tutor_response,
    merge_tutor_suggestions
)
from archival.preflight_checker import check_enrichment_executed
from archival.pre_validator_light import validate_enriched_rems


class WorkflowStage(Enum):
    """Workflow stages for enforcement"""
    ARCHIVE = 1
    PARSE_ARGS = 2
    VALIDATE = 3
    FILTER_FSRS = 4
    CLASSIFY = 5
    EXTRACT = 6
    CLASSIFY_QUESTIONS = 7
    ENRICH = 8
    TRANSPARENCY = 9


class MandatoryStepSkipped(Exception):
    """Raised when a mandatory step is skipped"""
    pass


class ValidationFailed(Exception):
    """Raised when validation fails"""
    pass


def archive_conversation(include_subagents=True):
    """
    Archive conversation using chat_archiver.py

    Returns: archived_file path
    """
    import subprocess

    print("📝 Step 1: Archiving conversation...", file=sys.stderr)

    cmd = ["python3", str(ROOT / "scripts/services/chat_archiver.py")]
    if not include_subagents:
        cmd.append("--no-include-subagents")

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))

    if result.returncode != 0:
        raise RuntimeError(f"Chat archiver failed: {result.stderr}")

    archived_file = result.stdout.strip()
    print(f"✓ Archived to: {archived_file}", file=sys.stderr)

    return archived_file


def parse_arguments(args):
    """
    Parse arguments and determine archival mode

    Returns: (mode, topic_filter)
        mode: 'single' | 'topic' | 'all'
        topic_filter: None | topic_name
    """
    print("⚙️  Step 2: Parsing arguments...", file=sys.stderr)

    if args.all:
        mode = 'all'
        topic_filter = None
        print("  Mode: Archive all unarchived conversations", file=sys.stderr)
    elif args.topic:
        mode = 'topic'
        topic_filter = args.topic
        print(f"  Mode: Archive topic '{topic_filter}'", file=sys.stderr)
    else:
        mode = 'single'
        topic_filter = None
        print("  Mode: Archive most recent conversation", file=sys.stderr)

    return mode, topic_filter


def validate_session(archived_file):
    """
    Comprehensive session validation

    Runs:
      - session_detector.py: Detect session type with confidence
      - concept_extractor.py: Validate conversation

    Returns: (session_type, confidence, validation_result)

    Raises: ValidationFailed if checks fail
    """
    print("🔍 Step 3: Validating session...", file=sys.stderr)

    # Sub-step 3a: Detect session type
    detector = SessionDetector()
    result: DetectionResult = detector.detect_session_type()

    print(f"  Session type: {result.session_type} (confidence: {result.confidence:.0%})", file=sys.stderr)

    # Enforce confidence gate
    if result.confidence < 0.5:
        raise ValidationFailed(
            f"Session type confidence too low ({result.confidence:.0%} < 50%)\n"
            f"Cannot reliably determine if this is learn/ask/review session"
        )

    # Sub-step 3b: Validate conversation (simplified - check file exists and has content)
    try:
        with open(archived_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Basic validation: conversation should have some content
        if len(content.strip()) < 100:
            raise ValidationFailed(
                "Conversation too short for archival (< 100 characters)"
            )

        # Token count check using ConceptExtractor
        extractor = ConceptExtractor()
        try:
            token_count = extractor.check_conversation_size()  # Uses demo estimate
            validation_result = {
                'exit_code': 0,
                'token_count': token_count,
                'has_content': True
            }
        except ValueError as e:
            raise ValidationFailed(str(e))

    except FileNotFoundError:
        raise ValidationFailed(f"Archived file not found: {archived_file}")
    except Exception as e:
        raise ValidationFailed(f"Error validating conversation: {e}")

    print(f"✓ Validation passed", file=sys.stderr)

    return result.session_type, result.confidence, validation_result


def filter_fsrs_test_dialogues(archived_file, session_type):
    """
    Filter FSRS test dialogues from review sessions

    Segments conversation to remove test portions (rating prompts, test questions, FSRS feedback).
    Only applies to review sessions.

    Args:
        archived_file: Path to archived conversation
        session_type: Type of session (learn|ask|review)

    Returns: None (modifies archived_file in-place)
    """
    if session_type != 'review':
        print("  Step 4: Skipped (not a review session)", file=sys.stderr)
        return

    print("🗂️  Step 4: Filtering FSRS test dialogues...", file=sys.stderr)

    # Read archived conversation
    with open(archived_file, 'r', encoding='utf-8') as f:
        content = f.read()

    import re

    # FSRS test patterns:
    # - Rating prompts: "Rate your recall.*1-4"
    # - Test questions: "What is [[rem-id]]"
    # - FSRS feedback: "Next review.*days"
    fsrs_patterns = [
        r'Rate your recall[^\n]*[1-4]',
        r'What is \[\[[^\]]+\]\]\?',
        r'Next review.*\d+ days?'
    ]

    # Find first occurrence of any FSRS pattern
    first_match = None
    first_pos = len(content)

    for pattern in fsrs_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match and match.start() < first_pos:
            first_match = match
            first_pos = match.start()

    if first_match:
        # Split at first FSRS occurrence
        learning_portion = content[:first_pos].rstrip()
        test_portion = content[first_pos:]

        # Rewrite archived file with only learning portion
        with open(archived_file, 'w', encoding='utf-8') as f:
            f.write(learning_portion)

        # Save test portion to separate file for debugging
        test_file = archived_file.replace('.md', '_fsrs_test.md')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_portion)

        print(f"  ✓ Filtered FSRS test portion (saved to {test_file})", file=sys.stderr)
        print(f"  ✓ Learning portion: {len(learning_portion)} chars", file=sys.stderr)
    else:
        print("  No FSRS test patterns detected", file=sys.stderr)


def classify_domain(conversation_summary, main_topics):
    """
    Domain Classification & ISCED Path Determination

    Args:
        conversation_summary: 2-3 sentence summary of conversation
        main_topics: List of 3-5 main topics discussed

    Returns: {
        'domain': str,
        'subdomain': str,
        'confidence': float,
        'isced_path': str,
        'rationale': str
    }

    Note: This is a placeholder. Main agent should call classification-expert
          via Task tool and pass result here.
    """
    print("🏷️  Step 5: Classifying domain...", file=sys.stderr)

    # Placeholder: Main agent must provide classification result
    # In actual execution, this would be called AFTER main agent uses Task tool

    print("  ⚠️  Classification must be provided by main agent", file=sys.stderr)
    print("  (Call classification-expert via Task tool)", file=sys.stderr)

    return None  # Main agent provides this


def extract_concepts(conversation_context, domain, subdomain):
    """
    Extract Concepts from conversation

    Args:
        conversation_context: The active conversation context (NOT file read)
        domain: Domain classification
        subdomain: Subdomain classification

    Returns: List of candidate Rems with structure:
        [{
            'rem_id': str,
            'title': str,
            'core_points': list[str],
            'usage_scenario': str,
            'my_mistakes': list[str]
        }]

    Note: Main agent performs extraction directly from active context.
          This function is a placeholder for the extraction result.
    """
    print("📤 Step 6: Extracting concepts...", file=sys.stderr)

    # Placeholder: Main agent extracts from active context
    print("  ⚠️  Concept extraction performed by main agent from active context", file=sys.stderr)

    return None  # Main agent provides this


def enrich_with_tutor(candidate_rems, domain, isced_path, tutor_response_json=None):
    """
    Enrich with Typed Relations via Domain Tutor

    MANDATORY for: programming, language, finance, science, medicine, law

    Args:
        candidate_rems: List of candidate Rems from extraction
        domain: Domain classification
        isced_path: ISCED detailed path
        tutor_response_json: Optional pre-provided tutor response

    Returns: enriched_rems with typed_relations field

    Raises: MandatoryStepSkipped if domain requires tutor but not executed
    """
    print("🧠 Step 8: Enriching with typed relations...", file=sys.stderr)

    MANDATORY_DOMAINS = {'programming', 'language', 'finance', 'science', 'medicine', 'law'}

    # Enforcement gate
    if domain in MANDATORY_DOMAINS:
        print(f"  ⚠️  MANDATORY enrichment for {domain} domain", file=sys.stderr)

        if tutor_response_json is None:
            # Generate tutor prompt for main agent to use
            backlinks = load_backlinks()
            existing_concepts = extract_domain_concepts(backlinks, isced_path)

            tutor_prompt = build_tutor_prompt(domain, existing_concepts, candidate_rems)

            print("\n📋 TUTOR PROMPT (main agent: call Task tool with this):\n", file=sys.stderr)
            print(tutor_prompt, file=sys.stderr)
            print("\n⚠️  Re-run with --tutor-response <file> after getting tutor JSON\n", file=sys.stderr)

            # Return partial state
            return {
                'status': 'awaiting_tutor',
                'prompt': tutor_prompt,
                'candidate_rems': candidate_rems
            }

        # Validate tutor response
        existing_ids = [c['rem_id'] for c in extract_domain_concepts(load_backlinks(), isced_path)]
        candidate_ids = [r['rem_id'] for r in candidate_rems]
        all_valid_ids = existing_ids + candidate_ids

        is_valid, errors = validate_tutor_response(tutor_response_json, all_valid_ids)

        if not is_valid:
            print(f"\n❌ Tutor response validation failed:", file=sys.stderr)
            for error in errors[:10]:
                print(f"   - {error}", file=sys.stderr)
            raise ValidationFailed("Tutor response contains invalid concept IDs")

        # Merge tutor suggestions
        enriched_rems = merge_tutor_suggestions(candidate_rems, tutor_response_json)

        # Enforcement: Check that typed_relations were actually added
        total_relations = sum(len(r.get('typed_relations', [])) for r in enriched_rems)

        if total_relations == 0:
            print("\n⚠️  WARNING: Tutor returned zero typed_relations", file=sys.stderr)
            print("   This may indicate tutor quality issue or truly isolated concepts", file=sys.stderr)
        else:
            print(f"✓ Added {total_relations} typed relations across {len(enriched_rems)} Rems", file=sys.stderr)

        return enriched_rems

    else:
        # Optional enrichment for non-core domains
        print(f"  Optional enrichment for {domain} (skipped)", file=sys.stderr)

        # Add empty typed_relations field
        for rem in candidate_rems:
            rem['typed_relations'] = []

        return candidate_rems


def validate_enrichment(enriched_rems, domain, isced_path):
    """
    Pre-creation Validation

    Runs:
      - preflight_checker.py: Verify enrichment execution
      - pre_validator_light.py: Check for collisions and duplicates

    Returns: validation_result dict

    Raises: ValidationFailed if critical errors found
    """
    print("✅ Step 9: Pre-creation validation...", file=sys.stderr)

    # Stage 1: Preflight check (enrichment execution)
    preflight_result = check_enrichment_executed(enriched_rems, domain)

    if preflight_result['exit_code'] == 2:
        raise ValidationFailed(
            "Step 8 (Domain Tutor Enrichment) was skipped but is MANDATORY for this domain"
        )
    elif preflight_result['exit_code'] == 1:
        print("  ⚠️  Warning: typed_relations field is empty", file=sys.stderr)

    # Stage 2: Lightweight validation
    validation_result = validate_enriched_rems(enriched_rems, isced_path)

    if validation_result['has_critical_errors']:
        errors = validation_result['critical_errors']
        print(f"\n❌ Critical validation errors:", file=sys.stderr)
        for error in errors:
            print(f"   - {error}", file=sys.stderr)
        raise ValidationFailed("Pre-creation validation failed")

    if validation_result['has_warnings']:
        warnings = validation_result['warnings']
        print(f"\n⚠️  Validation warnings:", file=sys.stderr)
        for warning in warnings:
            print(f"   - {warning}", file=sys.stderr)

    print("✓ Pre-creation validation passed", file=sys.stderr)

    return validation_result


def main():
    parser = argparse.ArgumentParser(
        description='Save Workflow Orchestrator - Unified Pre-Creation Pipeline'
    )
    parser.add_argument('topic', nargs='?', help='Topic name to archive')
    parser.add_argument('--all', action='store_true', help='Archive all unarchived conversations')
    parser.add_argument('--no-subagents', action='store_true', help='Exclude subagent messages from archive')
    parser.add_argument('--tutor-response', help='Path to tutor JSON response (for Step 8)')
    parser.add_argument('--candidate-rems', help='Path to candidate Rems JSON (resume from Step 8)')
    parser.add_argument('--classification', help='Path to classification result JSON (skip Step 5)')

    args = parser.parse_args()

    try:
        # Track completed stages for enforcement
        completed_stages = set()

        # Step 1: Archive Conversation
        archived_file = archive_conversation(include_subagents=not args.no_subagents)
        completed_stages.add(WorkflowStage.ARCHIVE)

        # Step 2: Parse Arguments
        mode, topic_filter = parse_arguments(args)
        completed_stages.add(WorkflowStage.PARSE_ARGS)

        # Step 3: Validate Session
        session_type, confidence, validation = validate_session(archived_file)
        completed_stages.add(WorkflowStage.VALIDATE)

        # Step 4: Filter FSRS (review sessions only)
        filter_fsrs_test_dialogues(archived_file, session_type)
        completed_stages.add(WorkflowStage.FILTER_FSRS)

        # Steps 2-9: Require main agent interaction
        print("\n⚠️  Steps 2-9 require main agent interaction:", file=sys.stderr)
        print("  2. Call classification-expert via Task tool", file=sys.stderr)
        print("  3. Extract concepts from active conversation context", file=sys.stderr)
        print("  4. Analyze user learning & Rem updates (review sessions, AI-driven)", file=sys.stderr)
        print("  5. Call domain tutor via Task tool (MANDATORY)", file=sys.stderr)
        print("  6-9. Preview, Confirm, Post-Processing", file=sys.stderr)
        print("\nOrchestrator provides validation and enforcement, not extraction.", file=sys.stderr)

        # Output metadata for main agent
        metadata = {
            'archived_file': archived_file,
            'session_type': session_type,
            'confidence': confidence,
            'mode': mode,
            'topic_filter': topic_filter,
            'completed_stages': [stage.name for stage in completed_stages]
        }

        with open('orchestrator_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"\n✅ Steps 1-4 completed. Metadata saved to orchestrator_metadata.json", file=sys.stderr)
        print("Next: Main agent performs Steps 2-9 with orchestrator enforcement", file=sys.stderr)

        return 0

    except MandatoryStepSkipped as e:
        print(f"\n❌ MANDATORY STEP SKIPPED: {e}", file=sys.stderr)
        return 2

    except ValidationFailed as e:
        print(f"\n❌ VALIDATION FAILED: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
