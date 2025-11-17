#!/usr/bin/env python3
"""
Universal Checklist Generator for Commands and Subagents

This module provides functions to:
1. Load workflow specifications from YAML frontmatter
2. Generate visual checklist markdown
3. Calculate complexity scores
4. Validate step dependencies
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_workflow_spec(name: str, spec_type: str = "command") -> Optional[Dict]:
    """
    Load workflow specification from YAML frontmatter.

    Args:
        name: Command name (e.g., "learn") or agent name (e.g., "language-tutor")
        spec_type: "command" or "agent"

    Returns:
        Dictionary with checklist configuration or None if not found
    """
    if spec_type == "command":
        file_path = Path(f".claude/commands/{name}.md")
    elif spec_type == "agent":
        # Try both locations: .claude/agents/{name}/instructions.md or .claude/agents/{name}.md
        file_path = Path(f".claude/agents/{name}/instructions.md")
        if not file_path.exists():
            file_path = Path(f".claude/agents/{name}.md")
    else:
        return None

    if not file_path.exists():
        return None

    try:
        content = file_path.read_text(encoding='utf-8')

        # Extract YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                return frontmatter.get("checklist")

        return None
    except Exception as e:
        print(f"Error loading workflow spec from {file_path}: {e}")
        return None


def calculate_complexity_score(steps: List[Dict], metadata: Optional[Dict] = None) -> float:
    """
    Calculate workflow complexity score.

    Formula:
    score = (steps × 0.3) + (irreversible × 2) + (error_cost × 3) + (external_calls × 1.5)

    Args:
        steps: List of workflow steps
        metadata: Optional metadata with manual overrides

    Returns:
        Complexity score (0-20 scale)
    """
    if metadata and "complexity_score" in metadata:
        return metadata["complexity_score"]

    num_steps = len(steps)

    # Count irreversible actions (file writes, external API calls)
    irreversible = sum(1 for step in steps if step.get("irreversible", False))

    # Count external calls (tool validations, script executions)
    external_calls = sum(1 for step in steps
                        if step.get("validation", {}).get("type") in
                        ["tool-call-check", "script-exit-code"])

    # Estimate error cost (high if required steps, low if optional)
    required_steps = sum(1 for step in steps if step.get("required", True))
    error_cost = 3 if required_steps >= num_steps * 0.7 else 1

    score = (num_steps * 0.3) + (irreversible * 2) + (error_cost * 3) + (external_calls * 1.5)

    return round(score, 1)


def validate_step_dependencies(steps: List[Dict]) -> Tuple[bool, Optional[str]]:
    """
    Validate step dependencies for circular references.

    Args:
        steps: List of workflow steps

    Returns:
        (is_valid, error_message)
    """
    step_ids = {step["id"] for step in steps}

    for step in steps:
        step_id = step.get("id")
        dependencies = step.get("dependencies", [])

        # Check if all dependencies exist
        for dep in dependencies:
            if dep not in step_ids:
                return False, f"Step '{step_id}' depends on non-existent step '{dep}'"

        # Check for self-dependency
        if step_id in dependencies:
            return False, f"Step '{step_id}' has circular dependency (depends on itself)"

    # Check for circular dependencies (simplified - doesn't catch all cycles)
    for step in steps:
        visited = set()
        current = step["id"]

        while current:
            if current in visited:
                return False, f"Circular dependency detected involving step '{current}'"
            visited.add(current)

            # Find next dependency
            current_step = next((s for s in steps if s["id"] == current), None)
            if not current_step or not current_step.get("dependencies"):
                break
            current = current_step["dependencies"][0] if current_step["dependencies"] else None

    return True, None


def generate_checklist_markdown(workflow_spec: Dict, current_step: int = 0) -> str:
    """
    Generate visual checklist markdown from workflow specification.

    Args:
        workflow_spec: Checklist configuration dictionary
        current_step: Current step index (0-based)

    Returns:
        Formatted markdown checklist string
    """
    if not workflow_spec or not workflow_spec.get("enabled"):
        return ""

    workflow = workflow_spec.get("workflow", {})
    steps = workflow.get("steps", [])
    metadata = workflow.get("metadata", {})
    enforcement = workflow_spec.get("enforcement", "advisory")

    if not steps:
        return ""

    # Validate dependencies
    is_valid, error = validate_step_dependencies(steps)
    if not is_valid:
        return f"⚠️  WORKFLOW ERROR: {error}"

    # Calculate complexity score
    complexity = calculate_complexity_score(steps, metadata)

    # Determine risk level
    if complexity >= 10:
        risk_level = "High Risk"
        risk_emoji = "🔴"
    elif complexity >= 5:
        risk_level = "Medium Risk"
        risk_emoji = "🟡"
    else:
        risk_level = "Low Risk"
        risk_emoji = "🟢"

    # Build checklist
    lines = []
    lines.append("⚠️  WORKFLOW CHECKLIST ACTIVE\n")

    if enforcement == "mandatory":
        lines.append("🔒 MANDATORY EXECUTION ORDER")
    else:
        lines.append("💡 RECOMMENDED WORKFLOW")

    lines.append(f"{risk_emoji} Complexity: {complexity}/20 - {risk_level}")

    if "estimated_duration" in metadata:
        lines.append(f"⏱️  Estimated Duration: {metadata['estimated_duration']}")

    lines.append("\nSTEP-BY-STEP CHECKLIST:\n")

    # Generate step list
    for i, step in enumerate(steps, 1):
        step_id = step.get("id", f"step-{i}")
        step_name = step.get("name", f"Step {i}")
        required = step.get("required", True)
        dependencies = step.get("dependencies", [])
        validation = step.get("validation", {})

        # Step marker
        marker = "🔴" if required else "🔵"
        current_marker = " ← YOU ARE HERE" if i == current_step + 1 else ""

        lines.append(f"{marker} Step {i}: {step_name}{current_marker}")

        # Show dependencies
        if dependencies:
            dep_nums = []
            for dep_id in dependencies:
                dep_idx = next((idx for idx, s in enumerate(steps, 1) if s["id"] == dep_id), None)
                if dep_idx:
                    dep_nums.append(f"Step {dep_idx}")

            if dep_nums:
                status = "✅" if i <= current_step else ""
                lines.append(f"   ↳ Requires: {', '.join(dep_nums)} {status}")

        # Show validation
        val_type = validation.get("type")
        if val_type and val_type != "none":
            if val_type == "tool-call-check":
                tool = validation.get("params", {}).get("tool", "Unknown")
                lines.append(f"   ↳ Validation: Tool call detected ({tool})")
            elif val_type == "file-exists":
                lines.append(f"   ↳ Validation: File exists")
            elif val_type == "script-exit-code":
                lines.append(f"   ↳ Validation: Script execution (exit code 0)")
            elif val_type == "json-field-check":
                lines.append(f"   ↳ Validation: JSON field check")
            elif val_type == "json-parse-check":
                lines.append(f"   ↳ Validation: JSON syntax validation")

        # Show error message if critical
        error_msg = validation.get("error_message")
        if error_msg and "CRITICAL" in step_name.upper():
            lines.append(f"   ↳ ⚠️  {error_msg.strip().split(chr(10))[0]}")

        lines.append("")

    # Add footer
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if enforcement == "mandatory":
        lines.append("⚠️  You MUST complete steps in order.")
        lines.append("⚠️  Skipping mandatory steps (🔴) will cause workflow violations.")
    else:
        lines.append("💡 Following this workflow is recommended for best results.")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    return "\n".join(lines)


def get_enforcement_level(complexity_score: float) -> str:
    """
    Determine enforcement level based on complexity score.

    Args:
        complexity_score: Calculated complexity score

    Returns:
        "mandatory", "advisory", or "off"
    """
    if complexity_score >= 10:
        return "mandatory"
    elif complexity_score >= 5:
        return "advisory"
    else:
        return "off"


if __name__ == "__main__":
    # Self-test
    print("Checklist Generator - Self Test")
    print("=" * 50)

    # Test loading workflow spec
    spec = load_workflow_spec("learn", "command")
    if spec:
        print("✅ Successfully loaded /learn workflow spec")
        checklist = generate_checklist_markdown(spec)
        print("\nGenerated Checklist:")
        print(checklist)
    else:
        print("⚠️  No workflow spec found for /learn (expected if not yet created)")
