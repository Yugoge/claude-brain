#!/usr/bin/env python3
"""
Preloaded TodoList for save workflow.

Auto-generated from .claude/commands/save.md by scripts/todo/generate_save_todos.py
DO NOT EDIT MANUALLY - edit save.md and re-run generator script.
"""


# (content, activeForm, extra_meta) tuples for each step
_STEPS = [
    ("Pre-Processing (Batch Execution)", "Pre-Processing (Batch Execution)", None),
    (
        "Domain Classification & ISCED Path (AI + Subagent)",
        "Domain Classification & ISCED Path (AI + Subagent)",
        {"subagent_call": {"agent": "classification-expert", "subagent_type": "classification-expert"}},
    ),
    ("Extract Concepts (AI-driven, no file creation)", "Extract Concepts (AI-driven, no file creation)", None),
    ("Analyze User Learning & Rem Updates (Learn/Review Sessions)", "Analyze User Learning & Rem Updates (Learn/Review Sessions)", None),
    (
        "Enrich with Typed Relations via Domain Tutor (AI + Subagent)",
        "Enrich with Typed Relations via Domain Tutor (AI + Subagent)",
        {"subagent_call": {"agent": "domain-tutor", "subagent_type": "general-purpose"}},
    ),
    ("Rem Extraction Transparency", "Rem Extraction Transparency", None),
    ("Generate Preview", "Generate Preview", None),
    ("User Confirmation", "User Confirmation", None),
    ("Update Learning Material Progress (Learn Sessions Only)", "Update Learning Material Progress (Learn Sessions Only)", None),
    ("Execute Automated Post-Processing", "Execute Automated Post-Processing", None),
]


def _build_step(index, desc, active, meta):
    """Build a single todo item dict from step tuple."""
    item = {
        "content": f"Step {index}: {desc}",
        "activeForm": f"Step {index}: {active}",
        "status": "pending",
    }
    if meta:
        item.update(meta)
    return item


def get_todos():
    """Return list of todo items for TodoWrite."""
    return [
        _build_step(i + 1, desc, active, meta)
        for i, (desc, active, meta) in enumerate(_STEPS)
    ]


if __name__ == "__main__":
    # CLI: print todos as formatted list
    import json
    todos = get_todos()
    print(json.dumps(todos, indent=2, ensure_ascii=False))
