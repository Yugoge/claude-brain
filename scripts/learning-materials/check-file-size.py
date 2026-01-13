#!/usr/bin/env python3
"""
File Size Checker for Learning Materials
=========================================

Checks if a file exceeds size thresholds and provides recommendations
for handling large files to avoid API 413 errors.

NEW: Content-type detection for PDFs to distinguish image-heavy vs text-heavy.

Usage:
  source venv/bin/activate && source venv/bin/activate && python scripts/check-file-size.py <file-path> [--threshold-mb 5]
  source venv/bin/activate && source venv/bin/activate && python scripts/check-file-size.py <file-path> --analyze-content

Exit codes:
  0 - File is safe to read fully
  1 - File is large, should use chunking
  2 - File not found or error
"""

import os
import sys
import json
import argparse
from pathlib import Path

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


# Size thresholds (in MB)
WARN_THRESHOLD_MB = 5
ERROR_THRESHOLD_MB = 20

# Content-type detection thresholds
IMAGE_HEAVY_MIN_IMAGES = 3  # Images per page
IMAGE_HEAVY_MAX_TEXT = 200   # Characters per page
TEXT_HEAVY_MAX_IMAGES = 1
TEXT_HEAVY_MIN_TEXT = 1500


def format_size(size_bytes):
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def analyze_pdf_content_type(file_path, sample_pages=3):
    """
    Analyze PDF content to determine if it's image-heavy or text-heavy.

    This helps decide optimal chunking strategy:
    - Image-heavy (picture books): 1 page at a time
    - Text-heavy (textbooks): 5-10 pages at a time
    - Mixed: 3-5 pages at a time

    Args:
        file_path: Path to PDF file
        sample_pages: Number of pages to sample (default 3)

    Returns:
        dict with content analysis results
    """
    if not PDFPLUMBER_AVAILABLE:
        return {
            "content_type": "unknown",
            "reason": "pdfplumber not installed",
            "recommended_chunk_pages": 5
        }

    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_sample = min(sample_pages, total_pages)

            total_images = 0
            total_text_chars = 0

            # Sample first N pages
            for i in range(pages_to_sample):
                page = pdf.pages[i]

                # Count images
                images = page.images
                total_images += len(images)

                # Count text characters
                text = page.extract_text() or ""
                total_text_chars += len(text)

            # Calculate averages
            avg_images_per_page = total_images / pages_to_sample
            avg_text_chars_per_page = total_text_chars / pages_to_sample

            # Classify content type
            if avg_images_per_page >= IMAGE_HEAVY_MIN_IMAGES or \
               avg_text_chars_per_page <= IMAGE_HEAVY_MAX_TEXT:
                content_type = "image_heavy"
                recommended_chunk_visual = 1
                recommended_chunk_text = total_pages  # Can preview all in text mode
                strategy = "text_preview_then_visual_study"
            elif avg_images_per_page <= TEXT_HEAVY_MAX_IMAGES and \
                 avg_text_chars_per_page >= TEXT_HEAVY_MIN_TEXT:
                content_type = "text_heavy"
                recommended_chunk_visual = 10
                recommended_chunk_text = 50
                strategy = "direct_visual_study"
            else:
                content_type = "mixed"
                recommended_chunk_visual = 5
                recommended_chunk_text = 20
                strategy = "adaptive_chunking"

            return {
                "content_type": content_type,
                "total_pages": total_pages,
                "analysis": {
                    "avg_images_per_page": round(avg_images_per_page, 1),
                    "avg_text_chars_per_page": round(avg_text_chars_per_page, 0),
                    "sample_pages": pages_to_sample
                },
                "recommended_chunk_pages": recommended_chunk_visual,
                "recommended_chunk_text_mode": recommended_chunk_text,
                "recommended_strategy": strategy,
                "token_estimate_per_page": {
                    "text_mode": int(avg_text_chars_per_page / 3),  # ~3 chars per token
                    "visual_mode": 1500 if content_type == "image_heavy" else 500
                }
            }

    except Exception as e:
        return {
            "content_type": "unknown",
            "error": str(e),
            "recommended_chunk_pages": 5
        }


