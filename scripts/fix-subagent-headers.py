#!/usr/bin/env python3
"""Fix mislabeled subagent headers in archived conversations.

Finds '### Assistant -> Subagent' followed by '### Assistant' patterns.
The second header should be '### Subagent (Name) -> Assistant'.
Detects subagent name from task prompt content keywords.

Safety: dry-run by default, --apply to modify. Creates .bak backups.
"""

import argparse
import re
from pathlib import Path

CHATS_DIR = Path(__file__).parent.parent / 'chats'

SUBAGENT_KEYWORDS = {
    'analyst': ['research', 'search', 'find', 'investigate', 'analyze',
                'look up', 'web search', 'explore'],
    'review-master': ['review session', 'review', 'spaced repetition',
                      'fsrs', 'quiz', 'test your'],
    'finance-tutor': ['finance', 'bond', 'option', 'derivative',
                      'pricing', 'yield', 'swap', 'cds', 'forex'],
    'programming-tutor': ['programming', 'code', 'debug', 'algorithm',
                          'python', 'c#', 'csharp', 'javascript'],
    'language-tutor': ['french', 'korean', 'english', 'grammar',
                       'vocabulary', 'pronunciation', 'language'],
    'book-tutor': ['extract', 'archive', 'save', 'knowledge point',
                   'conversation', 'summarize', 'rem'],
    'classification-expert': ['classify', 'isced', 'dewey',
                              'classification', 'taxonomy'],
    'science-tutor': ['physics', 'chemistry', 'biology', 'science'],
    'medicine-tutor': ['medical', 'medicine', 'diagnosis', 'clinical'],
    'law-tutor': ['legal', 'law', 'statute', 'court'],
}


def detect_subagent(task_content):
    """Detect subagent type from task prompt content."""
    lower = task_content.lower()
    scores = {}
    for agent, keywords in SUBAGENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > 0:
            scores[agent] = score
    if not scores:
        return 'Subagent'
    best = max(scores, key=scores.get)
    return best.replace('-', ' ').title()


def process_file(md_path, dry_run, verbose):
    """Process one markdown file. Returns (fixes_count, fixes_list)."""
    text = md_path.read_text(encoding='utf-8')
    lines = text.split('\n')
    fixes = []

    i = 0
    while i < len(lines):
        if lines[i].strip() != '### Assistant \u2192 Subagent':
            i += 1
            continue

        # Collect task prompt content
        task_lines = []
        j = i + 1
        in_cb = False
        while j < len(lines):
            s = lines[j].strip()
            if s.startswith('```'):
                in_cb = not in_cb
            if not in_cb and s.startswith('### '):
                break
            task_lines.append(lines[j])
            j += 1

        # Check if next header is mislabeled ### Assistant
        if j < len(lines) and lines[j].strip() == '### Assistant':
            task_content = '\n'.join(task_lines)
            agent_label = detect_subagent(task_content)
            new_hdr = f'### Subagent ({agent_label}) \u2192 Assistant'
            fixes.append((j, '### Assistant', new_hdr))
            i = j + 1
        else:
            i = j + 1
        continue

    if fixes and not dry_run:
        backup = md_path.with_suffix('.md.bak')
        backup.write_text(text, encoding='utf-8')
        for ln, old, new in fixes:
            lines[ln] = new
        md_path.write_text('\n'.join(lines), encoding='utf-8')

    return len(fixes), fixes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('-v', '--verbose', action='store_true')
    args = ap.parse_args()

    total = 0
    fixed_files = 0

    for d in sorted(CHATS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith('_'):
            continue
        for md in sorted(d.glob('*.md')):
            n, fixes = process_file(md, not args.apply, args.verbose)
            if n > 0:
                fixed_files += 1
                total += n
                tag = 'FIXED' if args.apply else 'WOULD FIX'
                print(f'  {tag} {md.name}: {n} headers')
                if args.verbose:
                    for ln, old, new in fixes:
                        print(f'    L{ln+1}: {old} -> {new}')

    print(f'\n{"="*50}')
    print(f'Mode: {"APPLY" if args.apply else "DRY-RUN"}')
    print(f'Files: {fixed_files}')
    print(f'Headers: {total}')
    if not args.apply and total > 0:
        print(f'\nRun with --apply to modify files.')


if __name__ == '__main__':
    main()
