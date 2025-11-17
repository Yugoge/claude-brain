#!/usr/bin/env python3
"""
Integration Test: Script Path Validation

Tests the validation of script paths across the entire codebase.
This ensures all documented scripts actually exist.

Author: Claude
Date: 2025-11-01
"""

import pytest
import sys
import subprocess
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT))


class TestScriptPathValidation:
    """Test suite for script path validation."""

    def test_validation_script_exists(self):
        """Test that the validation script exists."""
        script_path = ROOT / 'scripts' / 'validation' / 'validate-script-paths.py'
        assert script_path.exists(), f"Validation script not found at {script_path}"

    def test_fix_script_exists(self):
        """Test that the fix script exists."""
        script_path = ROOT / 'scripts' / 'validation' / 'fix-script-paths.py'
        assert script_path.exists(), f"Fix script not found at {script_path}"

    def test_validation_runs_successfully(self):
        """Test that validation script runs without errors."""
        result = subprocess.run(
            ['python3', 'scripts/validation/validate-script-paths.py', '--summary'],
            cwd=ROOT,
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Validation failed: {result.stderr}"

    def test_json_output_format(self):
        """Test that JSON output is valid."""
        import json
        result = subprocess.run(
            ['python3', 'scripts/validation/validate-script-paths.py', '--json'],
            cwd=ROOT,
            capture_output=True,
            text=True
        )

        try:
            data = json.loads(result.stdout)
            assert 'summary' in data
            assert 'valid' in data['summary']
            assert 'invalid' in data['summary']
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON output: {result.stdout}")

    def test_critical_scripts_exist(self):
        """Test that critical scripts referenced in commands exist."""
        critical_scripts = [
            'scripts/utilities/scan-and-populate-rems.py',
            'scripts/knowledge-graph/rebuild-backlinks.py',
            'scripts/review/review_loader.py',
            'scripts/review/review_scheduler.py',
            'scripts/review/fsrs_algorithm.py',
        ]

        for script in critical_scripts:
            script_path = ROOT / script
            assert script_path.exists(), f"Critical script missing: {script}"

    @pytest.mark.slow
    def test_dry_run_fix_does_not_modify(self):
        """Test that dry-run mode doesn't modify files."""
        # Get initial modification times
        test_file = ROOT / '.claude' / 'commands' / 'review.md'
        if test_file.exists():
            initial_mtime = test_file.stat().st_mtime

            # Run fix in dry-run mode
            subprocess.run(
                ['python3', 'scripts/validation/fix-script-paths.py', '--dry-run'],
                cwd=ROOT,
                capture_output=True
            )

            # Check file wasn't modified
            assert test_file.stat().st_mtime == initial_mtime, \
                "File was modified in dry-run mode"


if __name__ == '__main__':
    # Run tests with pytest if available, otherwise run basic tests
    try:
        import pytest
        pytest.main([__file__, '-v'])
    except ImportError:
        print("Running basic tests without pytest...")
        test = TestScriptPathValidation()
        test.test_validation_script_exists()
        test.test_fix_script_exists()
        test.test_critical_scripts_exist()
        print("✅ Basic tests passed")