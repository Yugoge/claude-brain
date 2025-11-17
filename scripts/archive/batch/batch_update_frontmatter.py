#!/usr/bin/env python3
"""
Batch update conversation files with manual summary frontmatter and summary content.
Only updates substantive fields (id, title, domain, tags, rems_extracted, summary).
Preserves technical fields (agent, turns, archived_by, archived_at, date).
"""

import re
import sys
from pathlib import Path

# File mapping: conversation_file -> manual_summary_file
FILE_MAPPING = {
    # 2025-10 files
    "chats/2025-10/understanding-vix-delta-spx-vega-and-volatility-as-conversation-2025-10-27.md":
        "docs/archive/conversations-manual-summaries/2025-10/vix-spx-vega-conversation-2025-10-27.md",
    "chats/2025-10/c-learning-ba-s-first-c-sample-test-conversation-2025-10-28.md":
        "docs/archive/conversations-manual-summaries/2025-10/csharp-learning-ba-python-conversation-2025-10-28.md",
    "chats/2025-10/french-review-session-grammar-and-expressions-conversation-2025-10-28.md":
        "docs/archive/conversations-manual-summaries/2025-10/french-review-session-conversation-2025-10-28.md",
    "chats/2025-10/risk-scenario-perturbation-analysis-time-ladder-ex-conversation-2025-10-28.md":
        "docs/archive/conversations-manual-summaries/2025-10/risk-scenario-time-ladder-conversation-2025-10-28.md",
    "chats/2025-10/options-greeks-time-scenario-analysis-conversation-2025-10-29.md":
        "docs/archive/conversations-manual-summaries/2025-10/options-greeks-time-scenario-analysis-2025-10-29.md",
    "chats/2025-10/capital-market-pricing-paradigms-curve-vs-vol-deep-conversation-2025-10-30.md":
        "docs/archive/conversations-manual-summaries/2025-10/capital-market-pricing-paradigms-conversation-2025-10-30.md",
    "chats/2025-10/c-programming-review-session-conversation-2025-10-30.md":
        "docs/archive/conversations-manual-summaries/2025-10/csharp-review-early-exit-conversation-2025-10-30.md",
    "chats/2025-10/french-1453-vocab-20251030-conversation-2025-10-30.md":
        "docs/archive/conversations-manual-summaries/2025-10/french-1453-vocabulary-learning-2025-10-30.md",

    # 2025-11 files
    "chats/2025-11/desire-driven-growth-2025-11-02.md":
        "docs/archive/conversations-manual-summaries/2025-11/desire-driven-economic-growth-conversation-2025-11-02.md",
    "chats/2025-11/french-grammar-negation-with-article-changes-conversation-2025-11-03.md":
        "docs/archive/conversations-manual-summaries/2025-11/french-grammar-session-2025-11-03.md",
    "chats/2025-11/fx-forward-primary-depo-rate-and-interest-rate-par-conversation-2025-11-03.md":
        "docs/archive/conversations-manual-summaries/2025-11/fx-forward-primary-depo-rate-conversation-2025-11-03.md",
    "chats/2025-11/nds-fx-options-payment-currency-conventions-conversation-2025-11-03.md":
        "docs/archive/conversations-manual-summaries/2025-11/nds-fx-options-payment-currency-conversation-2025-11-03.md",
    "chats/2025-11/bloomberg-ovdv-black-scholes-deep-dive-volatility-conversation-2025-11-04.md":
        "docs/archive/conversations-manual-summaries/2025-11/bloomberg-ovdv-conversation-2025-11-04.md",
}

def extract_frontmatter(content):
    """Extract YAML frontmatter from markdown content."""
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if match:
        return match.group(0), match.group(1)
    return None, None

def parse_yaml_frontmatter(yaml_str):
    """Parse YAML frontmatter into dictionary."""
    result = {}
    for line in yaml_str.strip().split('\n'):
        if ': ' in line:
            key, value = line.split(': ', 1)
            result[key] = value
    return result

def extract_summary(content):
    """Extract Summary section content."""
    pattern = r'## Summary\n\n(.*?)(?=\n## |\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

