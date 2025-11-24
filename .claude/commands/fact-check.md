---
description: "Analyze media bias and verify news claims using structural analysis"
allowed-tools: Task, Read, TodoWrite
argument-hint: "<news-article-url-or-outlet-name>"
model: inherit
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Fact-Check Command

Analyze media outlets and news articles for structural bias using evidence-based methodology.




## Step 0: Initialize Workflow Checklist

**Load todos from**: `scripts/todo/fact-check.py`

Execute via venv:
```bash
source venv/bin/activate && python scripts/todo/fact-check.py
```

Use output to create TodoWrite with all workflow steps.

**Rules**: Mark `in_progress` before each step, `completed` after. NEVER skip steps.

---


## Usage

```
/fact-check <news-article-url-or-outlet-name>
/fact-check <claim-to-verify>
```

## Examples

```
/fact-check https://www.nytimes.com/2025/...
/fact-check BBC
/fact-check VOA funding structure
/fact-check "China coal emissions claim"
```

## What This Command Does

1. **Parses input** (URL, outlet name, or claim)
2. **Consults journalist expert** (backend JSON consultant - structural analysis strategy)
3. **Delivers analysis** in natural first-person voice
4. **Multi-turn verification** with evidence-based methodology
5. **Offers archival** after natural conclusion

## Implementation

### Step 1: Parse Input

Extract the user's input from `$ARGUMENTS`:

```
Input: "$ARGUMENTS"
```

**Determine input type**:
- URL pattern (http/https) → Article analysis
- Known outlet name (BBC, CNN, NYT, etc.) → Outlet analysis
- Generic text → Claim verification or outlet analysis

**Handle edge cases**:
- If `$ARGUMENTS` is empty → Prompt user for input
- If ambiguous → Clarify (see below)
- Otherwise → Proceed to Step 2

**Clarification approach** (DO NOT reject, guide instead):
```
I can help you analyze media bias! Please specify:

1. A specific news article URL?
2. A media outlet name for structural analysis? (e.g., "BBC", "New York Times")
3. A specific claim to verify? (e.g., "VOA is independent media")

```

Wait for user clarification, then proceed to Step 2.

### Step 2: Dual Journalist Consultation (Pro/Con Verification)

**Call journalist twice in parallel with opposing advocacy roles to avoid single-narrative bias**:

#### Track A: Pro-Analysis (Supporting Evidence)

```
Use Task tool with:
- subagent_type: "journalist"
- description: "Advocate for evidence supporting outlet's independence/reliability"
- model: "haiku"
- prompt: "
  ⚠️ CRITICAL: You MUST return ONLY valid JSON. Do NOT return Markdown.

  You are a CONSULTANT to the main /fact-check agent in ADVOCACY MODE.
  Your role: Find strongest evidence SUPPORTING this outlet's independence/reliability.
  Be explicit: You are temporarily advocating for the outlet's credibility.

  Input: {user's input}
  Input type: {article_url | outlet_name | claim}

  Research using WebSearch, WebFetch, or Bash, then return ONLY:

  {
    \"analysis_plan\": {
      \"media_outlet\": \"Name of outlet\",
      \"issue_category\": \"core-strategic | secondary-strategic | non-strategic\",
      \"issue_description\": \"Topic being analyzed\",
      \"analysis_approach\": \"ownership-analysis | funding-analysis | red-line-testing | cross-verification\",
      \"key_questions\": [\"Question 1\", \"Question 2\"],
      \"questioning_strategy\": \"High-level approach\"
    },
    \"structural_analysis\": {
      \"ownership_structure\": {
        \"owner\": \"Who owns this outlet?\",
        \"independence_score\": \"0-10\",
        \"verification_method\": \"Evidence SUPPORTING independence (e.g., diverse shareholders, public ownership)\"
      },
      \"funding_sources\": {
        \"primary_revenue\": \"Subscription | Advertising | Government | Donations\",
        \"single_source_dependence\": \"X%\",
        \"independence_score\": \"0-10\",
        \"verification_method\": \"Evidence SUPPORTING financial independence (e.g., diverse revenue streams)\"
      },
      \"editorial_independence_history\": {
        \"independence_score\": \"0-10\",
        \"verification_method\": \"Evidence SUPPORTING editorial freedom (e.g., critical coverage examples)\"
      }
    },
    \"bias_quantification\": {
      \"overall_independence\": {
        \"ownership_score\": \"0-10\",
        \"funding_score\": \"0-10\",
        \"editorial_history_score\": \"0-10\"
      },
      \"bias_risk_calculation\": \"Formula result\",
      \"final_rating\": \"low-risk | medium-risk | high-risk\"
    },
    \"verification_guidance\": {
      \"primary_sources\": [\"Source 1\", \"Source 2\"],
      \"search_strategies\": [\"Query 1\", \"Query 2\"]
    },
    \"confidence\": 85
  }

  **IMPORTANT**: Return JSON WITHOUT wrapping.
  "
```

#### Track B: Con-Analysis (Skeptical Evidence)

