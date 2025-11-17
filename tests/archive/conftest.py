"""
Shared pytest configuration and fixtures for all tests.

This file is automatically loaded by pytest and makes fixtures
available to all test files without needing to import them.
"""

import pytest
import tempfile
import shutil
import json
import sys
from pathlib import Path
from datetime import datetime

# Add scripts directory and all subdirectories to Python path for all tests
REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Add main scripts directory
sys.path.insert(0, str(SCRIPTS_DIR))

# Add all subdirectories
for subdir in ['review', 'knowledge-graph', 'memory', 'learning-materials',
               'analytics', 'adaptive', 'learning-goals', 'validation',
               'utilities', 'hooks']:
    subdir_path = SCRIPTS_DIR / subdir
    if subdir_path.exists():
        sys.path.insert(0, str(subdir_path))


# ============================================================================
# Directory and File Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Provides a temporary directory that is cleaned up after the test."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_file():
    """Provides a temporary file that is cleaned up after the test."""
    fd, temp_path = tempfile.mkstemp()
    yield Path(temp_path)
    try:
        Path(temp_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def fixtures_dir():
    """Provides path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_pdf(fixtures_dir):
    """Provides path to the test PDF file."""
    return fixtures_dir / "test-book.pdf"


@pytest.fixture
def corrupted_pdf(fixtures_dir):
    """Provides path to the corrupted PDF file."""
    return fixtures_dir / "corrupted.pdf"


# ============================================================================
# FSRS Fixtures
# ============================================================================

@pytest.fixture
def fsrs_algorithm():
    """Provides a FSRS algorithm instance with default parameters."""
    from fsrs_algorithm import FSRSAlgorithm
    return FSRSAlgorithm()


@pytest.fixture
def sample_review_state():
    """Provides a sample review state for testing."""
    return {
        "difficulty": 5.0,
        "stability": 10.0,
        "retrievability": 0.9,
        "interval": 7,
        "review_count": 3,
        "last_review": datetime.now().isoformat()
    }


@pytest.fixture
def sample_schedule():
    """Provides a sample review schedule."""
    return {
        "concepts": {
            "test-concept-001": {
                "id": "test-concept-001",
                "title": "Test Concept 1",
                "domain": "finance",
                "next_review": datetime.now().isoformat(),
                "difficulty": 5.0,
                "stability": 10.0,
                "review_count": 2
            },
            "test-concept-002": {
                "id": "test-concept-002",
                "title": "Test Concept 2",
                "domain": "programming",
                "next_review": datetime.now().isoformat(),
                "difficulty": 3.0,
                "stability": 15.0,
                "review_count": 5
            }
        }
    }


# ============================================================================
# Knowledge Base Fixtures
# ============================================================================

@pytest.fixture
def sample_rem():
    """Provides a sample Rem (knowledge concept)."""
    return {
        "id": "test-rem-001",
        "title": "Call Option",
        "content": "A call option gives the buyer the right to buy an asset.",
        "domain": "finance",
        "sub_domain": "derivatives",
        "tags": ["options", "derivatives", "financial-instruments"],
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat()
    }


@pytest.fixture
def sample_backlinks():
    """Provides a sample backlinks structure."""
    return {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat(),
        "concepts": {
            "call-option": {
                "path": "knowledge-base/finance/concepts/call-option.md",
                "incoming": [
                    {
                        "from": "put-option",
                        "type": "contrasts_with",
                        "context": "Call options vs put options"
                    }
                ],
                "outgoing": [
                    {
                        "to": "option-contract",
                        "type": "is_type_of",
                        "context": "Call option is a type of option contract"
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_taxonomy():
    """Provides a sample taxonomy structure."""
    return {
        "version": "1.0.0",
        "isced_mappings": {
            "finance": {
                "broad": "04",
                "narrow": "041",
                "detailed": "0411",
                "name": "Accounting and taxation"
            },
            "programming": {
                "broad": "06",
                "narrow": "061",
                "detailed": "0613",
                "name": "Software and applications development"
            }
        },
        "dewey_mappings": {
            "finance": {
                "main": "330",
                "division": "332",
                "hierarchy": ["300 Social Sciences", "330 Economics", "332 Financial economics"]
            },
            "programming": {
                "main": "000",
                "division": "005",
                "hierarchy": ["000 Computer science", "005 Computer programming"]
            }
        }
    }


# ============================================================================
# Classification Fixtures
# ============================================================================

@pytest.fixture
def question_classifier():
    """Provides a QuestionClassifier instance."""
    from classify_question import QuestionClassifier
    return QuestionClassifier()


@pytest.fixture
def sample_classification_result():
    """Provides a sample classification result."""
    return {
        "domain": "finance",
        "confidence": 75.5,
        "suggested_domains": ["finance", "economics"],
        "isced": {
            "broad": "04",
            "narrow": "041",
            "detailed": "0411",
            "name": "Accounting and taxation"
        },
        "dewey": {
            "main": "330",
            "division": "332",
            "hierarchy": ["300 Social Sciences", "330 Economics", "332 Financial economics"]
        },
        "message": "High confidence classification"
    }


# ============================================================================
# Test Data Generators
# ============================================================================

@pytest.fixture
def make_temp_json():
    """Factory fixture for creating temporary JSON files."""
    created_files = []

    def _make_temp_json(data, suffix='.json'):
        fd, temp_path = tempfile.mkstemp(suffix=suffix)
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2)
        created_files.append(temp_path)
        return Path(temp_path)

    yield _make_temp_json

    # Cleanup
    for path in created_files:
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass


@pytest.fixture
def make_temp_markdown():
    """Factory fixture for creating temporary Markdown files."""
    created_files = []

    def _make_temp_markdown(content, frontmatter=None):
        fd, temp_path = tempfile.mkstemp(suffix='.md')

        full_content = ""
        if frontmatter:
            full_content = "---\n"
            for key, value in frontmatter.items():
                full_content += f"{key}: {value}\n"
            full_content += "---\n\n"

        full_content += content

        with open(temp_path, 'w') as f:
            f.write(full_content)

        created_files.append(temp_path)
        return Path(temp_path)

    yield _make_temp_markdown

    # Cleanup
    for path in created_files:
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass


# ============================================================================
# pytest Configuration
# ============================================================================

def pytest_configure(config):
    """pytest configuration hook."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "visual: marks tests as visual/rendering tests"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Get the relative path from tests/
        rel_path = Path(item.fspath).relative_to(Path(__file__).parent)

        # Auto-mark based on directory
        if "integration" in rel_path.parts:
            item.add_marker(pytest.mark.integration)
        elif "e2e" in rel_path.parts:
            item.add_marker(pytest.mark.e2e)
        elif "visual" in rel_path.parts:
            item.add_marker(pytest.mark.visual)
        elif "unit" in rel_path.parts:
            # Unit tests get no special marker (they're the default)
            pass


# ============================================================================
# Utility Functions
# ============================================================================

@pytest.fixture
def assert_json_valid():
    """Provides a function to assert JSON file validity."""
    def _assert_json_valid(file_path):
        with open(file_path) as f:
            data = json.load(f)  # Will raise if invalid
        return data
    return _assert_json_valid


@pytest.fixture
def assert_file_exists():
    """Provides a function to assert file existence."""
    def _assert_file_exists(file_path):
        path = Path(file_path)
        assert path.exists(), f"File does not exist: {file_path}"
        return path
    return _assert_file_exists
