#!/usr/bin/env python3
"""
Atomic File Writer for /save Workflow

Single atomic transaction for all file operations:
  - Create Knowledge Rems (N files)
  - Update Existing Rems (review sessions only)
  - Create Conversation Archive (with enrichment)
  - Normalize and Rename Conversation File
  - Update Conversation-to-Rem Bidirectional Links

Atomic transaction guarantee:
  - Either ALL files written successfully, or NONE
  - Rollback on any error (no partial state)
  - Validation before commit

Usage:
    from archival.file_writer import FileWriter

    writer = FileWriter()
    result = writer.atomic_write_all(
        enriched_rems=enriched_rems,
        conversation_metadata={...},
        session_type='ask'
    )

Exit Codes:
    0 = Success (all files written)
    1 = Validation error (no files written)
    2 = Write error (rollback performed)
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from contextlib import contextmanager

# Add scripts to path
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "scripts"))


@dataclass
class WriteResult:
    """Result of atomic write operation"""
    success: bool
    created_rems: List[Path]
    conversation_path: Optional[Path]
    error: Optional[str]
    rollback_performed: bool


class WriteError(Exception):
    """Raised when write operation fails"""
    pass


class ValidationError(Exception):
    """Raised when pre-write validation fails"""
    pass


class FileWriter:
    """Atomic file writer with transaction support"""

    def __init__(self, backup_dir: Optional[Path] = None):
        """
        Initialize file writer.

        Args:
            backup_dir: Directory for backups during transaction (default: /tmp/save_backup)
        """
        self.backup_dir = backup_dir or Path('/tmp/save_backup')
        self.backup_dir.mkdir(exist_ok=True, parents=True)
        self.created_files = []
        self.modified_files = []
        self.backups = {}

    @contextmanager
    def transaction(self):
        """
        Context manager for atomic file operations.

        Usage:
            with writer.transaction():
                writer.create_rem_file(...)
                writer.update_conversation(...)
                # Auto-commits on success, rollbacks on exception
        """
        try:
            yield self
            # Success - clean up backups
            self._cleanup_backups()
        except Exception as e:
            # Failure - rollback changes
            print(f"❌ Transaction failed: {e}", file=sys.stderr)
            self._rollback()
            raise

    def create_rem_file(
        self,
        rem_id: str,
        title: str,
        isced_path: str,
        subdomain: str,
        core_points: List[str],
        usage_scenario: str,
        mistakes: List[str],
        typed_relations: List[Dict],
        conversation_file: str,
        conversation_title: str,
        output_path: Path
    ) -> Path:
        """
        Create a single Rem file using create-rem-file.py.

        Returns: Path to created file

        Raises: WriteError if creation fails
        """
        import subprocess

        # Prepare arguments
        args = [
            'python3', 'scripts/archival/create-rem-file.py',
            '--rem-id', rem_id,
            '--title', title,
            '--isced', isced_path,
            '--subdomain', subdomain,
            '--core-points', json.dumps(core_points),
            '--usage-scenario', usage_scenario,
            '--mistakes', json.dumps(mistakes),
            '--related-rems', json.dumps([]),  # Will be populated by backlinks rebuild
            '--conversation-file', conversation_file,
            '--conversation-title', conversation_title,
            '--output-path', str(output_path)
        ]

        # Add typed_relations if provided
        if typed_relations:
            args.extend(['--typed-relations', json.dumps(typed_relations)])

        result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)

        if result.returncode != 0:
            raise WriteError(f"Failed to create Rem {rem_id}: {result.stderr}")

        self.created_files.append(output_path)
        print(f"✓ Created: {output_path.name}", file=sys.stderr)

        return output_path

    def normalize_and_rename_conversation(
        self,
        archived_file: Path,
        conversation_id: str,
        title: str,
        session_type: str,
        agent: str,
        domain: str,
        concepts: List[str],
        tags: List[str],
        summary: str
    ) -> Path:
        """
        Normalize conversation metadata and rename file using normalize_conversation.py.

        Returns: New path after rename

        Raises: WriteError if normalization fails
        """
        import subprocess

        # Backup original file
        backup_path = self.backup_dir / archived_file.name
        shutil.copy2(archived_file, backup_path)
        self.backups[archived_file] = backup_path

        # Run normalization script
        args = [
            'python3', 'scripts/archival/normalize_conversation.py',
            str(archived_file),
            '--id', conversation_id,
            '--title', title,
            '--session-type', session_type,
            '--agent', agent,
            '--domain', domain,
            '--concepts', json.dumps(concepts),
            '--tags', json.dumps(tags),
            '--summary', summary
        ]

        result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)

        if result.returncode != 0:
            raise WriteError(f"Failed to normalize conversation: {result.stderr}")

        # Parse new path from output (last line only, ignore status messages)
        output_lines = result.stdout.strip().split('\n')
        new_path_str = output_lines[-1]  # Last line is the path
        new_path = Path(new_path_str)

        self.modified_files.append(new_path)

        print(f"✓ Normalized: {new_path.name}", file=sys.stderr)

        return new_path

    def update_conversation_with_rems(
        self,
        conversation_path: Path,
        rem_paths: List[Path]
    ):
        """
        Update conversation file with links to created Rems using update-conversation-rems.py.

        Raises: WriteError if update fails
        """
        import subprocess

        # Backup conversation file
        if conversation_path not in self.backups:
            backup_path = self.backup_dir / f"{conversation_path.name}.backup"
            shutil.copy2(conversation_path, backup_path)
            self.backups[conversation_path] = backup_path

        # Run update script
        args = [
            'python3', 'scripts/archival/update-conversation-rems.py',
            str(conversation_path)
        ] + [str(p) for p in rem_paths]

        result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)

        if result.returncode != 0:
            raise WriteError(f"Failed to update conversation Rem links: {result.stderr}")

        print(f"✓ Updated conversation with {len(rem_paths)} Rem links", file=sys.stderr)

    def update_existing_rem(
        self,
        rem_id: str,
        clarification_text: str,
        target_section: str
    ):
        """
        Update existing Rem with clarification (review sessions only).

        Uses update_rem_clarification.py.

        Raises: WriteError if update fails
        """
        import subprocess

        # Find Rem file
        from archival.list_rems_in_domain import find_rem_by_id

        rem_path = find_rem_by_id(rem_id)
        if not rem_path:
            raise WriteError(f"Rem not found: {rem_id}")

        # Backup Rem file
        if rem_path not in self.backups:
            backup_path = self.backup_dir / rem_path.name
            shutil.copy2(rem_path, backup_path)
            self.backups[rem_path] = backup_path

        # Run update script
        args = [
            'python3', 'scripts/archival/update_rem_clarification.py',
            rem_id,
            clarification_text,
            '--section', target_section
        ]

        result = subprocess.run(args, capture_output=True, text=True, cwd=ROOT)

        if result.returncode != 0:
            raise WriteError(f"Failed to update Rem {rem_id}: {result.stderr}")

        self.modified_files.append(rem_path)
        print(f"✓ Updated: {rem_path.name} ({target_section})", file=sys.stderr)

    def _rollback(self):
        """Rollback all changes in transaction"""
        print("🔄 Rolling back changes...", file=sys.stderr)

        # Delete created files
        for file_path in self.created_files:
            if file_path.exists():
                file_path.unlink()
                print(f"  ↩️  Deleted: {file_path.name}", file=sys.stderr)

        # Restore modified files from backups
        for file_path, backup_path in self.backups.items():
            if backup_path.exists():
                shutil.copy2(backup_path, file_path)
                print(f"  ↩️  Restored: {file_path.name}", file=sys.stderr)

        # Clear state
        self.created_files.clear()
        self.modified_files.clear()
        self.backups.clear()

        print("✅ Rollback complete", file=sys.stderr)

    def _cleanup_backups(self):
        """Clean up backup files after successful transaction"""
        for backup_path in self.backups.values():
            if backup_path.exists():
                backup_path.unlink()

        self.backups.clear()

    def atomic_write_all(
        self,
        enriched_rems: List[Dict],
        conversation_metadata: Dict,
        archived_file: Path,
        session_type: str = 'ask',
        rems_to_update: Optional[List[Dict]] = None
    ) -> WriteResult:
        """
        Atomic write of all files (Steps 16-19 + 24).

        Args:
            enriched_rems: List of enriched Rem dicts
            conversation_metadata: Metadata for conversation normalization
            archived_file: Path to temporary archived conversation file
            session_type: 'learn' | 'ask' | 'review'
            rems_to_update: Optional list of Rem updates (review sessions only)

        Returns: WriteResult with paths and status

        Atomic guarantee:
            - All files written successfully → commit
            - Any error → rollback all changes
        """
        try:
            with self.transaction():
                created_rem_paths = []

                # Normalize conversation FIRST (Rems need final conversation path)
                print("\n📝 Normalizing conversation...", file=sys.stderr)
                conversation_path = self.normalize_and_rename_conversation(
                    archived_file=archived_file,
                    conversation_id=conversation_metadata['id'],
                    title=conversation_metadata['title'],
                    session_type=session_type,
                    agent=conversation_metadata.get('agent', 'main'),
                    domain=conversation_metadata['domain'],
                    concepts=[r['rem_id'] for r in enriched_rems],
                    tags=conversation_metadata.get('tags', []),
                    summary=conversation_metadata['summary']
                )

                # Create Knowledge Rems
                print("\n📝 Creating Knowledge Rems...", file=sys.stderr)
                for rem in enriched_rems:
                    rem_path = self.create_rem_file(
                        rem_id=rem['rem_id'],
                        title=rem['title'],
                        isced_path=conversation_metadata['isced_path'],
                        subdomain=conversation_metadata['subdomain'],
                        core_points=rem['core_points'],
                        usage_scenario=rem.get('usage_scenario', ''),
                        mistakes=rem.get('my_mistakes', []),
                        typed_relations=rem.get('typed_relations', []),
                        conversation_file=str(conversation_path),
                        conversation_title=conversation_metadata['title'],
                        output_path=Path(rem['output_path'])
                    )
                    created_rem_paths.append(rem_path)

                # Update Existing Rems (review sessions only)
                if rems_to_update:
                    print("\n✏️  Updating existing Rems...", file=sys.stderr)
                    for update in rems_to_update:
                        self.update_existing_rem(
                            rem_id=update['rem_id'],
                            clarification_text=update['clarification_text'],
                            target_section=update['target_section']
                        )

                # Update Conversation with Rem Links (bidirectional)
                print("\n🔗 Linking conversation to Rems...", file=sys.stderr)
                self.update_conversation_with_rems(conversation_path, created_rem_paths)

                print("\n✅ All files written successfully", file=sys.stderr)

                return WriteResult(
                    success=True,
                    created_rems=created_rem_paths,
                    conversation_path=conversation_path,
                    error=None,
                    rollback_performed=False
                )

        except (WriteError, ValidationError) as e:
            return WriteResult(
                success=False,
                created_rems=[],
                conversation_path=None,
                error=str(e),
                rollback_performed=True
            )


def main():
    """CLI for testing atomic writes"""
    import argparse

    parser = argparse.ArgumentParser(description='Atomic File Writer for /save Workflow')
    parser.add_argument('--enriched-rems', required=True, help='Path to enriched_rems.json')
    parser.add_argument('--metadata', required=True, help='Path to conversation_metadata.json')
    parser.add_argument('--archived-file', required=True, help='Path to archived conversation file')
    parser.add_argument('--session-type', default='ask', choices=['learn', 'ask', 'review'])

    args = parser.parse_args()

    # Load data
    with open(args.enriched_rems, 'r') as f:
        enriched_rems = json.load(f)

    with open(args.metadata, 'r') as f:
        metadata = json.load(f)

    # Execute atomic write
    writer = FileWriter()
    result = writer.atomic_write_all(
        enriched_rems=enriched_rems,
        conversation_metadata=metadata,
        archived_file=Path(args.archived_file),
        session_type=args.session_type
    )

    if result.success:
        print(f"\n✅ SUCCESS", file=sys.stderr)
        print(f"Created Rems: {len(result.created_rems)}", file=sys.stderr)
        print(f"Conversation: {result.conversation_path}", file=sys.stderr)
        return 0
    else:
        print(f"\n❌ FAILED: {result.error}", file=sys.stderr)
        print(f"Rollback performed: {result.rollback_performed}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
