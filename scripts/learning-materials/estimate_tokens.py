#!/usr/bin/env python3
"""
Token Estimation Utility for Knowledge System

This tool estimates token consumption for file operations BEFORE execution,
preventing API Error 413 by proactive assessment.

Core Capabilities:
- Estimate tokens for text content (3 chars ≈ 1 token)
- Estimate tokens for images (1KB ≈ 100 tokens)
- Estimate tokens for PDF pages (text + images combined)
- Evaluate safety against context limits
- Provide actionable recommendations

Context Limits (Claude Sonnet 4):
- Maximum: 200,000 tokens
- Safe threshold: 180,000 tokens (with 20,000 buffer)
- Recommended single operation: <50,000 tokens
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple
import PyPDF2
from PIL import Image
import io

# Token estimation constants
CHARS_PER_TOKEN = 3.0
BYTES_PER_IMAGE_TOKEN = 10  # 1KB = 100 tokens
CONSERVATIVE_MULTIPLIER = 1.5  # Safety factor for images

# Context limits
MAX_CONTEXT = 200000
SAFE_THRESHOLD = 180000
RECOMMENDED_LIMIT = 50000


class TokenEstimator:
    """Estimates token consumption for various file operations"""

    def __init__(self):
        self.max_context = MAX_CONTEXT
        self.safe_threshold = SAFE_THRESHOLD
        self.recommended_limit = RECOMMENDED_LIMIT

    def estimate_text_tokens(self, text: str) -> int:
        """Estimate tokens for text content"""
        return int(len(text) / CHARS_PER_TOKEN)

    def estimate_image_tokens(self, image_bytes: bytes) -> int:
        """Estimate tokens for image content"""
        base_tokens = len(image_bytes) / BYTES_PER_IMAGE_TOKEN
        # Apply conservative multiplier for safety
        return int(base_tokens * CONSERVATIVE_MULTIPLIER)

    def estimate_pdf_page_tokens(self, pdf_path: str, page_num: int) -> Dict:
        """Estimate tokens for a single PDF page"""
        result = {
            'page': page_num,
            'text_tokens': 0,
            'image_tokens': 0,
            'total_tokens': 0,
            'has_images': False,
            'image_count': 0
        }

        try:
            with open(pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)

                if page_num >= len(pdf.pages):
                    return result

                page = pdf.pages[page_num]

                # Extract text
                text = page.extract_text() or ""
                result['text_tokens'] = self.estimate_text_tokens(text)

                # Extract images
                if '/XObject' in page['/Resources']:
                    xobjects = page['/Resources']['/XObject'].get_object()

                    for obj_name in xobjects:
                        obj = xobjects[obj_name]

                        if obj['/Subtype'] == '/Image':
                            result['has_images'] = True
                            result['image_count'] += 1

                            # Estimate image size
                            try:
                                width = obj['/Width']
                                height = obj['/Height']

                                # Estimate compressed size
                                # PDFs typically store JPEG with 10:1 compression ratio
                                # Raw RGB: width × height × 3 bytes
                                # JPEG compressed: apply 0.1 compression ratio
                                compression_ratio = 0.1  # JPEG compression
                                estimated_bytes = int(width * height * 3 * compression_ratio)
                                image_tokens = self.estimate_image_tokens(
                                    b'x' * estimated_bytes
                                )
                                result['image_tokens'] += image_tokens
                            except:
                                # Fallback: assume moderate size image
                                result['image_tokens'] += 5000

                result['total_tokens'] = result['text_tokens'] + result['image_tokens']

        except Exception as e:
            print(f"Warning: Error processing page {page_num}: {e}", file=sys.stderr)

        return result

    def estimate_pdf_tokens(self, pdf_path: str, start_page: int = 0,
                          end_page: int = None) -> Dict:
        """Estimate tokens for PDF page range"""
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            return {
                'error': f'File not found: {pdf_path}',
                'safe': False
            }

        file_size = pdf_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        result = {
            'file_path': str(pdf_path),
            'file_size': file_size,
            'file_size_mb': round(file_size_mb, 2),
            'total_pages': 0,
            'pages_analyzed': [],
            'total_tokens': 0,
            'text_tokens': 0,
            'image_tokens': 0,
            'safe': True,
            'recommendation': '',
            'max_safe_pages': 0
        }

        try:
            with open(pdf_path, 'rb') as f:
                pdf = PyPDF2.PdfReader(f)
                result['total_pages'] = len(pdf.pages)

                if end_page is None:
                    end_page = len(pdf.pages)

                end_page = min(end_page, len(pdf.pages))

                # Estimate tokens for requested page range
                for page_num in range(start_page, end_page):
                    page_result = self.estimate_pdf_page_tokens(pdf_path, page_num)
                    result['pages_analyzed'].append(page_result)
                    result['total_tokens'] += page_result['total_tokens']
                    result['text_tokens'] += page_result['text_tokens']
                    result['image_tokens'] += page_result['image_tokens']

                # Calculate average tokens per page
                if result['pages_analyzed']:
                    avg_tokens = result['total_tokens'] / len(result['pages_analyzed'])

                    # Calculate max safe pages
                    result['max_safe_pages'] = int(self.safe_threshold / avg_tokens)

                # Evaluate safety
                result['safe'] = result['total_tokens'] <= self.safe_threshold

                # Generate recommendation
                if result['total_tokens'] > self.safe_threshold:
                    result['recommendation'] = 'COMPRESS_REQUIRED'
                elif result['total_tokens'] > self.recommended_limit:
                    result['recommendation'] = 'REDUCE_PAGES'
                elif file_size_mb > 10:
                    result['recommendation'] = 'COMPRESS_SUGGESTED'
                else:
                    result['recommendation'] = 'SAFE'

        except Exception as e:
            result['error'] = str(e)
            result['safe'] = False

        return result

    def format_report(self, estimation: Dict) -> str:
        """Format estimation result as human-readable report"""
        if 'error' in estimation:
            return f"❌ Error: {estimation['error']}"

        report = []
        report.append("📊 Token Estimation Report")
        report.append("=" * 50)
        report.append(f"File: {estimation['file_path']}")
        report.append(f"Size: {estimation['file_size_mb']} MB")
        report.append(f"Total Pages: {estimation['total_pages']}")
        report.append(f"Pages Analyzed: {len(estimation['pages_analyzed'])}")
        report.append("")
        report.append("Token Breakdown:")
        report.append(f"  Text Tokens: {estimation['text_tokens']:,}")
        report.append(f"  Image Tokens: {estimation['image_tokens']:,}")
        report.append(f"  Total Tokens: {estimation['total_tokens']:,}")
        report.append("")
        report.append("Context Limits:")
        report.append(f"  Maximum: {self.max_context:,} tokens")
        report.append(f"  Safe Threshold: {self.safe_threshold:,} tokens")
        report.append(f"  Recommended: {self.recommended_limit:,} tokens")
        report.append("")

        # Safety assessment
        if estimation['safe']:
            report.append("✅ Status: SAFE to proceed")
        else:
            report.append("⚠️  Status: EXCEEDS SAFE LIMIT")

        report.append("")

        # Recommendations
        rec = estimation['recommendation']
        if rec == 'SAFE':
            report.append("💡 Recommendation: Safe to read directly")
        elif rec == 'REDUCE_PAGES':
            report.append("💡 Recommendation: Reduce page count")
            report.append(f"   Max safe pages: {estimation['max_safe_pages']}")
        elif rec == 'COMPRESS_SUGGESTED':
            report.append("💡 Recommendation: Compression suggested (large file)")
        elif rec == 'COMPRESS_REQUIRED':
            report.append("💡 Recommendation: COMPRESSION REQUIRED")
            report.append(f"   Max safe pages: {estimation['max_safe_pages']}")
            report.append("   Consider compressing the entire PDF first")

        return "\n".join(report)


def main():
    """CLI interface for token estimation"""
    if len(sys.argv) < 2:
        print("Usage: python estimate_tokens.py <pdf_path> [start_page] [end_page]")
        print("\nExample:")
        print("  python estimate_tokens.py document.pdf")
        print("  python estimate_tokens.py document.pdf 0 5")
        sys.exit(1)

    pdf_path = sys.argv[1]
    start_page = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    end_page = int(sys.argv[3]) if len(sys.argv) > 3 else None

    estimator = TokenEstimator()
    result = estimator.estimate_pdf_tokens(pdf_path, start_page, end_page)

    # Print report
    print(estimator.format_report(result))

    # Also save JSON for programmatic use
    json_path = Path(pdf_path).with_suffix('.tokens.json')
    with open(json_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n📄 Detailed results saved to: {json_path}")

    # Exit with appropriate code
    sys.exit(0 if result['safe'] else 1)


if __name__ == '__main__':
    main()
