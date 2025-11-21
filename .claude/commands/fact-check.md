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

### Step 2: Initial Journalist Consultation (JSON)

**Consult journalist expert for analysis strategy**:

```
Use Task tool with:
- subagent_type: "journalist"
- description: "Analyze media bias and provide verification strategy"
- model: "haiku"  # Fast model for JSON consultation
- prompt: "
  ⚠️ CRITICAL: You MUST return ONLY valid JSON. Do NOT return Markdown.

  You are a CONSULTANT to the main /fact-check agent, NOT the user's analyst.
  The user will NEVER see your response - only the main agent will.

  **OUTPUT REQUIREMENTS**:
  - Return ONLY the JSON object specified below
  - NO markdown code blocks (no ```json)
  - NO explanatory text before or after JSON
  - NO conversational Markdown formatting
  - If you violate this, the main agent will fail to parse your response

  Your task: Analyze this input and provide structural analysis strategy as JSON.

  Input: {user's input}
  Input type: {article_url | outlet_name | claim}

  ---

  Research using WebSearch, WebFetch (for article content), or Bash (for data lookup), then return ONLY:

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
        \"verification_method\": \"Wikipedia, annual reports, etc.\"
      },
      \"funding_sources\": {
        \"primary_revenue\": \"Subscription | Advertising | Government | Donations\",
        \"single_source_dependence\": \"X%\",
        \"independence_score\": \"0-10\",
        \"verification_method\": \"How to verify\"
      },
      \"editorial_independence_history\": {
        \"independence_score\": \"0-10\",
        \"verification_method\": \"Search queries\"
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

  **IMPORTANT**: Return the JSON object above WITHOUT any wrapping.
  "
```

Critical:
- Journalist responds with JSON ONLY (not user-facing text)
- Main agent receives structural analysis guidance
- User NEVER sees journalist's response

### Step 3: Validate and Parse Journalist Response

**Before proceeding, validate the journalist's response**:

The journalist should have returned a JSON object. Parse and validate it:

**Validation Logic**:

1. **Check if response is valid JSON**:
   - Try to parse the response as JSON
   - Check for required fields: `analysis_plan`, `structural_analysis`, `bias_quantification`

2. **If valid JSON** → Proceed to Step 4 with guidance

3. **If invalid/Markdown** → Extract what you can:
   - Look for ownership/funding information mentioned
   - Look for verification sources mentioned
   - Create minimal guidance object

4. **If no useful response** → Use fallback:
   - Create empty guidance object
   - Plan to analyze using basic structural framework

**Error Handling Rules**:
- ✅ Never tell user "journalist failed" or expose internal errors
- ✅ Always proceed with analysis (even if guidance is minimal)
- ✅ Graceful degradation: something is better than nothing

**Result**: You now have a `guidance` object (guaranteed to exist) to use in Step 4.

### Step 4: Internalize Guidance and Respond Naturally

Architecture: This command uses the Three-Party Architecture pattern:
- You (main agent) orchestrate the analysis and are THE ANALYST visible to user
- Journalist subagent provides JSON consultation via Task tool (backend responses only)
- User sees natural analysis only (no "I'm consulting..." meta-commentary)

Your Role:
- Internalize journalist's JSON guidance (structural analysis, verification methods)
- Respond in first-person analyst voice ("Let me...", "I will...", "We can...")
- Present analysis naturally without revealing consultation process

**Principle**: EVIDENCE-BASED ANALYSIS

- **Default**: Present findings + verification method (<300 tokens)
- **Full analysis**: When user requests details (<600 tokens)

**Depth escalation keywords**: "show me evidence", "how do you know", "verify this", "prove it", "sources"

Formulate YOUR response based on the analysis:

Forbidden (Third-Party Language):
- "Based on the journalist's analysis..."
- "The expert suggests..."
- "Let me consult the specialist..."
- Any mention of consultants or backend process

Required (Natural Analyst Voice):
- Use first-person ("Let me analyze...", "I found...", "The evidence shows...")
- Direct evidence presentation (ownership data, funding sources, verification links)
- Natural analytical flow (no meta-commentary)

Response Strategy:

```
If analysis_approach == "ownership-analysis":
  - Present ownership structure with evidence
  - Show independence score with rationale
  - Provide verification sources

If analysis_approach == "funding-analysis":
  - Present funding breakdown with sources
  - Calculate dependence ratio
  - Show independence score

If analysis_approach == "red-line-testing":
  - Identify core strategic issues
  - Test for critical coverage
  - Quantify bias risk

If analysis_approach == "cross-verification":
  - Compare multiple sources
  - Present contradictions
  - Evaluate credibility
```

### Step 5: Multi-Turn Analysis Loop

Conversation Flow:
1. User responds or asks follow-up question
2. You assess: What additional evidence is needed?
3. You determine: Re-consult journalist for deeper analysis?
4. If re-consultation needed: Journalist returns JSON with new findings
5. You respond: Naturally in first-person, incorporating new evidence
6. Repeat until user satisfied

Architecture Reminder:
- Consultation happens in background (user doesn't see Task tool calls)
- JSON responses from journalist are translated to evidence-based analysis by you
- Maintain analytical flow (no "let me consult..." interruptions)

Re-consultation (if needed):
```
Use Task tool with:
- subagent_type: "journalist"
- description: "Get deeper structural analysis"
- model: "haiku"
- prompt: "
  ⚠️ CRITICAL: You MUST return ONLY valid JSON. Do NOT return Markdown.

  User's latest question: {user's question}

  Previous analysis you provided: {previous JSON}

  **OUTPUT REQUIREMENTS**:
  - Return ONLY the JSON object below
  - NO markdown formatting
  - NO explanatory text

  Based on user's question, provide NEXT analysis step as JSON:
  {
    \"analysis_update\": {
      \"new_findings\": \"What new evidence was found\",
      \"verification_sources\": [\"Source 1\", \"Source 2\"],
      \"updated_scores\": {\"ownership\": X, \"funding\": Y, \"editorial\": Z},
      \"next_steps\": \"What to analyze next\"
    }
  }
  "
```

Receive new guidance → Validate → Internalize → Respond naturally

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