def update_conversation_file(chat_file, manual_file, root_dir):
    """Update single conversation file with manual summary content."""
    chat_path = root_dir / chat_file
    manual_path = root_dir / manual_file

    if not chat_path.exists():
        print(f"❌ Chat file not found: {chat_file}")
        return False

    if not manual_path.exists():
        print(f"❌ Manual summary not found: {manual_file}")
        return False

    # Read files
    chat_content = chat_path.read_text(encoding='utf-8')
    manual_content = manual_path.read_text(encoding='utf-8')

    # Extract manual summary data
    _, manual_yaml_str = extract_frontmatter(manual_content)
    if not manual_yaml_str:
        print(f"❌ No frontmatter in manual summary: {manual_file}")
        return False

    manual_yaml = parse_yaml_frontmatter(manual_yaml_str)
    manual_summary = extract_summary(manual_content)

    if not manual_summary:
        print(f"⚠️  No summary found in: {manual_file}")
        manual_summary = "*(Summary not available)*"

    # Extract current chat data
    chat_frontmatter_str, chat_yaml_str = extract_frontmatter(chat_content)
    if not chat_yaml_str:
        print(f"❌ No frontmatter in chat file: {chat_file}")
        return False

    chat_yaml = parse_yaml_frontmatter(chat_yaml_str)

    # Build updated frontmatter (keep technical fields, update substantive fields)
    updated_yaml_lines = []
    updated_yaml_lines.append(f"id: {manual_yaml.get('id', chat_yaml['id'])}")
    updated_yaml_lines.append(f"title: {manual_yaml.get('title', chat_yaml['title'])}")
    updated_yaml_lines.append(f"date: {chat_yaml['date']}")  # Keep original
    updated_yaml_lines.append(f"agent: {chat_yaml['agent']}")  # Keep original
    updated_yaml_lines.append(f"domain: {manual_yaml.get('domain', chat_yaml['domain'])}")

    # Handle rems_extracted (may be named differently in manual summary - legacy support)
    rems = manual_yaml.get('rems_extracted', manual_yaml.get('concepts_extracted', '[]'))
    updated_yaml_lines.append(f"rems_extracted: {rems}")

    updated_yaml_lines.append(f"turns: {chat_yaml['turns']}")  # Keep original
    updated_yaml_lines.append(f"tags: {manual_yaml.get('tags', '[]')}")
    updated_yaml_lines.append(f"archived_by: {chat_yaml['archived_by']}")  # Keep original
    updated_yaml_lines.append(f"archived_at: {chat_yaml['archived_at']}")  # Keep original

    new_frontmatter = "---\n" + "\n".join(updated_yaml_lines) + "\n---"

    # Replace frontmatter
    updated_content = chat_content.replace(chat_frontmatter_str, new_frontmatter)

    # Update title in body
    title_pattern = r'^# .*?$'
    new_title = f"# {manual_yaml.get('title', chat_yaml['title'])}"
    updated_content = re.sub(title_pattern, new_title, updated_content, count=1, flags=re.MULTILINE)

    # Update domain in metadata
    domain_pattern = r'\*\*Domain\*\*: .*?$'
    new_domain_line = f"**Domain**: {manual_yaml.get('domain', chat_yaml['domain'])}"
    updated_content = re.sub(domain_pattern, new_domain_line, updated_content, count=1, flags=re.MULTILINE)

    # Update Summary section
    summary_pattern = r'## Summary\n\n\*\(Summary will be generated by /save from active context\)\*'
    new_summary = f"## Summary\n\n{manual_summary}"
    updated_content = re.sub(summary_pattern, new_summary, updated_content, flags=re.MULTILINE)

    # Write back
    chat_path.write_text(updated_content, encoding='utf-8')
    print(f"✅ Updated: {chat_file}")
    return True

def main():
    root_dir = Path("/root/knowledge-system")

    print("=" * 60)
    print("Batch Frontmatter Update Script")
    print("=" * 60)
    print(f"Total files to update: {len(FILE_MAPPING)}")
    print()

    success_count = 0
    for chat_file, manual_file in FILE_MAPPING.items():
        if update_conversation_file(chat_file, manual_file, root_dir):
            success_count += 1
        print()

    print("=" * 60)
    print(f"✅ Successfully updated: {success_count}/{len(FILE_MAPPING)} files")
    print("=" * 60)

if __name__ == "__main__":
    main()
