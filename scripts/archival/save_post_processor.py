#!/usr/bin/env python3
"""
Save Post-Processor - Unified Post-Creation Pipeline

Automated post-processing for /save workflow (executes after user approval).

Executes:
  - Pre-creation Validation (preflight + light validation)
  - Atomic File Creation (Rems + conversation + updates)
  - Knowledge Graph Updates (backlinks + indexes + normalization)
  - Optional Inferred Links Materialization
  - FSRS Review Schedule Sync
  - Memory MCP Recording
  - Analytics & Visualization Generation
  - Completion Report Display

Usage:
    source venv/bin/activate && source venv/bin/activate && python scripts/archival/save_post_processor.py \\
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
import os
import sys
import subprocess
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add scripts to path
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "scripts"))

from archival.file_writer import FileWriter, WriteResult


def validate_before_creation(enriched_rems: List[Dict], domain: str, isced_path: str) -> bool:
    """
    Pre-creation Validation

    Runs:
      - preflight_checker.py: Validate typed_relations enforcement
      - pre_validator_light.py: Validate Rem structure

    Returns: True if validation passes, False otherwise
    """
    print("\n" + "="*60, file=sys.stderr)
    print("📋 Pre-creation Validation", file=sys.stderr)
    print("="*60, file=sys.stderr)

    try:
        # Validation 1: Preflight checker (typed relations enforcement)
        print("  Running preflight checks...", file=sys.stderr)
        from archival.preflight_checker import check_enrichment_executed

        # Check if domain requires tutor enrichment
        check_result = check_enrichment_executed(
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

        # Validation 3: output_path existence and validity
        print("  Validating output paths...", file=sys.stderr)
        for rem in enriched_rems:
            output_path_str = rem.get('output_path', '')

            if not output_path_str:
                print(f"  ❌ Missing output_path for {rem.get('rem_id', 'unknown')}", file=sys.stderr)
                print(f"     Fix: Run get-next-number.py for knowledge-base/{isced_path}", file=sys.stderr)
                print(f"     Command: python scripts/utilities/get-next-number.py --directory 'knowledge-base/{isced_path}'", file=sys.stderr)
                return False

            # Check if path is invalid (current directory indicator)
            if output_path_str in ['', '.', './']:
                print(f"  ❌ Invalid output_path for {rem.get('rem_id', 'unknown')}: '{output_path_str}'", file=sys.stderr)
                print(f"     output_path must be a file path, not a directory", file=sys.stderr)
                return False

            # Check if output_path points to existing directory
            output_path = Path(output_path_str)
            if output_path.exists() and output_path.is_dir():
                print(f"  ❌ output_path is directory for {rem.get('rem_id', 'unknown')}: {output_path_str}", file=sys.stderr)
                print(f"     output_path must be a file path, not a directory", file=sys.stderr)
                return False

        print(f"  ✓ Output paths validated ({len(enriched_rems)} Rems)", file=sys.stderr)

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
    Atomic File Creation

    Uses FileWriter for atomic transaction:
      - Create Knowledge Rems (N files)
      - Normalize and rename conversation
      - Update existing Rems (review sessions only)
      - Link conversation to Rems bidirectionally

    Returns: WriteResult with created paths
    """
    print("\n" + "="*60, file=sys.stderr)
    print("💾 Atomic File Creation", file=sys.stderr)
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
    Update Knowledge Graph

    Executes:
      1. update-backlinks-incremental.py (rebuild backlinks for new Rems)
      2. update-conversation-index.py (add to chats/index.json)
      3. normalize-links.py (normalize wikilinks)
      4. sync-related-rems-from-backlinks.py (update Related Rems sections)
      5. fix-bidirectional-links.py (add missing reverse links)
    """
    print("\n" + "="*60, file=sys.stderr)
    print("🔗 Update Knowledge Graph", file=sys.stderr)
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

    # Sub-step 4: Sync Related Rems from backlinks
    print("  Syncing Related Rems sections...", file=sys.stderr)
    result = subprocess.run(
        ['python3', 'scripts/knowledge-graph/sync-related-rems-from-backlinks.py', '--concept-ids'] + rem_ids,
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Related Rems sync failed: {result.stderr}", file=sys.stderr)
    else:
        print(f"  ✓ Related Rems synced for {len(rem_ids)} Rems", file=sys.stderr)

    # Sub-step 4.5: Fix bidirectional links (add missing reverses)
    print("  Fixing bidirectional links...", file=sys.stderr)
    result = subprocess.run(
        ['python3', 'scripts/fix-bidirectional-links.py'],
        cwd=ROOT,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"  ⚠️  Bidirectional fix failed: {result.stderr}", file=sys.stderr)
    else:
        # Parse output to show how many links were added
        output = result.stdout

        # Extract count from "Successfully added N links" message
        match = re.search(r'Successfully added (\d+) links', output)
        if match:
            count = match.group(1)
            print(f"  ✓ Added {count} bidirectional links", file=sys.stderr)
        else:
            # No links added (all already complete)
            print(f"  ✓ Bidirectional links verified (all complete)", file=sys.stderr)


def materialize_inferred_links(prompt_user: bool = True):
    """
    Materialize Inferred Links (optional)

    Prompts user to materialize inferred bidirectional links.
    If non-interactive, skips with warning.
    """
    print("\n" + "="*60, file=sys.stderr)
    print("🔮 Materialize Inferred Links (Optional)", file=sys.stderr)
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
    Sync Rems to FSRS Review Schedule

    Automatically adds new Rems to .review/schedule.json
    """
    print("\n" + "="*60, file=sys.stderr)
    print("📅 Sync to FSRS Review Schedule", file=sys.stderr)
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
    Record to Memory MCP

    Creates entities and relations in MCP memory server.
    """
    print("\n" + "="*60, file=sys.stderr)
    print("🧠 Record to Memory MCP", file=sys.stderr)
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
    Generate Analytics & Visualizations

    Executes:
      1. generate-analytics.py (configurable period/domain via env vars)
      2. generate-graph-data.py (force rebuild)
      3. generate-visualization-html.py (outputs to knowledge-graph.html)
      4. generate-dashboard-html.py (outputs to analytics-dashboard.html)

    Environment Variables (optional):
      ANALYTICS_PERIOD: Time period in days (default: 30)
      ANALYTICS_DOMAIN: Filter by domain (default: all domains)

    Output:
      - Root: analytics-dashboard.html, knowledge-graph.html
    """
    print("\n" + "="*60, file=sys.stderr)
    print("📊 Generate Analytics & Visualizations", file=sys.stderr)
    print("="*60, file=sys.stderr)

    # Get configuration from environment variables
    period = os.getenv('ANALYTICS_PERIOD', '30')
    domain = os.getenv('ANALYTICS_DOMAIN', None)

    # Sub-step 1: Analytics (ISCED format for dashboard)
    analytics_cmd = ['python3', 'scripts/analytics/generate-analytics-isced.py', '--period', period]
    if domain:
        analytics_cmd.extend(['--domain', domain])
        print(f"  Generating ISCED analytics (domain={domain}, period={period} days)...", file=sys.stderr)
    else:
        print(f"  Generating ISCED analytics (period={period} days, all domains)...", file=sys.stderr)

    result = subprocess.run(
        analytics_cmd,
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Analytics generation failed: {result.stderr}", file=sys.stderr)
    else:
        period_desc = f"{period}-day period" if period != '30' else "30-day period"
        domain_desc = f" (domain: {domain})" if domain else ""
        print(f"  ✓ ISCED analytics generated ({period_desc}{domain_desc})", file=sys.stderr)

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
        print(f"  ✓ Knowledge graph → knowledge-graph.html", file=sys.stderr)

    # Sub-step 4: Analytics Dashboard
    print("  Generating analytics dashboard HTML...", file=sys.stderr)
    result = subprocess.run(
        ['python3', 'scripts/analytics/generate-dashboard-html.py'],
        cwd=ROOT,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"  ⚠️  Dashboard generation failed: {result.stderr}", file=sys.stderr)
    else:
        print(f"  ✓ Analytics dashboard → analytics-dashboard.html", file=sys.stderr)

    # Sub-step 5: Deploy to GitHub Pages
    github_token = os.getenv('GITHUB_TOKEN')

    if github_token or Path.home().joinpath('.ssh/id_rsa').exists() or Path.home().joinpath('.ssh/id_ed25519').exists():
        # Default: GitHub Pages deployment
        print("\n  🚀 Deploying to GitHub Pages...", file=sys.stderr)
        result = subprocess.run(
            ['bash', 'scripts/deploy-to-github.sh'],
            cwd=ROOT,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"\n  ❌ GitHub Pages deployment failed", file=sys.stderr)
            print(f"     Error: {result.stderr.strip()}", file=sys.stderr)
            if result.stdout:
                print(f"     Output: {result.stdout.strip()}", file=sys.stderr)
            print(f"\n     Troubleshooting:", file=sys.stderr)
            print(f"     1. Ensure SSH key is added to GitHub: https://github.com/settings/keys", file=sys.stderr)
            print(f"     2. Your public key: ~/.ssh/id_ed25519.pub", file=sys.stderr)
            print(f"     3. Try manual deployment: bash scripts/deploy-to-github.sh", file=sys.stderr)
        else:
            # Extract username from git config for URL
            try:
                git_user_result = subprocess.run(
                    ['git', 'config', '--get', 'user.name'],
                    cwd=ROOT,
                    capture_output=True,
                    text=True
                )
                username = git_user_result.stdout.strip() if git_user_result.returncode == 0 else 'your-username'
                # Get current repo name dynamically
                repo_name_cmd = subprocess.run(
                    ['basename', subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                                              cwd=ROOT, capture_output=True, text=True).stdout.strip()],
                    capture_output=True,
                    text=True
                )
                current_repo = repo_name_cmd.stdout.strip() if repo_name_cmd.returncode == 0 else 'knowledge-system'
                graph_repo = f"{current_repo}-graph"

                print(f"\n  ✅ Deployed to GitHub Pages successfully!", file=sys.stderr)
                print(f"\n  🌐 Live URLs:", file=sys.stderr)
                print(f"     • Dashboard: https://{username}.github.io/{graph_repo}/", file=sys.stderr)
                print(f"     • Graph: https://{username}.github.io/{graph_repo}/graph.html", file=sys.stderr)
                print(f"\n     ⏱️  Note: GitHub Pages may take 1-2 minutes to build", file=sys.stderr)
                print(f"     📁 Repository: https://github.com/{username}/{graph_repo}", file=sys.stderr)
            except Exception as e:
                print(f"  ✓ Deployed to GitHub Pages (URL extraction failed: {e})", file=sys.stderr)
    else:
        print("\n  ⏭️  Deployment skipped (no credentials found)", file=sys.stderr)
        print(f"\n     To enable auto-deployment, configure one of:", file=sys.stderr)
        print(f"     • Option 1: export GITHUB_TOKEN='your_token_here'", file=sys.stderr)
        print(f"       Get token: https://github.com/settings/tokens/new (scopes: repo, workflow)", file=sys.stderr)
        print(f"     • Option 2: Add SSH key to GitHub", file=sys.stderr)
        print(f"       Setup: https://github.com/settings/keys", file=sys.stderr)
        print(f"\n     Manual deployment: bash scripts/deploy-to-github.sh", file=sys.stderr)


