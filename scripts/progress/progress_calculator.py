#!/usr/bin/env python3
"""
Progress calculation module
Contains ProgressCalculator class for statistics calculation
"""

from datetime import datetime, timedelta
from pathlib import Path

class ProgressCalculator:
    """Calculate progress statistics for the knowledge system."""

    def __init__(self, data):
        self.data = data
        self.materials = data.get('materials_index', {}).get('materials', {})
        self.schedule = data.get('schedule', {})
        self.history = data.get('history', {})
        self.kb_metadata = data.get('kb_metadata', {})

    def calculate_overall_stats(self):
        """Calculate system-wide statistics."""
        # Material statistics
        total_materials = len(self.materials)
        completed = sum(1 for m in self.materials.values() if m.get('status') == 'completed')
        in_progress = sum(1 for m in self.materials.values() if m.get('status') == 'in-progress')
        not_started = total_materials - completed - in_progress

        # Concept statistics
        total_concepts = self.kb_metadata.get('total_concepts', 0)
        by_domain = self.kb_metadata.get('by_domain', {})

        # Time statistics
        learning_sessions = self.history.get('sessions', [])
        total_time = sum(s.get('duration_minutes', 0) for s in learning_sessions)
        avg_session = total_time / len(learning_sessions) if learning_sessions else 0

        # Streak calculation
        streak = self.calculate_learning_streak(learning_sessions)

        # Review statistics
        concepts_due_today = self.schedule.get('metadata', {}).get('concepts_due_today', 0)
        next_review_date = self.get_next_review_date()

        return {
            'materials': {
                'total': total_materials,
                'completed': completed,
                'in_progress': in_progress,
                'not_started': not_started
            },
            'concepts': {
                'total': total_concepts,
                'by_domain': by_domain
            },
            'time': {
                'total_hours': total_time / 60 if total_time else 0,
                'average_session_minutes': avg_session
            },
            'streak': streak,
            'review': {
                'due_today': concepts_due_today,
                'next_date': next_review_date
            }
        }

    def calculate_domain_stats(self, domain):
        """Calculate statistics for a specific domain."""
        # Filter materials by domain
        domain_materials = []
        for path, material in self.materials.items():
            if f'/{domain}/' in path or path.startswith(f'learning-materials/{domain}/'):
                domain_materials.append({
                    'path': path,
                    'title': material.get('title', path.split('/')[-1]),
                    'status': material.get('status', 'not-started'),
                    'progress_percentage': material.get('progress_percentage', 0),
                    'learned_concepts': material.get('learned_concepts', []),
                    'current_position': material.get('current_position', 'Beginning')
                })

        # Get domain concepts
        total_concepts = self.kb_metadata.get('by_domain', {}).get(domain, 0)

        # Review stats for domain
        domain_review = self.calculate_domain_review_stats(domain)

        return {
            'materials': domain_materials,
            'total_concepts': total_concepts,
            'recent_concepts': [],  # Would need to read actual files for this
            'review': domain_review
        }

    def calculate_material_stats(self, material_path):
        """Calculate statistics for a specific material."""
        material = self.materials.get(material_path, {})

        # Try to load progress file
        progress_file = Path(material_path.replace('.pdf', '.progress.md')
                             .replace('.epub', '.progress.md')
                             .replace('.md', '.progress.md'))

        if progress_file.exists():
            # Parse progress file (simplified)
            return {
                'title': material.get('title', material_path.split('/')[-1]),
                'type': material.get('type', 'unknown'),
                'status': material.get('status', 'not-started'),
                'progress_percentage': material.get('progress_percentage', 0),
                'current_position': material.get('current_position', 'Beginning'),
                'started': material.get('started', 'Unknown'),
                'completed': material.get('completed'),
                'learned_concepts': material.get('learned_concepts', []),
                'toc': [],  # Would need to parse from progress file
                'learning_journal': []  # Would need to parse from progress file
            }

        return {
            'title': material_path.split('/')[-1],
            'type': 'unknown',
            'status': 'not-started',
            'progress_percentage': 0,
            'current_position': 'Not started',
            'learned_concepts': []
        }

    def calculate_learning_streak(self, sessions):
        """Calculate current learning streak in days."""
        if not sessions:
            return 0

        # Sort sessions by date
        sorted_sessions = sorted(sessions, key=lambda s: s.get('date', ''), reverse=True)

        streak = 0
        today = datetime.now().date()
        current_date = today

        for session in sorted_sessions:
            session_date = datetime.strptime(session.get('date', ''), '%Y-%m-%d').date()

            # Check if session is on expected date
            if session_date == current_date:
                streak += 1
                current_date -= timedelta(days=1)
            elif session_date < current_date:
                break

        return streak

    def get_next_review_date(self):
        """Get the next review date from schedule."""
        concepts = self.schedule.get('concepts', [])
        if not concepts:
            return None

        # Find earliest due date
        next_date = None
        for concept in concepts:
            # Handle both dict and string formats
            if isinstance(concept, dict):
                due_date = concept.get('next_review')
            else:
                continue  # Skip non-dict entries

            if due_date and (not next_date or due_date < next_date):
                next_date = due_date

        return next_date

    def calculate_domain_review_stats(self, domain):
        """Calculate review statistics for a domain."""
        concepts = self.schedule.get('concepts', [])
        domain_concepts = [c for c in concepts if domain in c.get('path', '')]

        today = datetime.now().strftime('%Y-%m-%d')
        due_today = sum(1 for c in domain_concepts if c.get('next_review') == today)

        # Calculate due this week
        week_from_now = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        due_this_week = sum(1 for c in domain_concepts
                           if today <= c.get('next_review', '') <= week_from_now)

        # Average quality (if tracked)
        qualities = [c.get('quality', 3) for c in domain_concepts if 'quality' in c]
        avg_quality = sum(qualities) / len(qualities) if qualities else 3.0

        return {
            'due_today': due_today,
            'due_this_week': due_this_week,
            'average_quality': avg_quality
        }

    def analyze_domain_balance(self, by_domain):
        """Analyze balance across domains."""
        if not by_domain:
            return {'imbalanced': False}

        total = sum(by_domain.values())
        if total == 0:
            return {'imbalanced': False}

        # Check for imbalance (one domain > 60% of total)
        for domain, count in by_domain.items():
            if count / total > 0.6:
                # Find least studied domain
                suggested = min(by_domain.keys(), key=lambda k: by_domain[k])
                return {
                    'imbalanced': True,
                    'dominant_domain': domain,
                    'suggested_domain': suggested
                }

        return {'imbalanced': False}