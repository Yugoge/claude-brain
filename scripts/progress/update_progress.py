#!/usr/bin/env python3
"""
Update Learning Material Progress File

Auto-updates progress file with minimal footprint:
- Updates position, progress %, session count
- Appends compressed session record (single line)
- Auto-compresses old sessions (keeps recent N detailed)
- Updates "## Rems Extracted" section with bidirectional links
- Updates "## Related Conversations" section with bidirectional links

Usage:
    source venv/bin/activate && python scripts/progress/update_progress.py \\
      --material-path "learning-materials/language/french/1453.pdf" \\
      --position "Pages 18-20" \\
      --concepts-count 6 \\
      --compress-threshold 3 \\
      --rems-extracted '[{"title": "Concept", "path": "knowledge-base/.../rem.md"}]' \\
      --conversation-file "chats/2025-12/conversation-2025-12-10.md"
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime


def extract_progress_percentage(position: str, total_pages: int) -> int:
    """
    Calculate progress % from position string.

    Examples:
        "Page 18" → 18 / total_pages
        "Pages 18-20" → 20 / total_pages
        "Chapter 5" → estimation based on total_pages
    """
    # Try to extract page number
    page_match = re.search(r'Pages?\s+(\d+)(?:-(\d+))?', position, re.IGNORECASE)
    if page_match:
        start = int(page_match.group(1))
        end = int(page_match.group(2)) if page_match.group(2) else start
        current = end
        if total_pages > 0:
            return int((current / total_pages) * 100)

    # Try chapter (estimate 10 pages per chapter)
    chapter_match = re.search(r'Chapter\s+(\d+)', position, re.IGNORECASE)
    if chapter_match:
        chapter_num = int(chapter_match.group(1))
        estimated_page = chapter_num * 10
        if total_pages > 0:
            return min(100, int((estimated_page / total_pages) * 100))

    # Try section
    section_match = re.search(r'Section\s+(\d+)', position, re.IGNORECASE)
    if section_match:
        section_num = int(section_match.group(1))
        estimated_page = section_num * 5
        if total_pages > 0:
            return min(100, int((estimated_page / total_pages) * 100))

    return 0  # Cannot determine


def read_progress_file(progress_path: Path) -> tuple:
    """
    Read progress file and extract frontmatter + content.

    Returns: (frontmatter_dict, content_lines)
    """
    if not progress_path.exists():
        return {}, []

    with open(progress_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract frontmatter
    frontmatter = {}
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if frontmatter_match:
        fm_text = frontmatter_match.group(1)
        for line in fm_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()

        # Remove frontmatter from content
        content = content[frontmatter_match.end():]

    return frontmatter, content.split('\n')


def write_progress_file(progress_path: Path, frontmatter: dict, content_lines: list):
    """Write progress file with frontmatter + content."""
    # Build frontmatter
    fm_lines = ['---']
    for key, value in frontmatter.items():
        fm_lines.append(f'{key}: {value}')
    fm_lines.append('---')
    fm_lines.append('')

    # Combine
    full_content = '\n'.join(fm_lines + content_lines)

    with open(progress_path, 'w', encoding='utf-8') as f:
        f.write(full_content)


def compress_old_sessions(content_lines: list, threshold: int = 3) -> list:
    """
    Compress old sessions, keep recent N detailed.

    Strategy:
        1. Find all session headers (### Session N)
        2. Keep last `threshold` sessions intact
        3. Compress older sessions to single-line summaries
    """
    # Find session headers
    session_indices = []
    for i, line in enumerate(content_lines):
        if re.match(r'^### Session \d+', line):
            session_indices.append(i)

    if len(session_indices) <= threshold:
        return content_lines  # No compression needed

    # Keep recent sessions
    keep_from = session_indices[-threshold]

    # Compress old sessions
    compressed = []
    old_sessions = []

    for i in range(len(session_indices) - threshold):
        start = session_indices[i]
        end = session_indices[i + 1] if i + 1 < len(session_indices) else keep_from

        # Extract session info
        session_content = content_lines[start:end]
        session_header = session_content[0]

        # Try to extract key info
        concepts_count = 0
        pages = ""
        date = ""
        conversation_link = ""

        for line in session_content:
            if 'concepts' in line.lower() and 'Rems' in line:
                num_match = re.search(r'(\d+)\s+Rems', line)
                if num_match:
                    concepts_count = int(num_match.group(1))
            if 'Pages covered' in line or 'Pages:' in line:
                page_match = re.search(r'Pages?\s*:?\s*([\d\-,]+)', line)
                if page_match:
                    pages = page_match.group(1)
            if re.search(r'\d{4}-\d{2}-\d{2}', session_header):
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', session_header)
                if date_match:
                    date = date_match.group()
            # Extract conversation link (markdown format)
            if 'Conversation:' in line or 'Conversation**:' in line or '→' in line:
                link_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
                if link_match:
                    conversation_link = f'[{link_match.group(1)}]({link_match.group(2)})'

        old_sessions.append({
            'num': i + 1,
            'date': date,
            'pages': pages,
            'concepts': concepts_count,
            'conversation_link': conversation_link
        })

    # Build compressed section with individual session lines
    if old_sessions:
        compressed.append('## Session History')
        compressed.append('')
        compressed.append('### Session Archive (Compressed)')
        compressed.append('')

        # Add each old session as single line with conversation link if available
        for sess in old_sessions:
            line = f'- **Session {sess["num"]}** ({sess["date"]}): '
            if sess['pages']:
                line += f'Pages {sess["pages"]}, '
            line += f'{sess["concepts"]} Rems'

            # Extract conversation link if present in original content
            conv_link = sess.get('conversation_link', '')
            if conv_link:
                line += f' → {conv_link}'

            compressed.append(line)

        compressed.append('')
        compressed.append('### Recent Sessions')
        compressed.append('')

    # Add recent sessions
    compressed.extend(content_lines[keep_from:])

    # Find where to insert (after "## Session History" or similar)
    insert_idx = 0
    for i, line in enumerate(content_lines):
        if line.startswith('## Session History') or line.startswith('## Learned Concepts'):
            insert_idx = i
            break

    # Rebuild content
    result = content_lines[:insert_idx]
    result.extend(compressed)

    return result


def update_progress(material_path: str, position: str = None,
                   concepts_count: int = 0, compress_threshold: int = 3,
                   rems_extracted: list = None, conversation_file: str = None):
    """
    Main update logic.

    Args:
        material_path: Path to learning material
        position: Current position (e.g., "Pages 18-20")
        concepts_count: Number of concepts extracted this session
        compress_threshold: Keep last N sessions detailed
        rems_extracted: List of dicts with 'title' and 'path' keys
        conversation_file: Path to archived conversation
    """
    # Determine progress file path
    mat_path = Path(material_path)
    progress_path = mat_path.with_suffix('.progress.md')

    if not progress_path.exists():
        print(json.dumps({
            'success': False,
            'error': f'Progress file not found: {progress_path}'
        }))
        return 1

    # Read progress file
    frontmatter, content_lines = read_progress_file(progress_path)

    # Update frontmatter
    total_pages = int(frontmatter.get('total_pages', 0)) if 'total_pages' in frontmatter else 0
    session_count = int(frontmatter.get('session_count', 0)) if 'session_count' in frontmatter else 0

    session_count += 1
    frontmatter['session_count'] = str(session_count)
    frontmatter['last_session'] = datetime.now().strftime('%Y-%m-%d')
    frontmatter['status'] = 'in-progress'

    if position:
        progress_pct = extract_progress_percentage(position, total_pages)
        frontmatter['progress_percentage'] = str(progress_pct)

    # Update "Current Position" in content
    for i, line in enumerate(content_lines):
        if line.startswith('- **Current Position**:'):
            if position:
                content_lines[i] = f'- **Current Position**: {position}'
        elif line.startswith('- **Progress**:'):
            pct = frontmatter.get('progress_percentage', '0')
            content_lines[i] = f'- **Progress**: {pct}%'
        elif line.startswith('- **Session Count**:'):
            content_lines[i] = f'- **Session Count**: {session_count}'
        elif line.startswith('- **Last Session**:'):
            content_lines[i] = f'- **Last Session**: {frontmatter["last_session"]}'

    # Append new session record (compressed format)
    session_line = f'### Session {session_count} ({frontmatter["last_session"]})'
    if position:
        session_line += f'\n- **Pages**: {position}'
    session_line += f'\n- **Concepts extracted**: {concepts_count} Rems'

    # Add conversation link if provided
    if conversation_file:
        conv_path = Path(conversation_file)
        conv_title = conv_path.stem.replace('-', ' ').title()
        relative_conv = Path('../../') / conv_path.relative_to(Path('chats'))
        session_line += f'\n- **Conversation**: [{conv_title}]({relative_conv})'

    # Find insertion point (after "## Session History" or "### Recent Sessions")
    insert_idx = len(content_lines)
    for i, line in enumerate(content_lines):
        if line.startswith('### Recent Sessions'):
            insert_idx = i + 2  # After header and blank line
            break
        elif line.startswith('## Session History'):
            insert_idx = i + 2
            break

    content_lines.insert(insert_idx, '')
    content_lines.insert(insert_idx + 1, session_line)

    # Compress old sessions
    content_lines = compress_old_sessions(content_lines, compress_threshold)

    # Update "## Rems Extracted" section
    if rems_extracted:
        rems_section_idx = -1
        for i, line in enumerate(content_lines):
            if line.startswith('## Rems Extracted'):
                rems_section_idx = i
                break

        if rems_section_idx >= 0:
            # Find end of section (next ## header or end of file)
            section_end = len(content_lines)
            for i in range(rems_section_idx + 1, len(content_lines)):
                if content_lines[i].startswith('##'):
                    section_end = i
                    break

            # Remove old content (keep header and format comment)
            existing_lines = content_lines[rems_section_idx:section_end]
            header_lines = [existing_lines[0]]  # ## Rems Extracted
            for line in existing_lines[1:]:
                if line.startswith('*(') or line.strip() == '':
                    header_lines.append(line)
                else:
                    break

            # Build new Rem links
            rem_links = []
            for rem in rems_extracted:
                title = rem.get('title', 'Untitled')
                path = rem.get('path', '')
                # Convert absolute path to relative path from progress file
                if path:
                    rem_path = Path(path)
                    relative = Path('../../') / rem_path.relative_to(Path('knowledge-base'))
                    rem_links.append(f'- **{title}** - [{title}]({relative})')

            # Rebuild section
            new_section = header_lines + [''] + rem_links + ['']
            content_lines[rems_section_idx:section_end] = new_section

    # Update "## Related Conversations" section
    if conversation_file:
        conv_section_idx = -1
        for i, line in enumerate(content_lines):
            if line.startswith('## Related Conversations'):
                conv_section_idx = i
                break

        if conv_section_idx >= 0:
            # Find end of section
            section_end = len(content_lines)
            for i in range(conv_section_idx + 1, len(content_lines)):
                if content_lines[i].startswith('##'):
                    section_end = i
                    break

            # Extract title and date from conversation file
            conv_path = Path(conversation_file)
            conv_title = conv_path.stem.replace('-', ' ').title()
            conv_date = frontmatter['last_session']

            # Convert to relative path
            relative_conv = Path('../../') / conv_path.relative_to(Path('chats'))

            # Check if already exists
            existing_lines = content_lines[conv_section_idx:section_end]
            already_exists = False
            for line in existing_lines:
                if str(relative_conv) in line:
                    already_exists = True
                    break

            if not already_exists:
                # Insert new conversation link
                insert_pos = conv_section_idx + 1
                # Skip header and format comments
                while insert_pos < section_end and (
                    content_lines[insert_pos].startswith('*(') or
                    content_lines[insert_pos].strip() == ''
                ):
                    insert_pos += 1

                conv_link = f'- **{conv_title}** ({conv_date}) - [{conv_title}]({relative_conv})'
                content_lines.insert(insert_pos, conv_link)

    # Write back
    write_progress_file(progress_path, frontmatter, content_lines)

    print(json.dumps({
        'success': True,
        'progress_file': str(progress_path),
        'new_progress': int(frontmatter.get('progress_percentage', 0)),
        'session_count': session_count
    }))

    return 0


def main():
    parser = argparse.ArgumentParser(description='Update learning material progress')
    parser.add_argument('--material-path', required=True, help='Path to learning material')
    parser.add_argument('--position', help='Current position (e.g., "Pages 18-20")')
    parser.add_argument('--concepts-count', type=int, default=0, help='Number of concepts extracted')
    parser.add_argument('--compress-threshold', type=int, default=3,
                       help='Keep last N sessions detailed')
    parser.add_argument('--rems-extracted', help='JSON list of dicts with title and path')
    parser.add_argument('--conversation-file', help='Path to archived conversation')

    args = parser.parse_args()

    # Parse rems_extracted if provided
    rems_extracted = None
    if args.rems_extracted:
        rems_extracted = json.loads(args.rems_extracted)

    return update_progress(
        args.material_path,
        args.position,
        args.concepts_count,
        args.compress_threshold,
        rems_extracted,
        args.conversation_file
    )


if __name__ == '__main__':
    sys.exit(main())
