#!/usr/bin/env python3
"""
EPUB Parser
Extracts text content from EPUB ebooks for learning
"""

import sys
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML."""

    def __init__(self):
        super().__init__()
        self.text = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False

    def handle_data(self, data):
        if not self.in_script:
            text = data.strip()
            if text:
                self.text.append(text)

    def get_text(self):
        return '\n'.join(self.text)


class EPUBParser:
    """Parser for EPUB ebook files."""

    NAMESPACES = {
        'n': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'pkg': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }

    @staticmethod
    def parse_epub(file_path: str, output_format: str = "markdown", section_number: int = None, search_query: str = None) -> str:
        """
        Parse an EPUB file and extract text content.

        Args:
            file_path: Path to EPUB file
            output_format: Output format ('markdown', 'json', or 'text')
            section_number: If specified, return only this section number (1-indexed)
            search_query: If specified, return only sections containing this text (case-insensitive)

        Returns:
            Extracted content in specified format
        """
        try:
            epub = zipfile.ZipFile(file_path, 'r')
        except Exception as e:
            return f"ERROR: Failed to open {file_path}: {e}"

        # Find the content file (OPF)
        try:
            container = epub.read('META-INF/container.xml')
            container_root = ET.fromstring(container)
            opf_path = container_root.find('.//n:rootfile', EPUBParser.NAMESPACES).get('full-path')
        except Exception as e:
            return f"ERROR: Failed to parse EPUB structure: {e}"

        # Parse metadata and content
        try:
            opf_content = epub.read(opf_path)
            opf_root = ET.fromstring(opf_content)

            metadata = EPUBParser._extract_metadata(opf_root)
            chapters = EPUBParser._extract_chapters(epub, opf_root, opf_path)

        except Exception as e:
            return f"ERROR: Failed to extract content: {e}"
        finally:
            epub.close()

        # Apply filters
        filtered_chapters = chapters

        # Filter by section number
        if section_number is not None:
            if 1 <= section_number <= len(chapters):
                filtered_chapters = [chapters[section_number - 1]]
            else:
                return f"ERROR: Section {section_number} not found (valid range: 1-{len(chapters)})"

        # Filter by search query
        if search_query is not None:
            search_lower = search_query.lower()
            filtered_chapters = [
                ch for ch in filtered_chapters
                if search_lower in ch['content'].lower()
            ]
            if not filtered_chapters:
                return f"No sections found containing: {search_query}"

        # Format output
        if output_format == "json":
            return json.dumps({
                "metadata": metadata,
                "chapters": filtered_chapters
            }, indent=2, ensure_ascii=False)

        elif output_format == "markdown":
            return EPUBParser._format_as_markdown(metadata, filtered_chapters)

        else:  # plain text
            return EPUBParser._format_as_text(metadata, filtered_chapters)

    @staticmethod
    def _extract_metadata(opf_root) -> dict:
        """Extract book metadata from OPF."""
        metadata = {
            "title": "Unknown",
            "author": "Unknown",
            "language": "Unknown",
            "publisher": "Unknown"
        }

        meta_section = opf_root.find('.//pkg:metadata', EPUBParser.NAMESPACES)
        if meta_section is not None:
            title = meta_section.find('.//dc:title', EPUBParser.NAMESPACES)
            if title is not None:
                metadata["title"] = title.text

            creator = meta_section.find('.//dc:creator', EPUBParser.NAMESPACES)
            if creator is not None:
                metadata["author"] = creator.text

            language = meta_section.find('.//dc:language', EPUBParser.NAMESPACES)
            if language is not None:
                metadata["language"] = language.text

            publisher = meta_section.find('.//dc:publisher', EPUBParser.NAMESPACES)
            if publisher is not None:
                metadata["publisher"] = publisher.text

        return metadata

    @staticmethod
    def _extract_chapters(epub, opf_root, opf_path) -> list:
        """Extract chapter content from EPUB."""
        chapters = []

        # Get manifest (list of files)
        manifest = {}
        for item in opf_root.findall('.//pkg:manifest/pkg:item', EPUBParser.NAMESPACES):
            manifest[item.get('id')] = item.get('href')

        # Get spine (reading order)
        spine = opf_root.findall('.//pkg:spine/pkg:itemref', EPUBParser.NAMESPACES)

        # Extract content in reading order
        opf_dir = str(Path(opf_path).parent)

        for idx, itemref in enumerate(spine, 1):
            item_id = itemref.get('idref')
            if item_id in manifest:
                file_path = manifest[item_id]
                if opf_dir and opf_dir != '.':
                    file_path = f"{opf_dir}/{file_path}"

                try:
                    content = epub.read(file_path).decode('utf-8')
                    text = EPUBParser._html_to_text(content)

                    if text.strip():
                        chapters.append({
                            "chapter_number": idx,
                            "content": text.strip()
                        })
                except Exception as e:
                    chapters.append({
                        "chapter_number": idx,
                        "content": f"[Error reading chapter: {e}]"
                    })

        return chapters

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert HTML to plain text."""
        parser = HTMLTextExtractor()
        parser.feed(html)
        return parser.get_text()

    @staticmethod
    def _format_as_markdown(metadata: dict, chapters: list) -> str:
        """Format extracted content as Markdown."""
        lines = []

        # Header
        lines.append(f"# {metadata['title']}\n")
        lines.append(f"**Author**: {metadata['author']}")
        lines.append(f"**Language**: {metadata['language']}")
        lines.append(f"**Publisher**: {metadata['publisher']}")
        lines.append(f"**Total Sections**: {len(chapters)}\n")
        lines.append("---\n")

        # Chapters
        for chapter in chapters:
            lines.append(f"## Section {chapter['chapter_number']}\n")
            lines.append(chapter['content'])
            lines.append("\n---\n")

        return "\n".join(lines)

    @staticmethod
    def _format_as_text(metadata: dict, chapters: list) -> str:
        """Format extracted content as plain text."""
        lines = []

        lines.append(f"{metadata['title']}")
        lines.append(f"Author: {metadata['author']}")
        lines.append(f"=" * 60 + "\n")

        for chapter in chapters:
            lines.append(f"Section {chapter['chapter_number']}")
            lines.append("-" * 60)
            lines.append(chapter['content'])
            lines.append("\n")

        return "\n".join(lines)


def main():
    """Command-line interface for EPUB parser."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Parse EPUB files and extract text content',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python parse-epub.py book.epub                     # All sections as markdown
  python parse-epub.py book.epub --format json       # All sections as JSON
  python parse-epub.py book.epub --section 4         # Only section 4
  python parse-epub.py book.epub --search "keyword"  # Sections containing keyword
  python parse-epub.py book.epub --section 4 --quiet # Section 4, suppress warnings
        '''
    )

    parser.add_argument('file', help='Path to EPUB file')
    parser.add_argument('--format', default='markdown', choices=['markdown', 'json', 'text'],
                        help='Output format (default: markdown)')
    parser.add_argument('--section', type=int, metavar='N',
                        help='Extract only section N (1-indexed)')
    parser.add_argument('--search', metavar='QUERY',
                        help='Extract only sections containing QUERY (case-insensitive)')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress non-critical output')

    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"ERROR: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    result = EPUBParser.parse_epub(
        args.file,
        output_format=args.format,
        section_number=args.section,
        search_query=args.search
    )
    print(result)


if __name__ == "__main__":
    main()
