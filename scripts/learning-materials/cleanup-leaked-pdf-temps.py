#!/usr/bin/env python3
"""
Cleanup Leaked PDF Temp Files
==============================

Finds and removes temporary PDF files created by extract-pdf-page-for-reading.py
that were not cleaned up due to crashes or interruptions.

Safety Features:
- Only removes files matching exact pattern: page_N_*.pdf
- Skips files modified in last 5 minutes (may be in use)
- Requires confirmation before deletion
- Reports all actions taken

Usage:
    source venv/bin/activate && source venv/bin/activate && python3 cleanup-leaked-pdf-temps.py              # Interactive
    source venv/bin/activate && source venv/bin/activate && python3 cleanup-leaked-pdf-temps.py --force      # No confirmation
    source venv/bin/activate && source venv/bin/activate && python3 cleanup-leaked-pdf-temps.py --dry-run    # Show only, don't delete
"""

import os
import sys
import glob
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta


def find_leaked_temp_files(temp_dir="/tmp", min_age_minutes=5):
    """
    Find temp PDF files matching pattern page_N_*.pdf.

    Args:
        temp_dir: Directory to search (default: /tmp)
        min_age_minutes: Minimum age in minutes before considering file leaked

    Returns:
        List of (file_path, age_minutes, size_bytes) tuples
    """
    pattern = os.path.join(temp_dir, "page_*.pdf")
    now = time.time()
    min_age_seconds = min_age_minutes * 60

    leaked_files = []

    for file_path in glob.glob(pattern):
        try:
            stat = os.stat(file_path)
            age_seconds = now - stat.st_mtime
            age_minutes = age_seconds / 60

            # Only include files older than minimum age
            if age_seconds >= min_age_seconds:
                leaked_files.append((
                    file_path,
                    age_minutes,
                    stat.st_size
                ))
        except (OSError, IOError):
            # File may have been deleted between glob and stat
            continue

    return leaked_files


def format_size(size_bytes):
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def format_age(age_minutes):
    """Format age in minutes as human-readable duration."""
    if age_minutes < 60:
        return f"{age_minutes:.0f} minutes"
    elif age_minutes < 1440:  # < 24 hours
        hours = age_minutes / 60
        return f"{hours:.1f} hours"
    else:
        days = age_minutes / 1440
        return f"{days:.1f} days"


def delete_files(file_list, dry_run=False):
    """
    Delete files from list.

    Args:
        file_list: List of (file_path, age_minutes, size_bytes) tuples
        dry_run: If True, don't actually delete

    Returns:
        (deleted_count, failed_count, total_size)
    """
    deleted_count = 0
    failed_count = 0
    total_size = 0

    for file_path, age_minutes, size_bytes in file_list:
        if dry_run:
            print(f"  [DRY RUN] Would delete: {os.path.basename(file_path)}")
            deleted_count += 1
            total_size += size_bytes
        else:
            try:
                os.unlink(file_path)
                print(f"  ✅ Deleted: {os.path.basename(file_path)}")
                deleted_count += 1
                total_size += size_bytes
            except (OSError, IOError) as e:
                print(f"  ❌ Failed: {os.path.basename(file_path)} - {e}")
                failed_count += 1

    return deleted_count, failed_count, total_size


def main():
    parser = argparse.ArgumentParser(
        description='Clean up leaked temporary PDF files from extraction process'
    )
    parser.add_argument(
        '--temp-dir',
        default='/tmp',
        help='Temporary directory to scan (default: /tmp)'
    )
    parser.add_argument(
        '--min-age',
        type=int,
        default=5,
        help='Minimum age in minutes before considering file leaked (default: 5)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )

    args = parser.parse_args()

    print("🔍 Scanning for leaked temporary PDF files...")
    print(f"   Directory: {args.temp_dir}")
    print(f"   Minimum age: {args.min_age} minutes")
    print()

    # Find leaked files
    leaked_files = find_leaked_temp_files(args.temp_dir, args.min_age)

    if not leaked_files:
        print("✅ No leaked temp files found!")
        print(f"   All temporary files are either recent (<{args.min_age} min) or cleaned up.")
        return 0

    # Display found files
    print(f"⚠️  Found {len(leaked_files)} leaked temp files:\n")

    total_size = sum(size for _, _, size in leaked_files)

    for file_path, age_minutes, size_bytes in leaked_files:
        filename = os.path.basename(file_path)
        print(f"  📄 {filename}")
        print(f"     Age: {format_age(age_minutes)}")
        print(f"     Size: {format_size(size_bytes)}")
        print()

    print(f"📊 Total: {len(leaked_files)} files, {format_size(total_size)}\n")

    # Confirmation
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be deleted\n")
        proceed = True
    elif args.force:
        print("⚡ FORCE MODE - Skipping confirmation\n")
        proceed = True
    else:
        response = input("❓ Delete these files? (yes/no): ").strip().lower()
        proceed = response in ['yes', 'y']

    if not proceed:
        print("❌ Cleanup cancelled.")
        return 1

    # Delete files
    print("\n🗑️  Cleaning up...\n")
    deleted_count, failed_count, cleaned_size = delete_files(leaked_files, args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("CLEANUP SUMMARY")
    print("=" * 60)

    if args.dry_run:
        print(f"  Would delete: {deleted_count} files")
        print(f"  Would free: {format_size(cleaned_size)}")
    else:
        print(f"  ✅ Deleted: {deleted_count} files")
        print(f"  ❌ Failed: {failed_count} files")
        print(f"  💾 Freed: {format_size(cleaned_size)}")

    if failed_count > 0:
        print(f"\n⚠️  {failed_count} files could not be deleted.")
        print("   Check permissions or if files are in use.")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
