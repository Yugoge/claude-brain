#!/usr/bin/env python3
"""
Generate detailed cleanup plan with categorization
"""

import json

# Based on audit analysis
cleanup_plan = {
    "KEEP_CORE": {
        "description": "Core system scripts - essential for operation",
        "scripts": [
            "scripts/knowledge-graph/rebuild-backlinks.py",
            "scripts/review/run_review.py",
            "scripts/services/chat_archiver.py",
            "scripts/utilities/kb-init.py",
        ]
    },

    "KEEP_COMMANDS": {
        "description": "Required by slash commands",
        "count": 40,
        "note": "See audit report for full list"
    },

    "KEEP_HOOKS": {
        "description": "Required by hooks system",
        "count": 14,
        "note": "See audit report for full list"
    },

    "KEEP_LIBRARY": {
        "description": "Library/utility scripts imported by others",
        "scripts": [
            # FSRS core (imported by review system)
            "scripts/review/fsrs_algorithm.py",  # ← imported by review_scheduler, scan-and-populate-rems
            "scripts/review/fsrs_parameters.py",  # ← parameter presets

            # Archival libraries (imported by workflow_orchestrator)
            "scripts/archival/question_classifier.py",  # ← imported by workflow_orchestrator

            # Hook libraries (imported by hook scripts)
            "scripts/hooks/checklist_generator.py",  # ← imported by hook-checklist-injection, hook-subagent-checklist

            # Memory libraries (infrastructure)
            "scripts/memory/memory_client.py",  # ← imported by agent_memory_utils, knowledge_graph_memory, etc.
            "scripts/memory/agent_memory_utils.py",
            "scripts/memory/knowledge_graph_memory.py",
            "scripts/memory/mcp_intelligent_proxy.py",
            "scripts/memory/unified_memory.py",
            "scripts/memory/memory_triggers.py",

            # Learning materials utilities
            "scripts/learning-materials/compress_pdf.py",  # ← referenced in kb-init

            # General utilities
            "scripts/knowledge-graph/rebuild_utils.py",
            "scripts/services/__init__.py",
            "scripts/utils/file_lock.py",
            "scripts/utils/token_estimation.py",

            # Validation utilities
            "scripts/validation/check-archive-naming.py",
            "scripts/validation/check-chinese-in-commands.py",
            "scripts/validation/run-all-validations.sh",
            "scripts/validation/validate-conversation-index.py",
            "scripts/validation/validate-rem-format.py",
            "scripts/validation/validate-rem-sources.py",
            "scripts/validation/validate-script-paths.py",
            "scripts/validation/validate-taxonomy.py",
        ]
    },

    "KEEP_USEFUL": {
        "description": "Not currently used but provide useful functionality",
        "scripts": [
            # FSRS advanced features
            "scripts/review/fsrs_optimizer.py",  # Parameter optimization
            "scripts/review/measure-fsrs-improvement.py",  # Performance analysis
            "scripts/review/reset-schedule.py",  # Review schedule management
            "scripts/review/review-stats.py",  # Statistics analysis
            "scripts/review/interleaved_review.py",  # Advanced review mode

            # Knowledge graph utilities
            "scripts/knowledge-graph/add-relation.py",  # Manual relation management
            "scripts/knowledge-graph/remove-invalid-related-concepts.py",  # Graph cleanup

            # Learning materials utilities
            "scripts/learning-materials/split-pdf-to-single-pages.py",  # PDF processing
            "scripts/learning-materials/validate-progress.py",  # Progress validation

            # Analytics
            "scripts/analytics/export_analytics.py",  # Data export

            # Service utilities
            "scripts/services/batch_extract_conversations.py",  # Batch processing

            # Other utilities
            "scripts/learning-goals/manage_learning_goals.py",  # Learning goals feature
            "scripts/utilities/subdomain_manager.py",  # Subdomain management
        ]
    },

    "ARCHIVE": {
        "description": "Archive to docs/archive/scripts/ - historical value",
        "target_dir": "docs/archive/scripts/migration/",
        "scripts": [
            "scripts/migration/fix-format-errors.py",
            "scripts/migration/fix-historical-conversations.py",
            "scripts/migration/fix-migrated-files.py",
            "scripts/migration/merge-manual-summaries.py",
            "scripts/migration/reextract-conversations.py",
            "scripts/migration/validate-migration.py",

            # One-time fixes with historical value
            "scripts/fix-chat-roles.sh",
            "scripts/utilities/match-manual-conversations.py",
            "scripts/utilities/merge-sessions.py",
            "scripts/utilities/remove-nonstandard-fields.py",
            "scripts/utilities/reprocess-conversations.py",
        ]
    },

    "DELETE": {
        "description": "One-time fix scripts - no historical value",
        "scripts": [
            "scripts/fix-subagent-roles.py",
            "scripts/knowledge-graph/fix-rems-batch.py",
            "scripts/utilities/fix-historical-attribution.py",
            "scripts/utilities/fix-rems-batch.py",
            "scripts/utilities/fix-subagent-markers.py",
            "scripts/validation/fix-script-paths.py",
        ]
    },

    "TESTS": {
        "description": "Keep all tests - essential for quality",
        "action": "KEEP",
        "scripts": [
            "tests/conftest.py",
            "tests/e2e/test_kb_init.py",
            "tests/integration/test_analytics_engine.py",
            "tests/integration/test_graph_advanced_features.py",
            "tests/integration/test_insights_system.py",
            "tests/integration/test_integration.py",
            "tests/integration/test_script_path_validation.py",
            "tests/unit/test_fsrs_algorithm.py",
            "tests/unit/test_fsrs_optimizer.py",
            "tests/unit/test_fsrs_parameters.py",
            "tests/unit/test_generate_graph_data.py",
            "tests/unit/test_hooks.py",
            "tests/unit/test_taxonomy_structure.py",
            "tests/unit/test_typed_links.py",
            "tests/visual/test_pdf_visual_extraction.py",
        ]
    }
}

