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
from relation_types import ASYMMETRIC_TYPES, SYMMETRIC_TYPES, PAIRED_TYPES


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
    Validate proposed relations against existing backlinks.

    Checks for:
    1. Same-type bidirectional (A→B type X, B→A type X) - WRONG for asymmetric
    2. Duplicate paired types (A→B prerequisite_of, A→B depends_on) - WRONG
    3. Wrong paired type (A→B prerequisite_of, B→A extends) - WRONG
    4. Bidirectional asymmetric in existing backlinks

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

            # Skip symmetric types (they SHOULD be bidirectional)
            if rel_type in SYMMETRIC_TYPES:
                continue

            # Check if NOT a known relation type
            if rel_type not in ASYMMETRIC_TYPES and rel_type not in SYMMETRIC_TYPES:
                errors.append(ContradictionError(
                    from_rem=rem_id,
                    to_rem=to_rem,
                    rel_type=rel_type,
                    issue=f"Unknown relation type '{rel_type}' (not in ASYMMETRIC_TYPES or SYMMETRIC_TYPES)",
                    severity='warning'
                ))
                continue

            # Check for reverse relation in PROPOSED relations
            if to_rem in proposed_relations:
                for reverse_to, reverse_type in proposed_relations[to_rem]:
                    if reverse_to == rem_id:
                        # Found reverse relation from target back to source

                        # CASE 1: Same-type bidirectional (ALWAYS WRONG for asymmetric)
                        if reverse_type == rel_type:
                            paired_type = PAIRED_TYPES.get(rel_type, None)
                            errors.append(ContradictionError(
                                from_rem=rem_id,
                                to_rem=to_rem,
                                rel_type=rel_type,
                                issue=f"Same-type bidirectional '{rel_type}' detected. " +
                                      (f"Should use paired type '{paired_type}' for reverse." if paired_type else "Asymmetric relations cannot be bidirectional with same type."),
                                severity='critical'
                            ))
                            continue  # Skip further checks for this relation

                        # CASE 2: Check if reverse is correct paired type
                        if rel_type in PAIRED_TYPES:
                            expected_reverse = PAIRED_TYPES[rel_type]

                            if reverse_type != expected_reverse:
                                errors.append(ContradictionError(
                                    from_rem=rem_id,
                                    to_rem=to_rem,
                                    rel_type=rel_type,
                                    issue=f"Wrong reverse type: expected '{expected_reverse}', got '{reverse_type}'",
                                    severity='critical'
                                ))

            # CASE 3: Check for reverse relation in EXISTING backlinks
            if (to_rem, rem_id, rel_type) in existing_relations:
                # Existing backlinks has B→A with same type
                paired_type = PAIRED_TYPES.get(rel_type, None)
                errors.append(ContradictionError(
                    from_rem=rem_id,
                    to_rem=to_rem,
                    rel_type=rel_type,
                    issue=f"Would create same-type bidirectional '{rel_type}' (reverse already exists in backlinks). " +
                          (f"Use paired type '{paired_type}' instead." if paired_type else ""),
                    severity='critical'
                ))

            # CASE 4: Check for PAIRED reverse in existing backlinks (informational)
            if rel_type in PAIRED_TYPES:
                expected_reverse = PAIRED_TYPES[rel_type]
                # Check if reverse exists (this is OK, just FYI)
                if (to_rem, rem_id, expected_reverse) in existing_relations:
                    # This is fine - correct paired relation exists
                    pass

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
    """Print a detailed validation report with severity levels."""

    print("\n" + "=" * 80)
    print("HIERARCHICAL CONSISTENCY VALIDATION REPORT")
    print("=" * 80)

    if not errors and not cycles:
        print("\n✅ VALIDATION PASSED: No hierarchical contradictions detected")
        print("\n" + "=" * 80)
        return

    # Count by severity
    critical = [e for e in errors if e.severity == 'critical']
    warnings = [e for e in errors if e.severity == 'warning']

    print(f"\n❌ VALIDATION FAILED:")
    print(f"   🔴 {len(critical)} critical errors")
    print(f"   ⚠️  {len(warnings)} warnings")

    if critical:
        print("\n" + "-" * 80)
        print("🔴 CRITICAL ERRORS (must fix)")
        print("-" * 80)

        # Group by issue type
        same_type = [e for e in critical if 'Same-type bidirectional' in e.issue]
        wrong_type = [e for e in critical if 'Wrong reverse type' in e.issue]
        backlink_conflict = [e for e in critical if 'already exists in backlinks' in e.issue]

        if same_type:
            print(f"\n  Same-Type Bidirectional ({len(same_type)}):")
            for i, error in enumerate(same_type[:5], 1):
                print(f"    {i}. {error.from_rem} ⟷ {error.to_rem} (both '{error.rel_type}')")
                print(f"       {error.issue}")
            if len(same_type) > 5:
                print(f"    ... and {len(same_type) - 5} more")

        if wrong_type:
            print(f"\n  Wrong Reverse Type ({len(wrong_type)}):")
            for i, error in enumerate(wrong_type[:5], 1):
                print(f"    {i}. {error.from_rem} → {error.to_rem}")
                print(f"       Issue: {error.issue}")
            if len(wrong_type) > 5:
                print(f"    ... and {len(wrong_type) - 5} more")

        if backlink_conflict:
            print(f"\n  Conflicts with Existing Backlinks ({len(backlink_conflict)}):")
            for i, error in enumerate(backlink_conflict[:5], 1):
                print(f"    {i}. {error.from_rem} → {error.to_rem}")
                print(f"       Issue: {error.issue}")
            if len(backlink_conflict) > 5:
                print(f"    ... and {len(backlink_conflict) - 5} more")

    if warnings:
        print("\n" + "-" * 80)
        print("⚠️  WARNINGS (should review)")
        print("-" * 80)
        for i, error in enumerate(warnings[:10], 1):
            print(f"  {i}. {error.from_rem} → {error.to_rem} ({error.rel_type})")
            print(f"     {error.issue}")

    if cycles:
        print("\n" + "-" * 80)
        print(f"🔄 PREREQUISITE CYCLES: {len(cycles)} detected")
        print("-" * 80)
        for i, cycle in enumerate(cycles, 1):
            print(f"\n  Cycle {i}: {' → '.join(cycle + [cycle[0]])}")

    print("\n" + "-" * 80)
    print("RECOMMENDED ACTIONS")
    print("-" * 80)
    print("""
1. Fix same-type bidirectional: Change one to paired type
   Example: If A→B 'used_in' and B→A 'used_in', change one to 'uses'

2. Fix wrong reverse types: Update to correct paired type
   Example: If A→B 'prerequisite_of', reverse should be 'depends_on'

3. For backlink conflicts: Check existing relations, avoid duplicates

4. For cycles: Identify which concept is more fundamental

5. If truly bidirectional needed: Use symmetric types
   (related_to, contrasts_with, complements, analogous_to)
    """)

    print("=" * 80)


# This module is a library for workflow_orchestrator.py
# Not intended for standalone CLI use - functions are imported and used directly
