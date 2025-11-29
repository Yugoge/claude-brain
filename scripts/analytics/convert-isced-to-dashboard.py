#!/usr/bin/env python3
"""
Convert ISCED analytics format to dashboard-compatible format
"""

import json
from pathlib import Path
import sys
from datetime import datetime

def convert_isced_to_dashboard(isced_data):
    """Convert ISCED analytics format to dashboard format"""

    dashboard_data = {
        'metadata': isced_data.get('metadata', {}),
        'summary': isced_data.get('summary', {}),
        'streak': {
            'current': 0,
            'longest': 0,
            'lastReviewDate': None
        },
        'retention': {
            'domains': {}
        },
        'learning': {
            'velocity': {},
            'mastery': {}
        },
        'review': {
            'adherence': {}
        },
        'time': {
            'distribution': {
                'morning': 0,
                'afternoon': 0,
                'evening': 0,
                'night': 0
            }
        }
    }

    # Convert retention curves by domain
    if 'retention_by_domain' in isced_data:
        for domain, data in isced_data['retention_by_domain'].items():
            dashboard_data['retention']['domains'][domain] = {
                'curve': data.get('curve', []),
                'conceptCount': data.get('conceptCount', 0)
            }

    # Convert velocity by domain
    if 'velocity_by_domain' in isced_data:
        for domain, data in isced_data['velocity_by_domain'].items():
            dashboard_data['learning']['velocity'][domain] = {
                'velocity': data.get('velocity', 0),
                'reviewsCompleted': data.get('reviewsCompleted', 0),
                'hoursInvested': data.get('hoursInvested', 0)
            }

    # Convert mastery by domain
    if 'mastery_by_domain' in isced_data:
        for domain, data in isced_data['mastery_by_domain'].items():
            dashboard_data['learning']['mastery'][domain] = {
                'masteryRate': data.get('masteryRate', 0),
                'totalConcepts': data.get('totalConcepts', 0),
                'masteredConcepts': data.get('masteredConcepts', 0),
                'learningConcepts': data.get('learningConcepts', 0),
                'difficultConcepts': data.get('difficultConcepts', 0)
            }

    # Convert adherence by domain
    if 'adherence_by_domain' in isced_data:
        for domain, data in isced_data['adherence_by_domain'].items():
            dashboard_data['review']['adherence'][domain] = {
                'rate': data.get('rate', 0),
                'dueReviews': data.get('dueReviews', 0),
                'completedReviews': data.get('completedReviews', 0)
            }

    return dashboard_data


def main():
    # Read ISCED analytics
    isced_path = Path('.review/analytics-isced.json')
    if not isced_path.exists():
        print("❌ ISCED analytics file not found")
        return 1

    with open(isced_path) as f:
        isced_data = json.load(f)

    # Convert to dashboard format
    dashboard_data = convert_isced_to_dashboard(isced_data)

    # Save converted data
    output_path = Path('.review/analytics-dashboard.json')
    with open(output_path, 'w') as f:
        json.dump(dashboard_data, f, indent=2)

    print(f"✅ Converted analytics saved to {output_path}")
    print(f"   Domains: {len(dashboard_data['retention']['domains'])}")
    print(f"   Total concepts: {dashboard_data['metadata'].get('totalConcepts', 0)}")

    return 0


if __name__ == '__main__':
    sys.exit(main())