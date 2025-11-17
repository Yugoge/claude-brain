---
description: "View learning progress across all materials or specific domains"
allowed-tools: Bash, Read, TodoWrite
argument-hint: "[domain | file-path]"
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Progress Command

View learning progress across all materials or specific domains.

## Usage

```
/progress
/progress <domain>
/progress <file-path>
```

## Examples

```
/progress                                    # Overall progress summary
/progress finance                            # Finance domain progress
/progress learning-materials/finance/options.pdf  # Specific material
```

## What This Command Does

1. **Reads progress data** from `.progress.md` files and `.index.json`
2. **Calculates statistics** (completion %, concepts learned, time spent)
3. **Displays learning trajectory** and recommendations
4. **Shows upcoming reviews** from FSRS schedule

## Implementation

Execute the progress display script:

```bash
source venv/bin/activate && python scripts/progress/display_progress.py "$@"
```

The script performs:
1. Parse arguments - Detects mode (overview | domain | material path)
2. Load data - Reads `.index.json`, `schedule.json`, `history.json`, KB metadata
3. Calculate statistics - Materials count, concepts learned, time spent, streak, review status
4. Format output - Generates dashboard with ASCII progress bars and charts
5. Generate recommendations - Personalized suggestions based on learning patterns

Script modules:
- `scripts/progress/display_progress.py` - Main entry point
- `scripts/progress/progress_calculator.py` - Statistics calculation (`ProgressCalculator` class)
- `scripts/progress/progress_formatter.py` - Output formatting (`ProgressFormatter` class)
- `scripts/progress/recommendation_engine.py` - Recommendations (`RecommendationEngine` class)

Supported modes:
- `/progress` - Overview dashboard (all materials, all domains)
- `/progress finance` - Domain-specific progress
- `/progress learning-materials/finance/options.pdf` - Individual material progress

## Notes

- Progress data is cached in `.index.json` for performance
- Recalculate on demand with `/progress --refresh`
- Charts and graphs use ASCII art (terminal-friendly)
- Recommendations are personalized based on learning patterns
- Goal: Provide motivation and clarity on learning progress
