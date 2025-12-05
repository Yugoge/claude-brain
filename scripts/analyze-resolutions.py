#!/usr/bin/env python3
import json
from collections import defaultdict

# Load backlinks
with open('knowledge-base/_index/backlinks.json') as f:
    data = json.load(f)

# Detect contradictions
contradictions = []
seen = set()

for rem_id, rem_data in data['links'].items():
    for link in rem_data.get('typed_links_to', []):
        to_id = link['to']
        rel_type = link['type']
        
        pair = tuple(sorted([rem_id, to_id]))
        key = (pair, rel_type)
        if key in seen:
            continue
            
        # Check reverse
        if to_id in data['links']:
            for rev_link in data['links'][to_id].get('typed_links_to', []):
                if rev_link['to'] == rem_id and rev_link['type'] == rel_type:
                    contradictions.append({
                        'a': rem_id,
                        'b': to_id,
                        'type': rel_type
                    })
                    seen.add(key)
                    break

# Categorize
strict_hierarchical = {'example_of', 'prerequisite_of', 'extends', 'specializes', 'generalizes'}
symmetric = {'contrasts_with', 'antonym', 'related_to', 'analogous_to', 'complements', 'derivationally_related'}
context = {'used_in', 'uses', 'used_by', 'member_of', 'applies_to', 'supported_by'}

by_category = defaultdict(list)

for c in contradictions:
    if c['type'] in strict_hierarchical:
        by_category['strict_hierarchical'].append(c)
    elif c['type'] in symmetric:
        by_category['symmetric'].append(c)
    elif c['type'] in context:
        by_category['context_dependent'].append(c)
    else:
        by_category['unknown'].append(c)

# Report
print("CONTRADICTION ANALYSIS")
print("=" * 60)
print(f"Total: {len(contradictions)} bidirectional contradictions")
print()

print("BY CATEGORY:")
print("-" * 40)
for cat, items in by_category.items():
    print(f"{cat}: {len(items)}")
    
    # Count by type
    by_type = defaultdict(int)
    for item in items:
        by_type[item['type']] += 1
    
    for t, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  - {t}: {count}")
print()

print("SAMPLE FIXES NEEDED:")
print("-" * 40)

# Show examples of strict hierarchical that need fixing
for c in by_category['strict_hierarchical'][:10]:
    a_info = data.get('concepts', {}).get(c['a'], {})
    b_info = data.get('concepts', {}).get(c['b'], {})
    
    print(f"\n{c['type'].upper()}:")
    print(f"  {a_info.get('title', c['a'])}")
    print(f"  ↔")
    print(f"  {b_info.get('title', c['b'])}")
    print(f"  IDs: {c['a']} ↔ {c['b']}")
    
    # Suggest fix
    if c['type'] == 'example_of':
        if 'etymology' in c['a']:
            print(f"  FIX: Remove {c['a']} → {c['b']}, keep {c['b']} → {c['a']}")
        elif 'etymology' in c['b']:
            print(f"  FIX: Remove {c['b']} → {c['a']}, keep {c['a']} → {c['b']}")
        elif 'vocabulary' in c['a'] or 'vocab' in c['a']:
            print(f"  FIX: Remove {c['b']} → {c['a']}, keep {c['a']} → {c['b']}")
        else:
            print(f"  FIX: Needs manual review")
