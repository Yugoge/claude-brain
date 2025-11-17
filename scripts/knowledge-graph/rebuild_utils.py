#!/usr/bin/env python3
"""
Shared utilities for rebuild scripts.

Provides common functionality for backlinks, indexes, and schedule rebuild operations:
- Backup file management with timestamped copies
- Logging configuration with multiple verbosity levels
- YAML frontmatter parsing for Rem metadata extraction
- JSON file validation
- Atomic file write operations to prevent corruption
"""

import json
import shutil
import logging
import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


def create_backup(file_path: Path, backup_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Create timestamped backup of file.

    Args:
        file_path: Path to file to backup
        backup_dir: Optional custom backup directory (default: same as file)

    Returns:
        Path to backup file, or None if source doesn't exist

    Examples:
        >>> backup = create_backup(Path("backlinks.json"))
        >>> print(backup)
        backlinks.json.backup-20251027-143052
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')

    if backup_dir:
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{file_path.name}.backup-{timestamp}"
    else:
        backup_path = file_path.parent / f"{file_path.name}.backup-{timestamp}"

    shutil.copy2(file_path, backup_path)
    return backup_path


def setup_logging(script_name: str, verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """
    Setup logging configuration for rebuild scripts.

    Args:
        script_name: Name of script for log prefix
        verbose: Enable DEBUG level logging
        quiet: Minimize output (WARNING and above only)

    Returns:
        Configured logger instance
    """
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format=f'[{script_name}] %(levelname)s: %(message)s'
    )
    return logging.getLogger(script_name)


def parse_rem_frontmatter(file_path: Path) -> Dict[str, Any]:
    """
    Parse YAML frontmatter from Rem markdown file.

    Extracts metadata between --- delimiters at start of file.
    Uses simple key-value parsing to avoid YAML dependency.

    Args:
        file_path: Path to markdown file

    Returns:
        Dictionary of frontmatter fields, empty dict if no frontmatter

    Examples:
        >>> fm = parse_rem_frontmatter(Path("concept.md"))
        >>> print(fm['id'])
        option-delta
    """
    file_path = Path(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return {}

    # Check for frontmatter
    if not content.startswith('---'):
        return {}

    # Find end of frontmatter
    end_pos = content.find('\n---', 3)
    if end_pos == -1:
        return {}

    frontmatter_text = content[3:end_pos].strip()

    # Parse simple YAML-style key: value pairs
    frontmatter = {}
    for line in frontmatter_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            frontmatter[key] = value

    return frontmatter


def validate_json_file(file_path: Path) -> bool:
    """
    Validate JSON file syntax.

    Args:
        file_path: Path to JSON file to validate

    Returns:
        True if valid JSON, False otherwise
    """
    file_path = Path(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return False


def atomic_write_json(file_path: Path, data: Dict[str, Any], indent: int = 2) -> None:
    """
    Write JSON data atomically to prevent corruption.

    Writes to temporary file first, then atomically renames to target.
    This ensures the target file is never partially written.

    Args:
        file_path: Target file path
        data: Dictionary to write as JSON
        indent: JSON indentation level (default: 2)

    Raises:
        OSError: If write or rename fails
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory
    fd, temp_path = tempfile.mkstemp(
        dir=file_path.parent,
        prefix=f'.{file_path.name}.tmp-',
        text=True
    )

    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)

        # Atomic rename (POSIX guarantees atomicity)
        Path(temp_path).replace(file_path)
    except Exception:
        # Clean up temp file on error
        try:
            Path(temp_path).unlink()
        except Exception:
            pass
        raise


def check_disk_space(file_path: Path, required_mb: int = 10) -> bool:
    """
    Check if sufficient disk space available.

    Args:
        file_path: Path to check (uses filesystem of this path)
        required_mb: Required space in megabytes (default: 10)

    Returns:
        True if sufficient space, False otherwise
    """
    try:
        stat = os.statvfs(file_path.parent)
        available_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        return available_mb >= required_mb
    except Exception:
        # If check fails, assume sufficient space
        return True


def cleanup_old_backups(file_path: Path, keep_count: int = 5) -> int:
    """
    Remove old backup files, keeping only most recent N.

    Args:
        file_path: Original file path (backups have .backup-TIMESTAMP suffix)
        keep_count: Number of recent backups to keep (default: 5)

    Returns:
        Number of backups deleted
    """
    file_path = Path(file_path)
    backup_pattern = f"{file_path.name}.backup-*"

    # Sort by filename timestamp (not mtime, as copy2 preserves original mtime)
    backups = sorted(
        file_path.parent.glob(backup_pattern),
        key=lambda p: p.name,  # Filename format: xxx.backup-YYYYMMDD-HHMMSS
        reverse=True  # Most recent first (lexicographic sort works for timestamp format)
    )

    deleted = 0
    for backup in backups[keep_count:]:
        try:
            backup.unlink()
            deleted += 1
        except Exception:
            pass

    return deleted