def check_file_size(file_path, threshold_mb=WARN_THRESHOLD_MB, analyze_content=False):
    """
    Check file size and return status with recommendations

    Args:
        file_path: Path to file
        threshold_mb: Size threshold in MB
        analyze_content: If True, analyze PDF content type

    Returns:
        dict with keys: safe, size_mb, size_str, recommendation, exit_code
        If analyze_content=True, also includes content_analysis
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return {
                "safe": False,
                "error": "File not found",
                "exit_code": 2
            }

        size_bytes = path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        size_str = format_size(size_bytes)

        # Perform content analysis if requested and file is PDF
        content_analysis = None
        if analyze_content and str(file_path).lower().endswith('.pdf'):
            content_analysis = analyze_pdf_content_type(file_path)

        # Build base result
        result = {
            "safe": size_mb < threshold_mb,
            "size_mb": round(size_mb, 2),
            "size_str": size_str,
            "file_path": str(file_path)
        }

        # Add content analysis if available
        if content_analysis:
            result["content_analysis"] = content_analysis

        # Determine safety level and recommendations
        if size_mb < threshold_mb:
            result.update({
                "recommendation": "safe_to_read",
                "message": f"File size ({size_str}) is within safe limits",
                "exit_code": 0
            })
        elif size_mb < ERROR_THRESHOLD_MB:
            suggestions = [
                "Extract table of contents first",
                "Read specific pages/chapters only",
                "Use extract-pdf-chunk.py for selective reading"
            ]

            # Add content-specific suggestions
            if content_analysis and content_analysis.get("content_type") == "image_heavy":
                suggestions.insert(0, f"⚠️ Image-heavy PDF detected! Use text preview mode first")
                suggestions.insert(1, f"Recommended: 1 page at a time for visual study")

            result.update({
                "recommendation": "use_chunking",
                "message": f"File is large ({size_str}). Recommend chunked reading.",
                "suggestions": suggestions,
                "exit_code": 1
            })
        else:
            suggestions = [
                "Extract metadata/TOC only",
                "Process in small chunks",
                "Consider splitting into smaller materials"
            ]

            if content_analysis and content_analysis.get("content_type") == "image_heavy":
                suggestions[1] = "Process 1 page at a time (image-heavy content)"

            result.update({
                "recommendation": "must_chunk",
                "message": f"File is very large ({size_str}). MUST use chunking to avoid API errors.",
                "suggestions": suggestions,
                "exit_code": 1
            })

        return result

    except Exception as e:
        return {
            "safe": False,
            "error": str(e),
            "exit_code": 2
        }


def main():
    parser = argparse.ArgumentParser(
        description='Check if a file is safe to read fully or needs chunking'
    )
    parser.add_argument('file_path', help='Path to file to check')
    parser.add_argument(
        '--threshold-mb',
        type=float,
        default=WARN_THRESHOLD_MB,
        help=f'Size threshold in MB (default: {WARN_THRESHOLD_MB})'
    )
    parser.add_argument(
        '--analyze-content',
        action='store_true',
        help='Analyze PDF content type (image-heavy vs text-heavy)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    args = parser.parse_args()

    result = check_file_size(args.file_path, args.threshold_mb, args.analyze_content)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        if result.get('error'):
            print(f"❌ Error: {result['error']}", file=sys.stderr)
        else:
            print(f"📄 File: {args.file_path}")
            print(f"📊 Size: {result['size_str']} ({result['size_mb']} MB)")

            # Show content analysis if available
            if 'content_analysis' in result:
                ca = result['content_analysis']
                if 'error' not in ca:
                    print(f"\n📖 Content Type: {ca['content_type'].upper()}")
                    print(f"   Pages: {ca['total_pages']}")
                    print(f"   Avg images/page: {ca['analysis']['avg_images_per_page']}")
                    print(f"   Avg text chars/page: {ca['analysis']['avg_text_chars_per_page']}")
                    print(f"\n💡 Recommended Strategy: {ca['recommended_strategy']}")
                    print(f"   Visual mode: {ca['recommended_chunk_pages']} pages/chunk")
                    print(f"   Text mode: {ca['recommended_chunk_text_mode']} pages/chunk")
                    print(f"\n⚡ Token Estimates:")
                    print(f"   Text mode: ~{ca['token_estimate_per_page']['text_mode']} tokens/page")
                    print(f"   Visual mode: ~{ca['token_estimate_per_page']['visual_mode']} tokens/page")

            print(f"\n{result['message']}")

            if 'suggestions' in result:
                print("\n💡 Suggestions:")
                for suggestion in result['suggestions']:
                    print(f"  • {suggestion}")

    sys.exit(result['exit_code'])


if __name__ == '__main__':
    main()
