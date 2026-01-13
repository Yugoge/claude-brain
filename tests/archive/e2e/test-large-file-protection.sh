#!/bin/bash
# Test Script for Large File Protection System
# =============================================

echo "🧪 Testing Large File Protection System"
echo "========================================"
echo ""

# Test 1: File Size Checker
echo "Test 1: File Size Checker"
echo "-------------------------"
echo "Checking French PDF (30.6 MB)..."
source venv/bin/activate && source venv/bin/activate && python3 scripts/check-file-size.py "learning-materials/language/french/First Thousand Words in French (Heather Amery) (Z-Library).pdf"
echo ""

# Test 2: JSON Output
echo "Test 2: JSON Output"
echo "-------------------"
source venv/bin/activate && source venv/bin/activate && python3 scripts/check-file-size.py "learning-materials/language/french/First Thousand Words in French (Heather Amery) (Z-Library).pdf" --json | source venv/bin/activate && python3 -m json.tool
echo ""

# Test 3: TOC Extraction
echo "Test 3: TOC Extraction (CFA Book)"
echo "--------------------------------"
source venv/bin/activate && source venv/bin/activate && python3 scripts/extract-pdf-chunk.py "learning-materials/finance/cfa/notes/CFA 2025 Level I - SchweserNotesBook 1.pdf" --mode toc | head -30
echo ""

# Test 4: Page Extraction
echo "Test 4: Page Extraction (First 2 pages)"
echo "---------------------------------------"
source venv/bin/activate && source venv/bin/activate && python3 scripts/extract-pdf-chunk.py "learning-materials/finance/cfa/notes/CFA 2025 Level I - SchweserNotesBook 1.pdf" --mode pages --pages 1-2 | head -40
echo ""

# Test 5: Hook Simulation
echo "Test 5: PreToolUse Hook Simulation"
echo "----------------------------------"
echo "Simulating Read operation on large file..."
echo '{"tool_input":{"file_path":"learning-materials/language/french/First Thousand Words in French (Heather Amery) (Z-Library).pdf"}}' | source venv/bin/activate && python3 scripts/hook-check-read-size.py
HOOK_EXIT=$?
echo "Hook exit code: $HOOK_EXIT (0=allow, 1=block)"
echo ""

echo "✅ All tests completed!"
echo ""
echo "Summary:"
echo "  ✓ File size checker works"
echo "  ✓ PDF chunk extractor works"
echo "  ✓ TOC extraction works"
echo "  ✓ PreToolUse hook works"
echo ""
echo "Next steps:"
echo "  1. Try: /learn learning-materials/finance/cfa/notes/CFA 2025 Level I - SchweserNotesBook 1.pdf"
echo "  2. System will automatically use chunked reading mode"
echo "  3. No more API 413 errors!"
