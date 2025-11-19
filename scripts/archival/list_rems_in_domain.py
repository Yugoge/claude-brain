#!/usr/bin/env python3
"""
List all Rems in a specific domain

Scans a domain directory for all Rem files and outputs them in JSON format
for use by workflow orchestrator and other archival tools.

Usage:
    python scripts/archival/list_rems_in_domain.py --domain-path <path> --output <file>

Examples:
    # List all French language Rems
    python scripts/archival/list_rems_in_domain.py \
        --domain-path "02-arts-and-humanities/023-languages/0231-language-acquisition" \
        --output rems.json

    # List all finance Rems
    python scripts/archival/list_rems_in_domain.py \
        --domain-path "04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance" \
        --output rems.json
"""

import json
import argparse
import sys
from pathlib import Path
import re

# Project root
ROOT = Path(__file__).parent.parent.parent
KB_DIR = ROOT / "knowledge-base"


def extract_frontmatter(file_path: Path) -> dict:
    """
    Extract YAML frontmatter from Rem file.

    Returns dict with frontmatter fields, or empty dict if none found.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter (between --- markers)
        match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            return {}

        frontmatter_text = match.group(1)
        frontmatter = {}

        # Simple YAML parser (key: value)
        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes
                if value.startswith('"') or value.startswith("'"):
                    value = value[1:-1]

                frontmatter[key] = value

        return frontmatter

    except Exception as e:
        print(f"Warning: Error reading {file_path}: {e}", file=sys.stderr)
        return {}


def extract_title_from_content(file_path: Path) -> str:
    """Extract title from first markdown heading."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#'):
                    return line.lstrip('#').strip()
        return file_path.stem
    except Exception:
        return file_path.stem


def list_rems_in_domain(domain_path: str) -> list:
    """
    Find all Rem files in a specific domain.

    Args:
        domain_path: Relative path from knowledge-base (e.g., "02-arts-and-humanities/...")

    Returns:
        List of dicts with rem metadata:
        [
            {
                "id": "rem-id",
                "title": "Rem Title",
                "file_path": "knowledge-base/.../file.md"
            },
            ...
        ]
    """
    domain_dir = KB_DIR / domain_path

    if not domain_dir.exists():
        raise ValueError(f"Domain directory not found: {domain_dir}")

    if not domain_dir.is_dir():
        raise ValueError(f"Not a directory: {domain_dir}")

    rems = []

    # Find all .md files in domain
    for md_file in domain_dir.glob("*.md"):
        # Skip hidden files and templates
        if md_file.name.startswith('.') or md_file.name.startswith('_'):
            continue

        # Extract metadata
        frontmatter = extract_frontmatter(md_file)

        # Get rem_id (prefer frontmatter, fallback to filename)
        rem_id = frontmatter.get('rem_id', md_file.stem)

        # Get title (prefer frontmatter, fallback to first heading)
        title = frontmatter.get('title')
        if not title:
            title = extract_title_from_content(md_file)

        rems.append({
            "id": rem_id,
            "title": title,
            "file_path": str(md_file.relative_to(ROOT))
        })

    return rems


def main():
    parser = argparse.ArgumentParser(
        description='List all Rems in a domain',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--domain-path',
        required=True,
        help='Domain path relative to knowledge-base (e.g., "0231-language-acquisition")'
    )

    parser.add_argument(
        '--output',
        required=True,
        help='Output JSON file path'
    )

    args = parser.parse_args()

    try:
        # List Rems
        rems = list_rems_in_domain(args.domain_path)

        # Write to output file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(rems, f, indent=2, ensure_ascii=False)

        print(f"✅ Listed {len(rems)} Rems from {args.domain_path}", file=sys.stderr)
        print(f"   Output: {output_path}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
