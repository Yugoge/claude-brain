#!/usr/bin/env python3
"""
Recommendation engine module
Generates personalized learning recommendations
"""

class RecommendationEngine:
    """Generate recommendations based on progress statistics."""

    def generate_recommendations(self, stats):
        """Generate personalized recommendations based on current statistics."""
        recommendations = []

        # Review recommendations
        if stats['review']['due_today'] > 0:
            recommendations.append(
                f"🔴 You have {stats['review']['due_today']} reviews due. Run `/review` soon!"
            )

        # Streak recommendations
        if stats['streak'] == 0:
            recommendations.append(
                "🎯 Start a learning streak! Even 15 minutes daily makes a difference."
            )
        elif stats['streak'] >= 7:
            recommendations.append(
                f"🔥 Amazing {stats['streak']}-day streak! Keep it going!"
            )
        elif stats['streak'] >= 3:
            recommendations.append(
                f"👍 {stats['streak']}-day streak! You're building momentum."
            )

        # Material recommendations
        materials = stats['materials']
        if materials['in_progress'] > 5:
            recommendations.append(
                "📚 You have many materials in progress. Consider focusing on 2-3 at a time."
            )

        if materials['not_started'] > 0 and materials['in_progress'] == 0:
            recommendations.append(
                f"🆕 You have {materials['not_started']} materials waiting. Ready to start one?"
            )

        # Completion recommendations
        if materials['total'] > 0:
            completion_rate = materials['completed'] / materials['total'] * 100
            if completion_rate > 80:
                recommendations.append(
                    "🏆 Excellent completion rate! Consider adding new materials."
                )
            elif completion_rate < 20 and materials['in_progress'] > 0:
                recommendations.append(
                    "💪 Focus on completing current materials before starting new ones."
                )

        # Balance recommendations
        by_domain = stats['concepts']['by_domain']
        balance = self.analyze_domain_balance(by_domain)
        if balance['imbalanced']:
            recommendations.append(
                f"⚖️ Most learning in {balance['dominant_domain']}. "
                f"Consider diversifying with {balance['suggested_domain']}."
            )

        # Time recommendations
        avg_session = stats['time']['average_session_minutes']
        if avg_session > 120:
            recommendations.append(
                "⏰ Long sessions detected. Consider shorter, more frequent sessions."
            )
        elif avg_session < 15 and avg_session > 0:
            recommendations.append(
                "⏰ Very short sessions. Try 30-45 minute focused sessions."
            )

        # Knowledge base recommendations
        if stats['concepts']['total'] > 100:
            if stats['review']['due_today'] == 0:
                recommendations.append(
                    "📝 With 100+ concepts, regular review is crucial for retention."
                )

        if stats['concepts']['total'] < 10 and materials['completed'] > 0:
            recommendations.append(
                "💡 Consider extracting more concepts from completed materials."
            )

        return recommendations

    def analyze_domain_balance(self, by_domain):
        """Analyze balance across learning domains."""
        if not by_domain:
            return {'imbalanced': False}

        total = sum(by_domain.values())
        if total == 0:
            return {'imbalanced': False}

        # Check for imbalance (one domain > 60% of total)
        for domain, count in by_domain.items():
            if count / total > 0.6:
                # Find least studied domain
                other_domains = {k: v for k, v in by_domain.items() if k != domain}
                if other_domains:
                    suggested = min(other_domains.keys(), key=lambda k: other_domains[k])
                else:
                    suggested = "a new domain"
                return {
                    'imbalanced': True,
                    'dominant_domain': domain,
                    'suggested_domain': suggested
                }

        return {'imbalanced': False}

    def get_priority_recommendations(self, stats):
        """Get high-priority recommendations that need immediate attention."""
        priority = []

        # Overdue reviews are highest priority
        if stats['review']['due_today'] > 10:
            priority.append({
                'level': 'critical',
                'action': 'Clear review backlog',
                'reason': f"{stats['review']['due_today']} reviews overdue"
            })

        # Broken streak is high priority
        if stats['streak'] == 0 and stats['time']['total_hours'] > 5:
            priority.append({
                'level': 'high',
                'action': 'Restart learning habit',
                'reason': 'Learning streak broken'
            })

        # Too many in-progress materials
        if stats['materials']['in_progress'] > 7:
            priority.append({
                'level': 'medium',
                'action': 'Complete current materials',
                'reason': 'Too many materials in progress'
            })

        return priority