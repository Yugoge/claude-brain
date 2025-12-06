#!/usr/bin/env python3
"""Check bidirectional link issues in chunks 04, 05, and 06."""

import json
from pathlib import Path
import sys

# Add scripts to path for imports
sys.path.append('/root/knowledge-system/scripts')

# Symmetric relations that MUST have reverse links
SYMMETRIC_RELATIONS = {'related_to', 'contrasts_with', 'complements', 'analogous_to'}

# Asymmetric relations and their required reverses
ASYMMETRIC_REVERSE_MAP = {
    'example_of': 'has_example',
    'used_in': 'uses',
    'implements': 'implemented_by',
    'requires': 'required_by',
    'enables': 'enabled_by',
    'applied_in': 'applies',
    'component_of': 'has_component',
    'measured_by': 'measures',
    'modeled_using': 'models',
    'triggered_by': 'triggers',
    'has_example': 'example_of',
    'uses': 'used_in',
    'implemented_by': 'implements',
    'required_by': 'requires',
    'enabled_by': 'enables',
    'applies': 'applied_in',
    'has_component': 'component_of',
    'measures': 'measured_by',
    'models': 'modeled_using',
    'triggers': 'triggered_by'
}

def find_rem_file(rem_id):
    """Find the actual path of a rem file."""
    base_path = Path('/root/knowledge-system/knowledge-base')

    # Search for the file
    for path in base_path.rglob(f'*{rem_id}.md'):
        if path.is_file():
            return path
    return None

def extract_relations_from_rem(rem_path):
    """Extract all relations from a rem file."""
    if not rem_path or not rem_path.exists():
        return {}

    content = rem_path.read_text()
    relations = {}

    # Extract from YAML front matter
    if content.startswith('---'):
        yaml_end = content.find('---', 3)
        if yaml_end > 0:
            yaml_section = content[3:yaml_end]
            for line in yaml_section.split('\n'):
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key = line.split(':', 1)[0].strip()
                    value = line.split(':', 1)[1].strip()

                    # Check if this is a relation field
                    if key in SYMMETRIC_RELATIONS or key in ASYMMETRIC_REVERSE_MAP:
                        # Parse the value (could be a list)
                        if value.startswith('[') and value.endswith(']'):
                            # It's a list
                            value = value[1:-1]  # Remove brackets
                            if value:
                                targets = [t.strip().strip('"').strip("'") for t in value.split(',')]
                                relations[key] = targets
                        elif value and value != '[]' and value != 'null':
                            # Single value
                            relations[key] = [value.strip('"').strip("'")]

    return relations

def check_reverse_link(source_rem, target_rem_id, expected_relation):
    """Check if target rem has the expected reverse link back to source."""
    target_path = find_rem_file(target_rem_id)
    if not target_path:
        return False, f"Target rem '{target_rem_id}' not found"

    target_relations = extract_relations_from_rem(target_path)

    # Check if the expected relation exists and points back to source
    if expected_relation in target_relations:
        targets = target_relations[expected_relation]
        # Extract just the rem ID from source path
        source_id = source_rem.stem.split('-', 1)[-1] if '-' in source_rem.stem else source_rem.stem

        # Check if source is in targets (handle various formats)
        for target in targets:
            if source_id in target or source_rem.stem in target:
                return True, "OK"

    return False, f"Missing reverse link: '{expected_relation}' pointing back to '{source_rem.stem}'"

def analyze_chunks():
    """Analyze chunks 04, 05, and 06 for bidirectional link issues."""

    # Read chunk definitions
    chunks = {}
    for chunk_num in [4, 5, 6]:
        chunk_file = Path(f'/tmp/rem_chunks/chunk_{chunk_num:02d}.json')
        if chunk_file.exists():
            with open(chunk_file) as f:
                data = json.load(f)
                chunks[chunk_num] = data['rems']

    all_issues = []

    for chunk_num, rem_ids in chunks.items():
        print(f"\n{'='*60}")
        print(f"CHUNK {chunk_num:02d} ANALYSIS")
        print('='*60)

        for rem_id in rem_ids:
            rem_path = find_rem_file(rem_id)
            if not rem_path:
                print(f"\n❌ {rem_id}: FILE NOT FOUND")
                continue

            relations = extract_relations_from_rem(rem_path)
            if not relations:
                continue

            issues = []

            # Check each relation
            for rel_type, targets in relations.items():
                for target in targets:
                    # Clean up target ID
                    target_id = target.strip()

                    if rel_type in SYMMETRIC_RELATIONS:
                        # Symmetric relation - must have same relation back
                        has_reverse, msg = check_reverse_link(rem_path, target_id, rel_type)
                        if not has_reverse:
                            issue = f"  - SYMMETRIC: {rel_type} → {target_id} (missing reverse {rel_type})"
                            issues.append(issue)
                            all_issues.append({
                                'chunk': chunk_num,
                                'source': rem_id,
                                'target': target_id,
                                'relation': rel_type,
                                'type': 'symmetric',
                                'missing': rel_type
                            })

                    elif rel_type in ASYMMETRIC_REVERSE_MAP:
                        # Asymmetric relation - must have specific reverse
                        reverse_rel = ASYMMETRIC_REVERSE_MAP[rel_type]
                        has_reverse, msg = check_reverse_link(rem_path, target_id, reverse_rel)
                        if not has_reverse:
                            issue = f"  - ASYMMETRIC: {rel_type} → {target_id} (missing reverse {reverse_rel})"
                            issues.append(issue)
                            all_issues.append({
                                'chunk': chunk_num,
                                'source': rem_id,
                                'target': target_id,
                                'relation': rel_type,
                                'type': 'asymmetric',
                                'missing': reverse_rel
                            })

            if issues:
                print(f"\n❌ {rem_id}:")
                for issue in issues:
                    print(issue)
            else:
                if relations:
                    print(f"\n✅ {rem_id}: All bidirectional links OK ({len(relations)} relations)")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY OF ALL ISSUES")
    print('='*60)

    if all_issues:
        print(f"\nTotal issues found: {len(all_issues)}")

        # Group by type
        symmetric_issues = [i for i in all_issues if i['type'] == 'symmetric']
        asymmetric_issues = [i for i in all_issues if i['type'] == 'asymmetric']

        print(f"\nSymmetric relation issues: {len(symmetric_issues)}")
        for issue in symmetric_issues:
            print(f"  - Chunk {issue['chunk']}: {issue['source']} --[{issue['relation']}]--> {issue['target']}")
            print(f"    Missing reverse: {issue['target']} --[{issue['missing']}]--> {issue['source']}")

        print(f"\nAsymmetric relation issues: {len(asymmetric_issues)}")
        for issue in asymmetric_issues:
            print(f"  - Chunk {issue['chunk']}: {issue['source']} --[{issue['relation']}]--> {issue['target']}")
            print(f"    Missing reverse: {issue['target']} --[{issue['missing']}]--> {issue['source']}")
    else:
        print("\n✅ No bidirectional link issues found in chunks 04, 05, and 06!")

    return all_issues

if __name__ == "__main__":
    issues = analyze_chunks()

    # Exit with error code if issues found
    sys.exit(1 if issues else 0)