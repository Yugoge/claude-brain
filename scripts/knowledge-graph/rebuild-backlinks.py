#!/usr/bin/env python3
"""
Rebuild Backlinks Script

Scans all Rems in knowledge-base/ and rebuilds bidirectional link index.
Parses [[wikilink]] patterns and frontmatter to create comprehensive link graph.

Usage:
    python3 scripts/rebuild-backlinks.py [options]

Options:
    --dry-run           Preview changes without writing
    --verbose           Enable DEBUG logging
    --quiet             Minimize output (warnings only)
    --backup-dir DIR    Custom backup directory
    --no-backup         Skip backup creation
    --cleanup-backups N Keep only N most recent backups

Examples:
    # Standard rebuild with backup
    python3 scripts/rebuild-backlinks.py

    # Preview without writing
    python3 scripts/rebuild-backlinks.py --dry-run

    # Verbose output for debugging
    python3 scripts/rebuild-backlinks.py --verbose

    # Custom backup location
    python3 scripts/rebuild-backlinks.py --backup-dir /backups
"""

import json
import re
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).parent
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT / "scripts"))

from rebuild_utils import (
    create_backup,
    setup_logging,
    parse_rem_frontmatter,
    atomic_write_json,
    check_disk_space,
    cleanup_old_backups
)
from utils.file_lock import FileLock

# Constants
ROOT = Path(__file__).parent.parent.parent
KB_DIR = ROOT / "knowledge-base"
IDX_DIR = KB_DIR / "_index"
BACKLINKS_PATH = IDX_DIR / "backlinks.json"

# Regex for wikilinks: [[concept-id]]
LINK_RE = re.compile(r'\[\[([a-z0-9\-]+)\]\]', re.IGNORECASE)

# Regex for typed wikilinks: [[concept-id]] {rel: relation_type}
# Example: [[put-option]] {rel: antonym}
TYPED_LINK_RE = re.compile(
    r"\[\[([a-z0-9\-]+)\]\]\s*\{[^}]*rel\s*:\s*([a-z_\-]+)[^}]*\}",
    re.IGNORECASE,
)

# Regex for Related Rems section markdown links with optional typing
# Example: [Title](filename.md) {rel: quantitative-formula}
# Matches both with and without {rel: ...} annotation
RELATED_REMS_LINK_RE = re.compile(
    r"\[([^\]]+)\]\(([^\)]+\.md)\)(?:\s*\{[^}]*rel\s*:\s*([a-z_\-]+)[^}]*\})?",
    re.IGNORECASE,
)


def scan_rems(kb_path: Path) -> List[Path]:
    """
    Scan knowledge base for all Rem markdown files (recursively).

    Args:
        kb_path: Root knowledge base directory

    Returns:
        List of paths to all .md files (excluding _* directories and backups)
    """
    rem_files = []

    if not kb_path.exists():
        return rem_files

    # Recursively find all .md files
    for md_file in kb_path.rglob('*.md'):
        # Skip template/index/backup directories
        if any(part.startswith('_') or 'backup' in part.lower()
               for part in md_file.parts):
            continue
        rem_files.append(md_file)

    return sorted(rem_files)


def extract_wikilinks(content: str) -> List[str]:
    """
    Extract [[wikilink]] patterns from markdown content.

    Args:
        content: Markdown text

    Returns:
        List of concept IDs found in wikilinks (deduplicated, order preserved)
    """
    matches = LINK_RE.findall(content)
    # Normalize to lowercase and deduplicate while preserving order
    seen = set()
    links = []
    for match in matches:
        normalized = match.lower()
        if normalized not in seen:
            seen.add(normalized)
            links.append(normalized)
    return links


