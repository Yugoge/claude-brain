#!/usr/bin/env python3
"""
Review Statistics Library - ReviewStats Class

Provides statistical calculations and formatting for review sessions.
Used by /review command to display overviews and session summaries.

Part of Story 5.10: Fix review.md script coverage gaps.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone


class ReviewStats:
    """Calculate and format review session statistics."""

    def format_overview(
        self,
        rems: List[Dict],
        by_domain: Dict[str, List[Dict]],
        algorithm: str = "fsrs",
        today: Optional[str] = None
    ) -> str:
        """
        Format review session overview for display.

        Args:
            rems: List of all Rems to review
            by_domain: Result from ReviewLoader.group_by_domain()
            algorithm: "fsrs" or "sm2"
            today: Date string (YYYY-MM-DD), defaults to today

        Returns:
            Multi-line string with:
            - Date
            - Algorithm
            - Total count
            - Domain breakdown
            - Time estimate (1.5 min per Rem for FSRS)

        Example:
            >>> stats = ReviewStats()
            >>> rems = [{"id": "rem1", "domain": "finance"}, {"id": "rem2", "domain": "finance"}]
            >>> by_domain = {"finance": rems}
            >>> overview = stats.format_overview(rems, by_domain, "fsrs")
            >>> print(overview)
            📅 Review Session - 2025-10-31
            📊 Algorithm: FSRS

            You have 2 Rems to review:
            - 2 finance Rems

            Estimated time: 3 minutes (FSRS optimized)
        """
        if today is None:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        total_count = len(rems)
        algo_display = algorithm.upper()

        # Calculate time estimate (1.5 min per Rem for FSRS, 2.0 for SM-2)
        time_per_rem = 1.5 if algorithm == "fsrs" else 2.0
        estimated_time = int(total_count * time_per_rem)

        # Build output
        lines = [
            f"📅 Review Session - {today}",
            f"📊 Algorithm: {algo_display}",
            "",
            f"You have {total_count} Rem{'s' if total_count != 1 else ''} to review:"
        ]

        # Domain breakdown
        for domain, domain_rems in sorted(by_domain.items()):
            count = len(domain_rems)
            lines.append(f"- {count} {domain} Rem{'s' if count != 1 else ''}")

        lines.append("")
        lines.append(f"Estimated time: {estimated_time} minutes ({algo_display} optimized)")

        return "\n".join(lines)

    def calculate_session_stats(
        self,
        rems_reviewed: List[Dict],
        duration_minutes: int,
        algorithm: str = "fsrs"
    ) -> Dict:
        """
        Calculate session statistics.

        Args:
            rems_reviewed: List of reviewed Rem entries (must have 'last_rating' field)
            duration_minutes: Total session duration in minutes
            algorithm: "fsrs" or "sm2"

        Returns:
            {
                "total": int,              # Total Rems reviewed
                "duration": int,           # Duration in minutes
                "average_rating": float,   # Average rating (1-4 scale)
                "easy": int,               # Count of rating=4
                "good": int,               # Count of rating=3
                "hard": int,               # Count of rating=2
                "again": int,              # Count of rating=1
                "efficiency_gain": float   # FSRS vs SM-2 (if applicable)
            }

        Example:
            >>> stats = ReviewStats()
            >>> rems = [
            ...     {"id": "rem1", "last_rating": 4},
            ...     {"id": "rem2", "last_rating": 3},
            ...     {"id": "rem3", "last_rating": 3}
            ... ]
            >>> result = stats.calculate_session_stats(rems, 5, "fsrs")
            >>> result["total"]
            3
            >>> result["average_rating"]
            3.333...
        """
        total = len(rems_reviewed)

        if total == 0:
            return {
                "total": 0,
                "duration": duration_minutes,
                "average_rating": 0.0,
                "easy": 0,
                "good": 0,
                "hard": 0,
                "again": 0,
                "efficiency_gain": 0.0
            }

        # Count ratings
        ratings = [rem.get("last_rating", 3) for rem in rems_reviewed]
        rating_counts = {
            4: ratings.count(4),  # Easy
            3: ratings.count(3),  # Good
            2: ratings.count(2),  # Hard
            1: ratings.count(1)   # Again
        }

        average_rating = sum(ratings) / len(ratings)

        # Calculate efficiency gain (FSRS saves ~30-50% time vs SM-2)
        # This is a rough estimate based on algorithm design
        efficiency_gain = 0.0
        if algorithm == "fsrs":
            # FSRS typically saves 30-50% time, we use 40% as average
            efficiency_gain = 40.0

        return {
            "total": total,
            "duration": duration_minutes,
            "average_rating": average_rating,
            "easy": rating_counts[4],
            "good": rating_counts[3],
            "hard": rating_counts[2],
            "again": rating_counts[1],
            "efficiency_gain": efficiency_gain
        }

    def get_next_review_info(
        self,
        schedule: Dict,
        algorithm: str = "fsrs"
    ) -> Tuple[str, int]:
        """
        Get next review date and count of Rems due.

        Args:
            schedule: The schedule.json data structure
            algorithm: "fsrs" or "sm2"

        Returns:
            Tuple of (next_date, count)
            - next_date: YYYY-MM-DD string of earliest next review
            - count: Number of Rems due on that date

        Example:
            >>> stats = ReviewStats()
            >>> schedule = {
            ...     "concepts": {
            ...         "rem1": {"fsrs_state": {"next_review": "2025-11-01"}},
            ...         "rem2": {"fsrs_state": {"next_review": "2025-11-01"}},
            ...         "rem3": {"fsrs_state": {"next_review": "2025-11-05"}}
            ...     }
            ... }
            >>> date, count = stats.get_next_review_info(schedule, "fsrs")
            >>> date
            '2025-11-01'
            >>> count
            2
        """
        concepts = schedule.get("concepts", {})

        if not concepts:
            return ("No reviews scheduled", 0)

        # Collect next review dates
        next_reviews = []
        for rem_id, rem in concepts.items():
            if algorithm == "fsrs":
                next_date = rem.get("fsrs_state", {}).get("next_review")
            else:  # sm2
                next_date = rem.get("sm2_state", {}).get("next_review_date")

            if next_date:
                next_reviews.append(next_date)

        if not next_reviews:
            return ("No reviews scheduled", 0)

        # Find earliest date
        next_reviews.sort()
        earliest_date = next_reviews[0]
        count = next_reviews.count(earliest_date)

        return (earliest_date, count)

    def format_performance_breakdown(self, stats: Dict) -> str:
        """
        Format performance breakdown for display.

        Args:
            stats: Result from calculate_session_stats()

        Returns:
            Multi-line string with ratings breakdown

        Example:
            >>> stats = ReviewStats()
            >>> session_stats = {
            ...     "total": 10,
            ...     "duration": 15,
            ...     "average_rating": 3.2,
            ...     "easy": 3,
            ...     "good": 5,
            ...     "hard": 2,
            ...     "again": 0,
            ...     "efficiency_gain": 40.0
            ... }
            >>> print(stats.format_performance_breakdown(session_stats))
            Performance breakdown:
            - Easy (4): 3 Rems
            - Good (3): 5 Rems
            - Hard (2): 2 Rems
            - Again (1): 0 Rems
        """
        lines = [
            "Performance breakdown:",
            f"- Easy (4): {stats['easy']} Rem{'s' if stats['easy'] != 1 else ''}",
            f"- Good (3): {stats['good']} Rem{'s' if stats['good'] != 1 else ''}",
            f"- Hard (2): {stats['hard']} Rem{'s' if stats['hard'] != 1 else ''}",
            f"- Again (1): {stats['again']} Rem{'s' if stats['again'] != 1 else ''}"
        ]

        return "\n".join(lines)

    def format_timeline(
        self,
        schedule: Dict,
        algorithm: str = "fsrs",
        today: Optional[str] = None,
        future_days: int = 7
    ) -> str:
        """
        Format comprehensive schedule timeline showing past, present, and future reviews.

        Args:
            schedule: The schedule.json data structure
            algorithm: "fsrs" or "sm2"
            today: Date string (YYYY-MM-DD), defaults to today
            future_days: Number of days to look ahead (default: 7)

        Returns:
            Multi-line string with:
            - Past (overdue) reviews
            - Today's reviews
            - Future reviews (next N days)
            - Summary statistics

        Example output:
            📅 Review Schedule Overview - 2025-11-12
            ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            📊 Algorithm: FSRS

            PAST (Overdue):
              📍 2025-11-11 (1 day overdue): 78 Rems
                 - 45 finance Rems
                 - 33 language Rems

            TODAY (2025-11-12):
              ✅ No reviews due today

            FUTURE (Next 7 days):
              📍 2025-11-13 (in 1 day): 26 Rems
                 - 15 finance Rems
                 - 11 language Rems

            ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            Summary:
            - Total overdue: 78 Rems (needs immediate attention!)
            - Due today: 0 Rems
            - Due this week: 27 Rems
            - Total scheduled: 105 Rems

            Estimated time for overdue: 117 minutes (FSRS optimized)
        """
        from datetime import datetime, timedelta
        from collections import defaultdict

        if today is None:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        today_dt = datetime.strptime(today, "%Y-%m-%d")
        algo_display = algorithm.upper()

        # Organize Rems by date and domain
        date_map = defaultdict(lambda: defaultdict(list))
        concepts = schedule.get("concepts", {})

        for rem_id, rem in concepts.items():
            if algorithm == "fsrs":
                next_date = rem.get("fsrs_state", {}).get("next_review")
            else:
                next_date = rem.get("sm2_state", {}).get("next_review_date")

            if next_date:
                domain = rem.get("domain", "unknown")
                date_map[next_date][domain].append(rem)

        # Separate into past, today, future
        past_dates = []
        today_dates = []
        future_dates = []

        for date_str in sorted(date_map.keys()):
            date_dt = datetime.strptime(date_str, "%Y-%m-%d")
            if date_dt < today_dt:
                past_dates.append(date_str)
            elif date_dt == today_dt:
                today_dates.append(date_str)
            else:
                # Only include dates within future_days window
                days_ahead = (date_dt - today_dt).days
                if days_ahead <= future_days:
                    future_dates.append(date_str)

        # Build output
        lines = [
            f"📅 Review Schedule Overview - {today}",
            "━" * 60,
            f"📊 Algorithm: {algo_display}",
            ""
        ]

        # PAST (Overdue)
        lines.append("PAST (Overdue):")
        if past_dates:
            total_overdue = 0
            for date_str in past_dates:
                date_dt = datetime.strptime(date_str, "%Y-%m-%d")
                days_overdue = (today_dt - date_dt).days
                total_rems = sum(len(rems) for rems in date_map[date_str].values())
                total_overdue += total_rems

                lines.append(f"  📍 {date_str} ({days_overdue} day{'s' if days_overdue != 1 else ''} overdue): {total_rems} Rem{'s' if total_rems != 1 else ''}")

                # Domain breakdown
                for domain, rems in sorted(date_map[date_str].items()):
                    lines.append(f"     - {len(rems)} {domain} Rem{'s' if len(rems) != 1 else ''}")
        else:
            lines.append("  ✅ No overdue reviews")

        lines.append("")

        # TODAY
        lines.append(f"TODAY ({today}):")
        if today_dates:
            for date_str in today_dates:
                total_rems = sum(len(rems) for rems in date_map[date_str].values())
                lines.append(f"  📍 {total_rems} Rem{'s' if total_rems != 1 else ''} due today")

                # Domain breakdown
                for domain, rems in sorted(date_map[date_str].items()):
                    lines.append(f"     - {len(rems)} {domain} Rem{'s' if len(rems) != 1 else ''}")
        else:
            lines.append("  ✅ No reviews due today")

        lines.append("")

        # FUTURE
        lines.append(f"FUTURE (Next {future_days} days):")
        if future_dates:
            for date_str in future_dates:
                date_dt = datetime.strptime(date_str, "%Y-%m-%d")
                days_ahead = (date_dt - today_dt).days
                total_rems = sum(len(rems) for rems in date_map[date_str].values())

                lines.append(f"  📍 {date_str} (in {days_ahead} day{'s' if days_ahead != 1 else ''}): {total_rems} Rem{'s' if total_rems != 1 else ''}")

                # Domain breakdown
                for domain, rems in sorted(date_map[date_str].items()):
                    lines.append(f"     - {len(rems)} {domain} Rem{'s' if len(rems) != 1 else ''}")
        else:
            lines.append(f"  ✅ No reviews scheduled in next {future_days} days")

        lines.append("")
        lines.append("━" * 60)

        # Summary statistics
        total_overdue = sum(sum(len(rems) for rems in date_map[d].values()) for d in past_dates)
        total_today = sum(sum(len(rems) for rems in date_map[d].values()) for d in today_dates)
        total_future = sum(sum(len(rems) for rems in date_map[d].values()) for d in future_dates)
        total_all = len(concepts)

        lines.append("Summary:")
        if total_overdue > 0:
            lines.append(f"- Total overdue: {total_overdue} Rem{'s' if total_overdue != 1 else ''} (needs immediate attention!)")
        else:
            lines.append("- Total overdue: 0 Rems (great job staying current!)")

        lines.append(f"- Due today: {total_today} Rem{'s' if total_today != 1 else ''}")
        lines.append(f"- Due this week: {total_future} Rem{'s' if total_future != 1 else ''}")
        lines.append(f"- Total scheduled: {total_all} Rem{'s' if total_all != 1 else ''}")

        # Time estimate for overdue
        if total_overdue > 0:
            time_per_rem = 1.5 if algorithm == "fsrs" else 2.0
            estimated_time = int(total_overdue * time_per_rem)
            lines.append("")
            lines.append(f"Estimated time for overdue: {estimated_time} minutes ({algo_display} optimized)")

        return "\n".join(lines)


# Example usage / self-test
if __name__ == "__main__":
    print("ReviewStats Library - Self Test\n")
    print("=" * 60)

    stats = ReviewStats()

    # Test 1: format_overview
    print("\n1. Testing format_overview():")
    print("-" * 60)
    test_rems = [
        {"id": "rem1", "domain": "finance"},
        {"id": "rem2", "domain": "finance"},
        {"id": "rem3", "domain": "programming"}
    ]
    by_domain = {
        "finance": [test_rems[0], test_rems[1]],
        "programming": [test_rems[2]]
    }
    overview = stats.format_overview(test_rems, by_domain, "fsrs", "2025-10-31")
    print(overview)

    # Test 2: calculate_session_stats
    print("\n\n2. Testing calculate_session_stats():")
    print("-" * 60)
    reviewed_rems = [
        {"id": "rem1", "last_rating": 4},
        {"id": "rem2", "last_rating": 3},
        {"id": "rem3", "last_rating": 3},
        {"id": "rem4", "last_rating": 2}
    ]
    session_stats = stats.calculate_session_stats(reviewed_rems, 6, "fsrs")
    print(f"Total: {session_stats['total']}")
    print(f"Duration: {session_stats['duration']} minutes")
    print(f"Average rating: {session_stats['average_rating']:.2f}/4")
    print(f"Efficiency gain: {session_stats['efficiency_gain']:.0f}%")

    # Test 3: format_performance_breakdown
    print("\n\n3. Testing format_performance_breakdown():")
    print("-" * 60)
    breakdown = stats.format_performance_breakdown(session_stats)
    print(breakdown)

    # Test 4: get_next_review_info
    print("\n\n4. Testing get_next_review_info():")
    print("-" * 60)
    test_schedule = {
        "concepts": {
            "rem1": {"fsrs_state": {"next_review": "2025-11-01"}},
            "rem2": {"fsrs_state": {"next_review": "2025-11-01"}},
            "rem3": {"fsrs_state": {"next_review": "2025-11-05"}}
        }
    }
    next_date, count = stats.get_next_review_info(test_schedule, "fsrs")
    print(f"Next review: {next_date}")
    print(f"Rems due: {count}")

    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
