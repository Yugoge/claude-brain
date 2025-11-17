#!/bin/bash
"""
Run All Validation Scripts

This script runs all validation scripts in the validation directory
and generates a comprehensive report.

Usage:
    ./scripts/validation/run-all-validations.sh [--fix]

Options:
    --fix    Auto-fix issues where possible

Author: Claude
Date: 2025-11-01
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."

echo -e "${BOLD}================================${NC}"
echo -e "${BOLD}Knowledge System Validation Suite${NC}"
echo -e "${BOLD}================================${NC}"
echo ""

# Track overall status
ALL_PASSED=true

# Function to run a validation script
run_validation() {
    local script_name=$1
    local description=$2

    echo -e "${BLUE}Running: ${description}${NC}"
    echo -e "Script: ${script_name}"
    echo "---"

    if [ -f "$SCRIPT_DIR/$script_name" ]; then
        if source venv/bin/activate && python "$SCRIPT_DIR/$script_name" --summary 2>&1; then
            echo -e "${GREEN}✅ PASSED${NC}"
        else
            echo -e "${RED}❌ FAILED${NC}"
            ALL_PASSED=false
        fi
    else
        echo -e "${YELLOW}⚠️  SKIPPED (script not found)${NC}"
    fi
    echo ""
}

# Run all validation scripts
echo -e "${BOLD}1. Script Path Validation${NC}"
run_validation "validate-script-paths.py" "Validate all script references in documentation"

echo -e "${BOLD}2. Conversation Index Validation${NC}"
run_validation "validate-conversation-index.py" "Validate conversation index structure"

echo -e "${BOLD}3. Taxonomy Validation${NC}"
run_validation "validate-taxonomy.py" "Validate knowledge taxonomy structure"

echo -e "${BOLD}4. Rem Format Validation${NC}"
run_validation "check_rem_formats.py" "Check Rem file formats"

echo -e "${BOLD}5. YAML Frontmatter Validation${NC}"
run_validation "validate-yaml-frontmatter.py" "Validate YAML frontmatter in markdown files"

echo -e "${BOLD}6. Rem Size Validation${NC}"
run_validation "validate-rem-size.py" "Validate Rem sizes are within limits"

echo -e "${BOLD}7. Requirements Validation (Story 5.11)${NC}"
run_validation "validate-5.11-requirements.py" "Validate Story 5.11 requirements"

# Check if --fix flag was provided
if [ "$1" == "--fix" ]; then
    echo -e "${BOLD}================================${NC}"
    echo -e "${BOLD}Running Auto-Fix Scripts${NC}"
    echo -e "${BOLD}================================${NC}"
    echo ""

    echo -e "${BLUE}Fixing script paths...${NC}"
    if source venv/bin/activate && python "$SCRIPT_DIR/fix-script-paths.py"; then
        echo -e "${GREEN}✅ Script paths fixed${NC}"
    else
        echo -e "${RED}❌ Fix failed${NC}"
    fi
    echo ""
fi

# Run integration tests if pytest is available
echo -e "${BOLD}================================${NC}"
echo -e "${BOLD}Integration Tests${NC}"
echo -e "${BOLD}================================${NC}"
echo ""

if command -v pytest &> /dev/null; then
    echo -e "${BLUE}Running integration tests...${NC}"
    if pytest "$PROJECT_ROOT/tests/integration/test_script_path_validation.py" -q; then
        echo -e "${GREEN}✅ Integration tests passed${NC}"
    else
        echo -e "${RED}❌ Integration tests failed${NC}"
        ALL_PASSED=false
    fi
else
    echo -e "${YELLOW}⚠️  pytest not installed - skipping integration tests${NC}"
fi

# Final summary
echo ""
echo -e "${BOLD}================================${NC}"
echo -e "${BOLD}Validation Summary${NC}"
echo -e "${BOLD}================================${NC}"

if [ "$ALL_PASSED" = true ]; then
    echo -e "${GREEN}${BOLD}✅ All validations passed!${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}❌ Some validations failed${NC}"
    echo -e "${YELLOW}Run with --fix flag to attempt auto-fixes${NC}"
    exit 1
fi