#!/usr/bin/env python3
"""
File Lock Utility for Safe Concurrent Access

Provides cross-platform file locking to prevent data corruption
when multiple processes write to the same file simultaneously.

Usage:
    from utils.file_lock import safe_write_json, FileLock

    # Automatic locking with context manager
    with FileLock('/path/to/file.json'):
        # Your file operations here
        pass

    # High-level JSON writer with automatic locking
    safe_write_json('/path/to/file.json', data)
"""

import fcntl
import json
import time
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict


class FileLock:
    """
    File lock using fcntl (POSIX systems).

    Provides exclusive lock to prevent concurrent writes.
    Automatically releases lock when exiting context.
    """

    def __init__(self, file_path: Path, timeout: int = 30):
        """
        Initialize file lock.

        Args:
            file_path: Path to file to lock
            timeout: Maximum seconds to wait for lock (default: 30)
        """
        self.file_path = Path(file_path)
        self.timeout = timeout
        self.lock_file = None
        self.lock_path = self.file_path.parent / f".{self.file_path.name}.lock"

    def __enter__(self):
        """Acquire lock (blocking with timeout)."""
        start_time = time.time()

        # Create lock file
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file = open(self.lock_path, 'w')

        # Try to acquire lock with timeout
        while True:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except IOError:
                if time.time() - start_time > self.timeout:
                    self.lock_file.close()
                    raise TimeoutError(
                        f"Could not acquire lock for {self.file_path} "
                        f"after {self.timeout}s. Another process may be using it."
                    )
                time.sleep(0.1)  # Wait 100ms before retry

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock."""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                # Clean up lock file
                if self.lock_path.exists():
                    self.lock_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors


def safe_write_json(
    file_path: Path,
    data: Dict[str, Any],
    indent: int = 2,
    timeout: int = 30,
    validator: callable = None
) -> None:
    """
    Safely write JSON with file locking and optional validation.

    Prevents data corruption from concurrent writes by:
    1. Running optional validator on data before write
    2. Acquiring exclusive file lock
    3. Writing to temporary file
    4. Atomic rename to target file
    5. Releasing lock

    Args:
        file_path: Path to JSON file
        data: Data to write (must be JSON-serializable)
        indent: JSON indentation (default: 2)
        timeout: Lock timeout in seconds (default: 30)
        validator: Optional callable(data) -> bool to validate before write
                   Raises ValueError if validation fails

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
        json.JSONEncodeError: If data is not JSON-serializable
        ValueError: If validator returns False or raises exception
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Run validator before acquiring lock (fail fast)
    if validator is not None:
        try:
            is_valid = validator(data)
            if not is_valid:
                raise ValueError(f"Data validation failed for {file_path}")
        except ValueError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise ValueError(f"Validator error: {e}")

    with FileLock(file_path, timeout=timeout):
        # Write to temporary file first
        temp_path = file_path.parent / f".{file_path.name}.tmp"

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
                f.flush()  # Ensure data is written to disk

            # Atomic rename (POSIX systems)
            temp_path.replace(file_path)

        except Exception:
            # Clean up temporary file on error
            if temp_path.exists():
                temp_path.unlink()
            raise


def safe_read_json(
    file_path: Path,
    default: Dict[str, Any] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Safely read JSON with file locking.

    Acquires shared lock to ensure consistent read
    (prevents reading during write).

    Args:
        file_path: Path to JSON file
        default: Default value if file doesn't exist
        timeout: Lock timeout in seconds (default: 30)

    Returns:
        Parsed JSON data or default value

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
        json.JSONDecodeError: If file contains invalid JSON
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return default if default is not None else {}

    with FileLock(file_path, timeout=timeout):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)


@contextmanager
def atomic_json_update(file_path: Path, timeout: int = 30):
    """
    Context manager for atomic JSON updates with proper locking.

    CRITICAL: This acquires the lock BEFORE reading to prevent race conditions.

    Usage:
        with atomic_json_update('data.json') as data:
            data['key'] = 'value'
            data['count'] += 1

    Args:
        file_path: Path to JSON file
        timeout: Lock timeout in seconds

    Yields:
        Dictionary with current JSON data (empty dict if file doesn't exist)
    """
    file_path = Path(file_path)

    # Acquire lock FIRST, then read-modify-write
    with FileLock(file_path, timeout=timeout):
        # Read current data AFTER acquiring lock
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}

        # Yield for modifications
        yield data

        # Write back atomically (still within lock)
        temp_path = file_path.parent / f".{file_path.name}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()

        # Atomic rename
        temp_path.replace(file_path)


# Example usage
if __name__ == '__main__':
    import sys

    # Demo: Safe concurrent writes
    test_file = Path('/tmp/test_lock.json')

    print(f"Writing to {test_file} with file lock...")

    with atomic_json_update(test_file) as data:
        data['timestamp'] = time.time()
        data['test'] = 'File lock works!'

    print(f"✅ Data written safely")

    # Read back
    result = safe_read_json(test_file)
    print(f"📖 Read back: {result}")

    # Cleanup
    test_file.unlink()
    print(f"🗑️  Cleaned up test file")
