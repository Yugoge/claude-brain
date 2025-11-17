#!/usr/bin/env python3
"""
Unified review scheduler supporting SM-2 and FSRS algorithms.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import sys
import os
import json
import shutil
import fcntl
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(__file__))

from fsrs_algorithm import FSRSAlgorithm


class ReviewScheduler:
    """FSRS-based review scheduler."""

    def __init__(self):
        self.fsrs = FSRSAlgorithm()

    def schedule_review(
        self,
        concept: Dict,
        rating: int
    ) -> Dict:
        """
        Schedule next review using FSRS algorithm.

        Args:
            concept: Concept data with fsrs_state
            rating: User rating (1-4: Again, Hard, Good, Easy)

        Returns:
            Updated concept with new FSRS state (JSON-safe string dates)
        """
        # Normalize rating to FSRS range (1-4)
        fsrs_rating = self._normalize_rating_for_fsrs(rating)

        # Update FSRS state (always returns JSON-safe strings)
        new_state = self.fsrs.review(
            concept.get("fsrs_state", {}),
            fsrs_rating
        )
        concept["fsrs_state"] = new_state

        # Ensure active_algorithm is set
        concept["active_algorithm"] = "fsrs"

        return concept

    def _normalize_rating_for_fsrs(self, rating: int) -> int:
        """Normalize rating to FSRS range (1-4)."""
        if rating < 1:
            return 1
        elif rating > 4:
            return 4
        else:
            return rating

    def get_next_review_date(self, concept: Dict) -> str:
        """
        Get next review date for concept.

        Args:
            concept: Concept data with fsrs_state

        Returns:
            Next review date (ISO string)
        """
        return concept.get("fsrs_state", {}).get("next_review")

    @staticmethod
    def _convert_dates_to_str(obj):
        """
        Recursively convert datetime objects to ISO format strings.

        Critical for JSON serialization - prevents TypeError.
        """
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, dict):
            return {k: ReviewScheduler._convert_dates_to_str(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [ReviewScheduler._convert_dates_to_str(item) for item in obj]
        return obj

    @staticmethod
    def save_schedule_atomic(schedule_path: str, schedule: Dict):
        """
        Atomically save schedule.json with datetime conversion and backup.

        This method prevents data corruption by:
        1. Creating a backup before modification
        2. Converting datetime objects to strings
        3. Writing to a temp file first
        4. Atomic rename (prevents partial writes)
        5. File locking (prevents concurrent writes)

        Args:
            schedule_path: Path to schedule.json
            schedule: Schedule data (may contain datetime objects)

        Raises:
            ValueError: If schedule data is invalid
            IOError: If write fails
            BlockingIOError: If file is locked by another process
        """
        schedule_path = Path(schedule_path)

        # 0. Acquire exclusive lock on schedule file
        # Use a separate lock file to avoid conflicts with the actual data file
        lock_path = schedule_path.with_suffix('.lock')
        lock_file = None

        try:
            lock_file = open(lock_path, 'w')
            # Try to acquire exclusive lock (non-blocking)
            # LOCK_EX = exclusive lock, LOCK_NB = non-blocking
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise BlockingIOError(
                    f"Schedule file is locked by another review session. "
                    f"Please wait for the other session to complete."
                )

            # 1. Backup existing file
            if schedule_path.exists():
                backup_dir = schedule_path.parent / 'backups'
                backup_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
                backup_path = backup_dir / f"{schedule_path.stem}-{timestamp}.json"
                shutil.copy2(schedule_path, backup_path)

                # Cleanup old backups (keep last 10)
                backups = sorted(backup_dir.glob(f"{schedule_path.stem}-*.json"))
                for old_backup in backups[:-10]:
                    old_backup.unlink()

            # 2. Convert datetime objects to strings
            clean_schedule = ReviewScheduler._convert_dates_to_str(schedule)

            # 3. Write to temp file first (atomic write pattern)
            temp_path = schedule_path.with_suffix('.tmp')
            try:
                with open(temp_path, 'w') as f:
                    json.dump(clean_schedule, f, indent=2)

                # 4. Atomic rename (POSIX guarantees atomicity)
                shutil.move(str(temp_path), str(schedule_path))

            except Exception as e:
                # Cleanup temp file on failure
                if temp_path.exists():
                    temp_path.unlink()
                raise IOError(f"Failed to save schedule: {e}")

        finally:
            # 5. Always release lock and cleanup
            if lock_file:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    lock_file.close()
                except:
                    pass
                # Remove lock file
                try:
                    if lock_path.exists():
                        lock_path.unlink()
                except:
                    pass

    def update_and_save(
        self,
        schedule_path: str,
        concept_id: str,
        rating: int
    ) -> Dict:
        """
        Update concept and save schedule atomically.

        Convenience method for review sessions - handles all the boilerplate safely.

        Args:
            schedule_path: Path to schedule.json
            concept_id: ID of concept to update
            rating: User rating (1-4: Again, Hard, Good, Easy)

        Returns:
            Updated concept with new FSRS state (JSON-safe string dates)

        Example:
            >>> scheduler = ReviewScheduler()
            >>> updated = scheduler.update_and_save(
            ...     '.review/schedule.json',
            ...     'finance-sharpe-ratio',
            ...     4
            ... )
            >>> print(updated['fsrs_state']['next_review'])
            '2025-11-15'
        """
        # Load current schedule
        with open(schedule_path, 'r') as f:
            schedule = json.load(f)

        # Update concept
        if concept_id not in schedule['concepts']:
            raise ValueError(f"Concept '{concept_id}' not found in schedule")

        concept = schedule['concepts'][concept_id]
        # Returns JSON-safe strings for dates
        updated_concept = self.schedule_review(concept, rating)
        schedule['concepts'][concept_id] = updated_concept

        # Save atomically with backup
        self.save_schedule_atomic(schedule_path, schedule)

        return updated_concept
