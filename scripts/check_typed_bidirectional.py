#!/usr/bin/env python3
"""Check bidirectional link issues in chunks 04, 05, and 06 using backlinks.json."""

import json
from pathlib import Path
import sys

# Symmetric relations that MUST have reverse links
SYMMETRIC_RELATIONS = {'related_to', 'contrasts_with', 'complements', 'analogous_to'}

# Asymmetric relations and their required reverses
ASYMMETRIC_REVERSE_MAP = {
    'example_of': 'has_example',
    'used_in': 'uses',
    'used_by': 'uses',
    'uses': 'used_by',
    'implements': 'implemented_by',
    'implemented_by': 'implements',
    'requires': 'required_by',
    'required_by': 'requires',
    'prerequisite_of': 'has_prerequisite',
    'has_prerequisite': 'prerequisite_of',
    'enables': 'enabled_by',
    'enabled_by': 'enables',
    'applied_in': 'applies',
    'applies': 'applied_in',
    'component_of': 'has_component',
    'has_component': 'component_of',
    'measured_by': 'measures',
    'measures': 'measured_by',
    'modeled_using': 'models',
    'models': 'modeled_using',
    'triggered_by': 'triggers',
    'triggers': 'triggered_by',
    'defines': 'defined_by',
    'defined_by': 'defines',
    'has_example': 'example_of'
}

def check_bidirectional_links():
    """Check for bidirectional link issues in chunks 04-06."""

    # Load backlinks index
    backlinks_path = Path('knowledge-base/_index/backlinks.json')
    if not backlinks_path.exists():
        print("ERROR: backlinks.json not found!")
        return []

    with open(backlinks_path) as f:
        backlinks_data = json.load(f)

    links = backlinks_data.get('links', {})

    # Get rems from chunks
    all_rems = []
    chunk_mapping = {}  # Track which chunk each rem belongs to

    for chunk_num in [4, 5, 6]:
        chunk_file = Path(f'/tmp/rem_chunks/chunk_{chunk_num:02d}.json')
        if chunk_file.exists():
            with open(chunk_file) as f:
                data = json.load(f)
                for rem in data['rems']:
                    all_rems.append(rem)
                    chunk_mapping[rem] = chunk_num

    print(f"Analyzing {len(all_rems)} rems from chunks 04-06...")
    print("="*60)

    all_issues = []

    for rem_id in all_rems:
        if rem_id not in links:
            continue

        rem_data = links[rem_id]
        chunk_num = chunk_mapping[rem_id]
        issues = []

        # Check typed_links_to (outgoing relations)
        typed_links = rem_data.get('typed_links_to', [])

        for link in typed_links:
            target_id = link.get('to')
            rel_type = link.get('type')

            if not target_id or not rel_type:
                continue

            # Check if target exists in links
            if target_id not in links:
                issues.append(f"  - Target '{target_id}' not found in index")
                continue

            target_data = links[target_id]
            target_incoming = target_data.get('typed_linked_from', [])

            if rel_type in SYMMETRIC_RELATIONS:
                # For symmetric relations, check if target has same relation back
                has_reverse = any(
                    inc.get('from') == rem_id and inc.get('type') == rel_type
                    for inc in target_incoming
                )

                if not has_reverse:
                    issue = {
                        'chunk': chunk_num,
                        'source': rem_id,
                        'target': target_id,
                        'relation': rel_type,
                        'type': 'symmetric',
                        'missing': f"{target_id} --[{rel_type}]--> {rem_id}"
                    }
                    issues.append(f"  - SYMMETRIC: {rel_type} → {target_id} (missing reverse {rel_type})")
                    all_issues.append(issue)

            elif rel_type in ASYMMETRIC_REVERSE_MAP:
                # For asymmetric relations, check if target has proper reverse
                expected_reverse = ASYMMETRIC_REVERSE_MAP[rel_type]

                has_reverse = any(
                    inc.get('from') == rem_id and inc.get('type') == expected_reverse
                    for inc in target_incoming
                )

                if not has_reverse:
                    # Also check if target has the relation in typed_links_to
                    target_outgoing = target_data.get('typed_links_to', [])
                    has_outgoing_reverse = any(
                        out.get('to') == rem_id and out.get('type') == expected_reverse
                        for out in target_outgoing
                    )

                    if not has_outgoing_reverse:
                        issue = {
                            'chunk': chunk_num,
                            'source': rem_id,
                            'target': target_id,
                            'relation': rel_type,
                            'type': 'asymmetric',
                            'missing': f"{target_id} --[{expected_reverse}]--> {rem_id}"
                        }
                        issues.append(f"  - ASYMMETRIC: {rel_type} → {target_id} (missing reverse {expected_reverse})")
                        all_issues.append(issue)

        if issues:
            print(f"\n❌ Chunk {chunk_num}: {rem_id}")
            for issue in issues:
                print(issue)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY OF ALL BIDIRECTIONAL LINK ISSUES")
    print("="*60)

    if all_issues:
        print(f"\nTotal issues found: {len(all_issues)}")

        # Group by type
        symmetric_issues = [i for i in all_issues if i['type'] == 'symmetric']
        asymmetric_issues = [i for i in all_issues if i['type'] == 'asymmetric']

        if symmetric_issues:
            print(f"\n✗ SYMMETRIC RELATION ISSUES ({len(symmetric_issues)}):")
            for issue in symmetric_issues:
                print(f"  Chunk {issue['chunk']}: {issue['source']} --[{issue['relation']}]--> {issue['target']}")
                print(f"    MISSING: {issue['missing']}")

        if asymmetric_issues:
            print(f"\n✗ ASYMMETRIC RELATION ISSUES ({len(asymmetric_issues)}):")
            for issue in asymmetric_issues:
                print(f"  Chunk {issue['chunk']}: {issue['source']} --[{issue['relation']}]--> {issue['target']}")
                print(f"    MISSING: {issue['missing']}")
    else:
        print("\n✅ No bidirectional link issues found in chunks 04, 05, and 06!")

    return all_issues

if __name__ == "__main__":
    issues = check_bidirectional_links()

    # Save issues to file for later processing
    if issues:
        with open('/tmp/bidirectional_issues.json', 'w') as f:
            json.dump(issues, f, indent=2)
        print(f"\n\nIssues saved to /tmp/bidirectional_issues.json")

    # Exit with error code if issues found
    sys.exit(1 if issues else 0)