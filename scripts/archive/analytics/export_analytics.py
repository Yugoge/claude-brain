#!/usr/bin/env python3
"""
Analytics Export System

Exports learning analytics and insights to multiple formats:
- HTML: Interactive dashboard artifact
- CSV: Tabular data for spreadsheet analysis
- JSON: Raw data for programmatic access

Part of Story 3.6: Analytics Insights Engine

Usage:
    python scripts/export_analytics.py --format html --output report.html
    python scripts/export_analytics.py --format csv --output data.csv
    python scripts/export_analytics.py --format json --output data.json
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


class AnalyticsExporter:
    """Export analytics and insights to various formats"""

    def __init__(
        self,
        analytics_path: str = '.review/analytics-cache.json',
        insights_path: str = '.review/insights.json'
    ):
        """
        Initialize exporter

        Args:
            analytics_path: Path to analytics cache
            insights_path: Path to insights cache
        """
        self.analytics_path = Path(analytics_path)
        self.insights_path = Path(insights_path)

        # Load data
        with open(self.analytics_path, 'r', encoding='utf-8') as f:
            self.analytics = json.load(f)

        if self.insights_path.exists():
            with open(self.insights_path, 'r', encoding='utf-8') as f:
                self.insights = json.load(f)
        else:
            self.insights = {}

    def export_html(self, output_path: str, title: str = "Learning Analytics Report"):
        """
        Export to interactive HTML dashboard

        Args:
            output_path: Output file path
            title: Report title
        """
        html_content = self._generate_html_dashboard(title)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"✓ HTML export complete: {output_path}")

    def export_csv(self, output_path: str):
        """
        Export to CSV format for spreadsheet analysis

        Args:
            output_path: Output file path
        """
        rows = []

        # Header
        rows.append(['Metric', 'Value', 'Details'])

        # Velocity metrics
        velocity = self.analytics.get('velocity', {})
        rows.append(['Velocity', velocity.get('velocity', 0), f"{velocity.get('benchmark', 'N/A')} learner"])
        rows.append(['Concepts Mastered', velocity.get('conceptsMastered', 0), f"in {velocity.get('hoursInvested', 0)} hours"])
        rows.append(['Velocity Trend', f"{velocity.get('trend', 0)}%", 'vs previous period'])

        # Adherence metrics
        adherence = self.analytics.get('adherence', {})
        rows.append(['Adherence', f"{adherence.get('adherence', 0)}%", adherence.get('classification', 'N/A')])
        rows.append(['On-Time Reviews', adherence.get('onTimeReviews', 0), f"of {adherence.get('totalDue', 0)} due"])

        # Streak metrics
        streak = self.analytics.get('streak', {})
        rows.append(['Current Streak', streak.get('currentStreak', 0), 'days'])
        rows.append(['Longest Streak', streak.get('longestStreak', 0), 'days'])
        rows.append(['Total Active Days', streak.get('totalActiveDays', 0), 'days'])

        # Time investment
        time_data = self.analytics.get('timeInvestment', {})
        rows.append(['Total Hours', time_data.get('totalHours', 0), 'hours invested'])
        rows.append(['Avg Session', time_data.get('averageSessionDuration', 0), 'hours per session'])

        # Domain breakdown
        by_domain = time_data.get('byDomain', {})
        for domain, hours in by_domain.items():
            rows.append([f'Time - {domain.title()}', hours, 'hours'])

        # Mastery metrics
        mastery = self.analytics.get('mastery', {})
        rows.append(['Total Concepts', mastery.get('totalConcepts', 0), 'concepts tracked'])

        domain_avg = mastery.get('domainAverages', {})
        for domain, avg in domain_avg.items():
            rows.append([f'Mastery - {domain.title()}', f"{avg}%", 'average mastery'])

        # Insights
        if self.insights:
            rows.append(['', '', ''])  # Empty row
            rows.append(['INSIGHTS', '', ''])

            for rec in self.insights.get('recommendations', []):
                rows.append([
                    f"Recommendation ({rec['priority']})",
                    rec['message'],
                    rec.get('actionable', '')
                ])

            for alert in self.insights.get('alerts', []):
                rows.append([
                    f"Alert ({alert['severity']})",
                    alert['message'],
                    alert['timestamp']
                ])

        # Write CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"✓ CSV export complete: {output_path}")
        print(f"  Rows: {len(rows)}")

    def export_json(self, output_path: str):
        """
        Export to JSON format for programmatic access

        Args:
            output_path: Output file path
        """
        export_data = {
            'exported': datetime.now().isoformat(),
            'analytics': self.analytics,
            'insights': self.insights,
            'metadata': {
                'period_days': self.analytics.get('period', 30),
                'domain_filter': self.analytics.get('domain'),
                'total_concepts': self.analytics.get('mastery', {}).get('totalConcepts', 0),
                'current_streak': self.analytics.get('streak', {}).get('currentStreak', 0)
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2)

        print(f"✓ JSON export complete: {output_path}")

    def _generate_html_dashboard(self, title: str) -> str:
        """Generate standalone HTML dashboard"""
        # Extract data
        velocity = self.analytics.get('velocity', {})
        adherence = self.analytics.get('adherence', {})
        streak = self.analytics.get('streak', {})
        time_data = self.analytics.get('timeInvestment', {})
        mastery = self.analytics.get('mastery', {})

        recommendations = self.insights.get('recommendations', [])
        alerts = self.insights.get('alerts', [])
        achievements = self.insights.get('achievements', [])
        trends = self.insights.get('trends', [])
        tips = self.insights.get('tips', [])

        # Priority colors
        priority_colors = {
            'critical': '#e74c3c',
            'high': '#e67e22',
            'medium': '#f39c12',
            'low': '#3498db'
        }

        # Build recommendations HTML
        recs_html = ""
        for rec in recommendations[:3]:
            color = priority_colors.get(rec['priority'], '#999')
            recs_html += f"""
            <div style="padding: 15px; margin-bottom: 10px; background: #fff;
                        border-left: 4px solid {color}; border-radius: 4px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between;">
                    <strong style="color: {color};">{rec['priority'].upper()}</strong>
                    <span style="font-size: 12px; color: #666;">{rec['type']}</span>
                </div>
                <p style="margin: 10px 0; font-size: 16px;">{rec['message']}</p>
                {f'<div><code>{rec["actionable"]}</code><br><small style="color: #888;">{rec["impact"]}</small></div>' if rec.get('actionable') else ''}
            </div>
            """

        # Build alerts HTML
        alerts_html = ""
        for alert in alerts:
            bg_color = '#ffe0e0' if alert['severity'] == 'critical' else '#fff3cd'
            icon = '🚨' if alert['severity'] == 'critical' else '⚠️'
            alerts_html += f"""
            <div style="padding: 10px; margin-bottom: 5px; background: {bg_color};
                        border-radius: 4px;">
                <strong>{icon}</strong> {alert['message']}
            </div>
            """

        # Build achievements HTML
        achievements_html = ""
        for ach in achievements:
            emoji = ach['message'].split()[0]
            text = ' '.join(ach['message'].split()[1:])
            achievements_html += f"""
            <div style="padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; border-radius: 8px; text-align: center;
                        min-width: 150px; margin: 5px;">
                <div style="font-size: 32px;">{emoji}</div>
                <div style="font-size: 14px; margin-top: 5px;">{text}</div>
            </div>
            """

        # Build trends HTML
        trends_html = ""
        for trend in trends:
            trends_html += f"""
            <div style="padding: 10px; margin-bottom: 5px; background: #f8f9fa;
                        border-radius: 4px;">
                {trend['message']}
            </div>
            """

        # Build tips HTML
        tips_html = ""
        for tip in tips:
            tips_html += f"""
            <div style="padding: 10px; margin-bottom: 5px; background: #e8f5e9;
                        border-radius: 4px; border-left: 3px solid #4caf50;">
                {tip}
            </div>
            """

        # Build metrics cards
        metrics_html = f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px; margin-bottom: 30px;">
            <div style="background: #3498db; color: white; padding: 20px; border-radius: 8px;">
                <div style="font-size: 14px; opacity: 0.9;">Velocity</div>
                <div style="font-size: 32px; font-weight: bold;">{velocity.get('velocity', 0)}</div>
                <div style="font-size: 12px; opacity: 0.8;">concepts/hour ({velocity.get('benchmark', 'N/A')})</div>
            </div>
            <div style="background: #2ecc71; color: white; padding: 20px; border-radius: 8px;">
                <div style="font-size: 14px; opacity: 0.9;">Adherence</div>
                <div style="font-size: 32px; font-weight: bold;">{adherence.get('adherence', 0)}%</div>
                <div style="font-size: 12px; opacity: 0.8;">{adherence.get('classification', 'N/A')}</div>
            </div>
            <div style="background: #e67e22; color: white; padding: 20px; border-radius: 8px;">
                <div style="font-size: 14px; opacity: 0.9;">Current Streak</div>
                <div style="font-size: 32px; font-weight: bold;">{streak.get('currentStreak', 0)}</div>
                <div style="font-size: 12px; opacity: 0.8;">days (best: {streak.get('longestStreak', 0)})</div>
            </div>
            <div style="background: #9b59b6; color: white; padding: 20px; border-radius: 8px;">
                <div style="font-size: 14px; opacity: 0.9;">Time Invested</div>
                <div style="font-size: 32px; font-weight: bold;">{time_data.get('totalHours', 0)}</div>
                <div style="font-size: 12px; opacity: 0.8;">hours total</div>
            </div>
        </div>
        """

        # Complete HTML template
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
                         Ubuntu, Cantarell, sans-serif;
            padding: 20px;
            background: #ecf0f1;
            color: #2c3e50;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            margin-bottom: 10px;
            color: #2c3e50;
        }}
        .subtitle {{
            color: #7f8c8d;
            margin-bottom: 30px;
        }}
        h2 {{
            margin-top: 30px;
            margin-bottom: 15px;
            color: #34495e;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <div class="subtitle">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
            Period: {self.analytics.get('period', 30)} days
        </div>

        <h2>📊 Key Metrics</h2>
        {metrics_html}

        <h2>🎯 Top Recommendations</h2>
        <div class="section">
            {recs_html if recs_html else '<p style="color: #7f8c8d;">No recommendations at this time. Keep up the great work!</p>'}
        </div>

        {f'<h2>⚠️ Active Alerts</h2><div class="section">{alerts_html}</div>' if alerts_html else ''}

        {f'<h2>🏆 Recent Achievements</h2><div class="section" style="display: flex; flex-wrap: wrap; gap: 10px;">{achievements_html}</div>' if achievements_html else ''}

        <h2>📈 Key Trends</h2>
        <div class="section">
            {trends_html if trends_html else '<p style="color: #7f8c8d;">Not enough historical data for trend analysis.</p>'}
        </div>

        <h2>💡 Learning Tips</h2>
        <div class="section">
            {tips_html if tips_html else '<p style="color: #7f8c8d;">Keep learning and tips will appear here!</p>'}
        </div>

        <hr style="margin: 40px 0; border: none; border-top: 1px solid #ecf0f1;">
        <div style="text-align: center; color: #95a5a6; font-size: 12px;">
            <p>Generated with Knowledge System Analytics Engine</p>
            <p>Story 3.6: Analytics Insights Engine</p>
        </div>
    </div>
</body>
</html>"""

        return html


def main():
    """CLI entry point for analytics export"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description='Export learning analytics to various formats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export HTML dashboard
  python scripts/export_analytics.py --format html --output report.html

  # Export CSV for Excel
  python scripts/export_analytics.py --format csv --output data.csv

  # Export JSON data
  python scripts/export_analytics.py --format json --output data.json
        """
    )

    parser.add_argument(
        '--format',
        type=str,
        required=True,
        choices=['html', 'csv', 'json'],
        help='Export format'
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Output file path'
    )
    parser.add_argument(
        '--title',
        type=str,
        default='Learning Analytics Report',
        help='Report title (HTML only)'
    )

    args = parser.parse_args()

    try:
        exporter = AnalyticsExporter()

        if args.format == 'html':
            exporter.export_html(args.output, args.title)
        elif args.format == 'csv':
            exporter.export_csv(args.output)
        elif args.format == 'json':
            exporter.export_json(args.output)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Run 'python scripts/generate-analytics.py' first", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
