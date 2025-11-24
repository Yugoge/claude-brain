---
description: "Dual-track fact verification using parallel hypothesis testing"
allowed-tools: Task, Read, TodoWrite, WebSearch, WebFetch, Bash
argument-hint: "<claim-to-verify>"
model: inherit
---

# Fact-Check Command

Verify claims using parallel hypothesis testing to avoid single-narrative bias.

## Core Principle

**Problem**: Single-perspective analysis leads to confirmation bias.
**Solution**: Generate opposing hypotheses, gather evidence for each equally, let user decide based on evidence quality.

---

## Step 0: Initialize Workflow

```bash
source venv/bin/activate && python scripts/todo/fact-check-parallel.py
```

Use output to create TodoWrite checklist.

---

## Step 1: Generate Hypotheses

Parse claim and generate 2-3 opposing interpretations:

```bash
source venv/bin/activate && python scripts/fact-check/generate_hypotheses.py "$ARGUMENTS"
```

Output: JSON with hypotheses A, B, C and search strategies.

---

## Step 2-4: Parallel Evidence Gathering

**For EACH hypothesis, independently consult journalist with role parameter**:

### Track A: Advocate for Hypothesis A

```
Task tool with:
- subagent_type: "journalist"
- description: "Gather evidence supporting hypothesis A"
- prompt: "
  You are consulting as an ADVOCATE for this hypothesis: {hypothesis_A}

  Your role: Find strongest evidence SUPPORTING this hypothesis.
  Be explicit: You are temporarily in advocacy mode, not neutral analysis.

  Input claim: {original_claim}
  Hypothesis to support: {hypothesis_A}

  Return JSON with:
  - analysis_plan (focused on pro-A evidence)
  - structural_analysis (if applicable)
  - verification_guidance (search queries for pro-A evidence)
  - evidence_quality_assessment
  - role: 'advocate_for_A'
  "
```

### Track B: Advocate for Hypothesis B

Same structure, but advocate for hypothesis B (counter-evidence).

### Track C: Advocate for Hypothesis C

Same structure, but advocate for alternative framing.

**CRITICAL**: Execute all three consultations. No shortcuts.

---

## Step 5: Evidence Collection (Parallel)

For each track, execute searches suggested by journalist consultant:

**Enforcement**:
- If Track A gets 5 WebSearch calls, Track B and C must also get 5 attempts each
- Document search queries used for each track
- Collect evidence with source citations

**Format**:
```json
{
  "aspects": ["Aspect 1", "Aspect 2", ...],
  "hypotheses": {
    "A": {
      "aspect1": {
        "evidence": "Evidence text",
        "source": "URL or citation",
        "quality": "peer-reviewed | government data | journalistic | anecdotal"
      }
    },
    "B": {...},
    "C": {...}
  }
}
```

---

## Step 6: Format Evidence Matrix

Generate comparison table:

```bash
echo '<evidence_json>' | source venv/bin/activate && python scripts/fact-check/format_evidence_matrix.py -
```

Present table to user showing evidence side-by-side.

---

## Step 7: Disagreement Analysis

Categorize conflicts:

```bash
echo '<evidence_json>' | source venv/bin/activate && python scripts/fact-check/analyze_disagreements.py -
```

Output shows:
- **Factual layer**: Consensus facts vs disputed facts
- **Interpretation layer**: Different frameworks applied to same facts
- **Value layer**: Which priorities lead to which conclusions

---

## Step 8: User-Guided Interpretation

**DO NOT impose conclusion. Instead**:

Present findings:
```
Evidence Comparison:

<evidence_matrix_table>

Key Disagreements:

Factual Consensus:
- <list agreed facts>

Disputed Facts:
- <list with competing evidence quality>

Interpretation Frameworks:
- Framework A: <explanation>
- Framework B: <explanation>

If you prioritize:
- Evidence quality X → Hypothesis A stronger
- Evidence quality Y → Hypothesis B stronger
- Context Z → Hypothesis C more accurate

Which aspects matter most to you for evaluating this claim?
```

---

## Step 9: Multi-Turn Loop

User may ask follow-up questions. Respond by:

1. Identifying which hypothesis/aspect they're probing
2. Gathering additional evidence (maintain parity across tracks if new searches needed)
3. Updating evidence matrix
4. Repeat Steps 6-8

**Turn Limits**:
- Turn 10: Offer summary
- Turn 15: Suggest archival
- Turn 18: Firm closure

---

## Step 10: Archival Prompt

After natural conclusion, offer archival:

```
This analysis covered [summary]. Would you like to archive?

1. Archive now
2. Preview first
3. Skip

Run /save to extract findings as Rems.
```

---

## Quality Checks

### Evidence Parity Audit

Before presenting Step 8, verify:
```
Track A: X searches, Y sources, Z evidence items
Track B: X searches, Y sources, Z evidence items
Track C: X searches, Y sources, Z evidence items
```

If imbalance detected, conduct additional searches for underrepresented track.

### Language Neutrality Audit

Check your presentation:
- Are descriptions for Hypothesis A and B equally neutral?
- Do you use stronger language for one hypothesis over another?
- Self-correct if bias detected in phrasing.

---

## Notes

- Scripts handle logic, prompt handles flow coordination
- Journalist agent called 3x with different roles (advocate_for_A/B/C)
- User sees unified analysis with transparent methodology
- No pre-judgment of which hypothesis is "correct"
- Evidence quality determines conclusions, not agent preference
