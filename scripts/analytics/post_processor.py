#!/usr/bin/env python3
"""
Post-Processor for /save Workflow

Consolidates Steps 22-26 (background post-processing):
  Step 22: Sync Rems to Review Schedule (FSRS)
  Step 23: Record to Memory MCP
  Step 25: Auto-generate Statistics
  Step 26: Generate Analytics & Visualizations

These operations run after file creation and graph maintenance.
Can be executed asynchronously (non-blocking for main workflow).

Usage:
    from analytics.post_processor import PostProcessor

    processor = PostProcessor()
    result = processor.post_process(
        created_rems=['rem-id-1', 'rem-id-2'],
        conversation_metadata={...}
    )

Exit Codes:
    0 = Success (all operations completed)
    1 = Partial success (some operations failed, non-critical)
    2 = Critical failure (FSRS sync failed)
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

# Add scripts to path
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "scripts"))


@dataclass
class PostProcessResult:
    """Result of post-processing operations"""
    success: bool
    fsrs_synced: bool
    fsrs_first_review: Optional[str]
    memory_mcp_recorded: bool
    analytics_generated: bool
    visualization_generated: bool
    errors: List[str]


class PostProcessError(Exception):
    """Raised when critical post-processing operation fails"""
    pass


class PostProcessor:
    """Background post-processor for /save workflow"""

    def __init__(self, kb_root: Optional[Path] = None):
        """
        Initialize post-processor.

        Args:
            kb_root: Knowledge base root (default: /root/knowledge-system)
        """
        self.kb_root = kb_root or ROOT
        self.errors = []

    def sync_rems_to_fsrs(self, created_rem_ids: List[str]) -> tuple[bool, Optional[str]]:
        """
        Step 22: Sync newly created Rems to FSRS review schedule.

        Args:
            created_rem_ids: List of newly created Rem IDs

        Returns: (success, first_review_date)

        Raises: PostProcessError if FSRS sync fails (critical)
        """
        print("📅 Step 22: Syncing Rems to FSRS schedule...", file=sys.stderr)

        try:
            result = subprocess.run(
                ['python3', 'scripts/utilities/scan-and-populate-rems.py', '--verbose', '--yes'],
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=60
            )

            if result.returncode != 0:
                raise PostProcessError(f"FSRS sync failed: {result.stderr}")

            # Parse first review date from output
            output = result.stdout + result.stderr
            import re
            match = re.search(r'First review: (\d{4}-\d{2}-\d{2})', output)
            first_review = match.group(1) if match else None

            print(f"  ✓ Synced {len(created_rem_ids)} Rems to FSRS", file=sys.stderr)
            if first_review:
                print(f"  📆 First review: {first_review}", file=sys.stderr)

            return True, first_review

        except subprocess.TimeoutExpired:
            raise PostProcessError("FSRS sync timed out (>60s)")
        except Exception as e:
            raise PostProcessError(f"FSRS sync failed: {e}")

    def record_to_memory_mcp(
        self,
        conversation_metadata: Dict,
        created_rems: List[Dict]
    ) -> bool:
        """
        Step 23: Record conversation and concepts to Memory MCP.

        Args:
            conversation_metadata: Conversation metadata
            created_rems: List of created Rem dicts (with rem_id, title, core_points)

        Returns: True if successful, False if failed (non-critical)

        Note: Graceful degradation - failure doesn't block workflow
        """
        print("\n🧠 Step 23: Recording to Memory MCP...", file=sys.stderr)

        try:
            # Try to import MCP tools
            try:
                from mcp_tools import create_entities, create_relations
            except ImportError:
                print("  ⚠️  Warning: MCP tools not available, skipping Memory recording", file=sys.stderr)
                return False

            # Create conversation entity
            conversation_entity = {
                'name': f"conversation-{conversation_metadata['id']}",
                'entityType': 'conversation',
                'observations': [
                    f"Topic: {conversation_metadata['title']}",
                    f"Domain: {conversation_metadata['domain']}",
                    f"Date: {conversation_metadata['date']}",
                    f"Extracted {len(created_rems)} Rems: {', '.join(r['rem_id'] for r in created_rems)}",
                    f"Session type: {conversation_metadata['session_type']}"
                ]
            }

            # Create concept entities
            concept_entities = []
            for rem in created_rems:
                entity = {
                    'name': rem['title'],
                    'entityType': f"{conversation_metadata['domain']}-rem",
                    'observations': [
                        f"Rem ID: {rem['rem_id']}",
                        f"File: knowledge-base/.../{{slug}}.md",
                        f"Core points: {', '.join(rem['core_points'][:2])}",  # First 2 points
                        f"Source conversation: conversation-{conversation_metadata['id']}"
                    ]
                }
                concept_entities.append(entity)

            # Create relations
            relations = []
            for rem in created_rems:
                relations.append({
                    'from': f"conversation-{conversation_metadata['id']}",
                    'to': rem['title'],
                    'relationType': 'extracted_rem'
                })

            # Execute MCP operations
            create_entities([conversation_entity] + concept_entities)
            create_relations(relations)

            print(f"  ✓ Recorded to Memory MCP", file=sys.stderr)
            print(f"    - 1 conversation entity", file=sys.stderr)
            print(f"    - {len(concept_entities)} concept entities", file=sys.stderr)
            print(f"    - {len(relations)} relations", file=sys.stderr)

            return True

        except Exception as e:
            # Non-critical error - log and continue
            error_msg = f"Memory MCP recording failed: {e}"
            print(f"  ⚠️  {error_msg}", file=sys.stderr)
            self.errors.append(error_msg)
            return False

    def generate_analytics(self, period: int = 30) -> bool:
        """
        Step 25: Generate learning analytics.

        Args:
            period: Analysis period in days

        Returns: True if successful, False if failed (non-critical)
        """
        print(f"\n📊 Step 25: Generating analytics (last {period} days)...", file=sys.stderr)

        try:
            result = subprocess.run(
                ['python3', 'scripts/analytics/generate-analytics.py', '--period', str(period)],
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=30
            )

            if result.returncode != 0:
                raise Exception(result.stderr)

            print("  ✓ Analytics generated: .review/analytics-cache.json", file=sys.stderr)
            return True

        except Exception as e:
            # Non-critical error - log and continue
            error_msg = f"Analytics generation failed: {e}"
            print(f"  ⚠️  {error_msg}", file=sys.stderr)
            self.errors.append(error_msg)
            return False

    def generate_visualizations(self) -> bool:
        """
        Step 26: Generate knowledge graph visualization.

        Returns: True if successful, False if failed (non-critical)
        """
        print("\n🎨 Step 26: Generating visualizations...", file=sys.stderr)

        try:
            # Step 26.1: Generate graph data
            result = subprocess.run(
                ['python3', 'scripts/knowledge-graph/generate-graph-data.py', '--force'],
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=60
            )

            if result.returncode != 0:
                raise Exception(result.stderr)

            # Step 26.2: Generate HTML visualization
            result = subprocess.run(
                ['python3', 'scripts/knowledge-graph/generate-visualization-html.py'],
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=30
            )

            if result.returncode != 0:
                raise Exception(result.stderr)

            print("  ✓ Visualization created: knowledge-graph.html", file=sys.stderr)
            return True

        except Exception as e:
            # Non-critical error - log and continue
            error_msg = f"Visualization generation failed: {e}"
            print(f"  ⚠️  {error_msg}", file=sys.stderr)
            self.errors.append(error_msg)
            return False

    def post_process(
        self,
        created_rem_ids: List[str],
        created_rems: List[Dict],
        conversation_metadata: Dict,
        analytics_period: int = 30
    ) -> PostProcessResult:
        """
        Execute complete post-processing pipeline (Steps 22-26).

        Args:
            created_rem_ids: List of newly created Rem IDs
            created_rems: List of created Rem dicts (with full data)
            conversation_metadata: Conversation metadata
            analytics_period: Analysis period in days

        Returns: PostProcessResult with status

        Critical operations (block on failure):
            - FSRS sync (Step 22)

        Non-critical operations (log but continue):
            - Memory MCP recording (Step 23)
            - Analytics generation (Step 25)
            - Visualization generation (Step 26)
        """
        try:
            print("\n🔧 Starting post-processing pipeline...", file=sys.stderr)

            # Step 22: FSRS sync (CRITICAL)
            fsrs_synced, first_review = self.sync_rems_to_fsrs(created_rem_ids)

            # Step 23: Memory MCP (non-critical)
            memory_recorded = self.record_to_memory_mcp(conversation_metadata, created_rems)

            # Step 25: Analytics (non-critical)
            analytics_generated = self.generate_analytics(analytics_period)

            # Step 26: Visualizations (non-critical)
            visualization_generated = self.generate_visualizations()

            # Determine overall success
            success = fsrs_synced  # At minimum, FSRS must succeed
            has_warnings = len(self.errors) > 0

            if success and not has_warnings:
                print("\n✅ Post-processing complete (all operations successful)", file=sys.stderr)
            elif success:
                print(f"\n⚠️  Post-processing complete with {len(self.errors)} warnings", file=sys.stderr)

            return PostProcessResult(
                success=success,
                fsrs_synced=fsrs_synced,
                fsrs_first_review=first_review,
                memory_mcp_recorded=memory_recorded,
                analytics_generated=analytics_generated,
                visualization_generated=visualization_generated,
                errors=self.errors
            )

        except PostProcessError as e:
            # Critical error (FSRS sync failed)
            return PostProcessResult(
                success=False,
                fsrs_synced=False,
                fsrs_first_review=None,
                memory_mcp_recorded=False,
                analytics_generated=False,
                visualization_generated=False,
                errors=[str(e)]
            )


def main():
    """CLI for testing post-processing"""
    import argparse

    parser = argparse.ArgumentParser(description='Post-Processor for /save Workflow')
    parser.add_argument('--rem-ids', nargs='+', required=True, help='List of created Rem IDs')
    parser.add_argument('--enriched-rems', required=True, help='Path to enriched_rems.json')
    parser.add_argument('--metadata', required=True, help='Path to conversation_metadata.json')
    parser.add_argument('--analytics-period', type=int, default=30, help='Analytics period in days')

    args = parser.parse_args()

    # Load data
    with open(args.enriched_rems, 'r') as f:
        created_rems = json.load(f)

    with open(args.metadata, 'r') as f:
        metadata = json.load(f)

    # Execute post-processing
    processor = PostProcessor()
    result = processor.post_process(
        created_rem_ids=args.rem_ids,
        created_rems=created_rems,
        conversation_metadata=metadata,
        analytics_period=args.analytics_period
    )

    if result.success:
        print(f"\n✅ SUCCESS", file=sys.stderr)
        print(f"FSRS synced: {result.fsrs_synced}", file=sys.stderr)
        if result.fsrs_first_review:
            print(f"First review: {result.fsrs_first_review}", file=sys.stderr)
        print(f"Memory MCP: {result.memory_mcp_recorded}", file=sys.stderr)
        print(f"Analytics: {result.analytics_generated}", file=sys.stderr)
        print(f"Visualization: {result.visualization_generated}", file=sys.stderr)

        if result.errors:
            print(f"\n⚠️  {len(result.errors)} warnings:", file=sys.stderr)
            for error in result.errors:
                print(f"  - {error}", file=sys.stderr)
            return 1  # Partial success

        return 0

    else:
        print(f"\n❌ FAILED", file=sys.stderr)
        for error in result.errors:
            print(f"  - {error}", file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
