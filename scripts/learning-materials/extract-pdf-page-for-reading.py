#!/usr/bin/env python3
"""
Extract Single PDF Page to Temporary File for Safe Reading
===========================================================

SOLUTION TO API ERROR 413:
- Read(file.pdf, offset=X, limit=Y) loads ENTIRE PDF regardless of parameters
- Claude API limit: 100 pages per request

ZERO-POLLUTION APPROACH:
- Extract ONLY the requested page to a temporary single-page PDF
- Return temp file path for immediate Read operation
- Caller must delete temp file after use
- No permanent file pollution

Usage Pattern:
  1. Call this script to extract page → get temp file path
  2. Use Claude Read tool on temp file (safe, only 1 page)
  3. Delete temp file immediately after reading
  4. Repeat for next page

Example:
  result = extract_page(pdf_path="book.pdf", page_num=5)
  temp_path = result["temp_file"]

  # Read with Claude
  content = Read(temp_path)

  # Delete immediately
  os.unlink(temp_path)

With TempFileGuard (recommended):
  with TempFileGuard() as guard:
      result = extract_page(pdf_path="book.pdf", page_num=5)
      temp_path = result["temp_file"]
      guard.register(temp_path)

      content = Read(temp_path)
      # Automatic cleanup on context exit

Dependencies:
  PyPDF2 (already installed)
"""

import sys
import json
import argparse
import tempfile
import os
import atexit
import signal
import time
from pathlib import Path
from typing import Optional, Dict, List

try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    print("❌ Missing PyPDF2. Install with: pip install PyPDF2", file=sys.stderr)
    sys.exit(1)


class TempFileGuard:
    """
    Context manager and signal handler for guaranteed temp file cleanup.

    Features:
    - Registers temp files for tracking
    - Cleans up on normal exit (atexit)
    - Cleans up on interrupts (SIGTERM, SIGINT)
    - Cleans up on context exit (__exit__)

    Usage:
        with TempFileGuard() as guard:
            temp_file = create_temp_file()
            guard.register(temp_file)
            # do work...
        # Automatic cleanup
    """

    _instances: List['TempFileGuard'] = []

    def __init__(self):
        self.temp_files: set = set()
        self._cleaned = False
        TempFileGuard._instances.append(self)

    def register(self, temp_file_path: str):
        """Register a temp file for cleanup."""
        if temp_file_path and os.path.exists(temp_file_path):
            self.temp_files.add(temp_file_path)

    def cleanup(self):
        """Clean up all registered temp files."""
        if self._cleaned:
            return

        for temp_file in list(self.temp_files):
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception:
                pass  # Best effort cleanup

        self.temp_files.clear()
        self._cleaned = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False

    @classmethod
    def cleanup_all(cls):
        """Clean up all TempFileGuard instances (for atexit/signal handlers)."""
        for instance in cls._instances:
            instance.cleanup()


# Register global cleanup handlers
atexit.register(TempFileGuard.cleanup_all)
signal.signal(signal.SIGTERM, lambda sig, frame: (TempFileGuard.cleanup_all(), sys.exit(0)))
signal.signal(signal.SIGINT, lambda sig, frame: (TempFileGuard.cleanup_all(), sys.exit(0)))


def validate_inputs(pdf_path: str, page_num: int) -> Optional[str]:
    """
    Validate extraction inputs.

    Returns:
        Error message if validation fails, None if valid
    """
    # Validate PDF path
    if not pdf_path:
        return "PDF path cannot be empty"

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        return f"PDF file does not exist: {pdf_path}"

    if not pdf_file.is_file():
        return f"Path is not a file: {pdf_path}"

    if pdf_file.suffix.lower() != '.pdf':
        return f"File is not a PDF: {pdf_path}"

    # Validate page number
    if not isinstance(page_num, int):
        return f"Page number must be integer, got {type(page_num).__name__}"

    if page_num < 0:
        return f"Page number cannot be negative: {page_num}"

    return None


def extract_single_page_to_temp(pdf_path: str, page_num: int, max_retries: int = 3) -> Dict:
    """
    Extract a single page to a temporary PDF file with retry logic.

    Args:
        pdf_path: Path to source PDF
        page_num: Page number (0-indexed)
        max_retries: Maximum retry attempts for transient failures

    Returns:
        dict with temp file path and metadata
    """
    result = {
        "success": False,
        "page_num": page_num,
        "temp_file": None,
        "file_size_mb": 0
    }

    # Input validation
    validation_error = validate_inputs(pdf_path, page_num)
    if validation_error:
        result["error"] = validation_error
        return result

    # Retry logic with exponential backoff
    for attempt in range(max_retries):
        try:
            # Read source PDF
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)

            # Validate page range
            if page_num >= total_pages:
                result["error"] = (
                    f"Page {page_num} out of range. "
                    f"PDF has {total_pages} pages (0-{total_pages-1})"
                )
                return result

            # Create writer with single page
            writer = PdfWriter()
            writer.add_page(reader.pages[page_num])

            # Create temp file
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.pdf',
                prefix=f'page_{page_num + 1}_'
            )

            # Write single-page PDF
            with os.fdopen(temp_fd, 'wb') as temp_file:
                writer.write(temp_file)

            # Get file size
            file_size = os.path.getsize(temp_path)

            result["success"] = True
            result["temp_file"] = temp_path
            result["file_size_mb"] = round(file_size / (1024 * 1024), 3)
            result["total_pages_in_source"] = total_pages
            result["warning"] = "⚠️  MUST DELETE THIS FILE AFTER USE! Call os.unlink(temp_file)"

            return result

        except (IOError, OSError) as e:
            # Transient error - retry
            if attempt < max_retries - 1:
                backoff_time = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
                result["retry_attempt"] = attempt + 1
                time.sleep(backoff_time)
                continue
            else:
                result["error"] = f"Failed after {max_retries} attempts: {str(e)}"
                return result

        except Exception as e:
            # Non-recoverable error
            result["error"] = f"Extraction failed: {str(e)}"
            return result

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Extract single PDF page to temporary file for safe reading'
    )
    parser.add_argument('pdf_path', help='Path to source PDF')
    parser.add_argument('page_num', type=int, help='Page number (0-indexed)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    result = extract_single_page_to_temp(args.pdf_path, args.page_num)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"✅ Extracted page {result['page_num'] + 1}")
            print(f"📄 Temp file: {result['temp_file']}")
            print(f"📏 Size: {result['file_size_mb']} MB")
            print(f"\n{result['warning']}")
            print(f"\nUsage:")
            print(f"  1. Read with Claude: Read('{result['temp_file']}')")
            print(f"  2. Delete after use: os.unlink('{result['temp_file']}')")
        else:
            print(f"❌ Error: {result.get('error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
