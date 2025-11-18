#!/usr/bin/env python3
"""
Add missing session_type fields to conversations.

Determines correct session_type by analyzing conversation content.
"""

import re
from pathlib import Path

# Map of files to their determined session types
# Analyzed based on agent, conversation content, and patterns
SESSION_TYPES = {
    'chats/2025-10/c-learning-ba-s-first-c-sample-test-conversation-2025-10-28.md': 'learn',
    'chats/2025-10/c-programming-review-session-conversation-2025-10-30.md': 'review',
    'chats/2025-10/capital-market-pricing-paradigms-curve-vs-vol-deep-conversation-2025-10-30.md': 'ask',
    'chats/2025-10/french-1453-vocab-20251030-conversation-2025-10-30.md': 'learn',
    'chats/2025-10/french-review-session-grammar-and-expressions-conversation-2025-10-28.md': 'learn',
    'chats/2025-10/options-greeks-time-scenario-analysis-conversation-2025-10-29.md': 'ask',
    'chats/2025-10/risk-scenario-perturbation-analysis-time-ladder-ex-conversation-2025-10-28.md': 'ask',
    'chats/2025-10/understanding-vix-delta-spx-vega-and-volatility-as-conversation-2025-10-27.md': 'learn',
    'chats/2025-11/bloomberg-ovdv-black-scholes-deep-dive-volatility-conversation-2025-11-04.md': 'ask',
    'chats/2025-11/desire-driven-growth-2025-11-02.md': 'ask',
    'chats/2025-11/epad-vs-jkm-european-power-and-asian-lng-derivativ-conversation-2025-11-05.md': 'ask',
    'chats/2025-11/fx-forward-primary-depo-rate-and-interest-rate-par-conversation-2025-11-03.md': 'ask',
    'chats/2025-11/nds-fx-options-payment-currency-conventions-conversation-2025-11-03.md': 'ask',
}

def add_session_type(file_path: Path, session_type: str):
    """Add session_type field to frontmatter."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match frontmatter
    match = re.match(r'^(---\n)(.*?)(---\n)', content, re.DOTALL)
    if not match:
        print(f"  ⚠️  No frontmatter in {file_path.name}")
        return False

    frontmatter = match.group(2)

    # Check if session_type already exists
    if re.search(r'^session_type:', frontmatter, re.MULTILINE):
        print(f"  ⏭️  session_type already exists in {file_path.name}")
        return False

    # Add session_type after date field (or at end if date not found)
    if re.search(r'^date:', frontmatter, re.MULTILINE):
        new_frontmatter = re.sub(
            r'^(date:.*)$',
            f'\\1\nsession_type: {session_type}',
            frontmatter,
            flags=re.MULTILINE
        )
    else:
        new_frontmatter = frontmatter.rstrip('\n') + f'\nsession_type: {session_type}\n'

    new_content = match.group(1) + new_frontmatter + match.group(3) + content[match.end():]

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"  ✓ Added session_type: {session_type} to {file_path.name}")
    return True

def main():
    root_dir = Path('.').resolve()
    print("📝 Adding missing session_type fields...")
    print("=" * 70)

    count = 0
    for file_rel, session_type in SESSION_TYPES.items():
        file_path = root_dir / file_rel
        if file_path.exists():
            if add_session_type(file_path, session_type):
                count += 1
        else:
            print(f"  ⚠️  File not found: {file_rel}")

    print("=" * 70)
    print(f"✅ Added session_type to {count} files")

if __name__ == '__main__':
    main()
