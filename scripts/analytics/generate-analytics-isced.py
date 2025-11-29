#!/usr/bin/env python3
"""
ISCED-based Learning Analytics System

Improves on the original analytics by:
1. Using ISCED classification instead of generic domains
2. Aggregating retention curves by ISCED domain
3. Showing meaningful learning velocity (reviews/hour instead of mastery/hour)
4. Domain-level aggregation for all metrics
"""

import json
import math
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# ISCED code to domain mapping
ISCED_DOMAINS = {
    '01': 'education',
    '02': 'humanities',
    '03': 'social-sciences',
    '04': 'business-law',
    '05': 'natural-sciences',
    '06': 'ict',
    '07': 'engineering',
    '08': 'agriculture',
    '09': 'health',
    '10': 'services'
}

# Domain display names
DOMAIN_NAMES = {
    'education': 'Education',
    'humanities': 'Arts & Humanities',
    'social-sciences': 'Social Sciences',
    'business-law': 'Business & Law',
    'natural-sciences': 'Natural Sciences',
    'ict': 'ICT',
    'engineering': 'Engineering',
    'agriculture': 'Agriculture',
    'health': 'Health & Medicine',
    'services': 'Services',
    'uncategorized': 'Uncategorized'
}


class ISCEDAnalytics:
    """Analytics engine with ISCED domain classification"""

    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path.cwd()

        # Load data sources
        self.schedule = self.load_json('.review/schedule.json')
        self.history = self.load_json('.review/history.json')
        self.chats = self.load_json('chats/index.json')

        # Load all Rem files to get ISCED classification
        self.concept_isced = self.load_concept_isced()

    def load_json(self, path: str) -> Dict:
        """Load JSON file or return empty dict"""
        try:
            full_path = self.base_path / path
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def load_concept_isced(self) -> Dict[str, str]:
        """Load ISCED classification for all concepts from Rem files"""
        concept_isced = {}
        kb_path = self.base_path / 'knowledge-base'

        for rem_file in kb_path.rglob('*.md'):
            if rem_file.name.startswith('_'):
                continue

            try:
                with open(rem_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]

                        # Extract rem_id and isced
                        rem_id = None
                        isced = None

                        for line in frontmatter.split('\n'):
                            line = line.strip()
                            if line.startswith('rem_id:'):
                                rem_id = line.split(':', 1)[1].strip()
                            elif line.startswith('isced:'):
                                isced = line.split(':', 1)[1].strip()

                        if rem_id and isced:
                            # Extract domain from ISCED code
                            domain = self.extract_domain_from_isced(isced)
                            concept_isced[rem_id] = domain

            except Exception:
                continue

        return concept_isced

    def extract_domain_from_isced(self, isced: str) -> str:
        """Extract ISCED domain from ISCED path"""
        if not isced:
            return 'uncategorized'

        # Try to extract first 2 digits
        match = re.match(r'^(\d{2})', isced)
        if match:
            code = match.group(1)
            return ISCED_DOMAINS.get(code, 'uncategorized')

        return 'uncategorized'

    def calculate_aggregated_retention_curves(self) -> Dict:
        """Calculate retention curves aggregated by ISCED domain"""
        domain_curves = defaultdict(list)

        concepts = self.schedule.get('concepts', {})

        for concept_id, data in concepts.items():
            # Get ISCED domain for this concept
            domain = self.concept_isced.get(concept_id, 'uncategorized')

            # Calculate retention curve for this concept
            fsrs_state = data.get('fsrs_state', {})
            stability = fsrs_state.get('stability', 1.0)
            difficulty = fsrs_state.get('difficulty', 5.0)

            # Strength based on FSRS parameters
            strength = stability * (11 - difficulty) / 10

            # Generate 30-day retention curve
            curve = []
            for day in range(31):
                retention = math.exp(-day / max(strength, 0.1)) * 100
                curve.append(min(100, max(0, retention)))

            domain_curves[domain].append(curve)

        # Average curves by domain
        aggregated = {}
        for domain, curves in domain_curves.items():
            if curves:
                # Calculate average retention for each day
                avg_curve = []
                for day in range(31):
                    day_values = [curve[day] for curve in curves if day < len(curve)]
                    avg_retention = sum(day_values) / len(day_values) if day_values else 0
                    avg_curve.append({
                        'day': day,
                        'retention': round(avg_retention, 1),
                        'date': (datetime.now() + timedelta(days=day)).isoformat()
                    })

                aggregated[domain] = {
                    'curve': avg_curve,
                    'conceptCount': len(curves),
                    'currentRetention': avg_curve[0]['retention'],
                    'domainName': DOMAIN_NAMES.get(domain, domain.title())
                }

        return aggregated

    def calculate_learning_velocity_by_domain(self, period_days: int = 30) -> Dict:
        """Calculate learning velocity by ISCED domain (reviews/hour not mastery/hour)"""
        cutoff_date = datetime.now() - timedelta(days=period_days)

        domain_stats = defaultdict(lambda: {'reviews': 0, 'hours': 0})

        # Count reviews from history
        for session in self.history.get('sessions', []):
            try:
                session_date = datetime.fromisoformat(
                    session.get('timestamp', '').replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                continue

            if session_date > cutoff_date:
                # Get domain from session
                for review in session.get('reviews', []):
                    concept_id = review.get('concept_id')
                    domain = self.concept_isced.get(concept_id, 'uncategorized')
                    domain_stats[domain]['reviews'] += 1

                # Add time invested
                duration_hours = session.get('duration', 0) / 3600
                # Distribute time across domains in this session
                domains_in_session = set()
                for review in session.get('reviews', []):
                    concept_id = review.get('concept_id')
                    domain = self.concept_isced.get(concept_id, 'uncategorized')
                    domains_in_session.add(domain)

                if domains_in_session:
                    hours_per_domain = duration_hours / len(domains_in_session)
                    for domain in domains_in_session:
                        domain_stats[domain]['hours'] += hours_per_domain

        # Calculate velocity for each domain
        velocities = {}
        for domain, stats in domain_stats.items():
            hours = stats['hours']
            reviews = stats['reviews']

            velocity = reviews / hours if hours > 0 else 0

            velocities[domain] = {
                'velocity': round(velocity, 2),
                'reviewsCompleted': reviews,
                'hoursInvested': round(hours, 1),
                'domainName': DOMAIN_NAMES.get(domain, domain.title()),
                'benchmark': 'fast' if velocity > 10 else 'medium' if velocity > 5 else 'slow'
            }

        return velocities

    def generate_domain_heatmap(self) -> Dict:
        """Generate mastery heatmap by ISCED domain"""
        domain_mastery = defaultdict(list)

        concepts = self.schedule.get('concepts', {})

        for concept_id, data in concepts.items():
            domain = self.concept_isced.get(concept_id, 'uncategorized')

            # Calculate mastery score
            fsrs_state = data.get('fsrs_state', {})
            stability = fsrs_state.get('stability', 1.0)
            difficulty = fsrs_state.get('difficulty', 5.0)
            review_count = fsrs_state.get('review_count', 0)

            # Mastery formula
            stability_score = min(stability, 100) * 0.6
            review_score = min(review_count * 5, 30)
            difficulty_score = (10 - min(difficulty, 10)) * 1.0

            mastery = min(stability_score + review_score + difficulty_score, 100)
            domain_mastery[domain].append(mastery)

        # Calculate domain averages and distributions
        heatmap = {}
        for domain, scores in domain_mastery.items():
            if scores:
                avg_mastery = sum(scores) / len(scores)

                # Categorize concepts
                novice = sum(1 for s in scores if s < 25)
                learning = sum(1 for s in scores if 25 <= s < 50)
                competent = sum(1 for s in scores if 50 <= s < 75)
                expert = sum(1 for s in scores if s >= 75)

                heatmap[domain] = {
                    'averageMastery': round(avg_mastery, 1),
                    'conceptCount': len(scores),
                    'distribution': {
                        'novice': novice,
                        'learning': learning,
                        'competent': competent,
                        'expert': expert
                    },
                    'domainName': DOMAIN_NAMES.get(domain, domain.title())
                }

        return heatmap

    def calculate_review_adherence_by_domain(self, period_days: int = 30) -> Dict:
        """Calculate review adherence by ISCED domain"""
        cutoff_date = datetime.now() - timedelta(days=period_days)

        domain_adherence = defaultdict(lambda: {'on_time': 0, 'late': 0, 'total': 0})

        concepts = self.schedule.get('concepts', {})

        for concept_id, data in concepts.items():
            domain = self.concept_isced.get(concept_id, 'uncategorized')

            fsrs_state = data.get('fsrs_state', {})
            next_review_str = fsrs_state.get('next_review')
            last_review_str = fsrs_state.get('last_review')

            if not next_review_str:
                continue

            try:
                next_review = datetime.fromisoformat(next_review_str.replace('Z', '+00:00'))
            except:
                continue

            # Only process if review was due in period
            if not (cutoff_date < next_review < datetime.now()):
                continue

            domain_adherence[domain]['total'] += 1

            if last_review_str:
                try:
                    last_review = datetime.fromisoformat(last_review_str.replace('Z', '+00:00'))
                    days_late = (last_review - next_review).days
                    if days_late <= 1:
                        domain_adherence[domain]['on_time'] += 1
                    else:
                        domain_adherence[domain]['late'] += 1
                except:
                    domain_adherence[domain]['late'] += 1
            else:
                domain_adherence[domain]['late'] += 1

        # Calculate adherence percentages
        adherence = {}
        for domain, stats in domain_adherence.items():
            total = stats['total']
            if total > 0:
                adherence_pct = (stats['on_time'] / total) * 100
                adherence[domain] = {
                    'adherence': round(adherence_pct, 1),
                    'onTime': stats['on_time'],
                    'late': stats['late'],
                    'totalDue': total,
                    'domainName': DOMAIN_NAMES.get(domain, domain.title()),
                    'classification': (
                        'excellent' if adherence_pct > 80 else
                        'good' if adherence_pct > 60 else
                        'poor'
                    )
                }

        return adherence

    def generate_full_report(self, period_days: int = 30) -> Dict:
        """Generate complete ISCED-based analytics report"""

        # Calculate all metrics
        retention = self.calculate_aggregated_retention_curves()
        velocity = self.calculate_learning_velocity_by_domain(period_days)
        mastery = self.generate_domain_heatmap()
        adherence = self.calculate_review_adherence_by_domain(period_days)

        # Calculate summary statistics
        total_concepts = len(self.schedule.get('concepts', {}))

        # Overall adherence (weighted average)
        total_on_time = sum(a.get('onTime', 0) for a in adherence.values())
        total_due = sum(a.get('totalDue', 0) for a in adherence.values())
        overall_adherence = (total_on_time / total_due * 100) if total_due > 0 else 0

        # Overall velocity (weighted average)
        total_reviews = sum(v.get('reviewsCompleted', 0) for v in velocity.values())
        total_hours = sum(v.get('hoursInvested', 0) for v in velocity.values())
        overall_velocity = total_reviews / total_hours if total_hours > 0 else 0

        return {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'period_days': period_days,
                'classification': 'ISCED'
            },
            'summary': {
                'total_concepts': total_concepts,
                'total_domains': len(retention),
                'review_adherence': round(overall_adherence, 1),
                'avg_velocity': round(overall_velocity, 1),
                'total_hours': round(total_hours, 1)
            },
            'retention_by_domain': retention,
            'velocity_by_domain': velocity,
            'mastery_by_domain': mastery,
            'adherence_by_domain': adherence
        }


def main():
    """Generate ISCED-based analytics"""
    engine = ISCEDAnalytics()
    report = engine.generate_full_report()

    # Save to file
    output_path = Path('.review/analytics-isced.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"✓ ISCED Analytics generated: {output_path}")
    print(f"  Total concepts: {report['summary']['total_concepts']}")
    print(f"  Domains tracked: {report['summary']['total_domains']}")
    print(f"  Overall adherence: {report['summary']['review_adherence']}%")
    print(f"  Average velocity: {report['summary']['avg_velocity']} reviews/hour")


if __name__ == '__main__':
    main()