#!/usr/bin/env python3
"""
Audit all scripts and tests to identify:
1. Required by commands/hooks/agents
2. Deprecated/historical (migration scripts)
3. One-time fix scripts
4. Candidates for archival
5. Candidates for deletion
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/home/user/knowledge-system")

def find_all_scripts():
    """Find all Python scripts and shell scripts"""
    scripts = []
    for root, dirs, files in os.walk(PROJECT_ROOT / "scripts"):
        for file in files:
            if file.endswith(('.py', '.sh')):
                rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                scripts.append(rel_path)
    return sorted(scripts)

def find_all_tests():
    """Find all test files"""
    tests = []
    test_dir = PROJECT_ROOT / "tests"
    if test_dir.exists():
        for root, dirs, files in os.walk(test_dir):
            for file in files:
                if file.endswith('.py'):
                    rel_path = os.path.relpath(os.path.join(root, file), PROJECT_ROOT)
                    tests.append(rel_path)
    return sorted(tests)

def scan_for_references(file_path, patterns):
    """Scan a file for script references"""
    references = set()
    try:
        with open(PROJECT_ROOT / file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for pattern in patterns:
                matches = re.findall(pattern, content)
                references.update(matches)
    except Exception as e:
        print(f"Warning: Could not scan {file_path}: {e}")
    return references

def analyze_commands():
    """Analyze all command files for script dependencies"""
    cmd_dir = PROJECT_ROOT / ".claude" / "commands"
    script_refs = defaultdict(list)

    if not cmd_dir.exists():
        return script_refs

    patterns = [
        r'scripts/[a-z_\-/]+\.py',
        r'scripts/[a-z_\-/]+\.sh',
    ]

    for cmd_file in cmd_dir.glob("*.md"):
        refs = scan_for_references(f".claude/commands/{cmd_file.name}", patterns)
        for ref in refs:
            script_refs[ref].append(f"command:{cmd_file.stem}")

    return script_refs

def analyze_hooks():
    """Analyze hooks configuration for script dependencies"""
    settings_file = PROJECT_ROOT / ".claude" / "settings.json"
    script_refs = defaultdict(list)

    if not settings_file.exists():
        return script_refs

    try:
        with open(settings_file, 'r') as f:
            settings = json.load(f)

        hooks = settings.get("hooks", {})
        for hook_type, hook_configs in hooks.items():
            for config in hook_configs:
                if "hooks" in config:
                    for hook in config["hooks"]:
                        cmd = hook.get("command", "")
                        match = re.search(r'scripts/[a-z_\-/]+\.py', cmd)
                        if match:
                            script_path = match.group(0)
                            script_refs[script_path].append(f"hook:{hook_type}")
    except Exception as e:
        print(f"Warning: Could not analyze hooks: {e}")

    return script_refs

def analyze_agents():
    """Analyze agent files for script dependencies"""
    agent_dir = PROJECT_ROOT / ".claude" / "agents"
    script_refs = defaultdict(list)

    if not agent_dir.exists():
        return script_refs

    patterns = [
        r'scripts/[a-z_\-/]+\.py',
        r'scripts/[a-z_\-/]+\.sh',
    ]

    for agent_file in agent_dir.glob("*.md"):
        refs = scan_for_references(f".claude/agents/{agent_file.name}", patterns)
        for ref in refs:
            script_refs[ref].append(f"agent:{agent_file.stem}")

    return script_refs

def analyze_script_imports():
    """Analyze Python scripts for internal dependencies"""
    import_refs = defaultdict(set)

    all_scripts = find_all_scripts()
    py_scripts = [s for s in all_scripts if s.endswith('.py')]

    for script in py_scripts:
        try:
            with open(PROJECT_ROOT / script, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find imports from scripts directory
            patterns = [
                r'from scripts\.([a-z_\-]+(?:\.[a-z_\-]+)*) import',
                r'import scripts\.([a-z_\-]+(?:\.[a-z_\-]+)*)',
                r'sys\.path\.append.*scripts',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match:
                        import_refs[script].add(match)
        except Exception:
            pass

    return import_refs

def categorize_scripts(all_scripts, used_by):
    """Categorize scripts into different groups"""

    categories = {
        "core_system": [],
        "commands_required": [],
        "hooks_required": [],
        "agents_required": [],
        "migration_historical": [],
        "fix_onetime": [],
        "utilities_library": [],
        "tests": [],
        "deprecated": [],
        "unused": []
    }

    for script in all_scripts:
        script_name = os.path.basename(script)
        script_dir = os.path.dirname(script)

        # Migration scripts
        if "migration/" in script:
            categories["migration_historical"].append(script)

        # Fix scripts (one-time)
        elif script_name.startswith("fix-") or "fix" in script_dir:
            categories["fix_onetime"].append(script)

        # Hook scripts
        elif "hooks/" in script and script_name.startswith("hook-"):
            if script in used_by:
                categories["hooks_required"].append(script)
            else:
                categories["deprecated"].append(script)

        # Utility/library scripts (imported by others)
        elif script in ["scripts/utils/file_lock.py", "scripts/utils/token_estimation.py",
                       "scripts/knowledge-graph/rebuild_utils.py",
                       "scripts/services/__init__.py"]:
            categories["utilities_library"].append(script)

        # Core system scripts (always needed)
        elif script in ["scripts/utilities/kb-init.py",
                       "scripts/knowledge-graph/rebuild-backlinks.py",
                       "scripts/review/run_review.py",
                       "scripts/services/chat_archiver.py"]:
            categories["core_system"].append(script)

        # Referenced by commands/hooks/agents
        elif script in used_by:
            refs = used_by[script]
            if any("command:" in r for r in refs):
                categories["commands_required"].append(script)
            elif any("hook:" in r for r in refs):
                categories["hooks_required"].append(script)
            elif any("agent:" in r for r in refs):
                categories["agents_required"].append(script)

        # Validation scripts (useful utilities)
        elif "validation/" in script:
            categories["utilities_library"].append(script)

        # Unused
        else:
            categories["unused"].append(script)

    return categories

def generate_report(categories, used_by):
    """Generate audit report"""

    print("=" * 80)
    print("SCRIPTS AND TESTS AUDIT REPORT")
    print("=" * 80)
    print()

    print("## SUMMARY")
    print("-" * 80)
    for category, scripts in categories.items():
        print(f"{category.replace('_', ' ').title()}: {len(scripts)}")
    print()

    print("## DETAILED BREAKDOWN")
    print("-" * 80)
    print()

    # Core System (must keep)
    print("### 1. CORE SYSTEM SCRIPTS (MUST KEEP)")
    print("These are essential for system operation:")
    print()
    for script in sorted(categories["core_system"]):
        refs = used_by.get(script, [])
        print(f"  ✓ {script}")
        if refs:
            print(f"    Used by: {', '.join(refs)}")
    print()

    # Command required
    print("### 2. COMMAND-REQUIRED SCRIPTS (MUST KEEP)")
    print("Required by slash commands:")
    print()
    for script in sorted(categories["commands_required"]):
        refs = [r for r in used_by.get(script, []) if "command:" in r]
        print(f"  ✓ {script}")
        print(f"    Used by: {', '.join(refs)}")
    print()

    # Hook required
    print("### 3. HOOK-REQUIRED SCRIPTS (MUST KEEP)")
    print("Required by hooks system:")
    print()
    for script in sorted(categories["hooks_required"]):
        refs = [r for r in used_by.get(script, []) if "hook:" in r]
        print(f"  ✓ {script}")
        print(f"    Used by: {', '.join(refs)}")
    print()

    # Agent required
    print("### 4. AGENT-REQUIRED SCRIPTS (MUST KEEP)")
    print("Required by agent configurations:")
    print()
    for script in sorted(categories["agents_required"]):
        refs = [r for r in used_by.get(script, []) if "agent:" in r]
        print(f"  ✓ {script}")
        print(f"    Used by: {', '.join(refs)}")
    print()

    # Utilities
    print("### 5. UTILITIES/LIBRARY SCRIPTS (KEEP)")
    print("Imported by other scripts or useful utilities:")
    print()
    for script in sorted(categories["utilities_library"]):
        print(f"  ✓ {script}")
    print()

    # Migration (archive candidates)
    print("### 6. MIGRATION/HISTORICAL SCRIPTS (ARCHIVE TO docs/archive/)")
    print("One-time migration scripts, no longer needed in active codebase:")
    print()
    for script in sorted(categories["migration_historical"]):
        print(f"  📦 {script}")
    print()

    # Fix scripts (archive or delete)
    print("### 7. FIX/ONE-TIME SCRIPTS (ARCHIVE OR DELETE)")
    print("One-time fix scripts - archive if historical value, delete if obsolete:")
    print()
    for script in sorted(categories["fix_onetime"]):
        has_main = False
        try:
            with open(PROJECT_ROOT / script, 'r') as f:
                has_main = 'if __name__ ==' in f.read()
        except:
            pass

        print(f"  {'🗑️' if has_main else '📦'} {script}")
    print()

    # Deprecated
    print("### 8. DEPRECATED SCRIPTS (DELETE)")
    print("No longer referenced anywhere, safe to delete:")
    print()
    for script in sorted(categories["deprecated"]):
        print(f"  🗑️  {script}")
    print()

    # Unused
    print("### 9. UNUSED SCRIPTS (INVESTIGATE)")
    print("Not referenced by commands/hooks/agents, investigate usage:")
    print()
    for script in sorted(categories["unused"]):
        print(f"  ❓ {script}")
    print()

    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()
    print("1. ARCHIVE to docs/archive/scripts/:")
    archive_count = len(categories["migration_historical"]) + len([s for s in categories["fix_onetime"] if "fix-historical" in s or "merge-" in s])
    print(f"   - {archive_count} migration/historical scripts")
    print()

    print("2. DELETE immediately:")
    delete_count = len(categories["deprecated"]) + len([s for s in categories["fix_onetime"] if s not in categories["migration_historical"]])
    print(f"   - {delete_count} one-time fix/deprecated scripts")
    print()

    print("3. INVESTIGATE usage:")
    print(f"   - {len(categories['unused'])} unused scripts")
    print()

    return categories

def main():
    # Find all scripts and tests
    all_scripts = find_all_scripts()
    all_tests = find_all_tests()

    print(f"Found {len(all_scripts)} scripts and {len(all_tests)} test files")
    print()

    # Analyze dependencies
    print("Analyzing dependencies...")
    cmd_refs = analyze_commands()
    hook_refs = analyze_hooks()
    agent_refs = analyze_agents()

    # Merge all references
    used_by = defaultdict(list)
    for refs_dict in [cmd_refs, hook_refs, agent_refs]:
        for script, refs in refs_dict.items():
            used_by[script].extend(refs)

    print(f"Found {len(used_by)} scripts referenced by commands/hooks/agents")
    print()

    # Categorize scripts
    categories = categorize_scripts(all_scripts, used_by)

    # Add tests to categories
    categories["tests"] = all_tests

    # Generate report
    generate_report(categories, used_by)

if __name__ == "__main__":
    main()
