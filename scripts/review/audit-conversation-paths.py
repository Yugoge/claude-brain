#!/usr/bin/env python3
"""
Audit conversation_source paths in Rem files.

Purpose: Validate that conversation_source paths in Rem files point to existing files
Root Cause: Commit c11f968 added conversation_source feature, but path errors can occur
Strategy: Scan all Rem files, extract source field, resolve paths, check existence

Usage:
    python audit-conversation-paths.py [--fix] [--domain <domain-path>]

Options:
    --fix: Attempt to auto-correct paths (removes suffixes like -3, -2, etc)
    --domain: Limit audit to specific domain (e.g., 04-business-administration-and-law)

Output: Report of broken paths and fixes applied
Exit Codes:
    0 = All paths valid (or fixed if --fix used)
    1 = Invalid paths found and not fixed
    2 = Script error
"""

import sys
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_BASE = PROJECT_ROOT / "knowledge-base"


def extract_source_path(rem_file: Path) -> Optional[str]:
    """
    Extract source path from Rem file frontmatter.

    Args:
        rem_file: Path to Rem file

    Returns:
        Source path string or None if not found
    """
    try:
        with open(rem_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract frontmatter
        frontmatter_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL | re.MULTILINE)
        if not frontmatter_match:
            return None

        frontmatter = frontmatter_match.group(1)

        # Extract source field
        source_match = re.search(r'^source:\s*(.+)$', frontmatter, re.MULTILINE)
        if not source_match:
            return None

        return source_match.group(1).strip()

    except Exception as e:
        print(f"Error reading {rem_file}: {e}", file=sys.stderr)
        return None


def resolve_source_path(rem_file: Path, source_path: str) -> Path:
    """
    Resolve relative source path to absolute path.

    Args:
        rem_file: Path to Rem file (for relative path resolution)
        source_path: Source path from frontmatter (relative or absolute)

    Returns:
        Absolute path to conversation file
    """
    if Path(source_path).is_absolute():
        return Path(source_path)

    # Handle relative paths starting with ../ (relative to Rem file location)
    if source_path.startswith('..'):
        return (rem_file.parent / source_path).resolve()

    # Otherwise resolve from PROJECT_ROOT (new standard format)
    return (PROJECT_ROOT / source_path).resolve()


def find_alternative_path(conversation_path: Path) -> Optional[Path]:
    """
    Find alternative path by removing suffixes like -3, -2, etc.

    Args:
        conversation_path: Path that doesn't exist

    Returns:
        Alternative path if found, None otherwise
    """
    # Extract base name without suffix
    # Example: derivatives-contract-expiry-2025-11-21-3.md → derivatives-contract-expiry-2025-11-21.md
    stem = conversation_path.stem  # derivatives-contract-expiry-2025-11-21-3
    suffix = conversation_path.suffix  # .md

    # Remove trailing -N pattern
    match = re.match(r'^(.+)-(\d+)$', stem)
    if not match:
        return None

    base_stem = match.group(1)  # derivatives-contract-expiry-2025-11-21
    alternative = conversation_path.parent / f"{base_stem}{suffix}"

    if alternative.exists():
        return alternative

    return None


