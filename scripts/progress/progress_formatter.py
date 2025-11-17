#!/usr/bin/env python3
"""
Progress formatting module
Contains ProgressFormatter class for output display
"""

class ProgressFormatter:
    """Format progress statistics for display."""

    def format_overview(self, stats):
        """Format system-wide overview dashboard."""
        lines = []
        lines.append("📊 Knowledge System Progress Dashboard\n")
        lines.append("=" * 50 + "\n")

        # Materials section
        materials = stats['materials']
        total = materials['total']
        if total > 0:
            completed_pct = (materials['completed'] / total * 100)
            in_progress_pct = (materials['in_progress'] / total * 100)
            not_started_pct = (materials['not_started'] / total * 100)
        else:
            completed_pct = in_progress_pct = not_started_pct = 0

        lines.append("📚 Learning Materials")
        lines.append(f"Total: {total}")
        lines.append(f"Completed: {materials['completed']} ({completed_pct:.0f}%)")
        lines.append(f"In Progress: {materials['in_progress']} ({in_progress_pct:.0f}%)")
        lines.append(f"Not Started: {materials['not_started']} ({not_started_pct:.0f}%)\n")

        # Progress bar
        if total > 0:
            bar = self.generate_progress_bar(completed_pct)
            lines.append(f"Overall Progress: {bar}\n")

        # Concepts section
        lines.append("🧠 Knowledge Base")
        lines.append(f"Total Concepts: {stats['concepts']['total']}\n")

        if stats['concepts']['by_domain']:
            lines.append("By Domain:")
            for domain, count in stats['concepts']['by_domain'].items():
                lines.append(f"- {domain.title()}: {count} concepts")
            lines.append("")

        # Time section
        lines.append("⏱️ Learning Investment")
        lines.append(f"Total Time: {stats['time']['total_hours']:.1f} hours")
        lines.append(f"Average Session: {stats['time']['average_session_minutes']:.0f} minutes")
        lines.append(f"Learning Streak: {stats['streak']} days 🔥\n")

        # Review section
        lines.append("📅 Review Schedule")
        if stats['review']['due_today'] > 0:
            lines.append(f"⚠️ {stats['review']['due_today']} concepts due for review today!")
            lines.append("   Run `/review` to start review session")
        else:
            lines.append("✅ No reviews due today")
            if stats['review']['next_date']:
                lines.append(f"   Next review: {stats['review']['next_date']}")
        lines.append("")

        return '\n'.join(lines)

    def format_domain_progress(self, domain_stats, domain):
        """Format domain-specific progress."""
        lines = []
        lines.append(f"📊 {domain.title()} Progress\n")
        lines.append("=" * 50 + "\n")

        # Materials in domain
        lines.append("📚 Materials:")
        for material in domain_stats['materials']:
            status_emoji = {
                'completed': '✅',
                'in-progress': '🔄',
                'not-started': '⏸️'
            }.get(material['status'], '❓')

            lines.append(f"{status_emoji} {material['title']}")
            lines.append(f"   Progress: {material['progress_percentage']}%")
            lines.append(f"   Concepts: {len(material['learned_concepts'])}")
            if material['status'] == 'in-progress':
                lines.append(f"   Position: {material['current_position']}")
            lines.append("")

        # Concepts
        lines.append(f"🧠 Total Concepts: {domain_stats['total_concepts']}")

        if domain_stats.get('recent_concepts'):
            lines.append("Recently Added:")
            for concept in domain_stats['recent_concepts'][:5]:
                lines.append(f"- [[{concept['id']}]] ({concept['created']})")
        lines.append("")

        # Review status
        lines.append("📅 Review Status:")
        review = domain_stats['review']
        lines.append(f"Due today: {review['due_today']}")
        lines.append(f"Due this week: {review['due_this_week']}")
        lines.append(f"Average quality: {review['average_quality']:.1f}/5")

        return '\n'.join(lines)

    def format_material_progress(self, material_stats):
        """Format individual material progress."""
        lines = []
        lines.append(f"📚 {material_stats['title']}\n")
        lines.append("=" * 50 + "\n")

        # Basic info
        lines.append("📖 Material Information:")
        lines.append(f"Type: {material_stats.get('type', 'Unknown')}")
        lines.append(f"Status: {material_stats['status']}\n")

        # Progress
        lines.append("📍 Current Progress:")
        lines.append(f"Position: {material_stats.get('current_position', 'Unknown')}")
        lines.append(f"Completion: {material_stats.get('progress_percentage', 0)}%")

        # Progress bar
        bar = self.generate_progress_bar(material_stats.get('progress_percentage', 0))
        lines.append(f"\n{bar}\n")

        if material_stats.get('started'):
            lines.append(f"Started: {material_stats['started']}")
        if material_stats.get('completed'):
            lines.append(f"Completed: {material_stats['completed']}")
        lines.append("")

        # Learned concepts
        concepts = material_stats.get('learned_concepts', [])
        lines.append(f"🧠 Concepts Learned: {len(concepts)}")
        if concepts:
            lines.append("Recent concepts:")
            for concept_id in concepts[-5:]:
                lines.append(f"- [[{concept_id}]]")
        lines.append("")

        # Next steps
        lines.append("🎯 Next Steps:")
        if material_stats['status'] == 'completed':
            lines.append("✅ Material completed!")
            lines.append("Consider:")
            lines.append("- Review learned concepts with `/review`")
            lines.append("- Explore related materials")
        else:
            lines.append(f"- Continue learning: `/learn {material_stats.get('path', 'material')}`")

        return '\n'.join(lines)

    def generate_progress_bar(self, percentage, width=30):
        """Generate ASCII progress bar."""
        filled = int(percentage / 100 * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {percentage:.0f}%"

    def format_ascii_chart(self, data, title="", width=40, height=10):
        """Generate simple ASCII chart for data visualization."""
        if not data:
            return ""

        lines = []
        if title:
            lines.append(title)
            lines.append("-" * width)

        # Normalize data
        max_val = max(data.values()) if data else 1

        for key, value in data.items():
            bar_width = int((value / max_val) * (width - len(key) - 10))
            bar = '█' * bar_width
            lines.append(f"{key:<15} {bar} {value}")

        return '\n'.join(lines)