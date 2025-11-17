#!/usr/bin/env python3
"""
PDF Compression Utility for Knowledge System

This tool performs ONE-TIME comprehensive compression of image-heavy PDFs
to prevent API Error 413 during learning sessions.

Compression Strategy:
- Resize images to reasonable dimensions (800-1200px width)
- Reduce JPEG quality (40-60)
- Optimize PDF structure
- Remove unnecessary metadata
- Preserve original file

Target: Compress 30MB+ PDFs to <5MB while maintaining readability.

Usage:
    python compress_pdf.py <input.pdf> [--quality 50] [--max-width 1000]
    python compress_pdf.py <input.pdf> --preset standard|aggressive

Output Location (Story 5.11):
    Compressed files are automatically saved to compressed/ subfolder:
    - Input:  learning-materials/domain/file.pdf
    - Output: learning-materials/domain/compressed/file.pdf
    - Metadata: learning-materials/domain/compressed/file.metadata.json
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict
import PyPDF2
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import io
import json
from datetime import datetime

# Compression presets
PRESETS = {
    'standard': {
        'quality': 50,
        'max_width': 1000,
        'expected_reduction': '70-80%'
    },
    'aggressive': {
        'quality': 40,
        'max_width': 800,
        'expected_reduction': '80-90%'
    }
}


class PDFCompressor:
    """Compresses image-heavy PDFs while maintaining readability"""

    def __init__(self, quality: int = 50, max_width: int = 1000):
        self.quality = quality
        self.max_width = max_width
        self.stats = {
            'pages_processed': 0,
            'images_processed': 0,
            'original_size': 0,
            'compressed_size': 0,
            'compression_ratio': 0
        }

    def compress_image(self, image_data: bytes) -> bytes:
        """Compress a single image"""
        try:
            # Load image
            img = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background

            # Resize if too large
            if img.width > self.max_width:
                ratio = self.max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)

            # Compress to JPEG
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=self.quality, optimize=True)
            compressed_data = output.getvalue()

            self.stats['images_processed'] += 1

            return compressed_data

        except Exception as e:
            print(f"Warning: Could not compress image: {e}", file=sys.stderr)
            return image_data

    def compress_pdf_simple(self, input_path: str, output_path: str) -> Dict:
        """
        Simple compression using PyPDF2 + PIL

        Note: This is a simplified approach. For production use,
        consider using pikepdf or Ghostscript for better compression.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            return {
                'success': False,
                'error': f'Input file not found: {input_path}'
            }

        self.stats['original_size'] = input_path.stat().st_size

        try:
            # Read input PDF
            reader = PdfReader(str(input_path))
            writer = PdfWriter()

            total_pages = len(reader.pages)
            print(f"Processing {total_pages} pages...")

            # Copy pages (basic compression)
            for i, page in enumerate(reader.pages):
                writer.add_page(page)
                self.stats['pages_processed'] += 1

                if (i + 1) % 5 == 0:
                    print(f"  Processed {i + 1}/{total_pages} pages...")

            # Write compressed PDF
            with open(output_path, 'wb') as f:
                writer.write(f)

            self.stats['compressed_size'] = output_path.stat().st_size
            self.stats['compression_ratio'] = (
                1 - self.stats['compressed_size'] / self.stats['original_size']
            ) * 100

            return {
                'success': True,
                'original_size': self.stats['original_size'],
                'compressed_size': self.stats['compressed_size'],
                'compression_ratio': self.stats['compression_ratio'],
                'pages_processed': self.stats['pages_processed'],
                'output_path': str(output_path)
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def compress_pdf_ghostscript(self, input_path: str, output_path: str) -> Dict:
        """
        Advanced compression using Ghostscript

        This provides much better compression for image-heavy PDFs.
        Requires Ghostscript to be installed on the system.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        if not input_path.exists():
            return {
                'success': False,
                'error': f'Input file not found: {input_path}'
            }

        self.stats['original_size'] = input_path.stat().st_size

        # Map quality to Ghostscript settings
        if self.quality >= 60:
            gs_setting = '/ebook'  # Good quality
        elif self.quality >= 40:
            gs_setting = '/screen'  # Lower quality, better compression
        else:
            gs_setting = '/screen'  # Minimum quality

        # Ghostscript command
        gs_cmd = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            f'-dPDFSETTINGS={gs_setting}',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-dDownsampleColorImages=true',
            f'-dColorImageResolution={int(self.max_width / 8.5)}',  # DPI based on max width
            f'-dDownsampleGrayImages=true',
            f'-dGrayImageResolution={int(self.max_width / 8.5)}',
            f'-dDownsampleMonoImages=true',
            f'-dMonoImageResolution={int(self.max_width / 8.5)}',
            f'-sOutputFile={output_path}',
            str(input_path)
        ]

        try:
            import subprocess
            result = subprocess.run(
                gs_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max
            )

            if result.returncode != 0:
                # Fallback to simple compression
                print("Ghostscript failed, using simple compression...", file=sys.stderr)
                return self.compress_pdf_simple(input_path, output_path)

            self.stats['compressed_size'] = output_path.stat().st_size
            self.stats['compression_ratio'] = (
                1 - self.stats['compressed_size'] / self.stats['original_size']
            ) * 100

            # Count pages
            reader = PdfReader(str(output_path))
            self.stats['pages_processed'] = len(reader.pages)

            return {
                'success': True,
                'method': 'ghostscript',
                'original_size': self.stats['original_size'],
                'compressed_size': self.stats['compressed_size'],
                'compression_ratio': self.stats['compression_ratio'],
                'pages_processed': self.stats['pages_processed'],
                'output_path': str(output_path)
            }

        except FileNotFoundError:
            print("Ghostscript not found, using simple compression...", file=sys.stderr)
            return self.compress_pdf_simple(input_path, output_path)
        except Exception as e:
            print(f"Ghostscript error: {e}, using simple compression...", file=sys.stderr)
            return self.compress_pdf_simple(input_path, output_path)

    def compress(self, input_path: str, output_path: str = None) -> Dict:
        """Main compression method - tries Ghostscript first, falls back to simple"""
        input_path = Path(input_path)

        if output_path is None:
            # Story 5.11: Output to compressed/ subfolder with same filename
            compressed_dir = input_path.parent / 'compressed'
            compressed_dir.mkdir(exist_ok=True)
            output_path = compressed_dir / input_path.name  # Same name, different folder
        else:
            output_path = Path(output_path)

        print(f"🗜️  Compressing PDF...")
        print(f"   Input: {input_path}")
        print(f"   Output: {output_path}")
        print(f"   Settings: quality={self.quality}, max_width={self.max_width}px")
        print()

        # Try Ghostscript first for best compression
        result = self.compress_pdf_ghostscript(str(input_path), str(output_path))

        # Save compression metadata
        if result['success']:
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'original_file': str(input_path),
                'compressed_file': str(output_path),
                'settings': {
                    'quality': self.quality,
                    'max_width': self.max_width
                },
                'result': result
            }

            # Save metadata with .metadata.json extension (Story 5.11)
            metadata_path = output_path.with_suffix('.metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        return result

    @staticmethod
    def format_report(result: Dict) -> str:
        """Format compression result as human-readable report"""
        if not result['success']:
            return f"❌ Compression failed: {result.get('error', 'Unknown error')}"

        orig_mb = result['original_size'] / (1024 * 1024)
        comp_mb = result['compressed_size'] / (1024 * 1024)

        report = []
        report.append("✅ Compression Complete!")
        report.append("=" * 50)
        report.append(f"Method: {result.get('method', 'simple')}")
        report.append(f"Pages Processed: {result['pages_processed']}")
        report.append("")
        report.append("Size Comparison:")
        report.append(f"  Original:    {orig_mb:.2f} MB")
        report.append(f"  Compressed:  {comp_mb:.2f} MB")
        report.append(f"  Reduction:   {result['compression_ratio']:.1f}%")
        report.append("")
        report.append(f"📁 Compressed File Path:")
        report.append(f"   {result['output_path']}")
        report.append("")
        report.append("💡 To use in /learn command:")
        report.append(f"   /learn {result['output_path']}")

        return "\n".join(report)


def main():
    """CLI interface for PDF compression"""
    parser = argparse.ArgumentParser(
        description='Compress image-heavy PDFs for efficient learning',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('input', help='Input PDF file')
    parser.add_argument('-o', '--output', help='Output PDF file (default: compressed/same-name.pdf)')
    parser.add_argument('-q', '--quality', type=int, default=50,
                       help='JPEG quality (1-100, default: 50)')
    parser.add_argument('-w', '--max-width', type=int, default=1000,
                       help='Maximum image width in pixels (default: 1000)')
    parser.add_argument('-p', '--preset', choices=['standard', 'aggressive'],
                       help='Use compression preset (overrides quality/max-width)')

    args = parser.parse_args()

    # Apply preset if specified
    if args.preset:
        preset = PRESETS[args.preset]
        quality = preset['quality']
        max_width = preset['max_width']
        print(f"Using {args.preset} preset (quality={quality}, max_width={max_width})")
        print(f"Expected reduction: {preset['expected_reduction']}")
        print()
    else:
        quality = args.quality
        max_width = args.max_width

    # Compress PDF
    compressor = PDFCompressor(quality=quality, max_width=max_width)
    result = compressor.compress(args.input, args.output)

    # Print report
    print()
    print(compressor.format_report(result))

    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