# Statistics
total_scripts = 112
keep_core = len(cleanup_plan["KEEP_CORE"]["scripts"])
keep_commands = cleanup_plan["KEEP_COMMANDS"]["count"]
keep_hooks = cleanup_plan["KEEP_HOOKS"]["count"]
keep_library = len(cleanup_plan["KEEP_LIBRARY"]["scripts"])
keep_useful = len(cleanup_plan["KEEP_USEFUL"]["scripts"])
archive = len(cleanup_plan["ARCHIVE"]["scripts"])
delete = len(cleanup_plan["DELETE"]["scripts"])
tests = len(cleanup_plan["TESTS"]["scripts"])

print("=" * 80)
print("CLEANUP PLAN SUMMARY")
print("=" * 80)
print()
print(f"Total scripts analyzed: {total_scripts}")
print()
print(f"KEEP (Essential):        {keep_core + keep_commands + keep_hooks} scripts")
print(f"  - Core system:         {keep_core}")
print(f"  - Commands:            {keep_commands}")
print(f"  - Hooks:               {keep_hooks}")
print()
print(f"KEEP (Library):          {keep_library} scripts")
print(f"KEEP (Useful features):  {keep_useful} scripts")
print(f"KEEP (Tests):            {tests} scripts")
print()
print(f"ARCHIVE (Migration):     {archive} scripts")
print(f"DELETE (One-time fix):   {delete} scripts")
print()
print("=" * 80)
print("DETAILED PLAN")
print("=" * 80)
print()

for category, data in cleanup_plan.items():
    if category in ["KEEP_COMMANDS", "KEEP_HOOKS"]:
        continue  # Skip detailed lists for these

    print(f"### {category}")
    print(f"{data['description']}")
    print()

    if "scripts" in data:
        for script in data["scripts"]:
            action_icon = "✓" if category.startswith("KEEP") or category == "TESTS" else "📦" if category == "ARCHIVE" else "🗑️"
            print(f"  {action_icon} {script}")
        print()

print("=" * 80)
print("EXECUTION COMMANDS")
print("=" * 80)
print()

print("# 1. Create archive directory")
print("mkdir -p docs/archive/scripts/migration")
print("mkdir -p docs/archive/scripts/fixes")
print()

print("# 2. Archive migration scripts")
for script in cleanup_plan["ARCHIVE"]["scripts"]:
    if "migration/" in script:
        target = script.replace("scripts/migration/", "docs/archive/scripts/migration/")
        print(f"git mv {script} {target}")
    else:
        target = script.replace("scripts/", "docs/archive/scripts/fixes/").replace("utilities/", "")
        print(f"git mv {script} {target}")
print()

print("# 3. Delete one-time fix scripts")
for script in cleanup_plan["DELETE"]["scripts"]:
    print(f"git rm {script}")
print()

print("# 4. Commit changes")
print('git commit -m "chore: Archive migration scripts and delete one-time fixes"')
print()

# Save JSON
with open("/home/user/knowledge-system/cleanup-plan.json", "w") as f:
    json.dump(cleanup_plan, f, indent=2)

print("Detailed plan saved to: cleanup-plan.json")
