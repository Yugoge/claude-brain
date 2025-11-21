#!/usr/bin/env python3
"""
Analyze Rems format issues to identify patterns.

Groups issues by type and provides detailed breakdown.
"""

import re
import sys
from pathlib import Path
from collections import defaultdict

def parse_yaml_frontmatter(content: str):
    """Extract YAML frontmatter."""
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not match:
        return {}, content

    yaml_text = match.group(1)
    body = match.group(2)

    yaml_dict = {}
    for line in yaml_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            yaml_dict[key.strip()] = value.strip()

    return yaml_dict, body

def analyze_rem(file_path: Path):
    """Analyze a single Rem file for issues."""
    issues = []

    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return ["Cannot read file"]

    # Check YAML frontmatter
    yaml_data, body = parse_yaml_frontmatter(content)

    if not yaml_data:
        issues.append("missing_yaml")
        return issues

    # Check for missing required fields
    required_fields = ['rem_id', 'subdomain', 'isced', 'created', 'source']
    for field in required_fields:
        if field not in yaml_data:
            issues.append(f"missing_field:{field}")

    # Check for Conversation Source section
    has_source_section = ('## Conversation Source' in content or
                          '## Source Conversation' in content)

    if not has_source_section:
        issues.append("missing_source_section")
    else:
        # Check for hyperlink
        source_match = re.search(
            r'## (?:Conversation Source|Source Conversation)\s+(.*?)(?:\n##|\Z)',
            content,
            re.DOTALL
        )
        if source_match:
            source_text = source_match.group(1)
            if not re.search(r'\[.*?\]\(.*?\.md\)', source_text):
                issues.append("missing_source_hyperlink")

    return issues

def main():
    root = Path("/home/user/knowledge-system")

    # Get all Rem files
    rem_files = list(root.glob("knowledge-base/**/*.md"))

    # Group issues by type
    issues_by_type = defaultdict(list)
    all_issues = {}

    for rem_file in rem_files:
        issues = analyze_rem(rem_file)
        if issues:
            all_issues[rem_file] = issues
            for issue in issues:
                issues_by_type[issue].append(rem_file)

    print("=" * 70)
    print("REMS FORMAT ISSUE ANALYSIS")
    print("=" * 70)
    print(f"\nTotal Rems: {len(rem_files)}")
    print(f"Rems with issues: {len(all_issues)}")
    print(f"Issue-free Rems: {len(rem_files) - len(all_issues)}")

    print("\n" + "=" * 70)
    print("ISSUE BREAKDOWN BY TYPE")
    print("=" * 70)

    for issue_type, files in sorted(issues_by_type.items(),
                                    key=lambda x: len(x[1]),
                                    reverse=True):
        print(f"\n{issue_type}: {len(files)} files")
        for f in files[:5]:  # Show first 5
            rel_path = f.relative_to(root)
            print(f"  - {rel_path}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")

    # Pattern analysis
    print("\n" + "=" * 70)
    print("PATTERN ANALYSIS")
    print("=" * 70)

    # Check if index files are causing issues
    index_files = [f for f in all_issues if 'index.md' in f.name.lower()]
    print(f"\nIndex files with issues: {len(index_files)}")

    # Check by domain
    domain_issues = defaultdict(int)
    for f in all_issues:
        parts = f.relative_to(root / "knowledge-base").parts
        if parts:
            domain = parts[0]
            domain_issues[domain] += 1

    print("\nIssues by domain:")
    for domain, count in sorted(domain_issues.items(),
                                key=lambda x: x[1],
                                reverse=True):
        print(f"  {domain}: {count} files")

    return 0

if __name__ == '__main__':
    sys.exit(main())
