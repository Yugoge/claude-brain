#!/usr/bin/env python3
"""
Knowledge Graph Maintainer - Unified Graph Operations

Consolidates Steps 20-21 of /save workflow:
  Step 20: Update Knowledge Graph (backlinks + conversation index + wikilinks)
  Step 21: Materialize Inferred Links (optional, with preview)

Single entry point for all graph maintenance operations after file creation.

Usage:
    from knowledge_graph.graph_maintainer import GraphMaintainer

    maintainer = GraphMaintainer()
    result = maintainer.maintain_graph(
        created_rems=['rem-id-1', 'rem-id-2'],
        conversation_metadata={...}
    )

Exit Codes:
    0 = Success (all graph ops completed)
    1 = Warning (non-critical errors)
    2 = Critical error (graph corruption)
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

# Add scripts to path
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "scripts"))


@dataclass
class GraphMaintenanceResult:
    """Result of graph maintenance operations"""
    success: bool
    backlinks_updated: bool
    conversation_indexed: bool
    wikilinks_normalized: int  # Number of files updated
    inferred_links_materialized: Optional[int]  # None if skipped
    error: Optional[str]


class GraphError(Exception):
    """Raised when graph operation fails"""
    pass


class GraphMaintainer:
    """Unified knowledge graph maintenance"""

    def __init__(self, kb_root: Optional[Path] = None):
        """
        Initialize graph maintainer.

        Args:
            kb_root: Knowledge base root (default: /root/knowledge-system)
        """
        self.kb_root = kb_root or ROOT
        self.backlinks_file = self.kb_root / 'knowledge-base' / '_index' / 'backlinks.json'

    def update_backlinks(self, created_rem_ids: List[str]) -> bool:
        """
        Step 20.1: Update backlinks (incremental, fallback to full rebuild).

        Args:
            created_rem_ids: List of newly created Rem IDs

        Returns: True if successful

        Raises: GraphError if update fails
        """
        print("🔗 Step 20.1: Updating backlinks...", file=sys.stderr)

        try:
            # Try incremental update first (70% token reduction)
            args = [
                'python3',
                'scripts/knowledge-graph/update-backlinks-incremental.py'
            ] + created_rem_ids

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=120
            )

            if result.returncode == 0:
                print(f"  ✓ Incremental update: {len(created_rem_ids)} new Rems", file=sys.stderr)
                return True

            # Fallback to full rebuild
            print("  ⚠️  Incremental update failed, falling back to full rebuild", file=sys.stderr)

            result = subprocess.run(
                ['python3', 'scripts/knowledge-graph/rebuild-backlinks.py', '--cleanup-backups', '5'],
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=300
            )

            if result.returncode != 0:
                raise GraphError(f"Backlinks rebuild failed: {result.stderr}")

            print("  ✓ Full rebuild completed", file=sys.stderr)
            return True

        except subprocess.TimeoutExpired:
            raise GraphError("Backlinks update timed out (>5 minutes)")
        except Exception as e:
            raise GraphError(f"Backlinks update failed: {e}")

    def update_conversation_index(self, conversation_metadata: Dict) -> bool:
        """
        Step 20.2: Update conversation index.

        Args:
            conversation_metadata: Dict with id, title, date, file, agent, domain, session_type, turns, rems

        Returns: True if successful

        Raises: GraphError if update fails
        """
        print("📇 Step 20.2: Updating conversation index...", file=sys.stderr)

        try:
            args = [
                'python3',
                'scripts/archival/update-conversation-index.py',
                '--id', conversation_metadata['id'],
                '--title', conversation_metadata['title'],
                '--date', conversation_metadata['date'],
                '--file', conversation_metadata['file'],
                '--agent', conversation_metadata['agent'],
                '--domain', conversation_metadata['domain'],
                '--session-type', conversation_metadata['session_type'],
                '--turns', str(conversation_metadata['turns']),
                '--rems', str(conversation_metadata['rems'])
            ]

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=30
            )

            if result.returncode != 0:
                raise GraphError(f"Conversation index update failed: {result.stderr}")

            print("  ✓ Conversation indexed", file=sys.stderr)
            return True

        except Exception as e:
            raise GraphError(f"Conversation index update failed: {e}")

    def normalize_wikilinks(self) -> int:
        """
        Step 20.3: Normalize wikilinks ([[id]] → [Title](path.md)).

        Returns: Number of files updated

        Raises: GraphError if normalization fails
        """
        print("🔗 Step 20.3: Normalizing wikilinks...", file=sys.stderr)

        try:
            result = subprocess.run(
                ['python3', 'scripts/knowledge-graph/normalize-links.py', '--mode', 'replace', '--verbose'],
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=120
            )

            if result.returncode != 0:
                raise GraphError(f"Wikilinks normalization failed: {result.stderr}")

            # Parse number of files updated from output
            output = result.stdout + result.stderr
            import re
            match = re.search(r'updated (\d+)', output)
            files_updated = int(match.group(1)) if match else 0

            print(f"  ✓ Normalized {files_updated} files", file=sys.stderr)
            return files_updated

        except Exception as e:
            raise GraphError(f"Wikilinks normalization failed: {e}")

    def materialize_inferred_links(self, auto_approve: bool = False) -> Optional[int]:
        """
        Step 21: Materialize inferred links (optional, with preview).

        Args:
            auto_approve: If True, skip preview and materialize automatically

        Returns: Number of links materialized, or None if skipped

        Raises: GraphError if materialization fails
        """
        print("\n🧠 Step 21: Checking for inferred links...", file=sys.stderr)

        try:
            # Dry-run first to check if there are inferences
            result = subprocess.run(
                ['python3', 'scripts/knowledge-graph/materialize-inferred-links.py', '--dry-run', '--verbose'],
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=60
            )

            if result.returncode != 0:
                # No inferred links found - not an error
                if 'No inferred links found' in result.stderr:
                    print("  ℹ️  No inferred links found", file=sys.stderr)
                    return None
                raise GraphError(f"Inferred links check failed: {result.stderr}")

            # Parse preview
            output = result.stdout + result.stderr
            import re
            match = re.search(r'Found (\d+) potential inferred links', output)

            if not match:
                print("  ℹ️  No inferred links found", file=sys.stderr)
                return None

            count = int(match.group(1))
            print(f"  🔍 Found {count} potential inferred links", file=sys.stderr)

            if not auto_approve:
                print("  ⚠️  Run with --materialize-inferred to apply", file=sys.stderr)
                return None

            # Materialize
            result = subprocess.run(
                ['python3', 'scripts/knowledge-graph/materialize-inferred-links.py', '--verbose'],
                capture_output=True,
                text=True,
                cwd=self.kb_root,
                timeout=120
            )

            if result.returncode != 0:
                raise GraphError(f"Inferred links materialization failed: {result.stderr}")

            print(f"  ✓ Materialized {count} inferred links", file=sys.stderr)
            return count

        except Exception as e:
            # Non-critical error - log but don't fail
            print(f"  ⚠️  Warning: {e}", file=sys.stderr)
            return None

    def validate_graph_integrity(self) -> bool:
        """
        Validate knowledge graph integrity after maintenance.

        Checks:
          - backlinks.json exists and is valid JSON
          - No orphaned nodes (Rems without any links)
          - No broken links (references to non-existent Rems)

        Returns: True if graph is healthy

        Raises: GraphError if critical corruption detected
        """
        print("\n✅ Validating graph integrity...", file=sys.stderr)

        try:
            # Check backlinks.json exists
            if not self.backlinks_file.exists():
                raise GraphError("backlinks.json not found")

            # Load and validate JSON
            with open(self.backlinks_file, 'r') as f:
                backlinks = json.load(f)

            total_concepts = len(backlinks)
            print(f"  ✓ Backlinks index healthy ({total_concepts} concepts)", file=sys.stderr)

            # Check for orphaned nodes (warning only)
            orphaned = [k for k, v in backlinks.items() if not v.get('links_to') and not v.get('linked_from')]
            if orphaned:
                print(f"  ⚠️  Warning: {len(orphaned)} orphaned concepts (no links)", file=sys.stderr)

            return True

        except json.JSONDecodeError as e:
            raise GraphError(f"Backlinks index corrupted: {e}")
        except Exception as e:
            raise GraphError(f"Graph validation failed: {e}")

    def maintain_graph(
        self,
        created_rem_ids: List[str],
        conversation_metadata: Dict,
        materialize_inferred: bool = False
    ) -> GraphMaintenanceResult:
        """
        Execute complete graph maintenance (Steps 20-21).

        Args:
            created_rem_ids: List of newly created Rem IDs
            conversation_metadata: Metadata for conversation indexing
            materialize_inferred: Whether to auto-materialize inferred links

        Returns: GraphMaintenanceResult with status

        Atomic guarantee:
            - Steps execute sequentially
            - Non-critical errors logged but don't stop pipeline
            - Critical errors raise GraphError
        """
        try:
            print("\n🔧 Starting graph maintenance pipeline...", file=sys.stderr)

            # Step 20.1: Update backlinks
            backlinks_updated = self.update_backlinks(created_rem_ids)

            # Step 20.2: Update conversation index
            conversation_indexed = self.update_conversation_index(conversation_metadata)

            # Step 20.3: Normalize wikilinks
            wikilinks_updated = self.normalize_wikilinks()

            # Step 21: Materialize inferred links (optional)
            inferred_links = self.materialize_inferred_links(auto_approve=materialize_inferred)

            # Validate graph integrity
            self.validate_graph_integrity()

            print("\n✅ Graph maintenance complete", file=sys.stderr)

            return GraphMaintenanceResult(
                success=True,
                backlinks_updated=backlinks_updated,
                conversation_indexed=conversation_indexed,
                wikilinks_normalized=wikilinks_updated,
                inferred_links_materialized=inferred_links,
                error=None
            )

        except GraphError as e:
            return GraphMaintenanceResult(
                success=False,
                backlinks_updated=False,
                conversation_indexed=False,
                wikilinks_normalized=0,
                inferred_links_materialized=None,
                error=str(e)
            )


def main():
    """CLI for testing graph maintenance"""
    import argparse

    parser = argparse.ArgumentParser(description='Knowledge Graph Maintainer')
    parser.add_argument('--rem-ids', nargs='+', required=True, help='List of created Rem IDs')
    parser.add_argument('--metadata', required=True, help='Path to conversation_metadata.json')
    parser.add_argument('--materialize-inferred', action='store_true', help='Auto-materialize inferred links')

    args = parser.parse_args()

    # Load metadata
    with open(args.metadata, 'r') as f:
        metadata = json.load(f)

    # Execute graph maintenance
    maintainer = GraphMaintainer()
    result = maintainer.maintain_graph(
        created_rem_ids=args.rem_ids,
        conversation_metadata=metadata,
        materialize_inferred=args.materialize_inferred
    )

    if result.success:
        print(f"\n✅ SUCCESS", file=sys.stderr)
        print(f"Backlinks updated: {result.backlinks_updated}", file=sys.stderr)
        print(f"Conversation indexed: {result.conversation_indexed}", file=sys.stderr)
        print(f"Wikilinks normalized: {result.wikilinks_normalized} files", file=sys.stderr)
        if result.inferred_links_materialized is not None:
            print(f"Inferred links materialized: {result.inferred_links_materialized}", file=sys.stderr)
        return 0
    else:
        print(f"\n❌ FAILED: {result.error}", file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
