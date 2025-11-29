#!/usr/bin/env python3
"""
Learning Analytics Aggregation System

Calculates 7 key metrics from review and learning data:
1. Retention curves (Ebbinghaus forgetting curve)
2. Learning velocity (concepts/hour)
3. Mastery heatmap (0-100% scores)
4. Review adherence (on-time %)
5. Predicted mastery (timeline forecasts)
6. Streak tracking (consecutive days)
7. Time investment (hours/domain)

Data Sources:
- .review/schedule.json: SM-2 review schedule
- .review/history.json: Review session history
- .review/adaptive-profile.json: Adaptive difficulty telemetry
- knowledge-base/_index/backlinks.json: Concept relationships
- chats/index.json: Conversation metadata

Output:
- .review/analytics-cache.json: Aggregated analytics data
"""

import json
import math
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


class AnalyticsEngine:
    """Aggregates learning analytics from multiple data sources"""

    def __init__(self, base_path: Path = None):
        """
        Initialize analytics engine

        Args:
            base_path: Base directory path (defaults to current directory)
        """
        self.base_path = base_path or Path.cwd()

        # Load all data sources
        self.schedule = self.load_json('.review/schedule.json')
        self.history = self.load_json('.review/history.json')
        self.adaptive = self.load_json('.review/adaptive-profile.json')
        self.backlinks = self.load_json('knowledge-base/_index/backlinks.json')
        self.chats = self.load_json('chats/index.json')

    def load_json(self, path: str) -> Dict:
        """
        Load JSON file or return empty dict

        Args:
            path: Relative path from base_path

        Returns:
            Parsed JSON data or empty dict
        """
        try:
            full_path = self.base_path / path
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {path} not found, using empty data", file=sys.stderr)
            return {}
        except json.JSONDecodeError as e:
            print(f"Warning: {path} has invalid JSON: {e}", file=sys.stderr)
            return {}

    def calculate_retention_curves(self, domain: Optional[str] = None) -> Dict:
        """
        Calculate Ebbinghaus retention curves per concept

        Formula: R(t) = e^(-t/S) where S = strength (based on EF and reps)

        Args:
            domain: Filter by domain (optional)

        Returns:
            Dict mapping concept IDs to retention curve data
        """
        retention_data = {}

        concepts = self.schedule.get('concepts', {})

        if not concepts:
            return {
                'error': 'No review data available. Complete some learning sessions first.',
                'concepts': {}
            }

        for concept_id, data in concepts.items():
            # Filter by domain if specified
            if domain and not concept_id.startswith(f"concepts/{domain}/"):
                continue

            # Extract SM-2 parameters
            ef = data.get('easinessFactor', 2.5)
            repetitions = data.get('repetitions', 0)
            interval = data.get('interval', 1)
            last_review_str = data.get('lastReview')

            # Handle missing lastReview
            if not last_review_str:
                last_review = datetime.now() - timedelta(days=1)
            else:
                try:
                    last_review = datetime.fromisoformat(last_review_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    last_review = datetime.now() - timedelta(days=1)

            # Calculate retention strength (higher EF and reps = stronger memory)
            strength = ef * (1 + repetitions * 0.2)

            # Generate retention curve for next 30 days
            days_since_review = (datetime.now() - last_review).days
            retention_curve = []

            for day in range(31):
                total_days = days_since_review + day
                # Ebbinghaus formula: R(t) = e^(-t/S)
                retention = math.exp(-total_days / strength)
                retention_curve.append({
                    'day': day,
                    'retention': min(100, retention * 100),  # Convert to percentage
                    'date': (datetime.now() + timedelta(days=day)).isoformat()
                })

            retention_data[concept_id] = {
                'curve': retention_curve,
                'currentRetention': retention_curve[0]['retention'],
                'nextReviewDue': data.get('nextReview'),
                'strength': strength
            }

        return retention_data

    def calculate_learning_velocity(
        self,
        period_days: int = 30,
        domain: Optional[str] = None
    ) -> Dict:
        """
        Calculate learning velocity (concepts mastered per hour)

        A concept is "mastered" if: EF > 2.5 OR repetitions >= 5

        Args:
            period_days: Number of days to analyze (default 30)
            domain: Filter by domain (optional)

        Returns:
            Dict with velocity, trend, and predictions
        """
        cutoff_date = datetime.now() - timedelta(days=period_days)

        concepts = self.schedule.get('concepts', {})

        # Get mastered concepts (EF > 2.5 or 5+ reps)
        mastered_concepts = []
        for concept_id, data in concepts.items():
            if domain and not concept_id.startswith(f"concepts/{domain}/"):
                continue

            ef = data.get('easinessFactor', 2.5)
            reps = data.get('repetitions', 0)
            last_review_str = data.get('lastReview')

            if not last_review_str:
                continue

            try:
                last_review = datetime.fromisoformat(last_review_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue

            if (ef > 2.5 or reps >= 5) and last_review > cutoff_date:
                mastered_concepts.append(concept_id)

        # Calculate total time invested from history and chats
        total_hours = self._calculate_total_hours(cutoff_date, domain)

        # Calculate velocity
        velocity = len(mastered_concepts) / total_hours if total_hours > 0 else 0

        # Calculate trend (compare to previous period)
        previous_period_velocity = self._calculate_velocity_for_period(
            cutoff_date - timedelta(days=period_days),
            cutoff_date,
            domain
        )

        trend = ((velocity - previous_period_velocity) / previous_period_velocity * 100
                if previous_period_velocity > 0 else 0)

        return {
            'velocity': round(velocity, 2),
            'conceptsMastered': len(mastered_concepts),
            'hoursInvested': round(total_hours, 1),
            'trend': round(trend, 1),
            'benchmark': self._classify_velocity(velocity)
        }

    def _calculate_total_hours(
        self,
        cutoff_date: datetime,
        domain: Optional[str] = None
    ) -> float:
        """
        Calculate total hours from history sessions and chat conversations

        Args:
            cutoff_date: Only count sessions after this date
            domain: Filter by domain (optional)

        Returns:
            Total hours invested
        """
        total_hours = 0.0

        # From .review/history.json
        for session in self.history.get('sessions', []):
            try:
                session_date = datetime.fromisoformat(
                    session.get('timestamp', '').replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                continue

            if session_date > cutoff_date:
                if domain and session.get('domain') != domain:
                    continue
                total_hours += session.get('duration', 0) / 3600  # Convert seconds to hours

        # From chats/index.json (estimate 30 min per conversation turn)
        conversations = self.chats.get('conversations', {})
        for conv_id, conv_data in conversations.items():
            try:
                conv_date = datetime.fromisoformat(conv_data.get('date', '') + 'T00:00:00')
            except (ValueError, AttributeError):
                continue

            if conv_date > cutoff_date:
                conv_domain = conv_data.get('domain', 'generic')
                if domain and conv_domain != domain:
                    continue

                # Estimate: 30 minutes per conversation (2 turns = 1 hour)
                turns = conv_data.get('turns', 0)
                total_hours += turns / 2.0

        return total_hours

    def _calculate_velocity_for_period(
        self,
        start_date: datetime,
        end_date: datetime,
        domain: Optional[str] = None
    ) -> float:
        """
        Helper to calculate velocity for specific period

        Args:
            start_date: Period start
            end_date: Period end
            domain: Filter by domain (optional)

        Returns:
            Velocity for the period
        """
        concepts = self.schedule.get('concepts', {})

        mastered = sum(
            1 for c, d in concepts.items()
            if (not domain or c.startswith(f"concepts/{domain}/")) and
            self._is_mastered_in_period(d, start_date, end_date)
        )

        # Calculate hours for this specific period
        hours = 0.0

        # From history
        for s in self.history.get('sessions', []):
            try:
                ts = datetime.fromisoformat(s.get('timestamp', '').replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue

            if start_date < ts <= end_date:
                if not domain or s.get('domain') == domain:
                    hours += s.get('duration', 0) / 3600

        # From chats
        for conv_id, conv_data in self.chats.get('conversations', {}).items():
            try:
                conv_date = datetime.fromisoformat(conv_data.get('date', '') + 'T00:00:00')
            except (ValueError, AttributeError):
                continue

            if start_date < conv_date <= end_date:
                if not domain or conv_data.get('domain') == domain:
                    hours += conv_data.get('turns', 0) / 2.0

        return mastered / hours if hours > 0 else 0

    def _is_mastered_in_period(
        self,
        concept_data: Dict,
        start_date: datetime,
        end_date: datetime
    ) -> bool:
        """Check if concept was mastered in the given period"""
        try:
            last_review = datetime.fromisoformat(
                concept_data.get('lastReview', '').replace('Z', '+00:00')
            )
        except (ValueError, AttributeError):
            return False

        if not (start_date < last_review <= end_date):
            return False

        ef = concept_data.get('easinessFactor', 2.5)
        reps = concept_data.get('repetitions', 0)

        return ef > 2.5 or reps >= 5

    def _classify_velocity(self, velocity: float) -> str:
        """Classify velocity as slow/medium/fast"""
        if velocity < 0.5:
            return "slow"
        elif velocity < 1.5:
            return "medium"
        else:
            return "fast"

    def generate_mastery_heatmap(self, domain: Optional[str] = None) -> Dict:
        """
        Generate mastery scores for all concepts

        Mastery Score Formula:
        - EF contributes 50%: (EF - 1.3) / 1.2 * 50
        - Repetitions contribute 50%: min(reps * 10, 50)

        Args:
            domain: Filter by domain (optional)

        Returns:
            Dict with mastery scores per concept and domain averages
        """
        mastery_scores = {}

        concepts = self.schedule.get('concepts', {})

        for concept_id, data in concepts.items():
            if domain and not concept_id.startswith(f"concepts/{domain}/"):
                continue

            # Calculate mastery score (0-100)
            ef = data.get('easinessFactor', 2.5)
            reps = data.get('repetitions', 0)

            # Formula: EF contributes 50%, repetitions contribute 50%
            ef_score = max(0, ((ef - 1.3) / 1.2) * 50)  # EF 1.3-2.5 maps to 0-50
            reps_score = min(reps * 10, 50)  # Each rep adds 10%, max 50
            mastery = min(ef_score + reps_score, 100)  # Cap at 100

            # Classify mastery level
            if mastery < 25:
                level = "novice"
            elif mastery < 50:
                level = "learning"
            elif mastery < 75:
                level = "competent"
            else:
                level = "expert"

            mastery_scores[concept_id] = {
                'score': round(mastery, 1),
                'level': level,
                'easinessFactor': ef,
                'repetitions': reps
            }

        # Calculate domain averages
        domain_averages = defaultdict(list)
        for concept_id, mastery_data in mastery_scores.items():
            concept_domain = concept_id.split('/')[1] if '/' in concept_id else 'generic'
            domain_averages[concept_domain].append(mastery_data['score'])

        domain_averages = {
            d: round(sum(scores) / len(scores), 1)
            for d, scores in domain_averages.items()
        }

        return {
            'concepts': mastery_scores,
            'domainAverages': domain_averages,
            'totalConcepts': len(mastery_scores)
        }

    def calculate_review_adherence(self, period_days: int = 30) -> Dict:
        """
        Calculate review adherence percentage

        Adherence = reviews completed on-time / total due reviews
        On-time = within 24 hours of due date

        Args:
            period_days: Analysis period in days

        Returns:
            Dict with adherence metrics
        """
        cutoff_date = datetime.now() - timedelta(days=period_days)

        on_time_reviews = 0
        late_reviews = 0
        total_due = 0

        concepts = self.schedule.get('concepts', {})

        for concept_id, data in concepts.items():
            next_review_str = data.get('nextReview')
            last_review_str = data.get('lastReview')

            if not next_review_str or not last_review_str:
                continue

            try:
                next_review = datetime.fromisoformat(next_review_str.replace('Z', '+00:00'))
                last_review = datetime.fromisoformat(last_review_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue

            # Check if review was due in period
            if cutoff_date < next_review < datetime.now():
                total_due += 1

                # Check if completed on time (within 24 hours)
                days_late = (last_review - next_review).days
                if days_late <= 1:
                    on_time_reviews += 1
                else:
                    late_reviews += 1

        adherence = (on_time_reviews / total_due * 100) if total_due > 0 else 100

        return {
            'adherence': round(adherence, 1),
            'onTimeReviews': on_time_reviews,
            'lateReviews': late_reviews,
            'totalDue': total_due,
            'classification': (
                'excellent' if adherence > 80 else
                'good' if adherence > 60 else
                'poor'
            )
        }

    def calculate_streak(self) -> Dict:
        """
        Calculate current and longest learning streaks

        A "learning day" is any day with at least 1 completed review or learning session

        Returns:
            Dict with current streak, longest streak, and activity stats
        """
        activity_dates = set()

        # From history sessions
        for session in self.history.get('sessions', []):
            try:
                date = datetime.fromisoformat(
                    session.get('timestamp', '').replace('Z', '+00:00')
                ).date()
                activity_dates.add(date)
            except (ValueError, AttributeError):
                continue

        # From chat conversations
        for conv_id, conv_data in self.chats.get('conversations', {}).items():
            try:
                date = datetime.fromisoformat(conv_data.get('date', '') + 'T00:00:00').date()
                activity_dates.add(date)
            except (ValueError, AttributeError):
                continue

        if not activity_dates:
            return {
                'currentStreak': 0,
                'longestStreak': 0,
                'lastActivity': None,
                'totalActiveDays': 0
            }

        # Sort dates
        sorted_dates = sorted(activity_dates)

        # Calculate current streak
        current_streak = 0
        today = datetime.now().date()
        check_date = today

        while check_date in activity_dates or check_date == today:
            if check_date in activity_dates:
                current_streak += 1
            check_date -= timedelta(days=1)
            if check_date < sorted_dates[0]:
                break

        # Calculate longest streak
        longest_streak = 1
        current_run = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                current_run += 1
                longest_streak = max(longest_streak, current_run)
            else:
                current_run = 1

        return {
            'currentStreak': current_streak,
            'longestStreak': max(longest_streak, current_streak),
            'lastActivity': sorted_dates[-1].isoformat(),
            'totalActiveDays': len(activity_dates)
        }

    def analyze_time_investment(self, domain: Optional[str] = None) -> Dict:
        """
        Analyze time invested per domain

        Args:
            domain: Filter by domain (optional)

        Returns:
            Dict with time breakdown by domain
        """
        time_by_domain = defaultdict(float)

        # From history sessions
        for session in self.history.get('sessions', []):
            session_domain = session.get('domain', 'generic')
            if domain and session_domain != domain:
                continue

            duration_hours = session.get('duration', 0) / 3600
            time_by_domain[session_domain] += duration_hours

        # From chat conversations (estimate 30 min per turn)
        for conv_id, conv_data in self.chats.get('conversations', {}).items():
            conv_domain = conv_data.get('domain', 'generic')
            if domain and conv_domain != domain:
                continue

            turns = conv_data.get('turns', 0)
            time_by_domain[conv_domain] += turns / 2.0

        total_time = sum(time_by_domain.values())

        # Calculate average session duration
        total_sessions = len(self.history.get('sessions', [])) + len(self.chats.get('conversations', {}))
        avg_duration = total_time / total_sessions if total_sessions > 0 else 0

        return {
            'byDomain': {d: round(h, 2) for d, h in time_by_domain.items()},
            'totalHours': round(total_time, 2),
            'averageSessionDuration': round(avg_duration, 2),
            'distribution': {
                d: round(h / total_time * 100, 1)
                for d, h in time_by_domain.items()
            } if total_time > 0 else {}
        }

    def predict_mastery_timeline(self, target_mastery: float = 80.0) -> Dict:
        """
        Predict when concepts will reach target mastery

        Args:
            target_mastery: Target mastery percentage (default 80%)

        Returns:
            Dict mapping concept IDs to mastery predictions
        """
        velocity_data = self.calculate_learning_velocity()
        velocity = velocity_data['velocity']

        if velocity == 0:
            return {
                'error': 'Cannot predict timeline: no learning velocity data',
                'predictions': {}
            }

        mastery_data = self.generate_mastery_heatmap()
        predictions = {}

        concepts = self.schedule.get('concepts', {})

        for concept_id, data in concepts.items():
            concept_mastery = mastery_data['concepts'].get(concept_id, {})
            current_mastery = concept_mastery.get('score', 0)

            if current_mastery >= target_mastery:
                predictions[concept_id] = {
                    'status': 'achieved',
                    'achievedDate': data.get('lastReview'),
                    'currentMastery': current_mastery
                }
            else:
                mastery_gap = target_mastery - current_mastery
                # Estimate hours needed (heuristic: 10% mastery per hour at current velocity)
                hours_needed = mastery_gap / (velocity * 10) if velocity > 0 else 999
                days_needed = hours_needed / 2  # Assume 2 hours learning per day

                predicted_date = datetime.now() + timedelta(days=days_needed)

                predictions[concept_id] = {
                    'status': 'in_progress',
                    'currentMastery': current_mastery,
                    'targetMastery': target_mastery,
                    'hoursNeeded': round(hours_needed, 1),
                    'daysNeeded': round(days_needed, 0),
                    'predictedDate': predicted_date.isoformat()
                }

        return predictions

    def generate_full_report(
        self,
        domain: Optional[str] = None,
        period_days: int = 30
    ) -> Dict:
        """
        Generate complete analytics report with all 7 metrics

        Args:
            domain: Filter by domain (optional)
            period_days: Analysis period in days

        Returns:
            Complete analytics report (dashboard-compatible format)
        """
        # Calculate all metrics
        retention = self.calculate_retention_curves(domain)
        velocity = self.calculate_learning_velocity(period_days, domain)
        mastery = self.generate_mastery_heatmap(domain)
        adherence = self.calculate_review_adherence(period_days)
        streak = self.calculate_streak()
        time_inv = self.analyze_time_investment(domain)
        predictions = self.predict_mastery_timeline()

        # Generate summary stats for dashboard
        summary = {
            'current_streak': streak.get('currentStreak', 0),
            'total_concepts': mastery.get('totalConcepts', 0),
            'review_adherence': adherence.get('adherence', 0),
            'avg_velocity': velocity.get('velocity', 0) * 7  # Convert to weekly
        }

        return {
            # Metadata
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'period_days': period_days,
                'domain_filter': domain
            },

            # Summary cards
            'summary': summary,

            # Detailed metrics (dashboard-compatible keys)
            'retention_curves': retention,
            'learning_velocity': velocity,
            'mastery_heatmap': mastery,
            'review_adherence': adherence,
            'streak_tracking': streak,
            'time_distribution': time_inv,
            'predictions': predictions,

            # Legacy keys (for compatibility)
            'retention': retention,
            'velocity': velocity,
            'mastery': mastery,
            'adherence': adherence,
            'streak': streak,
            'timeInvestment': time_inv
        }


def main():
    """CLI entry point for analytics generation"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate learning analytics',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate full analytics
  python generate-analytics.py

  # Filter by domain
  python generate-analytics.py --domain finance

  # Analyze last 7 days
  python generate-analytics.py --period 7

  # Custom output location
  python generate-analytics.py --output /tmp/analytics.json
        """
    )

    parser.add_argument(
        '--domain',
        type=str,
        help='Filter by domain (e.g., finance, programming)'
    )
    parser.add_argument(
        '--period',
        type=int,
        default=30,
        help='Analysis period in days (default: 30)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='.review/analytics-cache.json',
        help='Output file path (default: .review/analytics-cache.json)'
    )

    args = parser.parse_args()

    # Generate analytics
    engine = AnalyticsEngine()
    report = engine.generate_full_report(args.domain, args.period)

    # Write to cache
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"✓ Analytics generated: {output_path}")
    print(f"  Period: {args.period} days")
    print(f"  Domain: {args.domain or 'All'}")

    velocity = report.get('velocity', {})
    print(f"  Velocity: {velocity.get('velocity', 0)} concepts/hour ({velocity.get('benchmark', 'N/A')})")

    adherence = report.get('adherence', {})
    print(f"  Adherence: {adherence.get('adherence', 0)}% ({adherence.get('classification', 'N/A')})")

    streak = report.get('streak', {})
    print(f"  Streak: {streak.get('currentStreak', 0)} days (longest: {streak.get('longestStreak', 0)})")

    time_inv = report.get('timeInvestment', {})
    print(f"  Time Investment: {time_inv.get('totalHours', 0)} hours")

    mastery = report.get('mastery', {})
    print(f"  Concepts Tracked: {mastery.get('totalConcepts', 0)}")


if __name__ == '__main__':
    main()
