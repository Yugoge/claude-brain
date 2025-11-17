#!/usr/bin/env python3
"""
Taxonomy Validation Script

Validates knowledge-base/.taxonomy.json structure and content.

Usage:
    python3 scripts/validate-taxonomy.py

Exit codes:
    0 - Validation passed
    1 - Validation failed
"""

import json
import sys
import re
from pathlib import Path


def validate_taxonomy():
    """Validate taxonomy file structure and content."""
    taxonomy_file = Path('knowledge-base/.taxonomy.json')

    # Check file exists
    if not taxonomy_file.exists():
        print("❌ Error: knowledge-base/.taxonomy.json not found")
        return False

    # Load and parse JSON
    try:
        with open(taxonomy_file) as f:
            taxonomy = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON - {e}")
        return False

    # Required fields
    required_fields = ['version', 'isced_mappings', 'dewey_mappings']
    for field in required_fields:
        if field not in taxonomy:
            print(f"❌ Error: Missing required field '{field}'")
            return False

    # Version format (semver)
    if not re.match(r'^\d+\.\d+\.\d+$', taxonomy['version']):
        print(f"❌ Error: Invalid version format (must be semver: X.Y.Z)")
        return False

    # Check mappings structure
    for domain, codes in taxonomy['isced_mappings'].items():
        if not isinstance(codes, list):
            print(f"❌ Error: isced_mappings['{domain}'] must be array")
            return False
        if not all(isinstance(code, str) for code in codes):
            print(f"❌ Error: All codes in isced_mappings['{domain}'] must be strings")
            return False

    for domain, codes in taxonomy['dewey_mappings'].items():
        if not isinstance(codes, list):
            print(f"❌ Error: dewey_mappings['{domain}'] must be array")
            return False
        if not all(isinstance(code, str) for code in codes):
            print(f"❌ Error: All codes in dewey_mappings['{domain}'] must be strings")
            return False

    # Check domain consistency (all domains should be in both mappings)
    isced_domains = set(taxonomy['isced_mappings'].keys())
    dewey_domains = set(taxonomy['dewey_mappings'].keys())

    if isced_domains != dewey_domains:
        missing_from_dewey = isced_domains - dewey_domains
        missing_from_isced = dewey_domains - isced_domains

        if missing_from_dewey:
            print(f"⚠️  Warning: Domains in ISCED but not Dewey: {missing_from_dewey}")
        if missing_from_isced:
            print(f"⚠️  Warning: Domains in Dewey but not ISCED: {missing_from_isced}")

    # Check for duplicate domain names
    if len(isced_domains) != len(taxonomy['isced_mappings']):
        print("❌ Error: Duplicate domain names detected in isced_mappings")
        return False

    if len(dewey_domains) != len(taxonomy['dewey_mappings']):
        print("❌ Error: Duplicate domain names detected in dewey_mappings")
        return False

    print("✅ Taxonomy validation passed")
    print(f"   Version: {taxonomy['version']}")
    print(f"   Domains: {', '.join(sorted(isced_domains))}")
    print(f"   ISCED codes: {sum(len(codes) for codes in taxonomy['isced_mappings'].values())} total")
    print(f"   Dewey codes: {sum(len(codes) for codes in taxonomy['dewey_mappings'].values())} total")

    # Optional: Check if domain_descriptions exist
    if 'domain_descriptions' in taxonomy:
        desc_domains = set(taxonomy['domain_descriptions'].keys())
        if desc_domains != isced_domains:
            print(f"   ⚠️  Note: domain_descriptions doesn't match all domains")

    return True


if __name__ == '__main__':
    success = validate_taxonomy()
    sys.exit(0 if success else 1)
