#!/usr/bin/env python3
"""
Main entry point for the /progress command
Displays learning progress across materials and domains
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from progress_calculator import ProgressCalculator
from progress_formatter import ProgressFormatter
from recommendation_engine import RecommendationEngine

def load_data():
    """Load all necessary JSON files."""
    data = {}

    # Load material index
    index_file = Path('learning-materials/.index.json')
    if index_file.exists():
        with open(index_file) as f:
            data['materials_index'] = json.load(f)
    else:
        data['materials_index'] = {'materials': {}, 'metadata': {'total_materials': 0}}

    # Load review schedule
    schedule_file = Path('.review/schedule.json')
    if schedule_file.exists():
        with open(schedule_file) as f:
            data['schedule'] = json.load(f)
    else:
        data['schedule'] = {'concepts': [], 'metadata': {'concepts_due_today': 0}}

    # Load history
    history_file = Path('.review/history.json')
    if history_file.exists():
        with open(history_file) as f:
            data['history'] = json.load(f)
    else:
        data['history'] = {'sessions': []}

    # Count knowledge base concepts
    kb_path = Path('knowledge-base')
    data['kb_metadata'] = {
        'total_concepts': sum(1 for f in kb_path.rglob('*.md') if not f.name.startswith('.')),
        'by_domain': {}
    }

    # Count by domain
    for domain_dir in kb_path.iterdir():
        if domain_dir.is_dir() and not domain_dir.name.startswith('.'):
            count = sum(1 for f in domain_dir.rglob('*.md'))
            if count > 0:
                data['kb_metadata']['by_domain'][domain_dir.name] = count

    return data

def main():
    """Main entry point."""
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    # Parse arguments
    if len(args) == 0:
        mode = "overview"
        target = None
    elif args[0] in ['finance', 'programming', 'language', 'science']:
        mode = "domain"
        target = args[0]
    elif args[0].startswith('learning-materials/'):
        mode = "material"
        target = args[0]
    else:
        print(f"Invalid argument: {args[0]}")
        print("Usage: /progress [domain|file-path]")
        return 1

    # Load data
    data = load_data()

    # Initialize components
    calculator = ProgressCalculator(data)
    formatter = ProgressFormatter()
    recommender = RecommendationEngine()

    # Calculate and display based on mode
    if mode == "overview":
        stats = calculator.calculate_overall_stats()
        output = formatter.format_overview(stats)
        recommendations = recommender.generate_recommendations(stats)
        print(output)
        if recommendations:
            print("\n💡 Recommendations:")
            for rec in recommendations:
                print(f"- {rec}")

    elif mode == "domain":
        domain_stats = calculator.calculate_domain_stats(target)
        output = formatter.format_domain_progress(domain_stats, target)
        print(output)

    elif mode == "material":
        material_stats = calculator.calculate_material_stats(target)
        output = formatter.format_material_progress(material_stats)
        print(output)

    return 0

if __name__ == '__main__':
    sys.exit(main())