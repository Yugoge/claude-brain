#!/usr/bin/env python3
"""
Generate standalone analytics dashboard HTML file with embedded data

Usage:
    python scripts/analytics/generate-dashboard-html.py
    python scripts/analytics/generate-dashboard-html.py --output custom-dashboard.html
"""

import json
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description='Generate analytics dashboard HTML')
    parser.add_argument('--input', type=str, default='.review/analytics-isced.json',
                       help='Input ISCED analytics JSON file')
    parser.add_argument('--template', type=str, default='scripts/analytics/analytics-dashboard-template.html',
                       help='HTML template file')
    parser.add_argument('--output', type=str, default='analytics-dashboard.html',
                       help='Output HTML file')
    args = parser.parse_args()

    # Load analytics data
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"⚠️  Warning: Analytics cache not found: {input_path}", file=sys.stderr)
        print("   Run: python scripts/analytics/generate-analytics.py", file=sys.stderr)
        print("   Creating empty dashboard...", file=sys.stderr)
        analytics_data = {
            "metadata": {
                "generated_at": "1970-01-01T00:00:00Z",
                "period_days": 30
            },
            "summary": {
                "current_streak": 0,
                "total_concepts": 0,
                "review_adherence": 0,
                "avg_velocity": 0
            }
        }
    else:
        with open(input_path, 'r', encoding='utf-8') as f:
            analytics_data = json.load(f)

    # Load template
    template_path = Path(args.template)
    if not template_path.exists():
        print(f"⚠️  Error: Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Embed analytics data
    analytics_data_js = f"const analyticsData = {json.dumps(analytics_data, indent=2)};"

    # Replace placeholder (handle both old and new format)
    html = template.replace(
        '// ANALYTICS_DATA_PLACEHOLDER\n        const analyticsData = null;  // Will be replaced by actual data',
        analytics_data_js
    )

    # Fallback: Also try single-line format
    if 'const analyticsData = null;' in html:
        html = html.replace(
            'const analyticsData = null;  // Will be replaced by actual data',
            analytics_data_js
        )

    # Write output
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # Print summary
    summary = analytics_data.get('summary', {})
    print(f"✅ Dashboard generated successfully", file=sys.stderr)
    print(f"   Concepts tracked: {summary.get('total_concepts', 0)}", file=sys.stderr)
    print(f"   Current streak: {summary.get('current_streak', 0)} days", file=sys.stderr)
    print(f"   Review adherence: {summary.get('review_adherence', 0):.1f}%", file=sys.stderr)
    print(f"   Output: {output_path.absolute()}", file=sys.stderr)
    print(f"\n   Open in browser: file://{output_path.absolute()}", file=sys.stderr)


if __name__ == '__main__':
    main()
