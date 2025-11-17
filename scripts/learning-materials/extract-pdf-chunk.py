#!/usr/bin/env python3
"""
PDF Chunk Extractor for Large Learning Materials
=================================================

Extracts specific portions of PDF files to avoid loading entire document.

Features:
- Extract table of contents/metadata only
- Extract specific page ranges
- Extract by chapter/section (if TOC available)
- **NEW**: Text-only vs Visual modes for image-heavy PDFs
- Safe chunking for context-limited environments

Usage:
  # Extract metadata/TOC only
  python scripts/extract-pdf-chunk.py file.pdf --mode toc

  # Extract specific pages (TEXT ONLY - fast, no images)
  python scripts/extract-pdf-chunk.py file.pdf --mode pages --pages 1-10 --text-only

  # Extract by percentage (VISUAL - includes images, for Claude Read)
  python scripts/extract-pdf-chunk.py file.pdf --mode percent --percent 0-10

  # Text-only mode: ~50 tokens/page vs Visual mode: ~1500 tokens/page

Dependencies:
  pip install PyPDF2 pdfplumber
"""

import sys
import json
import argparse
from pathlib import Path

try:
    import PyPDF2
    import pdfplumber
except ImportError:
    print("❌ Missing dependencies. Install with:", file=sys.stderr)
    print("   pip install PyPDF2 pdfplumber", file=sys.stderr)
    sys.exit(1)


def extract_toc(pdf_path):
    """Extract table of contents and metadata"""
    result = {
        "type": "toc",
        "metadata": {},
        "outline": [],
        "page_count": 0
    }

    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            result["page_count"] = len(reader.pages)

            # Extract metadata
            if reader.metadata:
                result["metadata"] = {
                    "title": reader.metadata.get('/Title', 'Unknown'),
                    "author": reader.metadata.get('/Author', 'Unknown'),
                    "subject": reader.metadata.get('/Subject', ''),
                    "creator": reader.metadata.get('/Creator', ''),
                }

            # Extract outline/bookmarks
            if hasattr(reader, 'outline') and reader.outline:
                result["outline"] = extract_outline_recursive(reader.outline, reader)

            # Sample first page for preview
            if len(reader.pages) > 0:
                first_page = reader.pages[0]
                result["first_page_preview"] = first_page.extract_text()[:500]

    except Exception as e:
        result["error"] = str(e)

    return result


def extract_outline_recursive(outline, reader, level=0):
    """Recursively extract PDF outline/bookmarks"""
    items = []
    for item in outline:
        if isinstance(item, list):
            items.extend(extract_outline_recursive(item, reader, level + 1))
        else:
            try:
                # PyPDF2 Destination object
                title = item.get('/Title', 'Untitled')
                items.append({
                    "level": level,
                    "title": title
                })
            except:
                pass
    return items


