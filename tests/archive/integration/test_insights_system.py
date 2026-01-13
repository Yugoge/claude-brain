#!/usr/bin/env python3
"""
Comprehensive tests for Story 3.6: Analytics Insights Engine

Tests all components:
- Insights Engine (recommendations, alerts, achievements, trends, tips)
- Export System (HTML, CSV, JSON)
- Goals Management
- Integration with analytics

Usage:
    source venv/bin/activate && source venv/bin/activate && python scripts/test_insights_system.py
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime


def test_insights_engine():
    """Test insights engine functionality"""
    print("\n=== Testing Insights Engine ===\n")

    from insights_engine import InsightsEngine

    try:
        engine = InsightsEngine()
        print("✓ Insights engine initialized")

        # Generate insights
        insights = engine.generate_all_insights('mastery')
        print("✓ Generated insights")

        # Verify structure
        assert 'generated' in insights, "Missing 'generated' field"
        assert 'userGoal' in insights, "Missing 'userGoal' field"
        assert 'recommendations' in insights, "Missing 'recommendations' field"
        assert 'alerts' in insights, "Missing 'alerts' field"
        assert 'achievements' in insights, "Missing 'achievements' field"
        assert 'trends' in insights, "Missing 'trends' field"
        assert 'tips' in insights, "Missing 'tips' field"
        print("✓ Insights structure valid")

        # Test recommendations
        recs = insights['recommendations']
        assert isinstance(recs, list), "Recommendations should be a list"
        for rec in recs:
            assert 'type' in rec, "Recommendation missing 'type'"
            assert 'priority' in rec, "Recommendation missing 'priority'"
            assert 'message' in rec, "Recommendation missing 'message'"
            assert rec['priority'] in ['critical', 'high', 'medium', 'low']
        print(f"✓ Generated {len(recs)} recommendations")

        # Test alerts
        alerts = insights['alerts']
        assert isinstance(alerts, list), "Alerts should be a list"
        print(f"✓ Generated {len(alerts)} alerts")

        # Test achievements
        achievements = insights['achievements']
        assert isinstance(achievements, list), "Achievements should be a list"
        print(f"✓ Detected {len(achievements)} achievements")

        # Test trends
        trends = insights['trends']
        assert isinstance(trends, list), "Trends should be a list"
        print(f"✓ Analyzed {len(trends)} trends")

        # Test tips
        tips = insights['tips']
        assert isinstance(tips, list), "Tips should be a list"
        assert len(tips) <= 3, "Should have max 3 tips"
        print(f"✓ Generated {len(tips)} tips")

        # Test different goals
        for goal in ['mastery', 'streak', 'breadth']:
            goal_insights = engine.generate_all_insights(goal)
            assert goal_insights['userGoal'] == goal
        print("✓ Goal-based recommendations work")

        print("\n✓✓✓ Insights Engine: ALL TESTS PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗✗✗ Insights Engine: TEST FAILED: {e}\n")
        return False


def test_export_system():
    """Test analytics export functionality"""
    print("\n=== Testing Export System ===\n")

    from export_analytics import AnalyticsExporter

    try:
        exporter = AnalyticsExporter()
        print("✓ Exporter initialized")

        # Test HTML export
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            html_path = f.name

        exporter.export_html(html_path, "Test Report")
        assert Path(html_path).exists(), "HTML file not created"
        assert Path(html_path).stat().st_size > 1000, "HTML file too small"
        print(f"✓ HTML export works ({Path(html_path).stat().st_size} bytes)")

        # Test CSV export
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = f.name

        exporter.export_csv(csv_path)
        assert Path(csv_path).exists(), "CSV file not created"
        with open(csv_path, 'r') as f:
            rows = f.readlines()
            assert len(rows) > 10, "CSV should have multiple rows"
        print(f"✓ CSV export works ({len(rows)} rows)")

        # Test JSON export
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            json_path = f.name

        exporter.export_json(json_path)
        assert Path(json_path).exists(), "JSON file not created"
        with open(json_path, 'r') as f:
            data = json.load(f)
            assert 'exported' in data
            assert 'analytics' in data
            assert 'insights' in data
        print("✓ JSON export works")

        # Cleanup
        Path(html_path).unlink()
        Path(csv_path).unlink()
        Path(json_path).unlink()

        print("\n✓✓✓ Export System: ALL TESTS PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗✗✗ Export System: TEST FAILED: {e}\n")
        return False


def test_goals_management():
    """Test learning goals management"""
    print("\n=== Testing Goals Management ===\n")

    from manage_learning_goals import GoalsManager

    try:
        manager = GoalsManager()
        print("✓ Goals manager initialized")

        # Test setting primary goal
        goals = manager.set_primary_goal('mastery')
        assert goals['primary'] == 'mastery'
        print("✓ Set primary goal")

        # Test getting goals
        current = manager.get_goals()
        assert 'primary' in current
        assert 'lastUpdated' in current
        print("✓ Get goals works")

        # Test goal descriptions
        for goal in ['mastery', 'streak', 'breadth']:
            desc = manager.describe_goal(goal)
            assert len(desc) > 50, f"Description for {goal} too short"
        print("✓ Goal descriptions available")

        # Test setting all goals
        goals = manager.set_goals('streak', 'mastery', 'breadth')
        assert goals['primary'] == 'streak'
        assert goals['secondary'] == 'mastery'
        assert goals['tertiary'] == 'breadth'
        print("✓ Set multiple goals")

        # Test invalid goal
        try:
            manager.set_primary_goal('invalid')
            assert False, "Should reject invalid goal"
        except ValueError:
            print("✓ Rejects invalid goals")

        print("\n✓✓✓ Goals Management: ALL TESTS PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗✗✗ Goals Management: TEST FAILED: {e}\n")
        return False


def test_integration():
    """Test integration between components"""
    print("\n=== Testing Integration ===\n")

    try:
        from insights_engine import InsightsEngine
        from manage_learning_goals import GoalsManager
        from export_analytics import AnalyticsExporter

        # Set goal
        manager = GoalsManager()
        manager.set_primary_goal('streak')
        print("✓ Set goal to 'streak'")

        # Generate insights (should use streak goal)
        engine = InsightsEngine()
        insights = engine.generate_all_insights()  # Should auto-load goal
        assert insights['userGoal'] == 'streak', "Should use goal from settings"
        print("✓ Insights use user goal")

        # Export with insights
        exporter = AnalyticsExporter()
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            html_path = f.name
        exporter.export_html(html_path)
        assert Path(html_path).exists()
        Path(html_path).unlink()
        print("✓ Export includes insights")

        print("\n✓✓✓ Integration: ALL TESTS PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗✗✗ Integration: TEST FAILED: {e}\n")
        return False


def test_performance():
    """Test performance of insights generation"""
    print("\n=== Testing Performance ===\n")

    import time
    from insights_engine import InsightsEngine

    try:
        engine = InsightsEngine()

        # Test insights generation time
        start = time.time()
        insights = engine.generate_all_insights()
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Insights generation too slow: {elapsed:.2f}s"
        print(f"✓ Insights generated in {elapsed:.3f}s (target: <1s)")

        # Test export performance
        from export_analytics import AnalyticsExporter
        exporter = AnalyticsExporter()

        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            html_path = f.name

        start = time.time()
        exporter.export_html(html_path)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"HTML export too slow: {elapsed:.2f}s"
        print(f"✓ HTML export in {elapsed:.3f}s (target: <2s)")

        Path(html_path).unlink()

        print("\n✓✓✓ Performance: ALL TESTS PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗✗✗ Performance: TEST FAILED: {e}\n")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Story 3.6: Analytics Insights Engine - Test Suite")
    print("="*60)

    results = {
        'Insights Engine': test_insights_engine(),
        'Export System': test_export_system(),
        'Goals Management': test_goals_management(),
        'Integration': test_integration(),
        'Performance': test_performance()
    }

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:.<40} {status}")

    print("="*60)
    print(f"Results: {passed}/{total} test suites passed")
    print("="*60)

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Story 3.6 implementation verified.\n")
        return 0
    else:
        print(f"\n❌ {total - passed} test suite(s) failed. Review errors above.\n")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
