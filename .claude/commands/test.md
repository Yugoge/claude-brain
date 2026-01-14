# Test Command

Test validation workflow with edge case detection, systematic validation, and quality enforcement.

## Usage

```bash
/test [--check-only | --fix-all | --validate]
```

## Options

- `--check-only` - Run validators without fixing violations (default)
- `--fix-all` - Run validators and auto-fix violations where possible
- `--validate` - Run validation and generate detailed report

## What It Does

1. **Runs all validators** from `tests/scripts/validate-*.py`
2. **Applies exclusions** - Skips documentation directories to prevent false positives:
   - `docs/` - Pedagogical code examples
   - `chats/` - Conversation archives
   - `knowledge-base/` - Learning materials
   - `tests/edge-cases/` - Historical records
   - `INDEX.md` files - Directory documentation
3. **Generates report** - Structured JSON report with violations and recommendations
4. **Identifies edge cases** - Detects patterns that violate development standards

## Edge Cases Detected

### Critical (P0)
- **EC-claude-001**: Hardcoded workflow steps
- **EC-claude-002**: Forced follow-up mechanisms
- **EC005**: Inline Python code (`python -c`, heredocs)

### Major (P1)
- **EC-claude-003**: Hardcoded extraction counts
- **EC-claude-004**: Missing venv usage validation
- **EC-claude-005**: User correction enforcement gaps
- **EC001**: Python invocations without venv activation
- **EC006**: Chinese content in functional code

### High (P2)
- **EC-kb-001**: Inverted semantic relations
- **EC004**: Hardcoded values (workflows, messages, defaults)

### Medium (P3)
- **EC-kb-002**: Inconsistent Rem file naming
- Directory structure violations
- File naming conventions

## Exclusion System

The test command uses the centralized exclusion configuration from `tests/config/exclusions.py` to prevent false positives.

**Why exclude documentation?**

Documentation often contains:
- **Bad practice examples** - "DON'T do this" code samples
- **Format analysis** - Quoted code showing inconsistencies
- **Historical records** - Git commit documentation
- **External references** - Code from other projects

These are pedagogical, not violations to fix.

**Impact of exclusions**:
- Before: 1,988 violations (71% false positives)
- After: ~25 legitimate violations
- Reduction: 98.7% false positives prevented

## Implementation

You MUST use the test-executor agent to run tests:

```markdown
I'll use the test-executor agent to run systematic validation.
```

Then launch the agent:
- **Agent**: test-executor
- **Tools**: All tools (Read, Write, Edit, Bash, Glob, Grep, etc.)
- **Task**: Execute validators with exclusions, generate report

The agent will:
1. Run `tests/scripts/run-all-validators.sh`
2. Validators automatically use `tests/config/exclusions.py`
3. Generate structured execution report
4. Return results and recommendations

## Report Format

Execution reports are saved to `tests/reports/execution-report-test-YYYYMMDD-HHMMSS.json`:

```json
{
  "request_id": "test-20260113-103138",
  "timestamp": "2026-01-13T12:42:44Z",
  "executor": {
    "status": "completed",
    "total_duration_seconds": 7866
  },
  "results": [
    {
      "validator": "validate-venv-usage",
      "edge_case": "EC001",
      "priority": "P0",
      "status": "fail",
      "violations_count": 14,
      "violations": [...]
    }
  ],
  "summary": {
    "total_validators": 20,
    "passed": 16,
    "failed": 4,
    "total_violations": 25
  }
}
```

## Common Issues

### Issue 1: False Positives in Documentation

**Problem**: Validators report violations in docs/, chats/, knowledge-base/

**Solution**: Already handled! The exclusion system prevents this.

**Verification**:
```bash
source ~/.claude/venv/bin/activate && python3 tests/scripts/validate-venv-usage.py --project-root .
# Should show ~14 violations (not 1,777)
```

### Issue 2: Validators Missing Exclusions

**Problem**: New validators don't use exclusion configuration

**Solution**: Add imports to new validators:
```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.exclusions import filter_files

# In validator function:
files = find_files(project_root, patterns)
files = filter_files(files, project_root)  # ← Apply exclusions
```

## Examples

### Example 1: Check Only

```bash
/test
```

Runs all validators, reports violations, no fixes.

### Example 2: With Fix

```bash
/test --fix-all
```

Runs validators and attempts to auto-fix violations where scripts exist.

### Example 3: Validation Report

```bash
/test --validate
```

Generates detailed validation report with edge case analysis.

## Developer Notes

### Adding New Validators

1. Create `tests/scripts/validate-{name}.py`
2. Import exclusion configuration:
   ```python
   sys.path.insert(0, str(Path(__file__).parent.parent))
   from config.exclusions import filter_files
   ```
3. Apply exclusions to file list:
   ```python
   files = filter_files(files, project_root)
   ```
4. Return JSON result with violations

### Adding New Exclusions

Edit `tests/config/exclusions.py`:

```python
EXCLUDED_DIRS = [
    'docs/',
    'chats/',
    'knowledge-base/',
    'new-directory/',  # ← Add here with comment explaining why
]
```

Document rationale in `tests/config/README.md`.

## Related Commands

- `/maintain` - Run knowledge base maintenance
- `/save` - Save learning session (includes validation)
- `/kb-init` - Initialize knowledge system

## Git History

- **2026-01-13**: Created test command with exclusion system
  - Prevents 1,400+ false positives from documentation
  - Centralized exclusion configuration
  - 98.7% reduction in false positives

## See Also

- `tests/config/README.md` - Exclusion system documentation
- `tests/config/exclusions.py` - Exclusion configuration
- `tests/scripts/run-all-validators.sh` - Test runner script
- `docs/architecture/test-validation.md` - Test system architecture (if exists)
