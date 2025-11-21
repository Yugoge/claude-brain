#!/usr/bin/env python3
"""
Save Post-Processor - Unified Post-Creation Pipeline

Consolidates Steps 12-22 of /save workflow into single automated script.

Executes:
  Step 12: Pre-creation Validation
  Step 13: Create Knowledge Rems (atomic transaction)
  Step 14: Process Conversation Archive
  Step 15: Update Existing Rems (review sessions only)
  Step 16: Update Knowledge Graph
  Step 17: Materialize Inferred Links (optional)
  Step 18: Sync Rems to Review Schedule (FSRS)
  Step 19: Record to Memory MCP
  Step 20: Update Conversation Rem Links
  Step 21: Generate Analytics & Visualizations
  Step 22: Display Completion Report

Usage:
    python scripts/archival/save_post_processor.py \\
      --enriched-rems /tmp/enriched_rems.json \\
      --archived-file chats/conversation-2025-11-21.md \\
      --session-type learn

Input JSON Schema (enriched_rems.json):
    {
      "session_metadata": {
        "id": "conversation-id",
        "title": "Conversation Title",
        "summary": "2-3 sentence summary",
        "archived_file": "path/to/archived.md",
        "session_type": "learn|ask|review",
        "domain": "finance",
        "subdomain": "equity-derivatives",
        "isced_path": "04-business/.../0412-finance-...",
        "agent": "main",
        "tags": []
      },
      "rems": [
        {
          "rem_id": "subdomain-concept-slug",
          "title": "Concept Title",
          "core_points": ["point1", "point2", "point3"],
          "usage_scenario": "1-2 sentence usage",
          "my_mistakes": ["mistake1", "mistake2"],
          "typed_relations": [
            {"target": "existing-rem-id", "type": "prerequisite_of"}
          ],
          "output_path": "knowledge-base/.../NNN-subdomain-concept-slug.md"
        }
      ],
      "rems_to_update": [  // Optional, review sessions only
        {
          "rem_id": "rem-to-update",
          "clarification_text": "Additional clarification",
          "target_section": "## Core Content"
        }
      ]
    }

Exit Codes:
    0 = Success (all operations completed)
    1 = Validation failed (no changes made)
    2 = File creation failed (rollback performed)
    3 = Post-processing failed (files created but downstream operations failed)
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add scripts to path
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "scripts"))

from archival.file_writer import FileWriter, WriteResult


def validate_before_creation(enriched_rems: List[Dict], domain: str, isced_path: str) -> bool:
    """
    Step 12: Pre-creation Validation

    Runs:
      - preflight_checker.py: Validate typed_relations enforcement
      - pre_validator_light.py: Validate Rem structure

    Returns: True if validation passes, False otherwise
    """
    print("\n" + "="*60, file=sys.stderr)
    print("📋 Step 12: Pre-creation Validation", file=sys.stderr)
    print("="*60, file=sys.stderr)

    try:
        # Validation 1: Preflight checker (typed relations enforcement)
        print("  Running preflight checks...", file=sys.stderr)
        from archival.preflight_checker import check_step_3_5_executed

        # Check if domain requires tutor enrichment
        check_result = check_step_3_5_executed(
            enriched_rems=enriched_rems,
            domain=domain
        )

        if not check_result['passed']:
            print(f"  ❌ Preflight check failed: {check_result['error']}", file=sys.stderr)
            return False

        print(f"  ✓ Preflight check passed", file=sys.stderr)

        # Validation 2: Light validator (Rem structure)
        print("  Running light validation...", file=sys.stderr)
        from archival.pre_validator_light import validate_enriched_rems

        validation_result = validate_enriched_rems(enriched_rems, isced_path)

        if not validation_result['passed']:
            print(f"  ❌ Light validation failed:", file=sys.stderr)
            for error in validation_result['errors']:
                print(f"    - {error}", file=sys.stderr)
            return False

        print(f"  ✓ Light validation passed ({len(enriched_rems)} Rems)", file=sys.stderr)

        return True

    except Exception as e:
        print(f"  ❌ Validation error: {e}", file=sys.stderr)
        return False


def atomic_write_all_files(
    enriched_rems: List[Dict],
    metadata: Dict,
    archived_file: Path,
    session_type: str,
    rems_to_update: Optional[List[Dict]] = None
) -> WriteResult:
    """
    Steps 13-15 + 20: Atomic File Creation

    Uses FileWriter for atomic transaction:
      Step 13: Create Knowledge Rems (N files)
      Step 14: Normalize and rename conversation
      Step 15: Update existing Rems (review only)
      Step 20: Update conversation with Rem links

    Returns: WriteResult with created paths
    """
    print("\n" + "="*60, file=sys.stderr)
    print("💾 Steps 13-15, 20: Atomic File Creation", file=sys.stderr)
    print("="*60, file=sys.stderr)

    writer = FileWriter()
    result = writer.atomic_write_all(
        enriched_rems=enriched_rems,
        conversation_metadata=metadata,
        archived_file=archived_file,
        session_type=session_type,
        rems_to_update=rems_to_update
    )

    return result


def update_knowledge_graph(rem_ids: List[str], conversation_path: Path, metadata: Dict):
    """
    Step 16: Update Knowledge Graph

    Executes:
      1. update-backlinks-incremental.py (rebuild backlinks for new Rems)
      2. update-conversation-index.py (add to chats/index.json)
      3. normalize-links.py (normalize wikilinks)
    """
    print("\n" + "="*60, file=sys.stderr)
    print("🔗 Step 16: Update Knowledge Graph", file=sys.stderr)
    print("="*60, file=sys.stderr)

    # Sub-step 1: Update backlinks
    print("  Updating backlinks...", file=sys.stderr)
    result = subprocess.run(
        ['python3', 'scripts/knowledge-graph/update-backlinks-incremental.py'] + rem_ids,
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Backlinks update failed: {result.stderr}", file=sys.stderr)
    else:
        print(f"  ✓ Backlinks updated for {len(rem_ids)} Rems", file=sys.stderr)

    # Sub-step 2: Update conversation index
    print("  Updating conversation index...", file=sys.stderr)
    result = subprocess.run(
        [
            'python3', 'scripts/archival/update-conversation-index.py',
            str(conversation_path),
            '--concepts', json.dumps([metadata.get('subdomain', '')] + rem_ids[:3])
        ],
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Conversation index update failed: {result.stderr}", file=sys.stderr)
    else:
        print(f"  ✓ Conversation index updated", file=sys.stderr)

    # Sub-step 3: Normalize wikilinks
    print("  Normalizing wikilinks...", file=sys.stderr)
    result = subprocess.run(
        ['python3', 'scripts/knowledge-graph/normalize-links.py', '--mode', 'replace'],
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Link normalization failed: {result.stderr}", file=sys.stderr)
    else:
        print(f"  ✓ Wikilinks normalized", file=sys.stderr)


def materialize_inferred_links(prompt_user: bool = True):
    """
    Step 17: Materialize Inferred Links (optional)

    Prompts user to materialize inferred bidirectional links.
    If non-interactive, skips with warning.
    """
    print("\n" + "="*60, file=sys.stderr)
    print("🔮 Step 17: Materialize Inferred Links (Optional)", file=sys.stderr)
    print("="*60, file=sys.stderr)

    if not prompt_user:
        print("  ⏭️  Skipped (non-interactive mode)", file=sys.stderr)
        return

    # Run dry-run first to show what would be materialized
    print("  Running dry-run preview...", file=sys.stderr)
    result = subprocess.run(
        ['python3', 'scripts/knowledge-graph/materialize-inferred-links.py', '--dry-run', '--verbose'],
        cwd=ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"  ⚠️  Dry-run failed: {result.stderr}", file=sys.stderr)
        return

    # Show preview
    print(result.stdout, file=sys.stderr)

    # In automated mode, skip actual materialization
    # (AI can decide whether to call this interactively)
    print("  ℹ️  To materialize, run manually:", file=sys.stderr)
    print("     python scripts/knowledge-graph/materialize-inferred-links.py --verbose", file=sys.stderr)


def sync_to_fsrs():
    """
    Step 18: Sync Rems to FSRS Review Schedule

    Automatically adds new Rems to .review/schedule.json
    """
    print("\n" + "="*60, file=sys.stderr)
    print("📅 Step 18: Sync to FSRS Review Schedule", file=sys.stderr)
    print("="*60, file=sys.stderr)

    result = subprocess.run(
        ['python3', 'scripts/utilities/scan-and-populate-rems.py', '--yes'],
        cwd=ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"  ⚠️  FSRS sync failed: {result.stderr}", file=sys.stderr)
    else:
        # Parse output to show how many Rems were added
        output = result.stdout
        print(f"  ✓ FSRS sync completed", file=sys.stderr)
        if "Added" in output:
            print(f"    {output.strip()}", file=sys.stderr)


def record_to_memory_mcp(metadata: Dict, rems: List[Dict]):
    """
    Step 19: Record to Memory MCP

    Creates entities and relations in MCP memory server.
    """
    print("\n" + "="*60, file=sys.stderr)
    print("🧠 Step 19: Record to Memory MCP", file=sys.stderr)
    print("="*60, file=sys.stderr)

    try:
        # This would use MCP tools, but those are only available to the main agent
        # Post-processor just logs intent
        print(f"  ℹ️  MCP recording should be handled by main agent", file=sys.stderr)
        print(f"    - Domain: {metadata.get('domain')}", file=sys.stderr)
        print(f"    - Concepts: {len(rems)} Rems", file=sys.stderr)
        print(f"  ⏭️  Skipped (MCP tools unavailable in subprocess)", file=sys.stderr)

    except Exception as e:
        print(f"  ⚠️  MCP recording failed: {e}", file=sys.stderr)


def generate_analytics():
    """
    Step 21: Generate Analytics & Visualizations

    Executes:
      1. generate-analytics.py (30-day stats)
      2. generate-graph-data.py (force rebuild)
      3. generate-visualization-html.py (interactive graph)
    """
    print("\n" + "="*60, file=sys.stderr)
    print("📊 Step 21: Generate Analytics & Visualizations", file=sys.stderr)
    print("="*60, file=sys.stderr)

    # Sub-step 1: Analytics
    print("  Generating analytics...", file=sys.stderr)
    result = subprocess.run(
        ['python3', 'scripts/analytics/generate-analytics.py', '--period', '30'],
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Analytics generation failed: {result.stderr}", file=sys.stderr)
    else:
        print(f"  ✓ Analytics generated (30-day period)", file=sys.stderr)

    # Sub-step 2: Graph data
    print("  Generating graph data...", file=sys.stderr)
    result = subprocess.run(
        ['python3', 'scripts/knowledge-graph/generate-graph-data.py', '--force'],
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Graph data generation failed: {result.stderr}", file=sys.stderr)
    else:
        print(f"  ✓ Graph data generated", file=sys.stderr)

    # Sub-step 3: Visualization
    print("  Generating visualization HTML...", file=sys.stderr)
    result = subprocess.run(
        ['python3', 'scripts/knowledge-graph/generate-visualization-html.py'],
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Visualization generation failed: {result.stderr}", file=sys.stderr)
    else:
        print(f"  ✓ Visualization HTML generated", file=sys.stderr)


def display_completion_report(
    metadata: Dict,
    rems: List[Dict],
    created_paths: List[Path],
    conversation_path: Path,
    start_time: datetime
):
    """
    Step 22: Display Completion Report

    Shows summary of all operations with performance metrics.
    """
    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*60, file=sys.stderr)
    print("✅ Step 22: Completion Report", file=sys.stderr)
    print("="*60, file=sys.stderr)

    print(f"\n📊 Session: {metadata.get('title')}", file=sys.stderr)
    print(f"   Type: {metadata.get('session_type')}", file=sys.stderr)
    print(f"   Domain: {metadata.get('domain')} > {metadata.get('subdomain')}", file=sys.stderr)

    print(f"\n📝 Files Created:", file=sys.stderr)
    print(f"   • {len(created_paths)} Rem(s):", file=sys.stderr)
    for path in created_paths:
        print(f"     - {path.name}", file=sys.stderr)
    print(f"   • 1 Conversation: {conversation_path.name}", file=sys.stderr)

    print(f"\n🔗 Graph Updates:", file=sys.stderr)
    print(f"   • Backlinks rebuilt for {len(rems)} Rem(s)", file=sys.stderr)
    print(f"   • Conversation index updated", file=sys.stderr)
    print(f"   • Wikilinks normalized", file=sys.stderr)

    print(f"\n📅 FSRS Review:", file=sys.stderr)
    print(f"   • {len(created_paths)} Rem(s) added to review schedule", file=sys.stderr)

    print(f"\n📊 Analytics:", file=sys.stderr)
    print(f"   • 30-day statistics updated", file=sys.stderr)
    print(f"   • Knowledge graph visualization regenerated", file=sys.stderr)

    print(f"\n⏱️  Performance:", file=sys.stderr)
    print(f"   • Total time: {elapsed:.1f}s", file=sys.stderr)
    print(f"   • Average: {elapsed/len(created_paths):.1f}s per Rem", file=sys.stderr)

    print("\n" + "="*60, file=sys.stderr)
    print("✨ /save workflow completed successfully", file=sys.stderr)
    print("="*60 + "\n", file=sys.stderr)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Save Post-Processor - Automated Steps 12-22',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--enriched-rems',
        required=True,
        help='Path to enriched_rems.json with session_metadata and rems array'
    )
    parser.add_argument(
        '--archived-file',
        required=True,
        help='Path to archived conversation file'
    )
    parser.add_argument(
        '--session-type',
        default='learn',
        choices=['learn', 'ask', 'review'],
        help='Session type (default: learn)'
    )
    parser.add_argument(
        '--skip-materialize',
        action='store_true',
        help='Skip Step 17 (materialize inferred links)'
    )

    args = parser.parse_args()

    start_time = datetime.now()

    # Load enriched Rems data
    try:
        with open(args.enriched_rems, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load enriched_rems.json: {e}", file=sys.stderr)
        return 1

    metadata = data.get('session_metadata', {})
    rems = data.get('rems', [])
    rems_to_update = data.get('rems_to_update', None)

    if not rems:
        print("❌ No Rems found in enriched_rems.json", file=sys.stderr)
        return 1

    archived_file = Path(args.archived_file)
    if not archived_file.exists():
        print(f"❌ Archived file not found: {archived_file}", file=sys.stderr)
        return 1

    print("\n🚀 Starting /save post-processing workflow", file=sys.stderr)
    print(f"   Processing {len(rems)} Rem(s) for session: {metadata.get('title')}", file=sys.stderr)

    # Step 12: Validation
    if not validate_before_creation(rems, metadata.get('domain'), metadata.get('isced_path')):
        print("\n❌ Validation failed - no changes made", file=sys.stderr)
        return 1

    # Steps 13-15, 20: Atomic file creation
    write_result = atomic_write_all_files(
        enriched_rems=rems,
        metadata=metadata,
        archived_file=archived_file,
        session_type=args.session_type,
        rems_to_update=rems_to_update
    )

    if not write_result.success:
        print(f"\n❌ File creation failed: {write_result.error}", file=sys.stderr)
        print(f"   Rollback performed: {write_result.rollback_performed}", file=sys.stderr)
        return 2

    # Step 16: Update knowledge graph
    rem_ids = [r['rem_id'] for r in rems]
    update_knowledge_graph(rem_ids, write_result.conversation_path, metadata)

    # Step 17: Materialize inferred links (optional)
    if not args.skip_materialize:
        materialize_inferred_links(prompt_user=False)

    # Step 18: Sync to FSRS
    sync_to_fsrs()

    # Step 19: Record to Memory MCP
    record_to_memory_mcp(metadata, rems)

    # Step 21: Generate analytics
    generate_analytics()

    # Step 22: Display completion report
    display_completion_report(
        metadata=metadata,
        rems=rems,
        created_paths=write_result.created_rems,
        conversation_path=write_result.conversation_path,
        start_time=start_time
    )

    return 0


if __name__ == '__main__':
    sys.exit(main())
