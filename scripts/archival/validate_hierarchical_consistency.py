"""
Hierarchical Consistency Validator Library
==========================================
Functions for validating typed relations don't create hierarchical contradictions.

This is a library module used by workflow_orchestrator.py.
Not intended for standalone use.

Created: 2025-12-05
Purpose: Prevent hierarchical contradictions in knowledge graph
"""

import json
import sys
from typing import List, Dict, Tuple, Set
from collections import defaultdict

# Import relation types from central configuration
from relation_types import ASYMMETRIC_TYPES, SYMMETRIC_TYPES


class ContradictionError:
    """Represents a hierarchical contradiction"""

    def __init__(self, from_rem: str, to_rem: str, rel_type: str,
                 issue: str, severity: str = 'critical'):
        self.from_rem = from_rem
        self.to_rem = to_rem
        self.rel_type = rel_type
        self.issue = issue
        self.severity = severity

    def __repr__(self):
        return f"ContradictionError({self.from_rem} --[{self.rel_type}]--> {self.to_rem}: {self.issue})"

    def to_dict(self):
        return {
            'type': 'hierarchical_contradiction',
            'from': self.from_rem,
            'to': self.to_rem,
            'rel_type': self.rel_type,
            'issue': self.issue,
            'severity': self.severity
        }


def load_json(file_path: str) -> dict:
    """Load JSON file with error handling - raises exceptions for caller to handle"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_relation_map(backlinks: dict) -> Dict[Tuple[str, str, str], bool]:
    """
    Build a map of existing relations for quick lookup.

    Returns: {(from_rem, to_rem, rel_type): True}
    """
    relation_map = {}

    for rem_id, data in backlinks.get('links', {}).items():
        for link in data.get('typed_links_to', []):
            key = (rem_id, link['to'], link['type'])
            relation_map[key] = True

    return relation_map


def validate_proposed_relations(
    enriched_rems: List[dict],
    existing_relations: Dict[Tuple[str, str, str], bool]
) -> Tuple[bool, List[ContradictionError]]:
    """
    Validate proposed relations in enriched_rems against existing backlinks.

    Returns: (is_valid, list_of_errors)
    """
    errors = []
    proposed_relations = defaultdict(list)

    # Collect all proposed relations
    for rem in enriched_rems:
        rem_id = rem.get('rem_id')
        for rel in rem.get('typed_relations', []):
            to_rem = rel['to']
            rel_type = rel['type']
            proposed_relations[rem_id].append((to_rem, rel_type))

    # Check each proposed relation
    for rem_id, relations in proposed_relations.items():
        for to_rem, rel_type in relations:

            # Skip symmetric types (they're allowed to be bidirectional)
            if rel_type in SYMMETRIC_TYPES:
                continue

            # Check if this is an asymmetric type
            if rel_type not in ASYMMETRIC_TYPES:
                continue

            # Check for reverse relation in PROPOSED relations
            # Look for (to_rem, rel_type) in proposed_relations[to_rem]
            if to_rem in proposed_relations:
                for reverse_to, reverse_type in proposed_relations[to_rem]:
                    if reverse_to == rem_id and reverse_type == rel_type:
                        errors.append(ContradictionError(
                            from_rem=rem_id,
                            to_rem=to_rem,
                            rel_type=rel_type,
                            issue=f"Bidirectional {rel_type} detected in proposed relations"
                        ))
                        break
                if errors and errors[-1].from_rem == rem_id:
                    continue

            # Check for reverse relation in EXISTING backlinks
            if (to_rem, rem_id, rel_type) in existing_relations:
                errors.append(ContradictionError(
                    from_rem=rem_id,
                    to_rem=to_rem,
                    rel_type=rel_type,
                    issue=f"Would create bidirectional {rel_type} (reverse already exists in backlinks)"
                ))

    return (len(errors) == 0, errors)


def detect_cycles(enriched_rems: List[dict]) -> List[List[str]]:
    """
    Detect cycles in prerequisite_of relations using DFS.

    Returns: List of cycles (each cycle is a list of rem_ids)
    """
    # Build graph of prerequisite relations
    graph = defaultdict(list)
    for rem in enriched_rems:
        rem_id = rem.get('rem_id')
        for rel in rem.get('typed_relations', []):
            if rel['type'] == 'prerequisite_of':
                # prerequisite_of: A -> B means "A is prerequisite for B"
                # So B depends on A, creating edge B <- A
                graph[rel['to']].append(rem_id)

    # DFS cycle detection
    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:])
                return True

        path.pop()
        rec_stack.remove(node)
        return False

    for rem in enriched_rems:
        rem_id = rem.get('rem_id')
        if rem_id not in visited:
            dfs(rem_id)

    return cycles


def print_validation_report(errors: List[ContradictionError], cycles: List[List[str]]):
    """Print a detailed validation report"""

    print("\n" + "=" * 80)
    print("HIERARCHICAL CONSISTENCY VALIDATION REPORT")
    print("=" * 80)

    if not errors and not cycles:
        print("\n✅ VALIDATION PASSED: No hierarchical contradictions detected")
        print("\n" + "=" * 80)
        return

    print(f"\n❌ VALIDATION FAILED: {len(errors)} contradictions detected")

    if errors:
        print("\n" + "-" * 80)
        print("CONTRADICTIONS BY TYPE")
        print("-" * 80)

        by_type = defaultdict(list)
        for error in errors:
            by_type[error.rel_type].append(error)

        for rel_type, type_errors in sorted(by_type.items()):
            print(f"\n{rel_type.upper()}: {len(type_errors)} contradictions")
            for i, error in enumerate(type_errors, 1):
                print(f"  {i}. {error.from_rem} ⟷ {error.to_rem}")
                print(f"     Issue: {error.issue}")

    if cycles:
        print("\n" + "-" * 80)
        print(f"PREREQUISITE CYCLES: {len(cycles)} detected")
        print("-" * 80)

        for i, cycle in enumerate(cycles, 1):
            print(f"\n  Cycle {i}: {' → '.join(cycle + [cycle[0]])}")

    print("\n" + "-" * 80)
    print("RECOMMENDED ACTIONS")
    print("-" * 80)
    print("""
1. Review each contradiction and determine correct direction
2. For prerequisite cycles, identify which concept is more fundamental
3. If bidirectional needed, use symmetric types (related_to, contrasts_with)
4. Update enriched_rems.json to remove problematic relations
5. Re-run validation to confirm fixes
    """)

    print("=" * 80)


# This module is a library for workflow_orchestrator.py
# Not intended for standalone CLI use - functions are imported and used directly