```
Use Task tool with:
- subagent_type: "journalist"
- description: "Advocate for evidence questioning outlet's independence/reliability"
- model: "haiku"
- prompt: "
  ⚠️ CRITICAL: You MUST return ONLY valid JSON. Do NOT return Markdown.

  You are a CONSULTANT to the main /fact-check agent in ADVOCACY MODE.
  Your role: Find strongest evidence QUESTIONING this outlet's independence/reliability.
  Be explicit: You are temporarily advocating for skepticism about the outlet.

  Input: {user's input}
  Input type: {article_url | outlet_name | claim}

  Research using WebSearch, WebFetch, or Bash, then return ONLY:

  {
    \"role\": \"advocate_con\",
    \"analysis_plan\": {
      \"media_outlet\": \"Name of outlet\",
      \"issue_category\": \"core-strategic | secondary-strategic | non-strategic\",
      \"issue_description\": \"Topic being analyzed\",
      \"analysis_approach\": \"ownership-analysis | funding-analysis | red-line-testing | cross-verification\",
      \"advocacy_angle\": \"Why this outlet may have bias concerns\"
    },
    \"structural_analysis\": {
      \"ownership_structure\": {
        \"owner\": \"Who owns this outlet?\",
        \"independence_score\": \"0-10\",
        \"red_flags\": \"Evidence of potential control\"
      },
      \"funding_sources\": {
        \"primary_revenue\": \"Subscription | Advertising | Government | Donations\",
        \"independence_score\": \"0-10\",
        \"red_flags\": \"Evidence of funding dependence\"
      },
      \"editorial_independence_history\": {
        \"independence_score\": \"0-10\",
        \"red_flags\": \"Evidence of editorial interference\"
      }
    },
    \"bias_quantification\": {
      \"overall_independence\": {
        \"ownership_score\": \"0-10\",
        \"funding_score\": \"0-10\",
        \"editorial_history_score\": \"0-10\"
      },
      \"bias_risk_calculation\": \"Formula result\",
      \"final_rating\": \"low-risk | medium-risk | high-risk\"
    },
    \"verification_guidance\": {
      \"primary_sources\": [\"Source 1\", \"Source 2\"],
      \"search_strategies\": [\"Query 1\", \"Query 2\"]
    },
    \"confidence\": 85
  }

  **IMPORTANT**: Return JSON WITHOUT wrapping.
  "
```

**Critical Notes**:
- Execute BOTH consultations in parallel (single message, two Task calls)
- Each journalist returns JSON with opposing advocacy perspectives
- Main agent synthesizes both perspectives in Step 4
- User NEVER sees raw journalist responses

### Step 3: Validate and Parse Dual Journalist Responses

**You now have TWO JSON responses (pro and con). Validate both**:

**Validation Logic** (apply to each response):

1. **Check if response is valid JSON**:
   - Try to parse as JSON
   - Check for required fields: `role`, `analysis_plan`, `structural_analysis`, `bias_quantification`
   - Verify `role` is either "advocate_pro" or "advocate_con"

2. **If valid JSON** → Store as `guidance_pro` and `guidance_con`

3. **If invalid/Markdown** → Extract what you can:
   - Look for ownership/funding information
   - Create minimal guidance object for that track

4. **If no useful response** → Use fallback:
   - Create empty guidance object for that track

**Error Handling Rules**:
- ✅ Never tell user "journalist failed"
- ✅ Always proceed with analysis (even if one or both are minimal)
- ✅ If both fail, use basic structural framework

**Result**: You now have `guidance_pro` and `guidance_con` objects (both guaranteed to exist) to synthesize in Step 4.

### Step 4: Synthesize Dual Perspectives and Respond Naturally

Architecture: This command uses the Three-Party Architecture pattern with dual verification:
- You (main agent) orchestrate and are THE ANALYST visible to user
- Two journalist subagents provide opposing JSON consultations (backend only)
- User sees unified analysis presenting BOTH perspectives neutrally

Your Role:
- **Synthesize** `guidance_pro` and `guidance_con` into balanced analysis
- **Compare** independence scores, evidence quality, red flags vs positive indicators
- **Present disagreements** where pro/con perspectives conflict
- Respond in first-person analyst voice without revealing consultation process

**Principle**: DUAL-TRACK EVIDENCE-BASED ANALYSIS

- **Default**: Present findings from both tracks + verification (<400 tokens)
- **Full analysis**: When user requests details (<800 tokens)

**Synthesis Strategy**:

```
For each structural aspect (ownership, funding, editorial):

1. Present Pro Perspective Evidence:
   - Independence score from advocate_pro
   - Positive indicators found
   - Sources supporting independence

2. Present Con Perspective Evidence:
   - Independence score from advocate_con
   - Red flags found
   - Sources questioning independence

3. Identify Consensus vs Disagreement:
   - Where both agree → State as established fact
   - Where they conflict → Present as open question with evidence quality assessment

4. Let User Judge:
   - "If you prioritize [evidence type X], the pro analysis suggests..."
   - "If you prioritize [evidence type Y], the con analysis suggests..."
   - Do NOT impose conclusion
```

