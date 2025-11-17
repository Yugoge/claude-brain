#!/usr/bin/env python3
"""
Comprehensive Test Suite for PDF Visual Extraction
===================================================

Tests the extract-pdf-page-for-reading.py script covering:
- Happy path extraction
- Edge cases (invalid inputs, out of range)
- Error handling
- Cleanup verification
- Integration scenarios

Requirements:
- pytest
- PyPDF2
"""

import pytest
import os
import sys
import tempfile
import signal
import subprocess
import time
from pathlib import Path

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "learning-materials"
sys.path.insert(0, str(SCRIPTS_DIR))

# Import using importlib to handle hyphenated filename
import importlib.util
spec = importlib.util.spec_from_file_location(
    "extract_pdf_page_for_reading",
    SCRIPTS_DIR / "extract-pdf-page-for-reading.py"
)
extraction_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extraction_module)

extract_single_page_to_temp = extraction_module.extract_single_page_to_temp
validate_inputs = extraction_module.validate_inputs
TempFileGuard = extraction_module.TempFileGuard


# Fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_PDF = FIXTURES_DIR / "test-book.pdf"
CORRUPTED_PDF = FIXTURES_DIR / "corrupted.pdf"


class TestInputValidation:
    """Test input validation logic."""

    def test_validate_valid_inputs(self):
        """Test validation passes for valid inputs."""
        error = validate_inputs(str(TEST_PDF), 0)
        assert error is None

    def test_validate_empty_path(self):
        """Test validation fails for empty PDF path."""
        error = validate_inputs("", 0)
        assert error is not None
        assert "cannot be empty" in error

    def test_validate_nonexistent_file(self):
        """Test validation fails for non-existent file."""
        error = validate_inputs("/tmp/nonexistent.pdf", 0)
        assert error is not None
        assert "does not exist" in error

    def test_validate_non_pdf_file(self):
        """Test validation fails for non-PDF file."""
        # Create temp non-PDF file
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_path = f.name

        try:
            error = validate_inputs(temp_path, 0)
            assert error is not None
            assert "not a PDF" in error
        finally:
            os.unlink(temp_path)

    def test_validate_negative_page_number(self):
        """Test validation fails for negative page numbers."""
        error = validate_inputs(str(TEST_PDF), -1)
        assert error is not None
        assert "negative" in error


class TestSinglePageExtraction:
    """Test single page extraction (happy path)."""

    def test_extract_first_page(self):
        """Test extracting first page (page 0)."""
        result = extract_single_page_to_temp(str(TEST_PDF), 0)

        assert result["success"] is True
        assert result["page_num"] == 0
        assert result["temp_file"] is not None
        assert os.path.exists(result["temp_file"])
        assert result["file_size_mb"] > 0
        assert result["total_pages_in_source"] == 3

        # Cleanup
        os.unlink(result["temp_file"])

    def test_extract_middle_page(self):
        """Test extracting middle page (page 1)."""
        result = extract_single_page_to_temp(str(TEST_PDF), 1)

        assert result["success"] is True
        assert result["page_num"] == 1
        assert os.path.exists(result["temp_file"])

        # Cleanup
        os.unlink(result["temp_file"])

    def test_extract_last_page(self):
        """Test extracting last page (page 2)."""
        result = extract_single_page_to_temp(str(TEST_PDF), 2)

        assert result["success"] is True
        assert result["page_num"] == 2
        assert os.path.exists(result["temp_file"])

        # Cleanup
        os.unlink(result["temp_file"])

    def test_temp_file_naming(self):
        """Test temp files have correct naming pattern."""
        result = extract_single_page_to_temp(str(TEST_PDF), 0)

        temp_file = result["temp_file"]
        filename = os.path.basename(temp_file)

        # Should match pattern: page_{page_num+1}_*.pdf
        assert filename.startswith("page_1_")
        assert filename.endswith(".pdf")

        # Cleanup
        os.unlink(temp_file)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_extract_page_out_of_range(self):
        """Test extracting page beyond PDF page count."""
        result = extract_single_page_to_temp(str(TEST_PDF), 999)

        assert result["success"] is False
        assert "out of range" in result["error"]
        assert result["temp_file"] is None

    def test_extract_from_corrupted_pdf(self):
        """Test extraction from corrupted PDF file."""
        result = extract_single_page_to_temp(str(CORRUPTED_PDF), 0)

        assert result["success"] is False
        assert "error" in result
        assert result["temp_file"] is None

    def test_extract_from_nonexistent_file(self):
        """Test extraction from non-existent file."""
        result = extract_single_page_to_temp("/tmp/nonexistent.pdf", 0)

        assert result["success"] is False
        assert "does not exist" in result["error"]


