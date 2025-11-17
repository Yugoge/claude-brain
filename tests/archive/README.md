# Test Suite Organization

## Directory Structure

```
tests/
├── README.md           # This file
├── conftest.py         # Shared pytest configuration and fixtures
├── fixtures/           # Test data and sample files
├── unit/               # Unit tests (isolated component tests)
├── integration/        # Integration tests (multi-component interactions)
├── e2e/                # End-to-end tests (full workflows)
└── visual/             # Visual/UI tests (PDF extraction, rendering)
```

## Test Categories

### Unit Tests (`unit/`)
**Purpose**: Test individual components in isolation
**Characteristics**:
- Fast execution (< 1 second per test)
- No external dependencies
- No file I/O (use mocks/fixtures)
- High code coverage

**Naming Convention**: `test_<module>.py`

**Examples**:
- `test_fsrs_algorithm.py` - FSRS algorithm logic
- `test_classify_question.py` - Question classification
- `test_hooks.py` - Hook script behavior

### Integration Tests (`integration/`)
**Purpose**: Test interactions between multiple components
**Characteristics**:
- Moderate execution time (1-10 seconds)
- Tests component interactions
- May use real file I/O
- Tests data flow between modules

**Naming Convention**: `test_<feature>_integration.py`

**Examples**:
- `test_ask_integration.py` - /ask command workflow
- `test_analytics_engine.py` - Analytics with review data
- `test_graph_advanced_features.py` - Knowledge graph operations

### E2E Tests (`e2e/`)
**Purpose**: Test complete user workflows end-to-end
**Characteristics**:
- Slower execution (10+ seconds)
- Tests full system behavior
- Simulates real user scenarios
- May create/modify files

**Naming Convention**: `test_<workflow>_e2e.py`

**Examples**:
- `test_kb_init.py` - Full system initialization
- `test_edge_cases.py` - Edge case workflows
- `test-large-file-protection.sh` - File protection workflow

### Visual Tests (`visual/`)
**Purpose**: Test visual rendering and extraction
**Characteristics**:
- Tests PDF/image processing
- Tests visual output quality
- May involve rendering validation

**Naming Convention**: `test_<component>_visual.py`

**Examples**:
- `test_pdf_visual_extraction.py` - PDF page extraction

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run by Category
```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests
pytest tests/e2e/

# Visual tests
pytest tests/visual/
```

### Run Specific Test File
```bash
pytest tests/unit/test_fsrs_algorithm.py
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=scripts --cov-report=html
```

## Writing New Tests

### Test Structure (AAA Pattern)
```python
def test_feature_name():
    # Arrange: Set up test data
    input_data = {"key": "value"}

    # Act: Execute the functionality
    result = function_under_test(input_data)

    # Assert: Verify the outcome
    assert result == expected_value
```

### Naming Conventions
- Test files: `test_*.py`
- Test functions: `test_<specific_behavior>()`
- Test classes: `Test<Component>`

**Good test names**:
- `test_fsrs_calculates_interval_correctly()`
- `test_classify_returns_finance_domain_for_option_question()`
- `test_kb_init_creates_all_directories()`

**Bad test names**:
- `test_1()` - Not descriptive
- `test_it_works()` - Too vague
- `test_function()` - Doesn't describe behavior

### Using Fixtures
```python
import pytest

@pytest.fixture
def sample_rem():
    """Fixture providing a sample Rem for testing."""
    return {
        "id": "test-001",
        "content": "Test concept",
        "domain": "finance"
    }

def test_rem_processing(sample_rem):
    result = process_rem(sample_rem)
    assert result["id"] == "test-001"
```

### Shared Fixtures
Common fixtures are defined in `conftest.py` and are automatically available to all tests.

## Test Requirements

### All Tests Must
1. Be deterministic (same input → same output)
2. Be independent (can run in any order)
3. Clean up after themselves (no side effects)
4. Have descriptive names
5. Include docstrings explaining what they test

### Tests Should Not
1. Depend on external services (use mocks)
2. Depend on other tests
3. Modify production data
4. Have hardcoded timestamps
5. Use `time.sleep()` for synchronization (use proper waits)

## Coverage Goals

- **Unit Tests**: 70% of test suite (high coverage, fast execution)
- **Integration Tests**: 20% of test suite (critical paths)
- **E2E Tests**: 10% of test suite (key workflows)

**Minimum Coverage**:
- Overall: 80% code coverage
- Critical modules: 90% code coverage

## Continuous Integration

Tests run automatically on:
- Every commit (unit tests only)
- Pull requests (all tests)
- Scheduled builds (all tests + performance benchmarks)

## Debugging Failed Tests

### Run Failed Test with Full Output
```bash
pytest tests/unit/test_fsrs_algorithm.py -v --tb=long
```

### Run Failed Test with pdb
```bash
pytest tests/unit/test_fsrs_algorithm.py --pdb
```

### Run with Print Statements
```bash
pytest tests/unit/test_fsrs_algorithm.py -s
```

## Performance Testing

Performance-sensitive tests should include timing assertions:

```python
import time

def test_fsrs_batch_performance():
    start = time.time()

    # Run 1000 reviews
    for i in range(1000):
        fsrs.review(state, rating=3)

    elapsed = time.time() - start
    assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s"
```

## Test Data

### Fixtures Directory
- Sample PDFs: `fixtures/test-book.pdf`
- Corrupted data: `fixtures/corrupted.pdf`
- JSON samples: `fixtures/*.json`

### Creating Test Data
```python
import tempfile
import json

def test_with_temp_file():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"test": "data"}, f)
        temp_path = f.name

    try:
        # Run test with temp_path
        result = process_file(temp_path)
        assert result is not None
    finally:
        os.unlink(temp_path)
```

## Related Documentation

- **QA Validation**: `/root/knowledge-system/docs/qa/validation/` - Manual validation docs
- **Hooks Documentation**: `/root/knowledge-system/docs/architecture/hooks.md`
- **Story Requirements**: `/root/knowledge-system/docs/stories/` - Feature requirements

## Contributing

When adding new features:
1. Write unit tests first (TDD)
2. Add integration tests for component interactions
3. Add E2E tests for critical user workflows
4. Update this README if adding new test categories
5. Ensure all tests pass before committing

## Questions?

See pytest documentation: https://docs.pytest.org/
