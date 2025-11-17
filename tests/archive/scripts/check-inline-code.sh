#!/bin/bash
# Quick check for inline Python code in command files

echo "Checking for inline Python code patterns..."

# Check for python3 -c patterns
if grep -r "python3 -c" .claude/commands/*.md 2>/dev/null; then
    echo "❌ FAILED: Found inline Python code!"
    exit 1
fi

# Check for python -c patterns
if grep -r "python -c" .claude/commands/*.md 2>/dev/null; then
    echo "❌ FAILED: Found inline Python code!"
    exit 1
fi

echo "✅ PASSED: No inline code patterns found"
exit 0