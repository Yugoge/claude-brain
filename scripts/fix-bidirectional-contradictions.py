#!/usr/bin/env python3
"""
Fix contradictory bidirectional relationships in rem files.
Uses backlinks.json as the single source of truth.
"""

import json
import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configuration
KNOWLEDGE_BASE = "/root/knowledge-system/knowledge-base"
BACKLINKS_FILE = f"{KNOWLEDGE_BASE}/_index/backlinks.json"
CONTRADICTIONS_FILE = "/tmp/source_contradictions.json"
UNIQUE_REM_IDS_FILE = "/tmp/unique_rem_ids.json"

class ContradictionFixer:
    def __init__(self):
        self.backlinks_data = None
        self.rem_ids = []
        self.rem_id_to_file = {}
        self.modifications = []
        self.errors = []
        self.warnings = []

    def load_data(self):
        """Load all necessary data files."""
        print("STEP 1: Loading data files...", file=sys.stderr)

        # Load backlinks
        with open(BACKLINKS_FILE, 'r') as f:
            self.backlinks_data = json.load(f)
        print(f"  ✓ Loaded backlinks.json (version {self.backlinks_data.get('version', 'unknown')})", file=sys.stderr)

        # Load unique rem_ids
        with open(UNIQUE_REM_IDS_FILE, 'r') as f:
            self.rem_ids = json.load(f)
        print(f"  ✓ Loaded {len(self.rem_ids)} unique rem_ids", file=sys.stderr)

    def find_rem_files(self):
        """Find markdown files for each rem_id."""
        print("\nSTEP 2: Finding markdown files for each rem_id...", file=sys.stderr)

        for rem_id in self.rem_ids:
            # Search for files containing this rem_id in frontmatter (recursive search)
            cmd = f'grep -r -l "rem_id: {rem_id}" {KNOWLEDGE_BASE} --include="*.md" 2>/dev/null || true'
            result = os.popen(cmd).read().strip()

            if result:
                files = [f for f in result.split('\n') if f and '_templates' not in f]
                if len(files) == 1:
                    self.rem_id_to_file[rem_id] = files[0]
                    print(f"  ✓ {rem_id} -> {os.path.basename(files[0])}", file=sys.stderr)
                elif len(files) > 1:
                    self.warnings.append(f"Multiple files found for {rem_id}: {files}")
                    self.rem_id_to_file[rem_id] = files[0]  # Use first one
                    print(f"  ⚠ {rem_id} -> {os.path.basename(files[0])} (multiple found)", file=sys.stderr)
                else:
                    self.warnings.append(f"No file found for rem_id: {rem_id}")
            else:
                self.warnings.append(f"No file found for rem_id: {rem_id}")

        print(f"\n  Found files for {len(self.rem_id_to_file)}/{len(self.rem_ids)} rem_ids", file=sys.stderr)

    def get_correct_relations(self, rem_id: str) -> List[Dict]:
        """Get correct typed_links_to from backlinks.json."""
        links_data = self.backlinks_data.get('links', {})
        rem_data = links_data.get(rem_id, {})
        return rem_data.get('typed_links_to', [])

    def get_target_filename(self, target_rem_id: str) -> str:
        """Get the filename (without .md) for a target rem_id."""
        if target_rem_id in self.rem_id_to_file:
            file_path = self.rem_id_to_file[target_rem_id]
            basename = os.path.basename(file_path)
            return basename[:-3]  # Remove .md extension
        return None

    def generate_related_rems_section(self, rem_id: str) -> str:
        """Generate the new ## Related Rems section."""
        relations = self.get_correct_relations(rem_id)

        lines = ["## Related Rems\n"]

        if not relations:
            lines.append("\n")
        else:
            for rel in relations:
                target_rem_id = rel.get('to')
                rel_type = rel.get('type', 'related')

                filename = self.get_target_filename(target_rem_id)
                if filename:
                    lines.append(f"- [{filename}]({filename}.md) {{rel: {rel_type}}}\n")
                else:
                    self.warnings.append(f"Target file not found for {target_rem_id} (referenced from {rem_id})")

        return ''.join(lines)

    def fix_file(self, rem_id: str, file_path: str):
        """Fix a single rem file."""
        try:
            # Read the file
            with open(file_path, 'r') as f:
                content = f.read()

            # Get correct relations
            new_section = self.generate_related_rems_section(rem_id)

            # Find and replace the Related Rems section
            # Pattern: ## Related Rems ... up to next ## section or end of file
            pattern = r'## Related Rems\n.*?(?=\n## |\Z)'

            old_match = re.search(pattern, content, re.DOTALL)

            if old_match:
                old_section = old_match.group(0)
                old_count = old_section.count('- [')
                new_count = new_section.count('- [')

                # Replace the section
                new_content = content[:old_match.start()] + new_section + content[old_match.end():]

                # Write back
                with open(file_path, 'w') as f:
                    f.write(new_content)

                self.modifications.append({
                    'rem_id': rem_id,
                    'file': file_path,
                    'old_count': old_count,
                    'new_count': new_count
                })

                print(f"Fixed: {rem_id} ({os.path.basename(file_path)})", file=sys.stderr)
                print(f"  Old relations: {old_count}", file=sys.stderr)
                print(f"  New relations: {new_count}", file=sys.stderr)

            else:
                # No Related Rems section found - insert before Conversation Source
                conv_pattern = r'\n## Conversation Source'
                conv_match = re.search(conv_pattern, content)

                if conv_match:
                    new_content = content[:conv_match.start()] + '\n' + new_section + content[conv_match.start():]

                    with open(file_path, 'w') as f:
                        f.write(new_content)

                    new_count = new_section.count('- [')
                    self.modifications.append({
                        'rem_id': rem_id,
                        'file': file_path,
                        'old_count': 0,
                        'new_count': new_count
                    })

                    print(f"Inserted: {rem_id} ({os.path.basename(file_path)})", file=sys.stderr)
                    print(f"  New relations: {new_count}", file=sys.stderr)
                else:
                    self.warnings.append(f"No Related Rems or Conversation Source section in {file_path}")

        except Exception as e:
            self.errors.append(f"Error processing {file_path}: {str(e)}")
            print(f"ERROR: {rem_id} - {str(e)}", file=sys.stderr)

    def process_all_files(self):
        """Process all rem files that need fixing."""
        print("\nSTEP 3: Processing rem files...", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        for rem_id, file_path in self.rem_id_to_file.items():
            self.fix_file(rem_id, file_path)

        print("=" * 60, file=sys.stderr)

    def generate_summary(self):
        """Generate summary report."""
        print("\n" + "=" * 80, file=sys.stderr)
        print("SUMMARY OF FIXES", file=sys.stderr)
        print("=" * 80, file=sys.stderr)

        total_added = sum(m['new_count'] - m['old_count'] for m in self.modifications if m['new_count'] > m['old_count'])
        total_removed = sum(m['old_count'] - m['new_count'] for m in self.modifications if m['old_count'] > m['new_count'])
        net_change = total_added - total_removed

        print(f"Total rem files processed: {len(self.modifications)}", file=sys.stderr)
        print(f"Total relationships added: {total_added}", file=sys.stderr)
        print(f"Total relationships removed: {total_removed}", file=sys.stderr)
        print(f"Net change: {'+' if net_change >= 0 else ''}{net_change}", file=sys.stderr)
        print("", file=sys.stderr)

        print("Files modified:", file=sys.stderr)
        for i, mod in enumerate(self.modifications, 1):
            basename = os.path.basename(mod['file'])
            print(f"{i}. {basename} - {mod['old_count']} relations → {mod['new_count']} relations", file=sys.stderr)

        if self.warnings:
            print("\n" + "=" * 80, file=sys.stderr)
            print(f"WARNINGS ({len(self.warnings)}):", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            for warning in self.warnings:
                print(f"  ⚠ {warning}", file=sys.stderr)

        if self.errors:
            print("\n" + "=" * 80, file=sys.stderr)
            print(f"ERRORS ({len(self.errors)}):", file=sys.stderr)
            print("=" * 80, file=sys.stderr)
            for error in self.errors:
                print(f"  ✗ {error}", file=sys.stderr)

        print("\n" + "=" * 80, file=sys.stderr)
        print("PROCESS COMPLETE", file=sys.stderr)
        print("=" * 80, file=sys.stderr)

    def run(self):
        """Main execution flow."""
        self.load_data()
        self.find_rem_files()
        self.process_all_files()
        self.generate_summary()


if __name__ == '__main__':
    fixer = ContradictionFixer()
    fixer.run()
