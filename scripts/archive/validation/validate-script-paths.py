#!/usr/bin/env python3
"""
Validate Script Paths in Documentation

This script validates that all script paths referenced in documentation
and command files actually exist in the filesystem.

Usage:
    python3 scripts/validation/validate-script-paths.py [--json] [--summary]

Options:
    --json      Output results in JSON format
    --summary   Show only summary without details
    --fix       Auto-fix known issues (use with caution)

Author: Claude
Date: 2025-11-01
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

# Project root
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT))

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

@dataclass
class ScriptReference:
    """Represents a unique script reference."""
    script_path: str
    locations: List[tuple] = field(default_factory=list)
    exists: bool = False
    error_type: str = ""

class ScriptPathValidator:
    """Validates script paths in documentation."""

    def __init__(self, root: Path):
        self.root = root
        self.references: Dict[str, ScriptReference] = {}
        self.ignore_patterns = [
            r'__pycache__',
            r'\.pyc$',
            r'^from\s+\w+\s+import',
            r'scripts/category$',
            r'scripts/\w+$',
            r'^\w+\.py$',
        ]

    def should_ignore(self, script_path: str) -> bool:
        """Check if a path should be ignored."""
        for pattern in self.ignore_patterns:
            if re.search(pattern, script_path):
                return True
        return False

    def extract_script_paths(self, content: str) -> Set[str]:
        """Extract unique script paths from content."""
        paths = set()

        patterns = [
            r'python3?\s+([^\s]+\.py)',
            r'`([^`]*scripts/[^`]+\.py)`',
            r'(scripts/[\w\-/]+\.py)',
            r'sys\.path\.append\([\'"]([^\'"]+)[\'"]\)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                if not self.should_ignore(match):
                    paths.add(match)

        return paths

    def scan_file(self, file_path: Path):
        """Scan a single file for script references."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')

            paths = self.extract_script_paths(content)

            for script_path in paths:
                if script_path not in self.references:
                    self.references[script_path] = ScriptReference(script_path=script_path)

                for line_num, line in enumerate(lines, 1):
                    if script_path in line:
                        self.references[script_path].locations.append(
                            (file_path, line_num, line.strip()[:100])
                        )

        except Exception as e:
            print(f"{Colors.WARNING}Warning: Could not read {file_path}: {e}{Colors.ENDC}")

    def validate_reference(self, ref: ScriptReference) -> bool:
        """Validate if a script reference exists and categorize error."""
        script_path = ref.script_path

        possible_paths = []

        if script_path.startswith('/'):
            possible_paths.append(Path(script_path))
        elif script_path.startswith('scripts/'):
            possible_paths.append(self.root / script_path)
        else:
            possible_paths.append(self.root / 'scripts' / script_path)
            possible_paths.append(self.root / script_path)

        for path in possible_paths:
            if path.exists():
                ref.exists = True
                return True

        # Categorize the error
        if 'unified_memory' in script_path:
            ref.error_type = "Legacy Script (deprecated)"
        elif 'kb-init.py' in script_path:
            ref.error_type = "Missing Initialization Script"
        elif 'validate-' in script_path:
            ref.error_type = "Missing Validation Script"
        elif 'rebuild-' in script_path or 'update-' in script_path:
            ref.error_type = "Path Issue (check knowledge-graph/)"
        elif 'scan-and-populate' in script_path and 'review/' in script_path:
            ref.error_type = "Wrong Directory (moved to utilities/)"
        else:
            ref.error_type = "Script Not Found"

        return False

    def run_validation(self, args):
        """Run the complete validation."""
        if not args.json and not args.summary:
            print(f"{Colors.HEADER}{Colors.BOLD}Script Path Validator{Colors.ENDC}")
            print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")
            print(f"Project Root: {self.root}\n")

        # Directories to scan
        scan_dirs = [
            (self.root / '.claude' / 'commands', '*.md'),
            (self.root / '.claude' / 'agents', '*.md'),
            (self.root / 'docs', '*.md'),
        ]

        # Scan all files
        total_files = 0
        for directory, pattern in scan_dirs:
            if directory.exists():
                files = list(directory.rglob(pattern))
                if not args.json and not args.summary:
                    print(f"{Colors.OKCYAN}Scanning {directory.relative_to(self.root)}: {len(files)} files{Colors.ENDC}")
                total_files += len(files)

                for file_path in files:
                    self.scan_file(file_path)

        if not args.json and not args.summary:
            print(f"\nTotal files scanned: {total_files}")
            print(f"Unique script references found: {len(self.references)}")

        # Validate references
        for ref in self.references.values():
            self.validate_reference(ref)

        # Generate report
        self.generate_report(args)

    def generate_report(self, args):
        """Generate report based on arguments."""
        valid = [r for r in self.references.values() if r.exists]
        invalid = [r for r in self.references.values() if not r.exists]

        if args.json:
            # JSON output
            report = {
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'valid': len(valid),
                    'invalid': len(invalid),
                    'total': len(self.references)
                },
                'invalid_references': [
                    {
                        'script': ref.script_path,
                        'error_type': ref.error_type,
                        'locations': [
                            {
                                'file': str(loc[0].relative_to(self.root)),
                                'line': loc[1]
                            }
                            for loc in ref.locations[:3]
                        ]
                    }
                    for ref in invalid
                ]
            }
            print(json.dumps(report, indent=2))

        else:
            # Terminal output
            print(f"\n{Colors.HEADER}{Colors.BOLD}Validation Results{Colors.ENDC}")
            print(f"{Colors.HEADER}{'=' * 60}{Colors.ENDC}")

            print(f"{Colors.BOLD}Summary:{Colors.ENDC}")
            print(f"  ✅ Valid script references: {len(valid)}")
            print(f"  ❌ Invalid script references: {len(invalid)}")
            print(f"  📊 Total unique references: {len(self.references)}")

            if not args.summary and invalid:
                # Group by error type
                errors_by_type = defaultdict(list)
                for ref in invalid:
                    errors_by_type[ref.error_type].append(ref)

                print(f"\n{Colors.FAIL}{Colors.BOLD}Invalid References by Category:{Colors.ENDC}")

                for error_type, refs in sorted(errors_by_type.items()):
                    print(f"\n{Colors.WARNING}{error_type} ({len(refs)} scripts):{Colors.ENDC}")

                    for ref in refs[:5]:
                        print(f"  • {Colors.FAIL}{ref.script_path}{Colors.ENDC}")
                        if ref.locations:
                            loc = ref.locations[0]
                            rel_path = loc[0].relative_to(self.root)
                            print(f"    Found in: {rel_path}:{loc[1]}")

                    if len(refs) > 5:
                        print(f"    ... and {len(refs) - 5} more")

            # Final status
            if not invalid:
                print(f"\n{Colors.OKGREEN}{Colors.BOLD}✅ All script paths are valid!{Colors.ENDC}")
            elif len(invalid) < 10:
                print(f"\n{Colors.WARNING}{Colors.BOLD}⚠️ Minor issues found - {len(invalid)} invalid references{Colors.ENDC}")
            else:
                print(f"\n{Colors.FAIL}{Colors.BOLD}❌ Significant issues - {len(invalid)} invalid references{Colors.ENDC}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Validate script paths in documentation')
    parser.add_argument('--json', action='store_true', help='Output results in JSON format')
    parser.add_argument('--summary', action='store_true', help='Show only summary')
    parser.add_argument('--fix', action='store_true', help='Auto-fix known issues (use separate fix script)')

    args = parser.parse_args()

    if args.fix:
        print("For auto-fixing, use: python3 scripts/validation/fix-script-paths.py")
        sys.exit(0)

    validator = ScriptPathValidator(ROOT)
    validator.run_validation(args)

if __name__ == '__main__':
    main()