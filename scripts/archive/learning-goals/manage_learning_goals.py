#!/usr/bin/env python3
"""
Learning Goals Management

Manages user learning goals for personalized insights.
Part of Story 3.6: Analytics Insights Engine

Goals:
- mastery: Focus on deep understanding and high retention
- streak: Focus on daily consistency and momentum
- breadth: Focus on exploring diverse topics

Usage:
    python scripts/manage_learning_goals.py --set mastery
    python scripts/manage_learning_goals.py --get
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class GoalsManager:
    """Manage user learning goals"""

    VALID_GOALS = ['mastery', 'streak', 'breadth']
    GOALS_FILE = '.review/learning-goals.json'

    def __init__(self):
        """Initialize goals manager"""
        self.goals_path = Path(self.GOALS_FILE)
        self.goals_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing goals or create default
        if self.goals_path.exists():
            with open(self.goals_path, 'r', encoding='utf-8') as f:
                self.goals = json.load(f)
        else:
            self.goals = {
                'primary': 'mastery',
                'secondary': None,
                'tertiary': None,
                'lastUpdated': datetime.now().isoformat(),
                'history': []
            }
            self._save()

    def _save(self):
        """Save goals to file"""
        with open(self.goals_path, 'w', encoding='utf-8') as f:
            json.dump(self.goals, f, indent=2)

    def set_primary_goal(self, goal: str) -> Dict:
        """
        Set primary learning goal

        Args:
            goal: Goal name (mastery, streak, breadth)

        Returns:
            Updated goals data
        """
        if goal not in self.VALID_GOALS:
            raise ValueError(
                f"Invalid goal: {goal}. "
                f"Must be one of: {', '.join(self.VALID_GOALS)}"
            )

        old_goal = self.goals['primary']

        # Update goals
        self.goals['primary'] = goal
        self.goals['lastUpdated'] = datetime.now().isoformat()

        # Add to history
        self.goals['history'].append({
            'from': old_goal,
            'to': goal,
            'timestamp': datetime.now().isoformat()
        })

        self._save()

        return self.goals

    def set_goals(
        self,
        primary: str,
        secondary: Optional[str] = None,
        tertiary: Optional[str] = None
    ) -> Dict:
        """
        Set all learning goals

        Args:
            primary: Primary goal
            secondary: Secondary goal (optional)
            tertiary: Tertiary goal (optional)

        Returns:
            Updated goals data
        """
        # Validate all goals
        for goal in [primary, secondary, tertiary]:
            if goal and goal not in self.VALID_GOALS:
                raise ValueError(
                    f"Invalid goal: {goal}. "
                    f"Must be one of: {', '.join(self.VALID_GOALS)}"
                )

        # Update goals
        self.goals['primary'] = primary
        self.goals['secondary'] = secondary
        self.goals['tertiary'] = tertiary
        self.goals['lastUpdated'] = datetime.now().isoformat()

        self._save()

        return self.goals

    def get_goals(self) -> Dict:
        """
        Get current goals

        Returns:
            Current goals data
        """
        return self.goals

    def get_primary_goal(self) -> str:
        """
        Get primary goal

        Returns:
            Primary goal name
        """
        return self.goals['primary']

    def describe_goal(self, goal: str) -> str:
        """
        Get description of a goal

        Args:
            goal: Goal name

        Returns:
            Goal description
        """
        descriptions = {
            'mastery': (
                "Mastery Focus: Deep understanding and high retention. "
                "Recommendations prioritize reviewing weak concepts, "
                "maintaining high retention scores, and building domain expertise."
            ),
            'streak': (
                "Streak Focus: Daily consistency and momentum. "
                "Recommendations prioritize maintaining daily activity, "
                "quick reviews to sustain streaks, and building learning habits."
            ),
            'breadth': (
                "Breadth Focus: Exploring diverse topics and domains. "
                "Recommendations prioritize learning new concepts, "
                "exploring different domains, and building broad knowledge base."
            )
        }
        return descriptions.get(goal, "Unknown goal")


def main():
    """CLI entry point for goals management"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description='Manage learning goals',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set primary goal
  python scripts/manage_learning_goals.py --set mastery

  # View current goals
  python scripts/manage_learning_goals.py --get

  # Set all goals
  python scripts/manage_learning_goals.py --set mastery --secondary streak

  # Describe a goal
  python scripts/manage_learning_goals.py --describe breadth
        """
    )

    parser.add_argument(
        '--set',
        type=str,
        choices=['mastery', 'streak', 'breadth'],
        help='Set primary learning goal'
    )
    parser.add_argument(
        '--secondary',
        type=str,
        choices=['mastery', 'streak', 'breadth'],
        help='Set secondary learning goal'
    )
    parser.add_argument(
        '--tertiary',
        type=str,
        choices=['mastery', 'streak', 'breadth'],
        help='Set tertiary learning goal'
    )
    parser.add_argument(
        '--get',
        action='store_true',
        help='Display current goals'
    )
    parser.add_argument(
        '--describe',
        type=str,
        choices=['mastery', 'streak', 'breadth'],
        help='Describe a goal'
    )

    args = parser.parse_args()

    try:
        manager = GoalsManager()

        if args.describe:
            print(f"\n{args.describe.upper()} GOAL\n")
            print(manager.describe_goal(args.describe))
            print()
        elif args.set:
            # Set goals
            goals = manager.set_goals(
                args.set,
                args.secondary,
                args.tertiary
            )
            print(f"✓ Learning goals updated")
            print(f"  Primary: {goals['primary']}")
            if goals.get('secondary'):
                print(f"  Secondary: {goals['secondary']}")
            if goals.get('tertiary'):
                print(f"  Tertiary: {goals['tertiary']}")
        elif args.get:
            # Get current goals
            goals = manager.get_goals()
            print(f"\nCURRENT LEARNING GOALS\n")
            print(f"Primary: {goals['primary']}")
            if goals.get('secondary'):
                print(f"Secondary: {goals['secondary']}")
            if goals.get('tertiary'):
                print(f"Tertiary: {goals['tertiary']}")
            print(f"\nLast updated: {goals['lastUpdated']}")
            print()
            print(manager.describe_goal(goals['primary']))
            print()
        else:
            parser.print_help()

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
