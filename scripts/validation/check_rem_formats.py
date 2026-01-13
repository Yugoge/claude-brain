#!/usr/bin/env python3
"""
Rem Format Checker - Fast validation of Rem frontmatter
Checks format compliance without reading full file content

Usage:
    source venv/bin/activate && source venv/bin/activate && python scripts/check_rem_formats.py                    # Check all Rems
    source venv/bin/activate && source venv/bin/activate && python scripts/check_rem_formats.py <file.md>          # Check specific file
    source venv/bin/activate && source venv/bin/activate && python scripts/check_rem_formats.py --verbose          # Detailed output
"""

import sys
import re
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Represents a validation error"""
    file: str
    line: int
    column: int
    severity: str  # 'error' or 'warning'
    message: str
    rule: str


class RemFormatChecker:
    """Fast Rem format checker - reads only frontmatter (first 100 lines)"""

    # New simplified template (v3.0) - Story 1.10 compliant
    REQUIRED_FIELDS = [
        'rem_id',      # Unique identifier: {subdomain}-{concept-slug}
        'subdomain',   # Subdomain classification (e.g., 'equity-derivatives', 'french')
        'isced',       # ISCED detailed code
        'created',     # Creation date (YYYY-MM-DD)
        'source',      # Source reference (e.g., 'chats/YYYY-MM/conversation.md')
    ]

    VALID_DOMAINS = [
        'finance', 'programming', 'language', 'science', 'health',
        'engineering', 'education', 'arts', 'social_sciences',
        'agriculture', 'services', 'generic'
    ]

    def __init__(self, taxonomy_path: str = '.taxonomy.json'):
        self.taxonomy_path = Path(taxonomy_path)
        self.errors: List[ValidationError] = []

    def check_file(self, file_path: Path) -> List[ValidationError]:
        """Check a single Rem file (fast - only reads frontmatter)"""
        self.errors = []

        try:
            # Read only first 100 lines (frontmatter should be within this)
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [f.readline() for _ in range(100)]

            # Extract frontmatter
            frontmatter, fm_end_line = self._extract_frontmatter(lines, file_path)
            if not frontmatter:
                self.errors.append(ValidationError(
                    file=str(file_path),
                    line=1,
                    column=1,
                    severity='error',
                    message='No frontmatter found (must start with ---)',
                    rule='frontmatter-required'
                ))
                return self.errors

            # Parse YAML
            try:
                data = yaml.safe_load(frontmatter)
            except yaml.YAMLError as e:
                self.errors.append(ValidationError(
                    file=str(file_path),
                    line=getattr(e, 'problem_mark', {}).get('line', 1) + 1,
                    column=getattr(e, 'problem_mark', {}).get('column', 1) + 1,
                    severity='error',
                    message=f'Invalid YAML: {e}',
                    rule='yaml-syntax'
                ))
                return self.errors

            # Run validation checks (v3.0 simplified template)
            self._check_required_fields(data, file_path)
            self._check_rem_id_format(data, file_path)
            self._check_subdomain_format(data, file_path)
            self._check_isced_v3_format(data, file_path)
            self._check_created_date_format(data, file_path)
            self._check_source_format(data, file_path)

        except Exception as e:
            self.errors.append(ValidationError(
                file=str(file_path),
                line=1,
                column=1,
                severity='error',
                message=f'Failed to read file: {e}',
                rule='file-read-error'
            ))

        return self.errors

    def _extract_frontmatter(self, lines: List[str], file_path: Path) -> Tuple[Optional[str], int]:
        """Extract frontmatter from first 100 lines"""
        if not lines or not lines[0].strip().startswith('---'):
            return None, 0

        # Find closing ---
        frontmatter_lines = []
        end_line = 0

        for i, line in enumerate(lines[1:], start=2):
            if line.strip() == '---':
                end_line = i
                break
            frontmatter_lines.append(line)

        if end_line == 0:
            return None, 0

        return '\n'.join(frontmatter_lines), end_line

    def _check_required_fields(self, data: Dict, file_path: Path):
        """Check all required fields are present"""
        for field_path in self.REQUIRED_FIELDS:
            parts = field_path.split('.')
            current = data

            for i, part in enumerate(parts):
                if not isinstance(current, dict) or part not in current:
                    self.errors.append(ValidationError(
                        file=str(file_path),
                        line=3,  # Approximate line in frontmatter
                        column=1,
                        severity='error',
                        message=f"Missing required field: '{field_path}'",
                        rule='required-field'
                    ))
                    break
                current = current[part]

    def _check_rem_id_format(self, data: Dict, file_path: Path):
        """Check rem_id format: {subdomain}-{concept-slug}"""
        rem_id = data.get('rem_id')
        if not rem_id:
            return  # Already caught by required fields check

        # Should be kebab-case with at least one hyphen
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)+$', str(rem_id)):
            self.errors.append(ValidationError(
                file=str(file_path),
                line=2,
                column=1,
                severity='error',
                message=f"Invalid rem_id format: '{rem_id}' (use kebab-case: subdomain-concept-slug)",
                rule='rem-id-format'
            ))

    def _check_subdomain_format(self, data: Dict, file_path: Path):
        """Check subdomain format (lowercase, hyphens allowed)"""
        subdomain = data.get('subdomain')
        if not subdomain:
            return  # Already caught by required fields check

        if not re.match(r'^[a-z]+(-[a-z]+)*$', str(subdomain)):
            self.errors.append(ValidationError(
                file=str(file_path),
                line=3,
                column=1,
                severity='error',
                message=f"Invalid subdomain format: '{subdomain}' (use lowercase with hyphens, e.g., 'equity-derivatives')",
                rule='subdomain-format'
            ))

        # Check rem_id starts with subdomain
        rem_id = data.get('rem_id', '')
        if subdomain and rem_id and not str(rem_id).startswith(str(subdomain) + '-'):
            self.errors.append(ValidationError(
                file=str(file_path),
                line=2,
                column=1,
                severity='warning',
                message=f"rem_id '{rem_id}' should start with subdomain '{subdomain}-'",
                rule='rem-id-subdomain-consistency'
            ))

    def _check_isced_v3_format(self, data: Dict, file_path: Path):
        """Check ISCED format (v3.0 simplified: full slug)"""
        isced = data.get('isced')
        if not isced:
            return  # Already caught by required fields check

        # Format: 4-digit code followed by slug
        # Example: NNNN-domain-slug
        if not re.match(r'^\d{4}-[a-z]+(-[a-z]+)*$', str(isced)):
            self.errors.append(ValidationError(
                file=str(file_path),
                line=4,
                column=1,
                severity='error',
                message=f"Invalid isced format: '{isced}' (use: NNNN-slug format)",
                rule='isced-v3-format'
            ))

    def _check_created_date_format(self, data: Dict, file_path: Path):
        """Check created date format (YYYY-MM-DD)"""
        created = data.get('created')
        if not created:
            return  # Already caught by required fields check

        if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(created)):
            self.errors.append(ValidationError(
                file=str(file_path),
                line=5,
                column=1,
                severity='error',
                message=f"Invalid created date format: '{created}' (use YYYY-MM-DD format)",
                rule='created-date-format'
            ))

    def _check_source_format(self, data: Dict, file_path: Path):
        """Check source format (should reference chats/ or 'unarchived')"""
        source = data.get('source')
        if not source:
            return  # Already caught by required fields check

        # Should either be 'unarchived' or a path to chats/
        if source != 'unarchived' and not str(source).startswith('chats/'):
            self.errors.append(ValidationError(
                file=str(file_path),
                line=6,
                column=1,
                severity='warning',
                message=f"Source should reference 'chats/YYYY-MM/file.md' or be 'unarchived' (got: '{source}')",
                rule='source-format'
            ))

    def check_all_rems(self, base_path: Path = Path('knowledge-base')) -> Dict[str, List[ValidationError]]:
        """Check all Rem files in knowledge base"""
        results = {}

        # Find all .md files (excluding templates)
        for md_file in base_path.rglob('*.md'):
            # Skip template files
            if '_templates' in str(md_file) or '_index' in str(md_file):
                continue

            errors = self.check_file(md_file)
            if errors:
                results[str(md_file)] = errors

        return results

    def format_report(self, results: Dict[str, List[ValidationError]], verbose: bool = False) -> str:
        """Format validation report (eslint-style)"""
        output = []
        total_errors = 0
        total_warnings = 0
        files_with_errors = 0

        if not results:
            return "\n✅ All Rem files passed format validation!\n"

        output.append("\nChecking Rem formats...\n")

        for file_path, errors in sorted(results.items()):
            files_with_errors += 1
            output.append(file_path)

            for error in errors:
                if error.severity == 'error':
                    total_errors += 1
                    icon = '✖'
                else:
                    total_warnings += 1
                    icon = '⚠'

                output.append(f"  {error.line}:{error.column}  {icon} {error.severity:7}  {error.message}")

                if verbose:
                    output.append(f"                 Rule: {error.rule}")

            output.append("")  # Blank line between files

        # Summary
        output.append(f"✖ {files_with_errors} file(s) with errors")
        output.append(f"  {total_errors} errors, {total_warnings} warnings")

        if not verbose:
            output.append("\nRun with --verbose for detailed fix suggestions.")

        return "\n".join(output)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Check Rem format compliance')
    parser.add_argument('files', nargs='*', help='Specific files to check (default: all)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    parser.add_argument('--base-path', default='knowledge-base', help='Base path for Rems')

    args = parser.parse_args()

    checker = RemFormatChecker()

    if args.files:
        # Check specific files
        results = {}
        for file_path in args.files:
            path = Path(file_path)
            if path.exists():
                errors = checker.check_file(path)
                if errors:
                    results[str(path)] = errors
            else:
                print(f"Error: File not found: {file_path}", file=sys.stderr)
                sys.exit(2)
    else:
        # Check all Rems
        results = checker.check_all_rems(Path(args.base_path))

    # Print report
    report = checker.format_report(results, verbose=args.verbose)
    print(report)

    # Exit with appropriate code
    if results:
        sys.exit(1)  # Errors found
    else:
        sys.exit(0)  # All passed


if __name__ == '__main__':
    main()