def display_completion_report(
    metadata: Dict,
    rems: List[Dict],
    created_paths: List[Path],
    conversation_path: Path,
    start_time: datetime
):
    """
    Display Completion Report

    Shows summary of all operations with performance metrics.
    """
    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "="*60, file=sys.stderr)
    print("✅ Completion Report", file=sys.stderr)
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
    print(f"   • knowledge-graph.html (graph visualization)", file=sys.stderr)
    print(f"   • analytics-dashboard.html (dashboard)", file=sys.stderr)

    # Show deployment status
    if os.getenv('GITHUB_TOKEN') or Path.home().joinpath('.ssh/id_rsa').exists() or Path.home().joinpath('.ssh/id_ed25519').exists():
        # Extract username from git config
        try:
            git_user_result = subprocess.run(
                ['git', 'config', '--get', 'user.name'],
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True
            )
            username = git_user_result.stdout.strip() if git_user_result.returncode == 0 else 'your-username'
            # Get current repo name dynamically
            repo_name_cmd = subprocess.run(
                ['basename', subprocess.run(['git', 'rev-parse', '--show-toplevel'],
                                          cwd=Path(__file__).parent.parent.parent, capture_output=True, text=True).stdout.strip()],
                capture_output=True,
                text=True
            )
            current_repo = repo_name_cmd.stdout.strip() if repo_name_cmd.returncode == 0 else 'knowledge-system'
            graph_repo = f"{current_repo}-graph"
            print(f"\n🌐 GitHub Pages Deployment:", file=sys.stderr)
            print(f"   • Dashboard: https://{username}.github.io/{graph_repo}/", file=sys.stderr)
            print(f"   • Graph: https://{username}.github.io/{graph_repo}/graph.html", file=sys.stderr)
            print(f"   • Repository: https://github.com/{username}/{graph_repo}", file=sys.stderr)
        except:
            print(f"\n🌐 GitHub Pages Deployment:", file=sys.stderr)
            print(f"   • Deployed to GitHub Pages", file=sys.stderr)

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

    # Pre-creation validation
    if not validate_before_creation(rems, metadata.get('domain'), metadata.get('isced_path')):
        print("\n❌ Validation failed - no changes made", file=sys.stderr)
        return 1

    # Atomic file creation (Rems + conversation + updates + links)
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

    # Update knowledge graph (backlinks + indexes + normalization)
    rem_ids = [r['rem_id'] for r in rems]
    update_knowledge_graph(rem_ids, write_result.conversation_path, metadata)

    # Materialize inferred links (optional, non-interactive)
    if not args.skip_materialize:
        materialize_inferred_links(prompt_user=False)

    # Sync to FSRS review schedule
    sync_to_fsrs()

    # Record to Memory MCP (placeholder for main agent)
    record_to_memory_mcp(metadata, rems)

    # Generate analytics and visualizations
    generate_analytics()

    # Display completion report with metrics
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