def fix_rem_source_path(rem_file: Path, old_path: str, new_path: str) -> bool:
    """
    Update source path in Rem file.

    Args:
        rem_file: Path to Rem file
        old_path: Old source path to replace
        new_path: New source path

    Returns:
        True if successful, False otherwise
    """
    try:
        with open(rem_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace source path in frontmatter
        # Use re.escape to handle special chars in path
        pattern = rf'^(source:\s*){re.escape(old_path)}$'
        replacement = rf'\1{new_path}'
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if new_content == content:
            return False  # No change made

        with open(rem_file, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return True

    except Exception as e:
        print(f"Error fixing {rem_file}: {e}", file=sys.stderr)
        return False


def audit_rem_files(domain_filter: Optional[str] = None, fix: bool = False) -> Tuple[List[Dict], List[Dict]]:
    """
    Audit all Rem files for conversation_source path validity.

    Args:
        domain_filter: Optional domain path to limit audit scope
        fix: If True, attempt to auto-correct paths

    Returns:
        Tuple of (invalid_paths, fixed_paths)
    """
    invalid_paths = []
    fixed_paths = []

    # Determine search path
    search_path = KNOWLEDGE_BASE / domain_filter if domain_filter else KNOWLEDGE_BASE

    if not search_path.exists():
        print(f"Error: Domain path not found: {search_path}", file=sys.stderr)
        sys.exit(2)

    # Find all Rem files
    rem_files = list(search_path.rglob("*.md"))

    print(f"Auditing {len(rem_files)} Rem files...")

    for rem_file in rem_files:
        # Skip non-Rem files (e.g., README.md)
        if rem_file.name.startswith('.') or rem_file.name.upper() == 'README.MD':
            continue

        # Extract source path
        source_path = extract_source_path(rem_file)
        if not source_path:
            continue  # No source field

        # Resolve to absolute path
        resolved_path = resolve_source_path(rem_file, source_path)

        # Check existence
        if not resolved_path.exists():
            # Invalid path found
            invalid_entry = {
                "rem_file": str(rem_file.relative_to(PROJECT_ROOT)),
                "source_path": source_path,
                "resolved_path": str(resolved_path),
                "error": "File not found"
            }

            # Try to find alternative
            alternative = find_alternative_path(resolved_path)

            if alternative:
                invalid_entry["alternative_found"] = str(alternative)

                if fix:
                    # Calculate new relative path from Rem location
                    try:
                        new_relative = alternative.relative_to(rem_file.parent)
                        new_relative_str = str(new_relative)

                        # Fix the Rem file
                        if fix_rem_source_path(rem_file, source_path, new_relative_str):
                            fixed_paths.append({
                                "rem_file": str(rem_file.relative_to(PROJECT_ROOT)),
                                "old_path": source_path,
                                "new_path": new_relative_str,
                                "status": "fixed"
                            })
                            continue  # Fixed, don't add to invalid list
                        else:
                            invalid_entry["fix_error"] = "Failed to update Rem file"
                    except ValueError:
                        # Alternative not relative to rem_file, use absolute
                        invalid_entry["fix_error"] = "Cannot create relative path"
            else:
                invalid_entry["alternative_found"] = None

            invalid_paths.append(invalid_entry)

    return invalid_paths, fixed_paths


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Audit conversation_source paths in Rem files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Audit all Rem files
    python audit-conversation-paths.py

    # Audit specific domain
    python audit-conversation-paths.py --domain 04-business-administration-and-law

    # Audit and fix invalid paths
    python audit-conversation-paths.py --fix

    # Audit and fix specific domain
    python audit-conversation-paths.py --fix --domain 04-business-administration-and-law
        """
    )

    parser.add_argument('--fix', action='store_true', help='Auto-correct invalid paths')
    parser.add_argument('--domain', type=str, help='Limit audit to specific domain')

    args = parser.parse_args()

    # Run audit
    invalid_paths, fixed_paths = audit_rem_files(args.domain, args.fix)

    # Print report
    print("\n" + "="*80)
    print("AUDIT REPORT")
    print("="*80)

    if fixed_paths:
        print(f"\n✅ FIXED PATHS ({len(fixed_paths)}):")
        for entry in fixed_paths:
            print(f"  - {entry['rem_file']}")
            print(f"    Old: {entry['old_path']}")
            print(f"    New: {entry['new_path']}")

    if invalid_paths:
        print(f"\n❌ INVALID PATHS ({len(invalid_paths)}):")
        for entry in invalid_paths:
            print(f"  - {entry['rem_file']}")
            print(f"    Source: {entry['source_path']}")
            print(f"    Resolved: {entry['resolved_path']}")
            print(f"    Error: {entry['error']}")
            if entry.get('alternative_found'):
                print(f"    Alternative: {entry['alternative_found']}")
                if 'fix_error' in entry:
                    print(f"    Fix Error: {entry['fix_error']}")
            else:
                print(f"    Alternative: Not found")
    else:
        print(f"\n✅ ALL PATHS VALID")

    print("\n" + "="*80)
    print(f"Total audited: {len(invalid_paths) + len(fixed_paths)}")
    print(f"Fixed: {len(fixed_paths)}")
    print(f"Invalid: {len(invalid_paths)}")
    print("="*80 + "\n")

    # Exit with appropriate code
    if invalid_paths:
        sys.exit(1)  # Invalid paths found
    else:
        sys.exit(0)  # All valid (or fixed)


if __name__ == "__main__":
    main()
