#!/usr/bin/env python3
"""
Measure FSRS efficiency improvement over SM-2.

Target: 30-50% reduction in review time
Measurement: (SM-2 reviews - FSRS reviews) / SM-2 reviews * 100
"""

import json
from datetime import datetime, timedelta
import os


def measure_improvement():
    """Measure FSRS improvement over baseline SM-2."""
    history_file = ".review/history.json"

    if not os.path.exists(history_file):
        print("❌ No review history found")
        return 0.0

    with open(history_file) as f:
        history_data = json.load(f)

    # Extract all reviews from sessions
    all_reviews = []
    if "sessions" in history_data:
        for session in history_data["sessions"]:
            if session.get("session_type") == "review":
                for review in session.get("reviews", []):
                    timestamp = review.get("timestamp")
                    if timestamp:
                        all_reviews.append({
                            "timestamp": datetime.fromisoformat(timestamp),
                            "algorithm": review.get("algorithm", "sm2"),
                            "rating": review.get("rating", 3)
                        })

    if not all_reviews:
        print("⚠️  No review data available")
        return 0.0

    # Sort by timestamp
    all_reviews.sort(key=lambda r: r["timestamp"])

    # Find migration date (first FSRS review)
    fsrs_reviews = [r for r in all_reviews if r["algorithm"] == "fsrs"]

    if not fsrs_reviews:
        print("⚠️  No FSRS reviews found yet")
        return 0.0

    migration_date = min(r["timestamp"] for r in fsrs_reviews)

    # Baseline period (before FSRS migration)
    baseline_start = migration_date - timedelta(days=30)  # 30 days before migration
    baseline_end = migration_date

    # Treatment period (after FSRS migration)
    treatment_start = migration_date
    treatment_end = datetime.now()

    # Count reviews in each period
    baseline_reviews = [
        r for r in all_reviews
        if baseline_start <= r["timestamp"] < baseline_end and r["algorithm"] == "sm2"
    ]

    treatment_reviews = [
        r for r in all_reviews
        if treatment_start <= r["timestamp"] <= treatment_end and r["algorithm"] == "fsrs"
    ]

    # Normalize to reviews per day
    baseline_days = (baseline_end - baseline_start).days
    treatment_days = (treatment_end - treatment_start).days

    baseline_rate = len(baseline_reviews) / baseline_days if baseline_days > 0 else 0
    treatment_rate = len(treatment_reviews) / treatment_days if treatment_days > 0 else 0

    # Calculate reduction
    if baseline_rate > 0:
        reduction = ((baseline_rate - treatment_rate) / baseline_rate) * 100
    else:
        reduction = 0

    # Display results
    print("📊 FSRS Efficiency Measurement")
    print("=" * 50)
    print(f"Baseline (SM-2): {baseline_rate:.2f} reviews/day")
    print(f"Treatment (FSRS): {treatment_rate:.2f} reviews/day")
    print(f"Reduction: {reduction:.1f}%")
    print()

    if reduction >= 30:
        print(f"✅ Target achieved (30-50% reduction)")
    else:
        print(f"⚠️  Below target (need {30 - reduction:.1f}% more reduction)")

    return reduction


if __name__ == "__main__":
    measure_improvement()
