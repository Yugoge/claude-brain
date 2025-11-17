#!/usr/bin/env python3
"""
Unit tests for Learning Analytics Engine

Tests all 7 key metrics:
1. Retention curves
2. Learning velocity
3. Mastery heatmap
4. Review adherence
5. Streak tracking
6. Time investment
7. Mastery predictions
"""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Add scripts to path - must be absolute path
import os
import importlib.util

scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'analytics'))

# Import module with hyphen in filename
spec = importlib.util.spec_from_file_location(
    "generate_analytics",
    os.path.join(scripts_path, "generate-analytics.py")
)
generate_analytics = importlib.util.module_from_spec(spec)
sys.modules["generate_analytics"] = generate_analytics
spec.loader.exec_module(generate_analytics)

# Now import the class
AnalyticsEngine = generate_analytics.AnalyticsEngine


class TestAnalyticsEngine(unittest.TestCase):
    """Test suite for AnalyticsEngine"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir)

        # Create test data directories
        (self.base_path / '.review').mkdir(parents=True)
        (self.base_path / 'knowledge-base' / '_index').mkdir(parents=True)
        (self.base_path / 'chats').mkdir(parents=True)

        # Sample test data
        self.sample_schedule = {
            "version": "1.0.0",
            "algorithm": "SM-2",
            "concepts": {
                "concepts/finance/portfolio-theory.md": {
                    "easinessFactor": 2.8,
                    "repetitions": 5,
                    "interval": 10,
                    "lastReview": (datetime.now() - timedelta(days=3)).isoformat(),
                    "nextReview": (datetime.now() + timedelta(days=7)).isoformat()
                },
                "concepts/programming/python-gil.md": {
                    "easinessFactor": 2.3,
                    "repetitions": 2,
                    "interval": 3,
                    "lastReview": (datetime.now() - timedelta(days=1)).isoformat(),
                    "nextReview": (datetime.now() + timedelta(days=2)).isoformat()
                }
            }
        }

        self.sample_history = {
            "version": "1.0.0",
            "sessions": [
                {
                    "timestamp": (datetime.now() - timedelta(days=5)).isoformat(),
                    "domain": "finance",
                    "duration": 3600  # 1 hour in seconds
                },
                {
                    "timestamp": (datetime.now() - timedelta(days=3)).isoformat(),
                    "domain": "programming",
                    "duration": 7200  # 2 hours
                }
            ]
        }

        self.sample_chats = {
            "version": "1.0.0",
            "conversations": {
                "finance-conv-1": {
                    "title": "Finance Concepts",
                    "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                    "domain": "finance",
                    "turns": 10  # 5 hours estimated
                }
            }
        }

        # Write test data to temp files
        self._write_json('.review/schedule.json', self.sample_schedule)
        self._write_json('.review/history.json', self.sample_history)
        self._write_json('chats/index.json', self.sample_chats)
        self._write_json('.review/adaptive-profile.json', {})
        self._write_json('knowledge-base/_index/backlinks.json', {})

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def _write_json(self, path: str, data: dict):
        """Helper to write JSON test data"""
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w') as f:
            json.dump(data, f)

    def test_initialization(self):
        """Test AnalyticsEngine initialization"""
        engine = AnalyticsEngine(self.base_path)

        self.assertIsNotNone(engine.schedule)
        self.assertIsNotNone(engine.history)
        self.assertIsNotNone(engine.chats)

    def test_retention_curve_calculation(self):
        """Test Ebbinghaus retention curve formula"""
        engine = AnalyticsEngine(self.base_path)
        retention = engine.calculate_retention_curves()

        # Check that retention data is generated
        self.assertIn("concepts/finance/portfolio-theory.md", retention)

        concept_retention = retention["concepts/finance/portfolio-theory.md"]

        # Check structure
        self.assertIn('curve', concept_retention)
        self.assertIn('currentRetention', concept_retention)
        self.assertIn('strength', concept_retention)

        # Check curve has 31 days (0-30)
        self.assertEqual(len(concept_retention['curve']), 31)

        # Check retention is between 0-100
        for point in concept_retention['curve']:
            self.assertGreaterEqual(point['retention'], 0)
            self.assertLessEqual(point['retention'], 100)

    def test_retention_curve_decay(self):
        """Test that retention decreases over time"""
        engine = AnalyticsEngine(self.base_path)
        retention = engine.calculate_retention_curves()

        concept_retention = retention["concepts/finance/portfolio-theory.md"]
        curve = concept_retention['curve']

        # Retention should generally decrease over time
        # (may have small increases due to rounding, but trend should be down)
        first_retention = curve[0]['retention']
        last_retention = curve[-1]['retention']

        self.assertLess(last_retention, first_retention,
                       "Retention should decay over time")

    def test_learning_velocity_calculation(self):
        """Test learning velocity metric"""
        engine = AnalyticsEngine(self.base_path)
        velocity_data = engine.calculate_learning_velocity(period_days=30)

        # Check structure
        self.assertIn('velocity', velocity_data)
        self.assertIn('conceptsMastered', velocity_data)
        self.assertIn('hoursInvested', velocity_data)
        self.assertIn('trend', velocity_data)
        self.assertIn('benchmark', velocity_data)

        # Check velocity is non-negative
        self.assertGreaterEqual(velocity_data['velocity'], 0)

        # Check benchmark is valid
        self.assertIn(velocity_data['benchmark'], ['slow', 'medium', 'fast'])

    def test_velocity_classification(self):
        """Test velocity benchmark classification"""
        engine = AnalyticsEngine(self.base_path)

        self.assertEqual(engine._classify_velocity(0.3), 'slow')
        self.assertEqual(engine._classify_velocity(0.8), 'medium')
        self.assertEqual(engine._classify_velocity(2.0), 'fast')

    def test_mastery_heatmap_generation(self):
        """Test mastery score calculation"""
        engine = AnalyticsEngine(self.base_path)
        mastery = engine.generate_mastery_heatmap()

        # Check structure
        self.assertIn('concepts', mastery)
        self.assertIn('domainAverages', mastery)
        self.assertIn('totalConcepts', mastery)

        # Check concepts have mastery scores
        for concept_id, data in mastery['concepts'].items():
            self.assertIn('score', data)
            self.assertIn('level', data)
            self.assertIn('easinessFactor', data)
            self.assertIn('repetitions', data)

            # Check score is 0-100
            self.assertGreaterEqual(data['score'], 0)
            self.assertLessEqual(data['score'], 100)

            # Check level is valid
            self.assertIn(data['level'], ['novice', 'learning', 'competent', 'expert'])

    def test_mastery_level_classification(self):
        """Test mastery level boundaries"""
        engine = AnalyticsEngine(self.base_path)

        # Manually create concepts with specific EF and reps
        # Mastery = min(((EF-1.3)/1.2)*50 + min(reps*10, 50), 100)
        test_schedule = {
            "version": "1.0.0",
            "concepts": {
                "novice": {"easinessFactor": 1.3, "repetitions": 0},      # 0 + 0 = 0
                "learning": {"easinessFactor": 1.5, "repetitions": 2},    # 8.3 + 20 = 28.3
                "competent": {"easinessFactor": 2.0, "repetitions": 3},   # 29.2 + 30 = 59.2
                "expert": {"easinessFactor": 2.5, "repetitions": 5}       # 50 + 50 = 100
            }
        }

        self._write_json('.review/schedule.json', test_schedule)
        engine = AnalyticsEngine(self.base_path)
        mastery = engine.generate_mastery_heatmap()

        # Check classifications
        self.assertEqual(mastery['concepts']['novice']['level'], 'novice')
        self.assertEqual(mastery['concepts']['learning']['level'], 'learning')
        self.assertEqual(mastery['concepts']['competent']['level'], 'competent')
        self.assertEqual(mastery['concepts']['expert']['level'], 'expert')

    def test_review_adherence_calculation(self):
        """Test review adherence metric"""
        engine = AnalyticsEngine(self.base_path)
        adherence = engine.calculate_review_adherence(period_days=30)

        # Check structure
        self.assertIn('adherence', adherence)
        self.assertIn('onTimeReviews', adherence)
        self.assertIn('lateReviews', adherence)
        self.assertIn('totalDue', adherence)
        self.assertIn('classification', adherence)

        # Check adherence is 0-100
        self.assertGreaterEqual(adherence['adherence'], 0)
        self.assertLessEqual(adherence['adherence'], 100)

        # Check classification is valid
        self.assertIn(adherence['classification'], ['excellent', 'good', 'poor'])

    def test_streak_calculation(self):
        """Test streak tracking"""
        engine = AnalyticsEngine(self.base_path)
        streak = engine.calculate_streak()

        # Check structure
        self.assertIn('currentStreak', streak)
        self.assertIn('longestStreak', streak)
        self.assertIn('lastActivity', streak)
        self.assertIn('totalActiveDays', streak)

        # Check streaks are non-negative
        self.assertGreaterEqual(streak['currentStreak'], 0)
        self.assertGreaterEqual(streak['longestStreak'], 0)

        # Longest should be >= current
        self.assertGreaterEqual(streak['longestStreak'], streak['currentStreak'])

    def test_time_investment_analysis(self):
        """Test time investment calculation"""
        engine = AnalyticsEngine(self.base_path)
        time_inv = engine.analyze_time_investment()

        # Check structure
        self.assertIn('byDomain', time_inv)
        self.assertIn('totalHours', time_inv)
        self.assertIn('averageSessionDuration', time_inv)
        self.assertIn('distribution', time_inv)

        # Check totals are positive
        self.assertGreater(time_inv['totalHours'], 0)

        # Check distribution sums to 100%
        total_dist = sum(time_inv['distribution'].values())
        self.assertAlmostEqual(total_dist, 100.0, places=1)

    def test_time_investment_domain_filtering(self):
        """Test domain filtering for time investment"""
        engine = AnalyticsEngine(self.base_path)

        # All domains
        all_time = engine.analyze_time_investment()

        # Finance only
        finance_time = engine.analyze_time_investment(domain='finance')

        # Finance time should be less than total
        self.assertLess(finance_time['totalHours'], all_time['totalHours'])

        # Finance domain should be the only one in byDomain
        self.assertEqual(len(finance_time['byDomain']), 1)
        self.assertIn('finance', finance_time['byDomain'])

    def test_mastery_prediction(self):
        """Test mastery timeline predictions"""
        engine = AnalyticsEngine(self.base_path)
        predictions = engine.predict_mastery_timeline(target_mastery=80.0)

        # Should have predictions for concepts
        self.assertIsInstance(predictions, dict)

        # Check predictions have correct structure
        for concept_id, prediction in predictions.items():
            if 'error' in prediction:
                continue

            self.assertIn('status', prediction)

            if prediction['status'] == 'achieved':
                self.assertIn('achievedDate', prediction)
            elif prediction['status'] == 'in_progress':
                self.assertIn('currentMastery', prediction)
                self.assertIn('targetMastery', prediction)
                self.assertIn('hoursNeeded', prediction)
                self.assertIn('predictedDate', prediction)

    def test_full_report_generation(self):
        """Test complete analytics report generation"""
        engine = AnalyticsEngine(self.base_path)
        report = engine.generate_full_report(period_days=30)

        # Check all required sections exist
        required_keys = [
            'generated',
            'period',
            'domain',
            'retention',
            'velocity',
            'mastery',
            'adherence',
            'streak',
            'timeInvestment',
            'predictions'
        ]

        for key in required_keys:
            self.assertIn(key, report, f"Missing key: {key}")

    def test_empty_data_handling(self):
        """Test handling of empty data sources"""
        # Create engine with empty data
        empty_schedule = {"version": "1.0.0", "concepts": {}}
        empty_history = {"version": "1.0.0", "sessions": []}
        empty_chats = {"version": "1.0.0", "conversations": {}}

        self._write_json('.review/schedule.json', empty_schedule)
        self._write_json('.review/history.json', empty_history)
        self._write_json('chats/index.json', empty_chats)

        engine = AnalyticsEngine(self.base_path)

        # Should not crash, should return empty/default values
        retention = engine.calculate_retention_curves()
        self.assertIn('error', retention)

        velocity = engine.calculate_learning_velocity()
        self.assertEqual(velocity['velocity'], 0.0)

        mastery = engine.generate_mastery_heatmap()
        self.assertEqual(mastery['totalConcepts'], 0)

        streak = engine.calculate_streak()
        self.assertEqual(streak['currentStreak'], 0)

    def test_domain_filtering(self):
        """Test domain filtering across all metrics"""
        engine = AnalyticsEngine(self.base_path)

        # Test retention filtering
        finance_retention = engine.calculate_retention_curves(domain='finance')
        self.assertIn('concepts/finance/portfolio-theory.md', finance_retention)
        self.assertNotIn('concepts/programming/python-gil.md', finance_retention)

        # Test velocity filtering
        finance_velocity = engine.calculate_learning_velocity(domain='finance')
        all_velocity = engine.calculate_learning_velocity()

        # Finance-specific velocity should differ from all
        self.assertIsNotNone(finance_velocity)

        # Test mastery filtering
        finance_mastery = engine.generate_mastery_heatmap(domain='finance')
        self.assertIn('concepts/finance/portfolio-theory.md', finance_mastery['concepts'])
        self.assertNotIn('concepts/programming/python-gil.md', finance_mastery['concepts'])


class TestAnalyticsCLI(unittest.TestCase):
    """Test CLI functionality"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_cli_help(self):
        """Test CLI help output"""
        import subprocess

        result = subprocess.run(
            ['python3', 'scripts/generate-analytics.py', '--help'],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn('Generate learning analytics', result.stdout)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