def extract_pages(pdf_path, start_page, end_page, text_only=False):
    """
    Extract text from specific page range (1-indexed)

    Args:
        pdf_path: Path to PDF file
        start_page: Starting page (1-indexed)
        end_page: Ending page (1-indexed)
        text_only: If True, extract text only (no images). If False, returns
                   instruction for Claude Read to process visuals.

    Returns:
        dict with extraction results
    """
    result = {
        "type": "pages",
        "start_page": start_page,
        "end_page": end_page,
        "content": "",
        "mode": "text_only" if text_only else "visual"
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            result["total_pages"] = total_pages

            # Validate range
            start_page = max(1, min(start_page, total_pages))
            end_page = max(start_page, min(end_page, total_pages))

            if text_only:
                # TEXT-ONLY MODE: Extract text, skip images
                # Fast, low token cost (~50 tokens/page)
                extracted_text = []
                for page_num in range(start_page - 1, end_page):
                    page = pdf.pages[page_num]
                    text = page.extract_text()
                    if text:
                        extracted_text.append(f"--- Page {page_num + 1} ---\n{text}\n")
                    else:
                        extracted_text.append(f"--- Page {page_num + 1} ---\n[No text content]\n")

                result["content"] = "\n".join(extracted_text)
                result["pages_extracted"] = end_page - start_page + 1
                result["char_count"] = len(result["content"])
            else:
                # VISUAL MODE: Dynamic single-page extraction (zero-pollution)
                #
                # SOLUTION TO API ERROR 413:
                # Read(pdf, offset=X, limit=Y) loads THE ENTIRE PDF regardless of parameters.
                #
                # ZERO-POLLUTION WORKAROUND:
                # 1. Extract each page to a temporary single-page PDF
                # 2. Read tool loads temp file (safe, only 1 page)
                # 3. Delete temp file immediately after reading
                # 4. No permanent files created (zero pollution)
                #
                result["content"] = "DYNAMIC_SINGLE_PAGE_EXTRACTION"
                result["message"] = (
                    f"Visual mode ready for pages {start_page}-{end_page}.\n"
                    f"\n"
                    f"WORKFLOW (per page):\n"
                    f"  1. Extract page to temp file: extract-pdf-page-for-reading.py\n"
                    f"  2. Read temp file with Claude Read tool (safe, ~1500 tokens)\n"
                    f"  3. Delete temp file immediately\n"
                    f"  4. Repeat for next page\n"
                    f"\n"
                    f"ZERO POLLUTION: Temp files auto-deleted after each page.\n"
                    f"\n"
                    f"Example for page {start_page}:\n"
                    f"  result = run('python3 scripts/extract-pdf-page-for-reading.py \"{pdf_path}\" {start_page - 1} --json')\n"
                    f"  temp_file = json.loads(result)['temp_file']\n"
                    f"  content = Read(temp_file)\n"
                    f"  os.unlink(temp_file)  # Delete immediately\n"
                    f"\n"
                    f"Estimated tokens: ~{(end_page - start_page + 1) * 1500} tokens total\n"
                    f"Pages to process: {end_page - start_page + 1}"
                )
                result["pages_extracted"] = end_page - start_page + 1
                result["char_count"] = 0
                result["extraction_method"] = "dynamic_single_page"
                result["extract_command_template"] = f"python3 scripts/extract-pdf-page-for-reading.py '{pdf_path}' {{page_num}} --json"

    except Exception as e:
        result["error"] = str(e)

    return result


def extract_by_percent(pdf_path, start_percent, end_percent):
    """Extract pages by percentage of document"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            start_page = max(1, int(total_pages * start_percent / 100))
            end_page = min(total_pages, int(total_pages * end_percent / 100))

            return extract_pages(pdf_path, start_page, end_page)

    except Exception as e:
        return {"type": "percent", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(
        description='Extract chunks from PDF files safely'
    )
    parser.add_argument('pdf_path', help='Path to PDF file')
    parser.add_argument(
        '--mode',
        choices=['toc', 'pages', 'percent'],
        default='toc',
        help='Extraction mode'
    )
    parser.add_argument(
        '--pages',
        help='Page range (e.g., "1-10")'
    )
    parser.add_argument(
        '--percent',
        help='Percentage range (e.g., "0-10")'
    )
    parser.add_argument(
        '--text-only',
        action='store_true',
        help='Extract text only, skip images (fast, ~50 tokens/page)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    # Validate file exists
    if not Path(args.pdf_path).exists():
        print(f"❌ File not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Extract based on mode
    if args.mode == 'toc':
        result = extract_toc(args.pdf_path)

    elif args.mode == 'pages':
        if not args.pages:
            print("❌ --pages required for pages mode (e.g., --pages 1-10)", file=sys.stderr)
            sys.exit(1)
        try:
            start, end = map(int, args.pages.split('-'))
            result = extract_pages(args.pdf_path, start, end, text_only=args.text_only)
        except ValueError:
            print("❌ Invalid page range format. Use: --pages 1-10", file=sys.stderr)
            sys.exit(1)

    elif args.mode == 'percent':
        if not args.percent:
            print("❌ --percent required for percent mode (e.g., --percent 0-10)", file=sys.stderr)
            sys.exit(1)
        try:
            start, end = map(float, args.percent.split('-'))
            result = extract_by_percent(args.pdf_path, start, end)
            # Note: text_only not applicable to percent mode (would need refactoring)
        except ValueError:
            print("❌ Invalid percent range format. Use: --percent 0-10", file=sys.stderr)
            sys.exit(1)

    # Output result
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        if result.get('error'):
            print(f"❌ Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        if result['type'] == 'toc':
            print(f"📚 PDF Metadata & TOC")
            print(f"{'='*60}")
            print(f"File: {args.pdf_path}")
            print(f"Pages: {result['page_count']}")
            print()

            if result['metadata']:
                print("📖 Metadata:")
                for key, value in result['metadata'].items():
                    print(f"  {key.title()}: {value}")
                print()

            if result['outline']:
                print("📑 Table of Contents:")
                for item in result['outline']:
                    indent = "  " * item['level']
                    print(f"{indent}• {item['title']}")
            else:
                print("📑 No table of contents found")

            if result.get('first_page_preview'):
                print(f"\n📄 First Page Preview:")
                print(result['first_page_preview'])

        else:  # pages or percent
            mode_label = f"[{result.get('mode', 'unknown').upper()}]" if 'mode' in result else ""
            print(f"📄 Extracted {mode_label}: Pages {result['start_page']}-{result['end_page']}")
            print(f"Total pages: {result.get('total_pages', 'unknown')}")
            print(f"Characters: {result.get('char_count', 0)}")

            if result.get('mode') == 'visual':
                # Visual mode signal
                print(f"\n{'='*60}")
                print("⚠️  VISUAL MODE")
                print(f"{'='*60}")
                print(result.get('message', ''))
                print(f"\nTo read these pages with images, use Claude Read tool:")
                print(f"  Read(file_path='...', limit={result['pages_extracted']})")
            else:
                # Text-only mode
                print(f"\n{'-'*60}\n")
                print(result['content'])


if __name__ == '__main__':
    main()