def extract_typed_links(content: str) -> List[Dict[str, str]]:
    """
    Extract typed wikilinks of the form [[id]] {rel: type} from markdown content.

    Returns a list of dictionaries: {"to": concept_id, "type": relation_type}
    Deduplicates by (to, type) while preserving first-seen order.
    """
    typed_matches = TYPED_LINK_RE.findall(content)
    seen_pairs = set()
    typed_links: List[Dict[str, str]] = []
    for to_id, rel_type in typed_matches:
        to_norm = to_id.lower()
        type_norm = rel_type.lower()
        key = (to_norm, type_norm)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        typed_links.append({"to": to_norm, "type": type_norm})
    return typed_links


def extract_related_rems_links(content: str) -> List[Dict[str, str]]:
    """
    Extract markdown links from Related Rems section.
    Format: [Title](filename.md) {rel: type} or [Title](filename.md)

    Extracts rem_id from filename. If filename contains subdomain prefix (e.g.,
    'fx-derivatives-039-name.md'), extracts the numeric portion and base name.
    Otherwise uses the full stem as rem_id.

    Returns list of dicts: {"to": rem_id, "type": relation_type or "related"}
    """
    # Find Related Rems section
    related_section_match = re.search(
        r'##\s+Related\s+Rems\s*\n(.*?)(?=\n##|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )

    if not related_section_match:
        return []

    related_section = related_section_match.group(1)
    matches = RELATED_REMS_LINK_RE.findall(related_section)

    seen_pairs = set()
    related_links: List[Dict[str, str]] = []

    for title, filename, rel_type in matches:
        # Extract rem_id from filename
        stem = Path(filename).stem

        # Try to extract rem_id from frontmatter-style naming
        # Pattern: subdomain-NNN-rem-id.md or NNN-rem-id.md
        # We want to extract the part after the number prefix
        id_match = re.match(r'^(?:[a-z\-]+\-)?(\d{3}\-)?(.+)$', stem, re.IGNORECASE)
        if id_match:
            rem_id = id_match.group(2) if id_match.group(2) else stem
        else:
            rem_id = stem

        rem_id = rem_id.lower()
        type_str = rel_type.lower() if rel_type else "related"

        key = (rem_id, type_str)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        related_links.append({"to": rem_id, "type": type_str})

    return related_links


def get_concept_id(file_path: Path, frontmatter: Dict[str, str]) -> str:
    """
    Get concept ID from frontmatter or filename fallback.

    Args:
        file_path: Path to Rem file
        frontmatter: Parsed frontmatter dictionary

    Returns:
        Concept ID (lowercase)
    """
    # Try frontmatter first (check both 'rem_id' and 'id')
    if 'rem_id' in frontmatter:
        return frontmatter['rem_id'].lower()
    if 'id' in frontmatter:
        return frontmatter['id'].lower()

    # Fallback to filename without extension
    return file_path.stem.lower()


def detect_cycles(graph: Dict[str, Dict], logger) -> List[List[str]]:
    """
    Detect cycles in the link graph using DFS.

    Args:
        graph: Link graph (concept_id -> {links_to, ...})
        logger: Logger instance

    Returns:
        List of cycles, where each cycle is a list of concept IDs
    """
    cycles = []
    visited = set()
    rec_stack = set()  # Recursion stack for cycle detection

    def dfs(node: str, path: List[str]) -> None:
        """DFS helper with path tracking."""
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            cycles.append(cycle)
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        # Explore neighbors
        node_data = graph.get(node, {})
        for neighbor in node_data.get('links_to', []):
            if neighbor in graph:  # Only follow valid links
                dfs(neighbor, path.copy())

        rec_stack.remove(node)

    # Run DFS from each unvisited node
    for concept_id in graph.keys():
        if concept_id not in visited:
            dfs(concept_id, [])

    # Log cycles if found
    if cycles:
        logger.warning(f"Found {len(cycles)} cycle(s) in link graph:")
        for i, cycle in enumerate(cycles, 1):
            cycle_str = ' → '.join(cycle)
            logger.warning(f"  Cycle {i}: {cycle_str}")
        logger.warning("These circular references won't break the system but may affect navigation.")

    return cycles


def build_backlink_graph(rem_files: List[Path], logger) -> Tuple[Dict[str, Dict], Set[str], Dict[str, Dict[str, str]]]:
    """
    Build bidirectional link graph from Rem files.

    Args:
        rem_files: List of paths to Rem markdown files
        logger: Logger instance for output

    Returns:
        Tuple of (link graph dict, set of broken link IDs, concepts metadata)
    """
    graph: Dict[str, Dict] = {}
    broken_links: Set[str] = set()
    concepts_meta: Dict[str, Dict[str, str]] = {}

    # First pass: collect all concept IDs and forward links
    concept_files: Dict[str, Path] = {}  # concept_id -> file_path
    forward_links: Dict[str, List[str]] = {}  # concept_id -> [target_ids]
    typed_forward_links: Dict[str, List[Dict[str, str]]] = {}  # concept_id -> [{to, type}]

    for file_path in rem_files:
        try:
            # Parse frontmatter
            frontmatter = parse_rem_frontmatter(file_path)

            # Get concept ID
            concept_id = get_concept_id(file_path, frontmatter)

            # Read full content for wikilink extraction
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract wikilinks
            links = extract_wikilinks(content)
            typed_links = extract_typed_links(content)
            related_rems_links = extract_related_rems_links(content)

            # Merge typed links from both sources
            # Related Rems section takes precedence (explicit curation)
            all_typed_links = related_rems_links + typed_links

            # Deduplicate by (to, type) keeping first occurrence
            seen_pairs = set()
            deduped_typed: List[Dict[str, str]] = []
            for link in all_typed_links:
                key = (link["to"], link["type"])
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    deduped_typed.append(link)

            # Store data
            concept_files[concept_id] = file_path
            forward_links[concept_id] = links
            typed_forward_links[concept_id] = deduped_typed

            # Concept metadata
            title = frontmatter.get('title', concept_id)
            # Store KB-relative POSIX path for portability
            try:
                rel_path = file_path.relative_to(KB_DIR).as_posix()
            except ValueError:
                # Fallback to POSIX path if not under KB_DIR
                rel_path = file_path.as_posix()
            concepts_meta[concept_id] = {
                "title": title,
                "file": rel_path,
            }

            logger.debug(f"Processed {concept_id}: {len(links)} links")

        except Exception as e:
            logger.warning(f"Failed to process {file_path}: {e}")
            continue

    # Build graph with forward and backward links
    all_concept_ids = set(concept_files.keys())

    for concept_id in all_concept_ids:
        links_to = forward_links.get(concept_id, [])

        # Check for broken links
        for target_id in links_to:
            if target_id not in all_concept_ids:
                broken_links.add(target_id)
                logger.warning(f"Broken link: [[{target_id}]] referenced by {concept_id}")

        graph[concept_id] = {
            "links_to": links_to,
            "typed_links_to": typed_forward_links.get(concept_id, []),
            "linked_from": [],
            "typed_linked_from": [],
            "inferred_links_to": [],  # two-hop inferred, untyped
        }

    # Second pass: build backward links
    for concept_id, data in graph.items():
        for target_id in data["links_to"]:
            if target_id in graph:
                graph[target_id]["linked_from"].append(concept_id)

        for typed in data.get("typed_links_to", []):
            target_id = typed.get("to")
            if target_id in graph:
                graph[target_id]["typed_linked_from"].append({
                    "from": concept_id,
                    "type": typed.get("type", "related")
                })

    # Third pass: build simple two-hop inferred links A->B->C => A => C
    for a_id, a_data in graph.items():
        inferred: List[Dict[str, str]] = []
        direct_set = set(a_data.get("links_to", []))
        for b_id in a_data.get("links_to", []):
            b_data = graph.get(b_id)
            if not b_data:
                continue
            for c_id in b_data.get("links_to", []):
                if c_id == a_id:
                    continue
                if c_id in direct_set:
                    continue
                # Avoid duplicates by (to, via)
                inferred.append({"to": c_id, "via": b_id})
        # Deduplicate by (to, via)
        seen_iv = set()
        deduped: List[Dict[str, str]] = []
        for item in inferred:
            key = (item["to"], item["via"])
            if key in seen_iv:
                continue
            seen_iv.add(key)
            deduped.append(item)
        a_data["inferred_links_to"] = deduped

    # Fourth pass: detect cycles (for monitoring, non-blocking)
    cycles = detect_cycles(graph, logger)

    return graph, broken_links, concepts_meta


def generate_backlinks_json(graph: Dict[str, Dict], broken_links: Set[str], concepts_meta: Dict[str, Dict[str, str]]) -> Dict:
    """
    Generate final backlinks.json structure.

    Args:
        graph: Bidirectional link graph
        broken_links: Set of broken link IDs

    Returns:
        Complete backlinks.json data structure
    """
    total_links = sum(len(data["links_to"]) for data in graph.values())

    return {
        "version": "1.1.0",
        "description": "Bidirectional link index for all knowledge Rems, with typed and inferred links",
        "links": graph,
        "concepts": concepts_meta,
        "metadata": {
            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total_concepts": len(graph),
            "total_links": total_links,
            "broken_links": sorted(broken_links)
        }
    }


def main():
    """Main entry point for rebuild-backlinks script."""
    parser = argparse.ArgumentParser(
        description='Rebuild bidirectional backlinks index',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing files')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable DEBUG level logging')
    parser.add_argument('--quiet', action='store_true',
                        help='Minimize output (warnings only)')
    parser.add_argument('--backup-dir', type=str,
                        help='Custom backup directory')
    parser.add_argument('--no-backup', action='store_true',
                        help='Skip backup creation')
    parser.add_argument('--cleanup-backups', type=int, metavar='N',
                        help='Keep only N most recent backups')

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging('rebuild-backlinks', verbose=args.verbose, quiet=args.quiet)

    try:
        # Scan for Rem files
        logger.info(f"Scanning {KB_DIR} for Rem files...")
        rem_files = scan_rems(KB_DIR)
        logger.info(f"Found {len(rem_files)} Rem files")

        if not rem_files:
            logger.warning("No Rem files found. Backlinks index will be empty.")

        # Build backlink graph
        logger.info("Building backlink graph...")
        graph, broken_links, concepts_meta = build_backlink_graph(rem_files, logger)
        logger.info(f"Built graph with {len(graph)} concepts")

        if broken_links:
            logger.warning(f"Found {len(broken_links)} broken links: {sorted(broken_links)}")

        # Generate output structure
        output = generate_backlinks_json(graph, broken_links, concepts_meta)

        # Dry-run mode
        if args.dry_run:
            logger.info("DRY RUN - would write to " + str(BACKLINKS_PATH))
            logger.info(f"Total concepts: {output['metadata']['total_concepts']}")
            logger.info(f"Total links: {output['metadata']['total_links']}")
            return 0

        # Check disk space
        if not check_disk_space(BACKLINKS_PATH, required_mb=1):
            logger.error("Insufficient disk space")
            return 3

        # Create backup
        if not args.no_backup and BACKLINKS_PATH.exists():
            backup_dir = Path(args.backup_dir) if args.backup_dir else None
            backup_path = create_backup(BACKLINKS_PATH, backup_dir)
            if backup_path:
                logger.info(f"Created backup: {backup_path}")

        # Write new index atomically WITH FILE LOCK
        IDX_DIR.mkdir(parents=True, exist_ok=True)

        # Use file lock to prevent concurrent writes
        with FileLock(BACKLINKS_PATH, timeout=60):
            atomic_write_json(BACKLINKS_PATH, output)
        logger.info(f"✅ Backlinks rebuilt: {BACKLINKS_PATH}")

        # Cleanup old backups
        if args.cleanup_backups:
            deleted = cleanup_old_backups(BACKLINKS_PATH, keep_count=args.cleanup_backups)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old backup(s)")

        return 0

    except KeyboardInterrupt:
        logger.error("Interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