class TestTempFileCleanup:
    """Test temp file cleanup mechanisms."""

    def test_temp_file_guard_context_manager(self):
        """Test TempFileGuard cleans up files on context exit."""
        temp_files = []

        with TempFileGuard() as guard:
            # Extract 3 pages
            for page_num in range(3):
                result = extract_single_page_to_temp(str(TEST_PDF), page_num)
                assert result["success"] is True
                temp_files.append(result["temp_file"])
                guard.register(result["temp_file"])

                # Verify files exist during context
                assert os.path.exists(result["temp_file"])

        # Verify all files cleaned up after context exit
        for temp_file in temp_files:
            assert not os.path.exists(temp_file), f"Leaked temp file: {temp_file}"

    def test_temp_file_guard_cleanup_on_exception(self):
        """Test TempFileGuard cleans up even on exceptions."""
        temp_file = None

        try:
            with TempFileGuard() as guard:
                result = extract_single_page_to_temp(str(TEST_PDF), 0)
                temp_file = result["temp_file"]
                guard.register(temp_file)

                # Raise exception during context
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify file cleaned up despite exception
        assert not os.path.exists(temp_file), "Temp file not cleaned up after exception"

    def test_multiple_page_workflow_no_leaks(self):
        """Test 10-page workflow leaves no leaked files."""
        # Count temp files before
        temp_dir = Path(tempfile.gettempdir())
        before_count = len(list(temp_dir.glob("page_*.pdf")))

        # Extract and cleanup 10 times
        for page_num in range(3):
            for _ in range(3):  # Do it 3 times per page = 9 total
                result = extract_single_page_to_temp(str(TEST_PDF), page_num)
                assert result["success"] is True

                # Immediate cleanup
                os.unlink(result["temp_file"])

        # Count temp files after
        after_count = len(list(temp_dir.glob("page_*.pdf")))

        assert after_count == before_count, f"Leaked {after_count - before_count} temp files"


class TestInterruptHandling:
    """Test signal interrupt handling."""

    def test_cleanup_on_sigterm(self):
        """Test temp files cleaned up on SIGTERM."""
        # This test requires subprocess to properly test signal handling
        script = f"""
import sys
import os
import signal
import importlib.util

# Import extraction module
spec = importlib.util.spec_from_file_location(
    "extract_pdf_page_for_reading",
    "/root/knowledge-system/scripts/extract-pdf-page-for-reading.py"
)
extraction_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extraction_module)

with extraction_module.TempFileGuard() as guard:
    result = extraction_module.extract_single_page_to_temp(
        '/root/knowledge-system/tests/fixtures/test-book.pdf',
        0
    )
    temp_file = result['temp_file']
    guard.register(temp_file)

    # Signal parent process we're ready
    print(f"READY:{{temp_file}}", flush=True)

    # Wait for signal
    import time
    time.sleep(10)
"""

        proc = subprocess.Popen(
            ["python3", "-c", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for script to create temp file
        temp_file = None
        try:
            # Read with timeout
            import select
            ready, _, _ = select.select([proc.stdout], [], [], 3)
            if ready:
                line = proc.stdout.readline().strip()
                if line.startswith("READY:"):
                    temp_file = line.split(":", 1)[1]

            # Verify temp file exists
            assert temp_file is not None, "Script didn't signal ready with temp file"
            assert os.path.exists(temp_file), "Temp file not created"

            # Send SIGTERM
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=2)

            # Verify temp file cleaned up
            time.sleep(0.5)  # Give cleanup time to run
            assert not os.path.exists(temp_file), "Temp file not cleaned up on SIGTERM"

        finally:
            try:
                proc.kill()
            except:
                pass


class TestBatchPerformance:
    """Test performance characteristics."""

    def test_50_page_extraction_performance(self):
        """Test 50-page extraction completes within 2 minutes."""
        start_time = time.time()

        # Extract 3 pages x 17 times = 51 total extractions
        for _ in range(17):
            for page_num in range(3):
                result = extract_single_page_to_temp(str(TEST_PDF), page_num)
                assert result["success"] is True

                # Cleanup immediately
                os.unlink(result["temp_file"])

        elapsed_time = time.time() - start_time

        # Should complete in under 120 seconds (2 minutes)
        assert elapsed_time < 120, f"Performance test failed: {elapsed_time:.1f}s > 120s"

        print(f"\n✅ 51 page extractions completed in {elapsed_time:.1f}s "
              f"({elapsed_time/51:.2f}s per page)")


class TestRetryLogic:
    """Test retry logic for transient failures."""

    def test_retry_on_io_error(self, monkeypatch):
        """Test retry logic with simulated IOError."""
        call_count = 0
        original_reader = None

        def mock_pdf_reader(pdf_path):
            nonlocal call_count, original_reader
            call_count += 1

            # Fail first 2 attempts, succeed on 3rd
            if call_count < 3:
                raise IOError("Simulated transient I/O error")

            # Import here to avoid circular import
            from PyPDF2 import PdfReader
            return PdfReader(pdf_path)

        # Monkey patch PdfReader
        monkeypatch.setattr(
            extraction_module,
            'PdfReader',
            mock_pdf_reader
        )

        # Should succeed after retries
        result = extract_single_page_to_temp(str(TEST_PDF), 0, max_retries=3)

        assert call_count == 3, "Should have retried twice"
        assert result["success"] is True

        # Cleanup
        if result["temp_file"]:
            os.unlink(result["temp_file"])


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
