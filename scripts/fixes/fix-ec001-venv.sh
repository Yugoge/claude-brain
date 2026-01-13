#!/bin/bash
# fix-ec001-venv.sh - Automatically add venv activation to Python calls
#
# Usage: ./fix-ec001-venv.sh [--dry-run] [--verbose]
#
# This script fixes EC001 violations by prefixing Python calls with venv activation

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
DRY_RUN=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--dry-run] [--verbose]"
      exit 1
      ;;
  esac
done

log() {
  if [ "$VERBOSE" = true ]; then
    echo "[INFO] $*"
  fi
}

# Patterns to fix (Python calls without venv activation)
# We need to be careful not to break existing correct patterns

fix_file() {
  local file="$1"
  local changes=0

  # Skip if file already has venv activation in most lines
  local python_lines=$(grep -c "python3\|python " "$file" 2>/dev/null || echo "0")
  local venv_lines=$(grep -c "source.*venv.*activate.*python" "$file" 2>/dev/null || echo "0")

  if [ "$python_lines" -eq 0 ]; then
    return 0
  fi

  # If most lines already have venv, skip
  if [ "$venv_lines" -gt $((python_lines / 2)) ]; then
    log "Skipping $file (already mostly fixed)"
    return 0
  fi

  # Create backup
  cp "$file" "$file.bak"

  # Fix patterns:
  # 1. Standalone python3/python commands
  # 2. Commands in backticks or $()
  # 3. Commands in bash -c

  # Pattern 1: python3 script.py (not already prefixed)
  sed -i 's/^\([[:space:]]*\)\(python3\? [^|&;]*\)$/\1source venv\/bin\/activate \&\& \2/' "$file" && ((changes++)) || true

  # Pattern 2: $(python3 ...) → $(source venv/bin/activate && python3 ...)
  sed -i 's/\$(\(python3\? [^)]*\))/$(source venv\/bin\/activate \&\& \1)/' "$file" && ((changes++)) || true

  # Pattern 3: `python3 ...` → `source venv/bin/activate && python3 ...`
  sed -i 's/`\(python3\? [^`]*\)`/`source venv\/bin\/activate \&\& \1`/' "$file" && ((changes++)) || true

  if [ "$changes" -gt 0 ]; then
    echo "Fixed $changes patterns in: $file"
    if [ "$DRY_RUN" = true ]; then
      # Restore from backup in dry-run mode
      mv "$file.bak" "$file"
    else
      rm "$file.bak"
    fi
  else
    rm "$file.bak"
  fi

  return 0
}

# Find all files with Python calls (excluding venv, tests/edge-cases docs, knowledge-base)
echo "Searching for files with Python violations..."

files_to_fix=$(find "$PROJECT_ROOT" \
  -type f \
  \( -name "*.md" -o -name "*.sh" \) \
  ! -path "*/venv/*" \
  ! -path "*/node_modules/*" \
  ! -path "*/.git/*" \
  ! -path "*/tests/edge-cases/*" \
  ! -path "*/knowledge-base/*" \
  -exec grep -l "python3\|python " {} \; 2>/dev/null || echo "")

total_files=$(echo "$files_to_fix" | wc -l)
echo "Found $total_files files to check"

if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "=== DRY RUN MODE ==="
  echo "No files will be modified"
  echo ""
fi

fixed_count=0
for file in $files_to_fix; do
  if [ -f "$file" ]; then
    fix_file "$file" && ((fixed_count++)) || true
  fi
done

echo ""
echo "=== Summary ==="
echo "Files checked: $total_files"
echo "Files modified: $fixed_count"

if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "This was a dry run. Run without --dry-run to apply changes."
fi
