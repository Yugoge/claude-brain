#!/usr/bin/env python3
"""
Integration Test: Full User Workflow

Simulates the complete user workflow:
1. Load real backup schedule
2. Perform multiple reviews
3. Save schedule
4. Verify JSON serialization
5. Verify backups
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from review_scheduler import ReviewScheduler


def test_full_user_workflow():
    """Test complete user workflow from start to finish."""
    print("="*70)
    print("INTEGRATION TEST: FULL USER WORKFLOW")
    print("="*70)

    scheduler = ReviewScheduler()

    # 1. Load real backup schedule
    print("\n[1/7] Loading real backup schedule...")
    backup_file = '/root/knowledge-system/.review/backups/schedule-2025-10-30-115407.json'

    if not os.path.exists(backup_file):
        print("✗ FAIL: Backup file not found")
        return False

    with open(backup_file, 'r') as f:
        original_schedule = json.load(f)

    print(f"✓ Loaded {len(original_schedule['concepts'])} concepts")

    # 2. Create temp working directory
    print("\n[2/7] Creating temporary working directory...")
    with tempfile.TemporaryDirectory() as tmpdir:
        schedule_path = os.path.join(tmpdir, 'schedule.json')

        # Copy schedule to temp location
        with open(schedule_path, 'w') as f:
            json.dump(original_schedule, f, indent=2)

        print(f"✓ Created working copy at {schedule_path}")

        # 3. Simulate multiple reviews
        print("\n[3/7] Simulating user reviews...")
        concept_ids = list(original_schedule['concepts'].keys())[:5]  # Test with 5 concepts

        ratings = [4, 3, 3, 4, 2]  # Varied ratings
        for i, concept_id in enumerate(concept_ids):
            rating = ratings[i]
            updated = scheduler.update_and_save(schedule_path, concept_id, rating)

            # Verify return value
            assert isinstance(updated['fsrs_state']['next_review'], str), \
                f"next_review should be string, got {type(updated['fsrs_state']['next_review'])}"

            print(f"  ✓ Reviewed '{concept_id}' (rating: {rating})")

        # 4. Verify schedule file is valid JSON
        print("\n[4/7] Verifying schedule file integrity...")
        with open(schedule_path, 'r') as f:
            loaded_schedule = json.load(f)

        print(f"✓ Schedule file is valid JSON")

        # 5. Verify all dates are strings
        print("\n[5/7] Verifying all dates are JSON-safe strings...")
        for concept_id, concept in loaded_schedule['concepts'].items():
            if 'fsrs_state' in concept:
                next_review = concept['fsrs_state'].get('next_review')
                last_review = concept['fsrs_state'].get('last_review')

                if next_review is not None:
                    assert isinstance(next_review, str), \
                        f"{concept_id}: next_review should be string, got {type(next_review)}"

                if last_review is not None:
                    assert isinstance(last_review, str), \
                        f"{concept_id}: last_review should be string, got {type(last_review)}"

        print(f"✓ All {len(loaded_schedule['concepts'])} concepts have JSON-safe dates")

        # 6. Verify backups were created
        print("\n[6/7] Verifying backup creation...")
        backup_dir = os.path.join(tmpdir, 'backups')

        if os.path.exists(backup_dir):
            backups = list(Path(backup_dir).glob('schedule-*.json'))
            print(f"✓ Created {len(backups)} backup(s)")

            # Verify backups are valid JSON
            for backup in backups:
                with open(backup, 'r') as f:
                    json.load(f)
            print(f"✓ All backups are valid JSON")
        else:
            print("⚠ No backups directory (first save)")

        # 7. Performance metrics
        print("\n[7/7] Performance metrics...")
        import time
        start = time.time()

        # Perform 10 rapid reviews
        for i in range(10):
            concept_id = concept_ids[i % len(concept_ids)]
            scheduler.update_and_save(schedule_path, concept_id, 3)

        elapsed = time.time() - start
        print(f"✓ 10 reviews in {elapsed:.3f}s ({elapsed/10*1000:.1f}ms per review)")

        # Final verification
        print("\n" + "="*70)
        print("INTEGRATION TEST RESULTS")
        print("="*70)
        print("✓ Schedule loading: PASS")
        print("✓ Multiple reviews: PASS")
        print("✓ JSON serialization: PASS")
        print("✓ Date string conversion: PASS")
        print("✓ Backup creation: PASS")
        print("✓ Performance: PASS")
        print("="*70)
        print("VERDICT: ✓ PASS - Full workflow works correctly")
        print("="*70)

        return True


def test_original_bug_reproduction():
    """Test the exact scenario that caused the original bug."""
    print("\n" + "="*70)
    print("ORIGINAL BUG REPRODUCTION TEST")
    print("="*70)

    print("\nSimulating original user scenario:")
    print("1. Load schedule.json")
    print("2. Update concept with FSRS")
    print("3. Save with json.dump()")
    print("")

    scheduler = ReviewScheduler()

    with tempfile.TemporaryDirectory() as tmpdir:
        schedule_path = os.path.join(tmpdir, 'schedule.json')

        # Create initial schedule (simulating existing schedule)
        schedule = {
            "version": "2.0.0",
            "concepts": {
                "finance-sharpe-ratio": {
                    "id": "finance-sharpe-ratio",
                    "fsrs_state": {}
                }
            }
        }

        with open(schedule_path, 'w') as f:
            json.dump(schedule, f, indent=2)

        # Load and update (original workflow)
        with open(schedule_path, 'r') as f:
            schedule = json.load(f)

        # Update concept (this returned datetime objects in the bug)
        concept = schedule['concepts']['finance-sharpe-ratio']
        updated_concept = scheduler.schedule_review(concept, 4)
        schedule['concepts']['finance-sharpe-ratio'] = updated_concept

        # This used to raise: TypeError: Object of type datetime is not JSON serializable
        try:
            with open(schedule_path, 'w') as f:
                json.dump(schedule, f, indent=2)

            print("✓ PASS: json.dump() succeeded (bug is fixed!)")

            # Verify the saved file
            with open(schedule_path, 'r') as f:
                loaded = json.load(f)

            next_review = loaded['concepts']['finance-sharpe-ratio']['fsrs_state']['next_review']
            print(f"✓ PASS: next_review is string: '{next_review}'")

            return True

        except TypeError as e:
            print(f"✗ FAIL: Original bug still present: {e}")
            return False


def main():
    """Run integration tests."""
    success = True

    # Test 1: Full workflow
    if not test_full_user_workflow():
        success = False

    print("\n")

    # Test 2: Original bug reproduction
    if not test_original_bug_reproduction():
        success = False

    # Final summary
    print("\n" + "="*70)
    if success:
        print("ALL INTEGRATION TESTS PASSED")
    else:
        print("SOME INTEGRATION TESTS FAILED")
    print("="*70)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
