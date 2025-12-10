#!/usr/bin/env python3
"""
Compress Progress Files - Clean up bloated session history

Applies standard template structure and compresses old sessions.

Usage:
    source venv/bin/activate && python scripts/progress/compress_progress.py --all
    source venv/bin/activate && python scripts/progress/compress_progress.py <progress-file>
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime


def compress_sessions(content_lines: list, threshold: int = 3) -> list:
    """
    Compress old sessions to single-line summaries.

    Strategy:
        1. Find all session headers (### Session N)
        2. Keep last `threshold` sessions intact
        3. Compress older to archive section
    """
    # Find session section start
    session_section_start = None
    for i, line in enumerate(content_lines):
        if line.startswith('## Session History') or line.startswith('## Learned Concepts'):
            session_section_start = i
            break

    if session_section_start is None:
        return content_lines  # No session section found

    # Find all session headers after session section
    session_indices = []
    for i in range(session_section_start, len(content_lines)):
        if re.match(r'^### Session \d+', content_lines[i]):
            session_indices.append(i)

    if len(session_indices) <= threshold:
        return content_lines  # No compression needed

    # Extract old sessions info
    old_sessions = []
    for i in range(len(session_indices) - threshold):
        start = session_indices[i]
        end = session_indices[i + 1] if i + 1 < len(session_indices) else len(content_lines)

        session_content = content_lines[start:end]
        session_header = session_content[0]

        # Extract info
        concepts_count = 0
        date = ""

        # Try to extract session number
        session_num_match = re.search(r'Session (\d+)', session_header)
        session_num = int(session_num_match.group(1)) if session_num_match else i + 1

        # Extract date
        date_match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', session_header)
        if date_match:
            date = date_match.group(1)

        # Extract concepts count
        for line in session_content:
            if 'Rems extracted' in line or 'concepts extracted' in line:
                num_match = re.search(r'(\d+)\s+(?:Rems|concepts)', line)
                if num_match:
                    concepts_count = int(num_match.group(1))

        old_sessions.append({
            'num': session_num,
            'date': date,
            'concepts': concepts_count
        })

    # Build new content
    result = content_lines[:session_section_start]
    result.append('## Session History')
    result.append('')

    # Add compressed archive section
    if old_sessions:
        first_date = old_sessions[0]['date']
        last_date = old_sessions[-1]['date']
        total_concepts = sum(s['concepts'] for s in old_sessions)

        result.append('### Session Archive (Compressed)')
        result.append(f'- Sessions 1-{len(old_sessions)}: {total_concepts} concepts extracted [{first_date} to {last_date}]')
        result.append('')

    # Add recent sessions header
    result.append('### Recent Sessions')
    result.append('')

    # Keep recent sessions
    recent_start = session_indices[-threshold]
    result.extend(content_lines[recent_start:])

    return result


def standardize_structure(content_lines: list) -> list:
    """
    Ensure progress file follows standard section order.

    Standard sections:
        1. Material Information
        2. Progress Tracking
        3. Session History
        4. Notes
    """
    # This is a simplified version - just ensure key sections exist
    has_material_info = any('## Material Information' in line for line in content_lines)
    has_progress_tracking = any('## Progress Tracking' in line for line in content_lines)
    has_session_history = any('## Session History' in line for line in content_lines)
    has_notes = any('## Notes' in line for line in content_lines)

    # If missing key sections, add them
    if not has_notes:
        content_lines.append('')
        content_lines.append('## Notes')
        content_lines.append('')
        content_lines.append('*Add learning notes, observations, or challenges here*')

    return content_lines


def compress_progress_file(progress_file: Path, threshold: int = 3):
    """Compress a single progress file."""
    if not progress_file.exists():
        print(f"Error: File not found: {progress_file}", file=sys.stderr)
        return False

    print(f"Processing: {progress_file.name}")

    # Read file
    with open(progress_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract frontmatter
    frontmatter_lines = []
    content_lines = []

    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if frontmatter_match:
        frontmatter_lines = ['---'] + frontmatter_match.group(1).split('\n') + ['---', '']
        content = content[frontmatter_match.end():]

    content_lines = content.split('\n')

    # Standardize structure
    content_lines = standardize_structure(content_lines)

    # Compress sessions
    original_lines = len(content_lines)
    content_lines = compress_sessions(content_lines, threshold)
    compressed_lines = len(content_lines)

    # Write back
    full_content = '\n'.join(frontmatter_lines + content_lines)
    with open(progress_file, 'w', encoding='utf-8') as f:
        f.write(full_content)

    print(f"  ✓ Compressed: {original_lines} → {compressed_lines} lines (saved {original_lines - compressed_lines} lines)")
    return True


def main():
    parser = argparse.ArgumentParser(description='Compress progress files')
    parser.add_argument('progress_file', nargs='?', help='Progress file to compress')
    parser.add_argument('--all', action='store_true', help='Compress all progress files')
    parser.add_argument('--compress-threshold', type=int, default=3,
                       help='Keep last N sessions detailed (default: 3)')

    args = parser.parse_args()

    if args.all:
        # Find all progress files
        progress_files = list(Path('learning-materials').rglob('*.progress.md'))
        print(f"Found {len(progress_files)} progress files\n")

        success_count = 0
        for pf in progress_files:
            if compress_progress_file(pf, args.compress_threshold):
                success_count += 1

        print(f"\n✓ Compressed {success_count}/{len(progress_files)} files")
        return 0 if success_count == len(progress_files) else 1

    elif args.progress_file:
        pf = Path(args.progress_file)
        return 0 if compress_progress_file(pf, args.compress_threshold) else 1

    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
