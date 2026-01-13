#!/usr/bin/env python3
"""
Knowledge System Initialization and Health Check

This script provides comprehensive validation, repair, and initialization
capabilities for the knowledge system, including:
- Directory structure validation and creation
- JSON file validation and repair
- Agent file verification
- Git repository health checks
- Python dependency verification
- Script permission validation
- Comprehensive reporting

Usage:
    source venv/bin/activate && source venv/bin/activate && python3 scripts/kb-init.py [options]
    /kb-init [options]

Options:
    --dry-run           Preview checks without making changes
    --non-interactive   Auto-apply safe repairs without prompting
    --verbose          Increase logging detail
    --repair-all       Automatically repair all detected issues
    --help             Show this help message
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import importlib.util
import shutil


# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'


# Required directory structure (core system directories only)
# Note: ISCED 3-level paths (e.g., 0231-language-acquisition) are created on-demand by /save
REQUIRED_DIRS = {
    "knowledge-base/": "Main knowledge repository",
    "knowledge-base/_index/": "Generated indexes (backlinks, graph-data)",
    "knowledge-base/_templates/": "Rem templates for different domains",
    "learning-materials/": "Source materials (PDFs, EPUBs, etc.)",
    "learning-materials/finance/": "Finance materials",
    "learning-materials/programming/": "Programming materials",
    "learning-materials/language/": "Language materials",
    ".review/": "Spaced repetition data (FSRS algorithm)",
    ".review/backups/": "FSRS schedule backups",
    "chats/": "Archived conversations",
    "scripts/": "Utility scripts",
    "docs/": "System documentation",
    ".claude/agents/": "Agent instruction files",
    ".claude/commands/": "Custom slash commands"
}

# ISCED-F 2013 Taxonomy Structure (11 broad fields + core files)
# This validates the complete taxonomy system that classification-expert depends on
REQUIRED_TAXONOMY = {
    "knowledge-base/_taxonomy/": "ISCED-F 2013 taxonomy root",
    "knowledge-base/_taxonomy/index.md": "Taxonomy system overview",
    "knowledge-base/_taxonomy/isced-index.md": "ISCED broad fields index",
    "knowledge-base/_taxonomy/00-generic-programmes-and-qualifications/": "ISCED 00: Generic programmes",
    "knowledge-base/_taxonomy/01-education/": "ISCED 01: Education",
    "knowledge-base/_taxonomy/02-arts-and-humanities/": "ISCED 02: Arts and humanities",
    "knowledge-base/_taxonomy/03-social-sciences-journalism-and-information/": "ISCED 03: Social sciences",
    "knowledge-base/_taxonomy/04-business-administration-and-law/": "ISCED 04: Business and law",
    "knowledge-base/_taxonomy/05-natural-sciences-mathematics-and-statistics/": "ISCED 05: Natural sciences",
    "knowledge-base/_taxonomy/06-information-and-communication-technologies-icts/": "ISCED 06: ICT",
    "knowledge-base/_taxonomy/07-engineering-manufacturing-and-construction/": "ISCED 07: Engineering",
    "knowledge-base/_taxonomy/08-agriculture-forestry-fisheries-and-veterinary/": "ISCED 08: Agriculture",
    "knowledge-base/_taxonomy/09-health-and-welfare/": "ISCED 09: Health",
    "knowledge-base/_taxonomy/10-services/": "ISCED 10: Services"
}

# JSON file schemas
JSON_SCHEMAS = {
    "knowledge-base/_index/backlinks.json": {
        "required_fields": ["version", "description", "links"],
        "version_format": r"^\d+\.\d+\.\d+$",
        "repair_strategy": "rebuild",
        "template": {
            "version": "1.1.0",
            "description": "Bidirectional link index for all knowledge Rems, with typed and inferred links",
            "links": {}
        }
    },
    "chats/index.json": {
        "required_fields": ["version", "conversations", "metadata"],
        "version_format": r"^\d+\.\d+\.\d+$",
        "repair_strategy": "reset",
        "template": {
            "version": "1.0.0",
            "conversations": {},
            "metadata": {
                "last_updated": None,
                "total_conversations": 0,
                "total_turns": 0,
                "total_concepts_extracted": 0,
                "total_rems_extracted": 0,
                "by_domain": {},
                "by_agent": {},
                "by_month": {}
            }
        }
    },
    ".review/schedule.json": {
        "required_fields": ["version", "default_algorithm", "concepts"],
        "version_format": r"^\d+\.\d+\.\d+$",
        "repair_strategy": "reset",
        "template": {
            "version": "2.0.0",
            "default_algorithm": "fsrs",
            "description": "FSRS-based spaced repetition schedule for all Rems",
            "concepts": {}
        }
    }
}

# Required agent files (updated for flat .md structure)
# Note: Section validation removed - agent structures are intentionally diverse
REQUIRED_AGENTS = {
    ".claude/agents/book-tutor.md": {
        "name": "book-tutor",
        "description": "Socratic teaching for books/reports"
    },
    ".claude/agents/language-tutor.md": {
        "name": "language-tutor",
        "description": "Language learning specialist (JSON consultant)"
    },
    ".claude/agents/finance-tutor.md": {
        "name": "finance-tutor",
        "description": "Finance domain specialist (JSON consultant)"
    },
    ".claude/agents/programming-tutor.md": {
        "name": "programming-tutor",
        "description": "Programming domain specialist (JSON consultant)"
    },
    ".claude/agents/medicine-tutor.md": {
        "name": "medicine-tutor",
        "description": "Medical & healthcare domain specialist (JSON consultant)"
    },
    ".claude/agents/law-tutor.md": {
        "name": "law-tutor",
        "description": "Legal domain specialist (JSON consultant)"
    },
    ".claude/agents/science-tutor.md": {
        "name": "science-tutor",
        "description": "Science domain specialist (JSON consultant)"
    },
    ".claude/agents/review-master.md": {
        "name": "review-master",
        "description": "Review conductor (JSON consultant)"
    },
    ".claude/agents/analyst.md": {
        "name": "analyst",
        "description": "Universal AI assistant for research (JSON consultant)"
    },
    ".claude/agents/classification-expert.md": {
        "name": "classification-expert",
        "description": "Domain classification specialist (UNESCO ISCED)"
    },
    ".claude/agents/journalist.md": {
        "name": "journalist",
        "description": "Media analysis expert (JSON consultant)"
    }
}

# Required executable scripts (updated paths for current architecture)
REQUIRED_SCRIPTS = [
    # Knowledge graph scripts
    "scripts/knowledge-graph/rebuild-backlinks.py",
    "scripts/knowledge-graph/generate-graph-data.py",
    "scripts/knowledge-graph/normalize-links.py",

    # Archival scripts (core /save workflow)
    "scripts/archival/save_orchestrator.py",
    "scripts/archival/save_post_processor.py",
    "scripts/archival/workflow_orchestrator.py",

    # Review scripts (core /review workflow)
    "scripts/review/run_review.py",
    "scripts/review/update_review.py",

    # Progress scripts
    "scripts/progress/display_progress.py",

    # Utilities
    "scripts/utilities/scan-and-populate-rems.py",
    "scripts/utilities/kb-init.py",

    # Learning materials
    "scripts/learning-materials/estimate_tokens.py",
    "scripts/learning-materials/extract-pdf-chunk.py",
    "scripts/learning-materials/check-file-size.py"
]


class InitReport:
    """Comprehensive initialization report generator."""

    def __init__(self):
        self.sections = {}
        self.issues = []
        self.repairs = []
        self.start_time = datetime.now()

    def add_section(self, name: str, status: Dict[str, Any]):
        """Add a validation section to report."""
        self.sections[name] = status

    def add_issue(self, issue: str):
        """Add an issue to the report."""
        self.issues.append(issue)

    def add_repair(self, repair: str):
        """Add a repair action to the report."""
        self.repairs.append(repair)

    def has_critical_issues(self) -> bool:
        """Check if any critical issues exist."""
        for section in self.sections.values():
            if isinstance(section, dict) and "failed" in section and section["failed"]:
                return True
        return False

    def has_warnings(self) -> bool:
        """Check if any warnings exist."""
        return len(self.issues) > 0

    def display(self, use_color: bool = True):
        """Display formatted report to console."""
        def colorize(text: str, color: str) -> str:
            return f"{color}{text}{Colors.RESET}" if use_color else text

        print("\n" + "=" * 50)
        print(colorize("📋 Knowledge System Initialization Report", Colors.BOLD))
        print("=" * 50)

        # Summary section
        print(f"\n{colorize('📊 Summary:', Colors.BOLD)}")

        if "directories" in self.sections:
            dirs = self.sections["directories"]
            total = len(dirs.get("existing", [])) + len(dirs.get("created", []))
            created = len(dirs.get("created", []))
            if created > 0:
                print(f"  📁 Directories: ✅ {total} present ({created} created)")
            else:
                print(f"  📁 Directories: ✅ {total} present")

        if "json_files" in self.sections:
            files = self.sections["json_files"]
            valid = len(files.get("valid", []))
            repaired = len(files.get("repaired", []))
            failed = len(files.get("failed", []))
            if repaired > 0:
                print(f"  📄 JSON Files: ✅ {valid} valid, 🔧 {repaired} repaired", end="")
                if failed > 0:
                    print(f", ❌ {failed} failed")
                else:
                    print()
            elif failed > 0:
                print(f"  📄 JSON Files: ✅ {valid} valid, ❌ {failed} failed")
            else:
                print(f"  📄 JSON Files: ✅ {valid} valid")

        if "taxonomy" in self.sections:
            taxonomy = self.sections["taxonomy"]
            total = len(REQUIRED_TAXONOMY)
            valid = len(taxonomy.get("valid", []))
            missing = len(taxonomy.get("missing", []))
            if missing == 0:
                print(f"  📚 Taxonomy System: ✅ {total} components")
            elif missing == total:
                print(f"  📚 Taxonomy System: ❌ Missing entirely ({total} components)")
            else:
                print(f"  📚 Taxonomy System: ⚠️  {valid}/{total} components ({missing} missing)")

        if "agents" in self.sections:
            agents = self.sections["agents"]
            valid = len(agents.get("valid", []))
            missing = len(agents.get("missing", []))
            invalid = len(agents.get("invalid", []))
            if missing > 0 or invalid > 0:
                print(f"  🤖 Agent Files: ✅ {valid} valid", end="")
                if missing > 0:
                    print(f", ⚠️  {missing} missing", end="")
                if invalid > 0:
                    print(f", ⚠️  {invalid} invalid", end="")
                print()
            else:
                print(f"  🤖 Agent Files: ✅ {valid} valid")

        if "git" in self.sections:
            git = self.sections["git"]
            checks = git.get("checks", {})
            if all(checks.values()):
                print("  🔧 Git Repository: ✅ Configured")
            else:
                print("  🔧 Git Repository: ⚠️  Issues detected")

        if "dependencies" in self.sections:
            deps = self.sections["dependencies"]
            installed = len(deps.get("installed", []))
            missing = len(deps.get("missing", []))
            if missing > 0:
                print(f"  🐍 Python Dependencies: ⚠️  {installed} installed, {missing} missing")
            else:
                print(f"  🐍 Python Dependencies: ✅ {installed} installed")

        if "permissions" in self.sections:
            perms = self.sections["permissions"]
            fixed = len(perms.get("fixed", []))
            if fixed > 0:
                print(f"  🔐 Script Permissions: 🔧 {fixed} fixed")
            else:
                print(f"  🔐 Script Permissions: ✅ All executable")

        # Issues detected
        if self.issues:
            print(f"\n{colorize('⚠️  Issues Detected:', Colors.YELLOW)}")
            for issue in self.issues:
                print(f"  - {issue}")

        # Repairs performed
        if self.repairs:
            print(f"\n{colorize('🔧 Repairs Performed:', Colors.GREEN)}")
            for repair in self.repairs:
                print(f"  - {repair}")

        # Overall status
        print("\n" + "=" * 50)
        if self.has_critical_issues():
            print(colorize("System Status: ❌ Critical Issues Detected", Colors.RED))
        elif self.has_warnings():
            print(colorize("System Status: ⚠️  Ready with Warnings", Colors.YELLOW))
        else:
            print(colorize("System Status: ✅ Fully Ready", Colors.GREEN))

        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"Completed in {elapsed:.2f} seconds")

    def save(self, file_path: str):
        """Save report to file."""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w') as f:
            f.write("Knowledge System Initialization Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("SECTIONS:\n")
            for name, status in self.sections.items():
                f.write(f"\n{name.upper()}:\n")
                f.write(json.dumps(status, indent=2) + "\n")

            if self.issues:
                f.write("\nISSUES:\n")
                for issue in self.issues:
                    f.write(f"  - {issue}\n")

            if self.repairs:
                f.write("\nREPAIRS:\n")
                for repair in self.repairs:
                    f.write(f"  - {repair}\n")

            if self.has_critical_issues():
                f.write("\nSTATUS: CRITICAL ISSUES DETECTED\n")
            elif self.has_warnings():
                f.write("\nSTATUS: READY WITH WARNINGS\n")
            else:
                f.write("\nSTATUS: FULLY READY\n")


def prompt_yes_no(message: str, default: bool = True) -> bool:
    """Prompt user for yes/no response."""
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{message} [{default_str}]: ").strip().lower()
        if response == "":
            return default
        elif response in ["y", "yes"]:
            return True
        elif response in ["n", "no"]:
            return False
        else:
            print("Please answer 'y' or 'n'")


def validate_directories(
    dry_run: bool = False,
    non_interactive: bool = False,
    verbose: bool = False
) -> Dict[str, List[str]]:
    """Validate and create required directories."""
    status = {"created": [], "existing": [], "failed": []}

    for dir_path, description in REQUIRED_DIRS.items():
        path = Path(dir_path)

        if path.exists():
            status["existing"].append(dir_path)
            if verbose:
                print(f"  ✅ {dir_path}")
        else:
            print(f"  ⚠️  Missing: {dir_path}")

            if dry_run:
                print(f"     Would create: {dir_path}")
                continue

            should_create = non_interactive or prompt_yes_no(
                f"Create directory '{dir_path}'?", default=True
            )

            if should_create:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    status["created"].append(dir_path)
                    print(f"  ✅ Created: {dir_path}")
                except Exception as e:
                    status["failed"].append((dir_path, str(e)))
                    print(f"  ❌ Failed to create: {e}")

    return status


def validate_json_files(
    dry_run: bool = False,
    non_interactive: bool = False,
    repair_all: bool = False,
    verbose: bool = False,
    report: Optional[InitReport] = None
) -> Dict[str, List]:
    """Validate all JSON files and repair if needed."""
    status = {"valid": [], "repaired": [], "failed": []}

    for file_path, schema in JSON_SCHEMAS.items():
        path = Path(file_path)

        if verbose:
            print(f"\n  Checking: {file_path}")

        # File missing
        if not path.exists():
            print(f"    ⚠️  File missing")
            if dry_run:
                print(f"    Would create from template")
            elif repair_all or non_interactive or prompt_yes_no("Create from template?", default=True):
                try:
                    create_from_template(path, schema)
                    status["repaired"].append(file_path)
                    if report:
                        report.add_repair(f"Created missing file: {file_path}")
                    print(f"    ✅ Created from template")
                except Exception as e:
                    status["failed"].append((file_path, str(e)))
                    print(f"    ❌ Failed to create: {e}")
            continue

        # Validate JSON syntax
        try:
            with open(path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"    ❌ Invalid JSON: {e}")
            if dry_run:
                print(f"    Would repair")
            elif repair_all or non_interactive or prompt_yes_no("Repair file?", default=True):
                try:
                    backup_and_repair(path, schema, report)
                    status["repaired"].append(file_path)
                    print(f"    ✅ Repaired")
                except Exception as e:
                    status["failed"].append((file_path, str(e)))
                    print(f"    ❌ Failed to repair: {e}")
            else:
                status["failed"].append((file_path, "Invalid JSON"))
            continue

        # Validate schema
        issues = []
        for field in schema["required_fields"]:
            if field not in data:
                issues.append(f"Missing field: {field}")

        if schema["version_format"] and "version" in data:
            if not re.match(schema["version_format"], str(data["version"])):
                issues.append("Invalid version format")

        if issues:
            print(f"    ⚠️  Schema issues: {', '.join(issues)}")
            if dry_run:
                print(f"    Would repair schema")
            elif repair_all or non_interactive or prompt_yes_no("Repair schema?", default=True):
                try:
                    repair_schema(path, data, schema, report)
                    status["repaired"].append(file_path)
                    print(f"    ✅ Schema repaired")
                except Exception as e:
                    status["failed"].append((file_path, str(e)))
                    print(f"    ❌ Failed to repair schema: {e}")
            else:
                status["failed"].append((file_path, issues))
        else:
            status["valid"].append(file_path)
            if verbose:
                print(f"    ✅ Valid")

    return status


def create_from_template(path: Path, schema: Dict[str, Any]):
    """Create JSON file from template."""
    path.parent.mkdir(parents=True, exist_ok=True)

    template = schema.get("template", {})
    if "last_updated" in template and template["last_updated"] is None:
        template["last_updated"] = datetime.now().isoformat()

    with open(path, 'w') as f:
        json.dump(template, f, indent=2)


def backup_and_repair(path: Path, schema: Dict[str, Any], report: Optional[InitReport] = None):
    """Backup corrupted file and repair."""
    # Create backup
    backup_path = path.with_suffix(path.suffix + '.backup')
    if path.exists():
        shutil.copy2(path, backup_path)
        if report:
            report.add_repair(f"Created backup: {backup_path}")

    # Repair based on strategy
    strategy = schema.get("repair_strategy", "reset")

    if strategy == "rebuild":
        # Try to run rebuild script, fall back to template if not available
        rebuild_script = Path("scripts/knowledge-graph/rebuild-backlinks.py")
        if "backlinks" in str(path) and rebuild_script.exists():
            try:
                subprocess.run(["python3", str(rebuild_script)], check=True)
                if report:
                    report.add_repair(f"Rebuilt backlinks: {path}")
            except subprocess.CalledProcessError:
                # Fall back to template if rebuild fails
                create_from_template(path, schema)
                if report:
                    report.add_repair(f"Fallback to template (rebuild failed): {path}")
        else:
            # Rebuild script doesn't exist, use template
            create_from_template(path, schema)
            if report:
                report.add_repair(f"Fallback to template (no rebuild script): {path}")
    elif strategy == "regenerate":
        # Use template
        create_from_template(path, schema)
        if report:
            report.add_repair(f"Regenerated from template: {path}")
    else:  # reset
        create_from_template(path, schema)
        if report:
            report.add_repair(f"Reset to empty state: {path}")


def repair_schema(
    path: Path,
    data: Dict[str, Any],
    schema: Dict[str, Any],
    report: Optional[InitReport] = None
):
    """Repair JSON schema by adding missing fields."""
    template = schema.get("template", {})

    for field in schema["required_fields"]:
        if field not in data:
            data[field] = template.get(field)

    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

    if report:
        report.add_repair(f"Repaired schema: {path}")


def validate_taxonomy(
    dry_run: bool = False,
    non_interactive: bool = False,
    verbose: bool = False,
    report: Optional[InitReport] = None
) -> Dict[str, List[str]]:
    """Validate ISCED-F 2013 taxonomy structure completeness."""
    status = {"valid": [], "missing": [], "created": []}

    for path_str, description in REQUIRED_TAXONOMY.items():
        path = Path(path_str)

        # Check if it's a file or directory
        is_file = path_str.endswith('.md')

        if path.exists():
            status["valid"].append(path_str)
            if verbose:
                print(f"  ✅ {path_str}")
        else:
            print(f"  ⚠️  Missing: {path_str}")
            status["missing"].append(path_str)

            if dry_run:
                print(f"     Would create: {path_str}")
                continue

            # For now, just report missing taxonomy components
            # In the future, could add template-based creation
            issue = f"Missing taxonomy component: {path_str}"
            if report:
                report.add_issue(issue)

    # Summary
    total = len(REQUIRED_TAXONOMY)
    valid_count = len(status["valid"])
    missing_count = len(status["missing"])

    if missing_count == 0:
        if verbose:
            print(f"\n  ✅ Taxonomy complete: {valid_count}/{total} components")
    elif missing_count == total:
        print(f"\n  ❌ Taxonomy missing entirely ({total} components)")
        if report:
            report.add_issue("Complete taxonomy system missing - classification-expert will not work")
    else:
        print(f"\n  ⚠️  Taxonomy incomplete: {valid_count}/{total} components ({missing_count} missing)")

    return status


def validate_agents(
    dry_run: bool = False,
    non_interactive: bool = False,
    verbose: bool = False
) -> Dict[str, List]:
    """Verify agent files exist and are readable."""
    status = {"valid": [], "missing": [], "invalid": []}

    for file_path, spec in REQUIRED_AGENTS.items():
        path = Path(file_path)

        if not path.exists():
            print(f"  ⚠️  Missing agent: {spec['name']}")
            status["missing"].append(file_path)
            continue

        # Basic validation: check if file is readable and not empty
        try:
            with open(path) as f:
                content = f.read()

            if len(content.strip()) < 100:
                print(f"  ⚠️  {spec['name']}: File too short (possibly empty)")
                status["invalid"].append((file_path, ["File too short"]))
            else:
                status["valid"].append(file_path)
                if verbose:
                    print(f"  ✅ {spec['name']}")
        except Exception as e:
            print(f"  ❌ {spec['name']}: Error reading file: {e}")
            status["invalid"].append((file_path, [str(e)]))

    return status


def validate_git(
    dry_run: bool = False,
    non_interactive: bool = False,
    verbose: bool = False,
    report: Optional[InitReport] = None
) -> Dict[str, Any]:
    """Check Git repository health."""
    status = {"checks": {}, "issues": []}

    # Check 1: Git initialized
    if not Path(".git").exists():
        print("  ⚠️  Git repository not initialized")
        status["checks"]["initialized"] = False
        if dry_run:
            print("     Would initialize Git repository")
        elif non_interactive or prompt_yes_no("Initialize Git repository?", default=True):
            subprocess.run(["git", "init"], check=True)
            print("  ✅ Git initialized")
            if report:
                report.add_repair("Initialized Git repository")
            status["checks"]["initialized"] = True
    else:
        status["checks"]["initialized"] = True
        if verbose:
            print("  ✅ Git initialized")

    # Check 2: Remote configured
    try:
        result = subprocess.run(
            ["git", "remote", "-v"],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            status["checks"]["remote"] = True
            if verbose:
                print("  ✅ Remote configured")
        else:
            status["checks"]["remote"] = False
            print("  ⚠️  No remote configured")
            issue = "Configure remote: git remote add origin <url>"
            status["issues"].append(issue)
            if report:
                report.add_issue(issue)
    except subprocess.CalledProcessError:
        status["checks"]["remote"] = False
        print("  ⚠️  Cannot check remote")

    # Check 3: .gitignore exists
    gitignore_path = Path(".gitignore")
    if gitignore_path.exists():
        status["checks"]["gitignore"] = True
        if verbose:
            print("  ✅ .gitignore present")

        # Verify required entries
        with open(gitignore_path) as f:
            gitignore_content = f.read()

        required_entries = [
            "__pycache__/",
            "*.pyc",
            ".DS_Store",
            "*.log",
            ".env"
        ]

        missing_entries = [
            entry for entry in required_entries
            if entry not in gitignore_content
        ]

        if missing_entries:
            print(f"  ⚠️  .gitignore missing entries: {', '.join(missing_entries)}")
            issue = f"Add to .gitignore: {', '.join(missing_entries)}"
            status["issues"].append(issue)
            if report:
                report.add_issue(issue)
    else:
        status["checks"]["gitignore"] = False
        print("  ⚠️  .gitignore missing")
        issue = "Create .gitignore file"
        status["issues"].append(issue)
        if report:
            report.add_issue(issue)

    # Check 4: Uncommitted changes
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            status["checks"]["clean"] = False
            change_count = len(result.stdout.strip().split("\n"))
            if verbose:
                print(f"  ℹ️  {change_count} uncommitted changes")
        else:
            status["checks"]["clean"] = True
            if verbose:
                print("  ✅ Working directory clean")
    except subprocess.CalledProcessError:
        status["checks"]["clean"] = None
        if verbose:
            print("  ⚠️  Cannot check Git status")

    return status


def validate_dependencies(verbose: bool = False) -> Dict[str, List[str]]:
    """Check Python dependencies from requirements.txt."""
    status = {"installed": [], "missing": []}

    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("  ⚠️  requirements.txt not found")
        return status

    with open(requirements_file) as f:
        packages = [
            line.split(">=")[0].split("==")[0].strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

    for package in packages:
        package_import_name = package.replace("-", "_")
        try:
            spec = importlib.util.find_spec(package_import_name)
            if spec is not None:
                status["installed"].append(package)
                if verbose:
                    print(f"  ✅ {package}")
            else:
                status["missing"].append(package)
                print(f"  ❌ {package} (not installed)")
        except (ImportError, ModuleNotFoundError):
            status["missing"].append(package)
            print(f"  ❌ {package} (not installed)")

    if status["missing"]:
        print(f"\n  💡 Install missing packages:")
        print(f"     pip install {' '.join(status['missing'])}")

    return status


def validate_permissions(
    dry_run: bool = False,
    verbose: bool = False,
    report: Optional[InitReport] = None
) -> Dict[str, List[str]]:
    """Verify script permissions and fix if needed."""
    status = {"valid": [], "fixed": [], "missing": []}

    for script_path in REQUIRED_SCRIPTS:
        path = Path(script_path)

        if not path.exists():
            print(f"  ⚠️  Script missing: {script_path}")
            status["missing"].append(script_path)
            continue

        # Check execute permission
        is_executable = os.access(path, os.X_OK)

        if is_executable:
            status["valid"].append(script_path)
            if verbose:
                print(f"  ✅ {script_path}")
        else:
            print(f"  ⚠️  Not executable: {script_path}")
            if not dry_run:
                try:
                    path.chmod(0o755)
                    status["fixed"].append(script_path)
                    if report:
                        report.add_repair(f"Fixed permissions: {script_path}")
                    print(f"  ✅ Fixed permissions: {script_path}")
                except Exception as e:
                    print(f"  ❌ Failed to fix permissions: {e}")
            else:
                print(f"     Would fix permissions")

    return status


def kb_init(
    dry_run: bool = False,
    non_interactive: bool = False,
    verbose: bool = False,
    repair_all: bool = False
):
    """Main initialization function."""
    report = InitReport()

    print("\n" + "=" * 50)
    print(f"{Colors.BOLD}🔧 Knowledge System Initialization{Colors.RESET}")
    print("=" * 50)

    if dry_run:
        print(f"\n{Colors.YELLOW}🔍 DRY RUN MODE - No changes will be made{Colors.RESET}")

    # Phase 1: Directory Structure
    print("\n📁 Checking directory structure...")
    dir_status = validate_directories(dry_run, non_interactive, verbose)
    report.add_section("directories", dir_status)

    # Phase 2: JSON Files
    print("\n📄 Validating JSON files...")
    json_status = validate_json_files(dry_run, non_interactive, repair_all, verbose, report)
    report.add_section("json_files", json_status)

    # Phase 3: Taxonomy System
    print("\n📚 Validating taxonomy structure...")
    taxonomy_status = validate_taxonomy(dry_run, non_interactive, verbose, report)
    report.add_section("taxonomy", taxonomy_status)

    # Phase 4: Agent Files
    print("\n🤖 Verifying agent files...")
    agent_status = validate_agents(dry_run, non_interactive, verbose)
    report.add_section("agents", agent_status)

    # Phase 4: Git Health
    print("\n🔧 Checking Git repository...")
    git_status = validate_git(dry_run, non_interactive, verbose, report)
    report.add_section("git", git_status)

    # Phase 5: Python Dependencies
    print("\n🐍 Checking Python dependencies...")
    deps_status = validate_dependencies(verbose)
    report.add_section("dependencies", deps_status)

    # Phase 6: Script Permissions
    print("\n🔐 Verifying script permissions...")
    perms_status = validate_permissions(dry_run, verbose, report)
    report.add_section("permissions", perms_status)

    # Generate and display report
    print("\n" + "=" * 50)
    report.display()

    # Save report
    if not dry_run:
        report_path = ".claude/init-report.txt"
        report.save(report_path)
        print(f"\n📝 Report saved to: {report_path}")

    # Exit with appropriate code
    if report.has_critical_issues():
        print(f"\n{Colors.RED}❌ Initialization incomplete - critical issues detected{Colors.RESET}")
        return 1
    elif report.has_warnings():
        print(f"\n{Colors.YELLOW}⚠️  Initialization complete with warnings{Colors.RESET}")
        return 2
    else:
        print(f"\n{Colors.GREEN}✅ Knowledge system ready{Colors.RESET}")
        return 0


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Knowledge System Initialization and Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  source venv/bin/activate && source venv/bin/activate && python3 scripts/kb-init.py                    # Interactive mode
  source venv/bin/activate && source venv/bin/activate && python3 scripts/kb-init.py --dry-run          # Preview without changes
  source venv/bin/activate && source venv/bin/activate && python3 scripts/kb-init.py --non-interactive  # Auto-repair mode
  source venv/bin/activate && source venv/bin/activate && python3 scripts/kb-init.py --repair-all       # Repair all issues
  source venv/bin/activate && source venv/bin/activate && python3 scripts/kb-init.py --verbose          # Detailed output
        """
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview checks without making changes"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Auto-apply safe repairs without prompting"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Increase logging detail"
    )
    parser.add_argument(
        "--repair-all",
        action="store_true",
        help="Automatically repair all detected issues"
    )

    args = parser.parse_args()

    try:
        exit_code = kb_init(
            dry_run=args.dry_run,
            non_interactive=args.non_interactive,
            verbose=args.verbose,
            repair_all=args.repair_all
        )
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Initialization cancelled by user{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Fatal error: {e}{Colors.RESET}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