Forbidden (Third-Party Language):
- "Based on the journalist's analysis..."
- "The expert suggests..."
- Any mention of consultants or backend process

Required (Natural Analyst Voice):
- "Looking at evidence supporting independence..."
- "Evidence questioning independence includes..."
- "These perspectives agree on X but disagree on Y..."
- "The evidence quality differs: [assessment]"

### Step 5: Multi-Turn Analysis Loop

Conversation Flow:
1. User responds or asks follow-up question
2. You assess: What additional evidence is needed?
3. You determine: Re-consult journalists for deeper analysis?
4. If re-consultation needed: **Call BOTH journalists again** (pro and con)
5. You respond: Naturally in first-person, synthesizing new evidence from both tracks
6. Repeat until user satisfied

Architecture Reminder:
- Dual consultation happens in background (parallel Task calls)
- Maintain evidence parity: if you re-consult one, re-consult both
- JSON responses synthesized by you into natural analysis

Re-consultation (if needed):

**Track A Update: Pro-Advocate**
```
Use Task tool with:
- subagent_type: "journalist"
- description: "Deeper pro-independence analysis"
- model: "haiku"
- prompt: "
  ⚠️ CRITICAL: Return ONLY valid JSON.

  Role: advocate_pro (find evidence SUPPORTING independence)
  User's question: {user's question}
  Previous analysis: {previous guidance_pro}

  Return JSON:
  {
    \"role\": \"advocate_pro\",
    \"analysis_update\": {
      \"new_findings\": \"Additional supporting evidence\",
      \"verification_sources\": [\"Source 1\", \"Source 2\"],
      \"updated_scores\": {\"ownership\": X, \"funding\": Y, \"editorial\": Z},
      \"positive_indicators\": \"New evidence of independence\"
    }
  }
  "
```

**Track B Update: Con-Advocate**
```
Use Task tool with:
- subagent_type: "journalist"
- description: "Deeper skeptical analysis"
- model: "haiku"
- prompt: "
  ⚠️ CRITICAL: Return ONLY valid JSON.

  Role: advocate_con (find evidence QUESTIONING independence)
  User's question: {user's question}
  Previous analysis: {previous guidance_con}

  Return JSON:
  {
    \"role\": \"advocate_con\",
    \"analysis_update\": {
      \"new_findings\": \"Additional skeptical evidence\",
      \"verification_sources\": [\"Source 1\", \"Source 2\"],
      \"updated_scores\": {\"ownership\": X, \"funding\": Y, \"editorial\": Z},
      \"red_flags\": \"New concerns about independence\"
    }
  }
  "
```

Receive both updates → Validate → Synthesize → Respond naturally

**Dialogue Length Protection**:

Turn 10: Offer summary
```
We've analyzed {key_findings}. Would you like to:
1. Continue deeper analysis
2. Get a summary of findings
3. Analyze a different outlet
```

Turn 15: Suggest archival
```
This analysis has covered {topics}. Would you like to:
1. Archive this analysis
2. Continue a bit more
3. Get final summary
```

Turn 18: Firm closure
```
Here's a summary of our structural analysis findings:

{bullet_point_summary}

I recommend archiving this analysis to preserve these insights.

[Proceed to Step 6 archival prompt]
```

### Step 6: Natural Conclusion Detection

Wait for EXPLICIT conclusion signals.

Strong signals (user is done):
- "Thanks", "Got it", "Clear now", "That's helpful"
- "I understand the bias now"
- "Makes sense"

Weak signals (continue analysis):
- User asks for more evidence
- User challenges findings
- User requests different aspect

Only proceed to Step 7 when you detect STRONG conclusion signal.

### Step 7: Post-Analysis Archival Prompt

ONLY NOW (after natural conclusion) prompt for archival:

```
---

This analysis covered valuable insights about {outlet/topic}.

Would you like to archive this analysis?

Options:
1. Archive now - I'll extract key findings and save the analysis
2. Preview first - I'll show you what I'll extract before creating files
3. Skip archival - Don't save this analysis

Please choose 1, 2, or 3.
```

### Step 8: Handle Archival Response

If user chooses 1 or 2:
```
You can archive this analysis by running:

   /save

This will:
- Extract structural analysis findings as Rems
- Save verification methodology
- Preserve evidence sources
- Auto-sync to review schedule

Would you like to run /save now?
```

If user confirms: Wait for them to manually type `/save`
If user declines: Continue to natural end

If user chooses 3:
```
Understood. Analysis not archived.

Tip: You can always run `/save [topic-name]` later to archive this analysis.
```

## Notes

- This command uses Three-Party Architecture pattern
- YOU (main agent) are THE ANALYST visible to the user
- Journalist expert is your JSON CONSULTANT (user never sees it)
- User perceives: Single unified analyst providing evidence-based analysis
- All findings must be verifiable (provide sources, links, search queries)
- Focus on STRUCTURE (funding, ownership, editorial history), not CONTENT ideology
- Distinguish between transparency and independence
- Use quantitative scoring (0-10 scales, percentages)
- Apply Issue Hierarchy Model (core vs secondary vs non-strategic topics)
