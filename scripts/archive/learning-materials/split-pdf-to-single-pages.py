#!/usr/bin/env python3
"""
Split PDF to Single Page Files
===============================

Splits a multi-page PDF into individual single-page PDF files.
This allows Claude Read tool to process each page safely without loading the entire PDF.

Solution to: API Error 413 when reading large PDFs
Root Cause: Read(file.pdf, offset=X, limit=Y) loads THE ENTIRE PDF regardless of parameters

Workaround: Split PDF into single-page files, then Read each page individually

Usage:
  # Split PDF into single pages in temp directory
  python scripts/split-pdf-to-single-pages.py input.pdf --output-dir /tmp/pdf-pages/

  # Returns JSON with list of created page files
  {
    "success": true,
    "original_file": "input.pdf",
    "total_pages": 191,
    "output_dir": "/tmp/pdf-pages/",
    "page_files": [
      "/tmp/pdf-pages/page_001.pdf",
      "/tmp/pdf-pages/page_002.pdf",
      ...
    ]
  }

Dependencies:
  pip install pypdf

References:
  - https://stackoverflow.com/questions/490195/split-a-multi-page-pdf-file-into-multiple-pdf-files-with-python
  - https://note.nkmk.me/en/python-pypdf2-pdf-merge-insert-split/
"""

import sys
import json
import argparse
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("❌ Missing dependency. Install with:", file=sys.stderr)
    print("   pip install pypdf", file=sys.stderr)
    sys.exit(1)


def split_pdf_to_single_pages(pdf_path, output_dir=None):
    """
    Split a multi-page PDF into individual single-page PDF files.

    Args:
        pdf_path: Path to the input PDF file
        output_dir: Directory to save the single-page PDFs (default: /tmp/pdf-pages-{basename}/)

    Returns:
        dict with split results
    """
    result = {
        "success": False,
        "original_file": str(pdf_path),
        "total_pages": 0,
        "output_dir": "",
        "page_files": []
    }

    try:
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            result["error"] = f"File not found: {pdf_path}"
            return result

        # Create output directory
        if output_dir is None:
            output_dir = Path(f"/tmp/pdf-pages-{pdf_path.stem}")
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)
        result["output_dir"] = str(output_dir)

        # Read input PDF
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        result["total_pages"] = total_pages

        # Split into individual pages
        page_files = []
        for page_num in range(total_pages):
            # Create writer for single page
            writer = PdfWriter()
            writer.add_page(reader.pages[page_num])

            # Save single-page PDF
            output_filename = output_dir / f"page_{page_num + 1:03d}.pdf"
            with open(output_filename, "wb") as output_file:
                writer.write(output_file)

            page_files.append(str(output_filename))

        result["page_files"] = page_files
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Split PDF into single-page PDF files'
    )
    parser.add_argument('pdf_path', help='Path to input PDF file')
    parser.add_argument(
        '--output-dir',
        help='Directory to save single-page PDFs (default: /tmp/pdf-pages-{basename}/)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Split PDF
    result = split_pdf_to_single_pages(args.pdf_path, args.output_dir)

    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"✅ Successfully split PDF into {result['total_pages']} pages")
            print(f"📁 Output directory: {result['output_dir']}")
            print(f"\n📄 Page files created:")
            for page_file in result["page_files"][:5]:
                print(f"  - {page_file}")
            if result["total_pages"] > 5:
                print(f"  ... and {result['total_pages'] - 5} more")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
