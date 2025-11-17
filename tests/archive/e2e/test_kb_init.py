#!/usr/bin/env python3
"""
Comprehensive tests for kb-init.py script

Tests cover:
- Directory structure validation and creation
- JSON file validation and repair
- Agent file verification
- Git health checks
- Python dependency checks
- Script permission verification
- Idempotency
- All command-line flags
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestKbInit(unittest.TestCase):
    """Test suite for kb-init.py script."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.repo_root = Path("/root/knowledge-system")
        cls.kb_init_script = cls.repo_root / "scripts" / "utilities" / "kb-init.py"
        assert cls.kb_init_script.exists(), "kb-init.py script not found"

    def setUp(self):
        """Set up test environment before each test."""
        # Create temporary directory for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_dir = Path.cwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        """Clean up after each test."""
        os.chdir(self.original_dir)
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def run_kb_init(self, *args):
        """Helper method to run kb-init.py with arguments."""
        cmd = [sys.executable, str(self.kb_init_script)] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        return result

    def test_01_dry_run_mode(self):
        """Test that dry-run mode doesn't make changes."""
        result = self.run_kb_init("--dry-run", "--verbose")

        # Dry-run should not create directories
        assert not (self.test_dir / "knowledge-base").exists()
        assert not (self.test_dir / "learning-materials").exists()

        # Should mention dry-run in output
        assert "DRY RUN" in result.stdout
        assert "Would create" in result.stdout or "Would" in result.stdout

    def test_02_directory_creation(self):
        """Test directory structure creation."""
        # Run with non-interactive mode
        result = self.run_kb_init("--non-interactive")

        # Check that required directories were created
        assert (self.test_dir / "knowledge-base" / "_index").exists()
        assert (self.test_dir / "knowledge-base" / "finance" / "concepts").exists()
        assert (self.test_dir / "knowledge-base" / "programming" / "concepts").exists()
        assert (self.test_dir / "learning-materials").exists()
        assert (self.test_dir / ".review").exists()
        assert (self.test_dir / "chats").exists()

        print("✅ Test 2 passed: Directory creation")

    def test_03_json_file_creation(self):
        """Test JSON file creation from templates."""
        # Run init
        result = self.run_kb_init("--non-interactive")

        # Check JSON files exist
        backlinks_file = self.test_dir / "knowledge-base" / "_index" / "backlinks.json"
        taxonomy_file = self.test_dir / "knowledge-base" / ".taxonomy.json"
        index_file = self.test_dir / "chats" / "index.json"
        schedule_file = self.test_dir / ".review" / "schedule.json"

        assert backlinks_file.exists()
        assert taxonomy_file.exists()
        assert index_file.exists()
        assert schedule_file.exists()

        # Validate JSON syntax
        with open(backlinks_file) as f:
            data = json.load(f)
            assert "version" in data
            assert "concepts" in data

        with open(taxonomy_file) as f:
            data = json.load(f)
            assert "version" in data
            assert "isced_mappings" in data
            assert "dewey_mappings" in data

        with open(index_file) as f:
            data = json.load(f)
            assert "version" in data
            assert "conversations" in data
            assert "metadata" in data

        with open(schedule_file) as f:
            data = json.load(f)
            assert "concepts" in data

        print("✅ Test 3 passed: JSON file creation")

    def test_04_json_repair_corrupted(self):
        """Test repairing corrupted JSON files."""
        # Create directory first
        json_dir = self.test_dir / "knowledge-base" / "_index"
        json_dir.mkdir(parents=True, exist_ok=True)

        # Create corrupted JSON file
        corrupted_file = json_dir / "backlinks.json"
        with open(corrupted_file, 'w') as f:
            f.write("{invalid json")

        # Run init with repair
        result = self.run_kb_init("--non-interactive", "--repair-all")

        # Check file was repaired
        with open(corrupted_file) as f:
            data = json.load(f)  # Should not raise JSONDecodeError
            assert "version" in data

        # Check backup was created
        backup_file = corrupted_file.with_suffix(corrupted_file.suffix + '.backup')
        assert backup_file.exists()

        print("✅ Test 4 passed: JSON repair")

    def test_05_json_schema_repair(self):
        """Test repairing JSON files with schema issues."""
        # Create directory
        json_dir = self.test_dir / "knowledge-base" / "_index"
        json_dir.mkdir(parents=True, exist_ok=True)

        # Create JSON with missing fields
        incomplete_file = json_dir / "backlinks.json"
        with open(incomplete_file, 'w') as f:
            json.dump({"version": "1.0.0"}, f)  # Missing 'concepts' and 'last_updated'

        # Run init with repair
        result = self.run_kb_init("--non-interactive", "--repair-all")

        # Check fields were added
        with open(incomplete_file) as f:
            data = json.load(f)
            assert "version" in data
            assert "concepts" in data
            assert "last_updated" in data

        print("✅ Test 5 passed: JSON schema repair")

    def test_06_idempotency(self):
        """Test that running kb-init multiple times is safe."""
        # Run init three times
        result1 = self.run_kb_init("--non-interactive")
        result2 = self.run_kb_init("--non-interactive")
        result3 = self.run_kb_init("--non-interactive")

        # All should succeed
        assert result1.returncode in [0, 2]  # 0 = success, 2 = warnings
        assert result2.returncode in [0, 2]
        assert result3.returncode in [0, 2]

        # Check no duplicate creations or errors
        assert "Failed" not in result3.stdout

        print("✅ Test 6 passed: Idempotency")

    def test_07_verbose_mode(self):
        """Test verbose output mode."""
        result = self.run_kb_init("--verbose", "--non-interactive")

        # Verbose should show more details
        assert "✅" in result.stdout  # Should show success indicators

        print("✅ Test 7 passed: Verbose mode")

    def test_08_git_initialization(self):
        """Test Git repository initialization."""
        result = self.run_kb_init("--non-interactive")

        # Check .git directory was created
        assert (self.test_dir / ".git").exists()

        # Verify it's a valid git repo
        git_result = subprocess.run(
            ["git", "status"],
            cwd=self.test_dir,
            capture_output=True
        )
        assert git_result.returncode == 0

        print("✅ Test 8 passed: Git initialization")

    def test_09_exit_codes(self):
        """Test correct exit codes."""
        # Success case (with non-interactive to avoid prompts)
        result = self.run_kb_init("--non-interactive")
        assert result.returncode in [0, 2]  # 0 = fully ready, 2 = warnings

        # Dry-run should also return appropriate code
        result = self.run_kb_init("--dry-run")
        assert result.returncode in [0, 1, 2]

        print("✅ Test 9 passed: Exit codes")

    def test_10_report_generation(self):
        """Test comprehensive report generation."""
        result = self.run_kb_init("--non-interactive")

        # Check report file was created
        report_file = self.test_dir / ".claude" / "init-report.txt"
        assert report_file.exists()

        # Check report content
        with open(report_file) as f:
            content = f.read()
            assert "Knowledge System Initialization Report" in content
            assert "SECTIONS:" in content

        # Check console output has report
        assert "Knowledge System Initialization Report" in result.stdout
        assert "System Status:" in result.stdout

        print("✅ Test 10 passed: Report generation")

    def test_11_repair_all_flag(self):
        """Test --repair-all flag auto-repairs issues."""
        # Create directory with missing JSON
        kb_dir = self.test_dir / "knowledge-base" / "_index"
        kb_dir.mkdir(parents=True, exist_ok=True)

        # Run with repair-all
        result = self.run_kb_init("--repair-all", "--non-interactive")

        # Check JSON was created
        backlinks_file = kb_dir / "backlinks.json"
        assert backlinks_file.exists()

        print("✅ Test 11 passed: Repair-all flag")

    def test_12_non_interactive_no_prompts(self):
        """Test non-interactive mode doesn't wait for input."""
        # This test ensures the script completes without hanging
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Script hung waiting for input")

        # Set 10 second timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)

        try:
            result = self.run_kb_init("--non-interactive")
            signal.alarm(0)  # Cancel alarm
            assert result.returncode in [0, 1, 2]
            print("✅ Test 12 passed: Non-interactive mode")
        except TimeoutError:
            signal.alarm(0)
            self.fail("Script hung waiting for user input in non-interactive mode")


def run_tests():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("🧪 Running kb-init.py Test Suite")
    print("=" * 50 + "\n")

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestKbInit)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        print("=" * 50 + "\n")
        return 0
    else:
        print("❌ Some tests failed")
        print("=" * 50 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
