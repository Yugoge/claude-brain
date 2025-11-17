#!/usr/bin/env python3
"""
Review Loader - ReviewLoader Class

Handles review workflow operations (argument parsing, filtering, grouping).
Used by /review command to manage review sessions.

Part of Story 5.10: Fix review.md script coverage gaps.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class ReviewLoader:
    """Handle review workflow operations."""

    def __init__(self, schedule_path: str = ".review/schedule.json"):
        """
        Initialize loader with schedule path.

        Args:
            schedule_path: Path to schedule.json file
        """
        self.schedule_path = Path(schedule_path)

    def parse_arguments(self, args: List[str]) -> Dict:
        """
        Parse /review command arguments.

        Args:
            args: Command arguments list

        Returns:
            {
                "mode": "automatic" | "domain" | "specific",
                "domain": str (if mode=domain),
                "rem_id": str (if mode=specific)
            }

        Examples:
            >>> loader = ReviewLoader()
            >>> loader.parse_arguments([])
            {'mode': 'automatic'}
            >>> loader.parse_arguments(['finance'])
            {'mode': 'domain', 'domain': 'finance'}
            >>> loader.parse_arguments(['[[option-delta]]'])
            {'mode': 'specific', 'rem_id': 'option-delta'}
        """
        if not args or len(args) == 0:
            return {"mode": "automatic"}

        arg = args[0].strip()

        # Check for wikilink format: [[rem-id]]
        if arg.startswith("[[") and arg.endswith("]]"):
            rem_id = arg[2:-2]  # Extract ID without brackets
            return {"mode": "specific", "rem_id": rem_id}

        # Otherwise treat as domain
        return {"mode": "domain", "domain": arg}

    def load_schedule(self) -> Dict:
        """
        Load schedule.json.

        Returns:
            Schedule dictionary with Rem entries (from "concepts" key)

        Raises:
            FileNotFoundError: If schedule.json doesn't exist
        """
        if not self.schedule_path.exists():
            raise FileNotFoundError(
                f"Schedule file not found: {self.schedule_path}. "
                f"Run `python3 scripts/scan-and-populate-rems.py` first."
            )

        with open(self.schedule_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Extract concepts dictionary (v2.0.0 format)
            return data.get("concepts", {})

    def filter_rems(
        self, criteria: Dict, today: Optional[str] = None
    ) -> List[Dict]:
        """
        Filter Rems by criteria.

        Args:
            criteria: From parse_arguments()
            today: YYYY-MM-DD (defaults to today)

        Returns:
            List of Rem entries matching criteria

        Examples:
            >>> loader = ReviewLoader()
            >>> # Automatic mode: Filter by due date
            >>> criteria = {"mode": "automatic"}
            >>> rems = loader.filter_rems(criteria, "2025-10-31")
            >>> # Returns only Rems due on or before 2025-10-31

            >>> # Domain mode: Filter by domain
            >>> criteria = {"mode": "domain", "domain": "finance"}
            >>> rems = loader.filter_rems(criteria)
            >>> # Returns all finance Rems

            >>> # Specific mode: Filter by ID
            >>> criteria = {"mode": "specific", "rem_id": "option-delta"}
            >>> rems = loader.filter_rems(criteria)
            >>> # Returns single Rem with ID "option-delta"
        """
        if today is None:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        schedule = self.load_schedule()
        mode = criteria.get("mode", "automatic")

        if mode == "automatic":
            # Filter Rems due today or earlier
            filtered = []
            for rem_id, rem_data in schedule.items():
                # Get next_review from fsrs_state (v2.0.0 format)
                fsrs_state = rem_data.get("fsrs_state", {})
                next_review = fsrs_state.get("next_review", "")
                if next_review and next_review <= today:
                    filtered.append({"id": rem_id, **rem_data})
            return filtered

        elif mode == "domain":
            # Filter Rems by domain (supports partial/hierarchical matching)
            domain_query = criteria.get("domain", "").lower()
            filtered = []
            for rem_id, rem_data in schedule.items():
                rem_domain = rem_data.get("domain", "").lower()

                # Support multiple matching strategies:
                # 1. Exact match: "02-arts-and-humanities/023-languages/0231-language-acquisition"
                # 2. Partial match: "finance" matches "*/0412-finance-banking-insurance"
                # 3. Hierarchical match: "language" matches "*/023-languages/*"
                if (rem_domain == domain_query or
                    domain_query in rem_domain or
                    any(domain_query in part for part in rem_domain.split('/'))):
                    filtered.append({"id": rem_id, **rem_data})
            return filtered

        elif mode == "specific":
            # Filter specific Rem by ID
            rem_id = criteria.get("rem_id", "")
            if rem_id in schedule:
                rem_data = schedule[rem_id]
                return [{"id": rem_id, **rem_data}]
            return []

        return []

    def group_by_domain(self, rems: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group Rems by domain.

        Args:
            rems: List of Rem entries

        Returns:
            {"finance": [...], "language": [...], ...}

        Example:
            >>> loader = ReviewLoader()
            >>> rems = [
            ...     {"id": "rem1", "domain": "finance", "title": "Option Delta"},
            ...     {"id": "rem2", "domain": "finance", "title": "Call Option"},
            ...     {"id": "rem3", "domain": "language", "title": "Subjunctive"}
            ... ]
            >>> grouped = loader.group_by_domain(rems)
            >>> list(grouped.keys())
            ['finance', 'language']
            >>> len(grouped['finance'])
            2
            >>> len(grouped['language'])
            1
        """
        grouped: Dict[str, List[Dict]] = {}

        for rem in rems:
            domain = rem.get("domain", "unknown")
            if domain not in grouped:
                grouped[domain] = []
            grouped[domain].append(rem)

        return grouped

    def sort_by_urgency(
        self, rems: List[Dict], scheduler
    ) -> List[Dict]:
        """
        Sort Rems by urgency (most overdue first).

        Args:
            rems: List of Rem entries
            scheduler: ReviewScheduler instance

        Returns:
            Sorted list (most overdue first)

        Example:
            >>> from review_scheduler import ReviewScheduler
            >>> loader = ReviewLoader()
            >>> scheduler = ReviewScheduler()
            >>> rems = [
            ...     {"id": "rem1", "next_review_date": "2025-10-30"},
            ...     {"id": "rem2", "next_review_date": "2025-10-25"},
            ...     {"id": "rem3", "next_review_date": "2025-10-28"}
            ... ]
            >>> sorted_rems = loader.sort_by_urgency(rems, scheduler)
            >>> [r["id"] for r in sorted_rems]
            ['rem2', 'rem3', 'rem1']
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        def urgency_key(rem: Dict) -> tuple:
            """Calculate urgency key for sorting."""
            # Get next_review from fsrs_state (v2.0.0 format)
            fsrs_state = rem.get("fsrs_state", {})
            next_review = fsrs_state.get("next_review", rem.get("next_review_date", ""))
            if not next_review:
                # No review date = highest urgency (never reviewed)
                return ("1900-01-01", 0)

            # Calculate days overdue (negative = future, positive = overdue)
            try:
                next_date = datetime.strptime(next_review, "%Y-%m-%d")
                today_date = datetime.strptime(today, "%Y-%m-%d")
                days_overdue = (today_date - next_date).days
            except ValueError:
                days_overdue = 0

            # Sort by: 1) Most overdue first, 2) Next review date (earliest first)
            return (next_review, -days_overdue)

        return sorted(rems, key=urgency_key)


# Self-test
if __name__ == "__main__":
    print("Running ReviewLoader self-test...")

    # Test parse_arguments
    loader = ReviewLoader()

    result = loader.parse_arguments([])
    assert result == {"mode": "automatic"}, f"Expected automatic mode, got {result}"

    result = loader.parse_arguments(["finance"])
    assert result == {
        "mode": "domain",
        "domain": "finance",
    }, f"Expected domain mode, got {result}"

    result = loader.parse_arguments(["[[option-delta]]"])
    assert result == {
        "mode": "specific",
        "rem_id": "option-delta",
    }, f"Expected specific mode, got {result}"

    print("✅ parse_arguments: PASS")

    # Test group_by_domain
    rems = [
        {"id": "rem1", "domain": "finance", "title": "Option Delta"},
        {"id": "rem2", "domain": "finance", "title": "Call Option"},
        {"id": "rem3", "domain": "language", "title": "Subjunctive"},
        {"id": "rem4", "domain": "programming", "title": "Binary Search"},
    ]

    grouped = loader.group_by_domain(rems)
    assert "finance" in grouped, "Expected finance domain"
    assert len(grouped["finance"]) == 2, "Expected 2 finance Rems"
    assert "language" in grouped, "Expected language domain"
    assert len(grouped["language"]) == 1, "Expected 1 language Rem"
    assert "programming" in grouped, "Expected programming domain"

    print("✅ group_by_domain: PASS")

    # Test sort_by_urgency (mock scheduler)
    class MockScheduler:
        pass

    rems = [
        {"id": "rem1", "next_review_date": "2025-10-30"},
        {"id": "rem2", "next_review_date": "2025-10-25"},
        {"id": "rem3", "next_review_date": "2025-10-28"},
    ]

    scheduler = MockScheduler()
    sorted_rems = loader.sort_by_urgency(rems, scheduler)

    # Most overdue first (earliest date)
    assert sorted_rems[0]["id"] == "rem2", "Expected rem2 first (most overdue)"
    assert sorted_rems[1]["id"] == "rem3", "Expected rem3 second"
    assert sorted_rems[2]["id"] == "rem1", "Expected rem1 last (least overdue)"

    print("✅ sort_by_urgency: PASS")

    print("\n✅ All ReviewLoader self-tests passed!")
    print(
        "\nNote: load_schedule() and filter_rems() require actual schedule.json file."
    )
    print("Run integration tests with real data to verify these methods.")

    sys.exit(0)
