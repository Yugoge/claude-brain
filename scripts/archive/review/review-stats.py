#!/usr/bin/env python3
"""
Review statistics CLI command implementation.

Displays performance metrics, comparisons, and exports data.
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'analytics'))
from performance_tracker import PerformanceTracker
from generate_dashboard import generate_comparison_dashboard, generate_detailed_report


def main():
    parser = argparse.ArgumentParser(
        description="View review performance statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Overall stats
  %(prog)s --algorithm fsrs   # FSRS-specific stats
  %(prog)s --period 30        # Last 30 days
  %(prog)s --export csv       # Export to CSV
  %(prog)s --detailed         # Detailed breakdown
        """
    )

    parser.add_argument(
        "--algorithm",
        choices=["sm2", "fsrs"],
        help="Show stats for specific algorithm"
    )
    parser.add_argument(
        "--period",
        type=int,
        help="Time period in days (default: all time)"
    )
    parser.add_argument(
        "--export",
        choices=["csv", "json"],
        help="Export data to file"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed concept-level breakdown"
    )
    parser.add_argument(
        "--history",
        default=".review/history.json",
        help="Path to history file (default: .review/history.json)"
    )

    args = parser.parse_args()

    tracker = PerformanceTracker(args.history)

    # Export functionality
    if args.export:
        output_file = f".review/performance-export.{args.export}"
        if args.export == "csv":
            tracker.export_to_csv(output_file)
            print(f"✅ Exported to {output_file}")
        elif args.export == "json":
            tracker.export_to_json(output_file)
            print(f"✅ Exported to {output_file}")
        return

    # Show detailed report
    if args.detailed:
        print(generate_detailed_report(args.history))
        return

    # Algorithm-specific stats
    if args.algorithm:
        print(f"\n📊 {args.algorithm.upper()} Statistics")
        print("="*60)

        retention = tracker.calculate_retention_rate(args.algorithm)
        burden = tracker.calculate_review_burden(args.algorithm, period_days=args.period or 7)
        efficiency = tracker.calculate_efficiency(args.algorithm)

        print(f"\nRetention Rate: {retention*100:.1f}%")
        print(f"Review Burden:  {burden['reviews_per_period']:.0f} reviews/week ({burden['hours_per_period']:.1f} hours)")
        print(f"Efficiency:     {efficiency:.2f}")
        print(f"Concepts:       {burden['concepts_per_period']:.0f} unique concepts")

        # Concept breakdown
        concepts = tracker.retention_by_concept(args.algorithm)
        if concepts:
            print(f"\nRetention by Concept:")
            print("-"*60)
            for concept, ret in sorted(concepts.items(), key=lambda x: x[1], reverse=True):
                bar = '█' * int(ret * 30)
                print(f"  {concept:<30} {ret*100:>6.1f}% {bar}")
        return

    # Default: comparison dashboard
    print(generate_comparison_dashboard(args.history))


if __name__ == "__main__":
    main()
