#!/bin/bash
# fix-ec001-docs.sh - Add venv activation to Python calls in documentation files
#
# Usage: ./fix-ec001-docs.sh [--dry-run]
#
# This script fixes EC001 violations in .md files by adding venv activation prefix

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "=== DRY RUN MODE - No changes will be made ==="
  echo ""
fi

# Fix Python calls in Markdown code blocks
# Pattern: python3 or python (without prior venv activation)
#
# Examples to fix:
#   python3 script.py
#   python script.py arg1 arg2
#   $(python3 -c "...")
#
# Already correct (skip):
#   source venv/bin/activate && python3 script.py
#   source ~/.claude/venv/bin/activate && python3 script.py

fix_md_file() {
  local file="$1"
  local temp_file="${file}.tmp"
  local changes=0

  # Use awk for more precise line-by-line processing
  awk '
  BEGIN { in_code_block = 0 }

  # Track code block boundaries
  /^```/ { in_code_block = !in_code_block; print; next }

  # Only process lines in code blocks or command examples
  {
    line = $0

    # Skip if already has venv activation
    if (line ~ /source.*venv.*activate.*&&.*python/) {
      print line
      next
    }

    # Pattern 1: Standalone python3/python at start of line
    if (line ~ /^[[:space:]]*(python3?[[:space:]]|python3?$)/) {
      sub(/^([[:space:]]*)(python3?)/, "\\1source venv/bin/activate && \\2", line)
      changes++
    }
    # Pattern 2: python3/python after shell operators
    else if (line ~ /[|&;][[:space:]]*python3?[[:space:]]/) {
      gsub(/([|&;][[:space:]]*)(python3?)/, "\\1source venv/bin/activate && \\2", line)
      changes++
    }
    # Pattern 3: $(python3 ...) subshells
    else if (line ~ /\$\(python3?[[:space:]]/) {
      gsub(/\$\((python3?)/, "$(source venv/bin/activate && \\1", line)
      changes++
    }

    print line
  }

  END { exit changes }
  ' "$file" > "$temp_file"

  if [ $? -gt 0 ]; then
    if [ "$DRY_RUN" = true ]; then
      echo "Would fix: $file"
      rm "$temp_file"
    else
      mv "$temp_file" "$file"
      echo "Fixed: $file"
    fi
    return 1
  else
    rm "$temp_file"
    return 0
  fi
}

# Find all .md files (exclude venv, knowledge-base, node_modules)
echo "Searching for Markdown files with Python violations..."

md_files=$(find "$PROJECT_ROOT" \
  -type f -name "*.md" \
  ! -path "*/venv/*" \
  ! -path "*/node_modules/*" \
  ! -path "*/.git/*" \
  ! -path "*/knowledge-base/*" \
  2>/dev/null || echo "")

total_files=0
fixed_files=0

for file in $md_files; do
  if [ -f "$file" ]; then
    ((total_files++))
    if fix_md_file "$file"; then
      :  # No changes needed
    else
      ((fixed_files++))
    fi
  fi
done

echo ""
echo "=== Summary ==="
echo "Files checked: $total_files"
echo "Files modified: $fixed_files"

if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "This was a dry run. Run without --dry-run to apply changes."
fi
