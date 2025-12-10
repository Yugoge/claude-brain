---
description: "Save learning session by extracting Rems, archiving conversation, and maintaining graph"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task, TodoWrite
argument-hint: "[topic-name | --all]"
model: inherit
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Save Command

Save learning sessions by extracting valuable Rems as ultra-minimal knowledge Rems, preserving the dialogue, and maintaining the knowledge graph.





### Step 0: Initialize Workflow Checklist

**Load todos from**: `scripts/todo/save.py`

Execute via venv:
```bash
source venv/bin/activate && python scripts/todo/save.py
```

Use output to create TodoWrite with all workflow steps.

**Rules**: Mark `in_progress` before each step, `completed` after. NEVER skip steps.

---


## Usage

```
/save
/save <topic-name>
/save --all
```

## Examples

```
/save                          # Archive most recent conversation
/save python-asyncio           # Archive specific topic
/save --all                    # Archive all unarchived conversations
```

## What This Command Does

Archive conversations (`/learn`, `/ask`, `/review`), extract ultra-minimal Rems (100-120 tokens), filter FSRS test dialogues, classify questions, update existing Rems (Type A clarifications), normalize wikilinks, rebuild indexes, materialize inferred links (optional), auto-generate stats/visualizations.

## Implementation


### Step 1: Pre-Processing (Batch Execution)

**Orchestrator handles all pre-processing atomically**:
```bash
source venv/bin/activate && python scripts/archival/save_orchestrator.py
```

**Automatically performs**:
1. **Archive Conversation**: `python3 scripts/services/chat_archiver.py`
2. **Parse Arguments**: Extract from `$ARGUMENTS` (topic-name | --all | empty)
3. **Session Validation**: Detect type (learn|ask|review) with confidence checks
4. **Filter FSRS** (review only): Remove test dialogues via pattern matching

**Outputs**:
- Filtered archived conversation (`chats/YYYY-MM/conversation-YYYY-MM-DD.md`)
- Session metadata (`/tmp/orchestrator_metadata.json`)

**Exit codes**:
- `0` = Valid → Continue to Step 2
- `1` = Too short (<3 turns) → Block
- `2` = Token limit exceeded (>150k) → Block

---

### Step 2: Domain Classification & ISCED Path (AI + Subagent)

**⚠️ CRITICAL**: This step determines where Rems will be stored. Incorrect classification = wrong directory = broken knowledge graph.

**Purpose**: Classify conversation into UNESCO ISCED taxonomy to determine correct storage path for Rems.

**Step-by-step execution**:

1. **Analyze conversation context** to extract key topics:
   - Identify 3-5 main concepts discussed
   - Summarize conversation focus in 2-3 sentences
   - Note technical domain (finance, programming, language, science, etc.)

2. **Call classification-expert agent** with Task tool:
   - **⚠️ CRITICAL**: Classify LEARNING CONTENT (what user learned), not pedagogical method (how we taught)
   - Prompt must include:
     - User's learning outcomes (concepts mastered, demonstrated understanding)
     - Pedagogical methods used (labeled as "methods used, DO NOT classify based on this")
   - Request 3-level ISCED classification (broad, narrow, detailed)
   - Agent returns JSON with `domain`, `isced` codes, and `confidence` score

3. **Parse classification result** from agent response:
   - Extract JSON from agent's final message
   - Validate required fields: `domain`, `isced.broad`, `isced.narrow`, `isced.detailed`
   - Check confidence level (warn if <70%)

4. **Map ISCED codes to folder paths**: Use 3-level directory structure `knowledge-base/{broad}/{narrow}/{detailed}/`

5. **Verify directory exists**:
   ```bash
   # Check if ISCED path exists in knowledge base
   test -d "knowledge-base/{broad-folder}/{narrow-folder}/{detailed-folder}" || \
     echo "⚠️  ISCED path not found - may need to create directory structure"
   ```

6. **Store classification result** in variables for later use:
   - `$domain` = domain name (e.g., "finance")
   - `$subdomain` = subdomain (e.g., "equity-derivatives")
   - `$isced_path` = full ISCED code (e.g., "04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance")
   - `$isced_detailed_path` = directory path for Step 17

**Fallback strategy**:
- If agent unavailable → Infer from conversation keywords (finance terms → 0412, code terms → 0611, etc.)
- If confidence <50% → Ask user to confirm classification
- If ISCED path missing → Create directory structure or use closest match

**Output stored for**:
- Step 3: Extract Concepts (determine subdomain)
- Step 5: Enrich with Typed Relations (load existing concepts from domain)
- Step 9: Post-Processing (determine file paths)

**CRITICAL**: All Rems MUST be saved to ISCED 3-level paths. No legacy domain shortcuts allowed.

---

### Step 3: Extract Concepts (AI-driven, no file creation)

**Main agent extraction process**:

**IMPORTANT**: Extract Rems from **active session context** (NOT from `archived_file`). The file is only used for Rem `source` field paths.

**Extraction Priority** (highest to lowest):
1. **Formulas & Equations**: Mathematical expressions, pricing models, technical calculations
2. **Professional Terminology**: Domain-specific terms, abbreviations, technical jargon, standard definitions
3. **Concepts & Mechanisms**: How systems work, causal relationships, theoretical frameworks
4. **Grammar Patterns & Rules**: Language structures, syntax rules, exception patterns (language domains)
5. **Procedures & Methods**: Step-by-step workflows, algorithms, problem-solving approaches

**LOW PRIORITY** (extract ONLY if user actively practiced/applied):
- Conversational examples, story contexts, narrative illustrations
- Background information, historical anecdotes
- Single-word vocabulary without grammar patterns or usage rules

**Extraction Process**:
1. Scan conversation for HIGH-PRIORITY content that user engaged with (questions, corrections, practice)
2. If user specified topic in /save arguments → Extract only concepts related to that topic
3. **Write extracted Rems to temp file** for validation:

```bash
cat > /tmp/candidate_rems.json << 'EOF'
[
  {
    "rem_id": "{subdomain}-{concept-slug}",
    "title": "{Concept Title}",
    "core_points": ["{point1}", "{point2}", "{point3}"],
    "usage_scenario": "",
    "my_mistakes": []
  }
]
EOF
```

**Note**: `usage_scenario` and `my_mistakes` are initially empty. They will be filled by the domain tutor in Step 5.

4. **Validate format immediately** (blocks on errors):

```bash
source venv/bin/activate && python scripts/archival/validate_extraction_format.py \
  --candidate-rems /tmp/candidate_rems.json
```

Exit codes: 0=valid, 1=invalid (blocks pipeline)

**Verification Rules**:
- ✅ User demonstrated understanding through practice, follow-up questions, or corrections
- ✅ Content has long-term retention value (formulas, mechanisms, patterns, not stories)
- ❌ AI's explanations user didn't engage with
- ❌ Narrative context without technical substance

**Output**: Validated `/tmp/candidate_rems.json` ready for Step 5 enrichment

---

### Step 4: Analyze User Learning & Rem Updates (Review Sessions Only)

**If session_type == "review"**, AI analyzes the full conversation context to determine:

**Two Decision Paths**:

1. **Existing Rem Updates** (Type A - Clarification):
   - User asked follow-up questions that revealed misunderstanding of existing Rem
   - User's subsequent responses confirmed they now understand the correction
   - **Verification required**: Did user demonstrate understanding through practice/confirmation?
   - ✅ Extract clarification text from AI's response that user engaged with
   - ❌ Don't update if user only asked but didn't confirm understanding

2. **New Concept Extraction** (Type B/C/D - Extension/Comparison/Application):
   - User asked questions that led to genuinely new knowledge
   - User showed engagement with the new concept (follow-up, examples, etc.)
   - Extract as new Rem following Step 3 rules

**Critical Judgment Criteria** (AI uses full conversation context):

- **For updates to existing Rems**:
  - Which Rem was being discussed? (Look for `[[rem-id]]` references or context)
  - What misconception did user have?
  - Did user confirm understanding after clarification?
  - Which section to update: `## Core Memory Points` (definitions) | `## Usage Scenario` (examples/usage) | `## My Mistakes` (corrections)

- **For new concepts**:
  - Is this genuinely new knowledge, or just clarification of existing Rem?
  - Did user engage with the concept beyond a single question?
  - Would this be useful as a standalone Rem?

**Output Format** (stored in memory for Steps 7 & 9):

```
rems_to_update = [
  {
    "rem_id": "{existing-rem-id}",
    "clarification_text": "{What user learned, extracted from AI response}",
    "target_section": "## Core Memory Points",
    "reasoning": "{Why this is an update vs new concept}"
  }
]
```

**Important Principles**:
- ✅ Judge based on **user's verified understanding**, not question patterns
- ✅ Use **full conversation context**, not isolated question text
- ✅ Only extract what user **actually learned and confirmed**
- ❌ Don't use pattern matching ("Can you clarify" ≠ automatic Type A)
- ❌ Don't extract if user asked but didn't engage with the answer

**Output**: Store `rems_to_update` list for Steps 7 and 9

---

### Step 5: Enrich with Typed Relations via Domain Tutor (AI + Subagent)

**⚠️ MANDATORY - DO NOT SKIP**: This step is required for [programming|language|finance|science|medicine|law] domains.

**Purpose**: Discover typed relations (synonym, prerequisite_of, contrasts_with, etc.) between new and existing concepts.

**3-Phase Workflow**:

**Phase 1: Generate Tutor Prompt**

```bash
source venv/bin/activate && python scripts/archival/workflow_orchestrator.py \
  --domain "$domain" \
  --isced-path "$isced_detailed_path" \
  --candidate-rems /tmp/candidate_rems.json
```

Script loads `/tmp/candidate_rems.json` from Step 3, outputs tutor prompt with existing concepts from domain and valid concept_id list.

**Phase 2: Call Domain Tutor**
- Use Task tool: `{domain}-tutor` (e.g., `language-tutor`, `finance-tutor`)
- Pass generated prompt from Phase 1
- Tutor returns JSON with typed_relations
- Write response to temp file: `/tmp/tutor_response.json`

**Phase 3: Merge Relations & Validate Hierarchical Consistency**
```bash
# Merge and validate
source venv/bin/activate && python scripts/archival/workflow_orchestrator.py \
  --domain "$domain" \
  --isced-path "$isced_detailed_path" \
  --candidate-rems /tmp/candidate_rems.json \
  --tutor-response /tmp/tutor_response.json \
  --output /tmp/enriched_rems.json
```

Script validates IDs, merges typed_relations, and enforces hierarchical consistency:
- Prevents bidirectional asymmetric contradictions
- Detects circular prerequisite chains
- Prevents multi-pair relations via semantic priority
- Auto-removes problematic relations with detailed warnings

**Output**: Enriched Rems saved to `/tmp/enriched_rems.json` (ready for Step 9)

**Fallback**: If tutor unavailable → Use original candidate Rems (empty typed_relations)

**⚠️ CRITICAL - User Modifies Candidate Rems**:

If user requests modifications to extracted concepts (filter, add, edit) in Step 8, you MUST:

1. **Update candidate_rems.json** with user's changes:
   ```bash
   cat > /tmp/candidate_rems.json << 'EOF'
   [{updated concepts}]
   EOF
   ```

2. **RE-RUN COMPLETE 3-PHASE WORKFLOW** (DO NOT skip phases):
   - Phase 1: Re-generate tutor prompt with new candidate list
   - Phase 2: Re-call domain tutor with new prompt
   - Phase 3: Merge and validate with new tutor response

3. **❌ FORBIDDEN SHORTCUTS**:
   - ❌ Manually editing tutor_response.json
   - ❌ Reusing old tutor prompt/response
   - ❌ Skipping Phase 1 and going directly to Phase 3

**Why**: The tutor prompt contains `valid_ids` list that includes both existing concepts AND candidate Rem IDs. When candidate Rems change, the valid_ids list becomes stale, causing ID validation errors in Phase 3.

**Correct workflow after user modification**:
```bash
# 1. Save filtered concepts
cat > /tmp/candidate_rems_filtered.json << 'EOF'
[{filtered concepts only}]
EOF

# 2. Phase 1: Re-generate prompt
source venv/bin/activate && python scripts/archival/workflow_orchestrator.py \
  --domain "$domain" \
  --isced-path "$isced_detailed_path" \
  --candidate-rems /tmp/candidate_rems_filtered.json

# 3. Phase 2: Copy prompt output, call tutor, save to /tmp/tutor_response_new.json

# 4. Phase 3: Merge with NEW tutor response
source venv/bin/activate && python scripts/archival/workflow_orchestrator.py \
  --domain "$domain" \
  --isced-path "$isced_detailed_path" \
  --candidate-rems /tmp/candidate_rems_filtered.json \
  --tutor-response /tmp/tutor_response_new.json \
  --output /tmp/enriched_rems_filtered.json
```

---

### Step 6: Rem Extraction Transparency

**After extracting and enriching Rems**, YOU (main agent) MUST present them in user-friendly format (no code):

**Subagent behavior**: May use NLP scripts, classification algorithms, graph analysis tools
**Main agent behavior**: Show user the RESULTS (extracted Rems), not the PROCESS (code)

**Code Presentation**:
- ❌ DON'T: Show script paths, JSON files, technical artifacts
- ✅ DO: Present extracted Rems in readable format (titles, summaries, relationships)
- Exception: User explicitly requests debugging/process details

**Code artifacts are tools for the system**, not content for the user.

**Post-Processing**: If helper scripts used, READ results and present in natural language (titles, summaries, relationships). ❌ Don't paste JSON/code. ✅ Present readable bullet points. Exception: User requests debugging details.

---

### Step 7: Generate Preview

**Format depends on session type**:

#### For Learn/Ask Sessions

Present ultra-compact 1-line previews:

**Format**:
```
N. [Title] → [1-line summary] → path/to/file.md
```

**Example**:
```
1. French Verb "Vouloir" → Conjugation patterns and usage → knowledge-base/.../french-verb-vouloir.md
2. Black-Scholes Model → Option pricing formula → knowledge-base/.../black-scholes-model.md
```

#### For Review Sessions

Use `preview_generator.format_review_preview()` with **three sections**:

```python
from archival.preview_generator import PreviewGenerator

generator = PreviewGenerator()
preview = generator.format_review_preview(
    concepts=extracted_concepts,           # From Step 3 extraction
    rems_reviewed=rems_reviewed_list,      # From orchestrator metadata
    rems_to_update=rems_to_update          # From Step 4 AI analysis
)

print(preview)
```

**Three-section format**:
```
📊 Review Session Analysis
✅ Reviewed Rems (FSRS Updated): {N}
  1. [[{rem-id-1}]] - Rating: {1-4}
💡 New Concepts Discovered: {N}
  1. **{Concept Title}** (Type {B|C|D})
⚙️ Rem Updates (Clarifications): {N}
  1. [[{rem-id}]] ({Section})
     + "{Clarification text...}"
📊 Summary:
  - Reviewed: {N} Rems | Create: {N} new | Update: {N} existing | Archive: 1 chat
```

**IMPORTANT**: Pass `rems_to_update` from Step 4 AI analysis to show Section 3 (Rem Updates).

**Show ALL previews** before user approval.

---

### Step 8: User Confirmation

Wait for explicit approval before creating files.

**Present**:
```
📊 [Topic] | [domain] | [N] concepts

[Previews from Step 7]

Files: [N] Rems + 1 conversation + 2 index updates
```

**Options**:
```xml
<options>
    <option>Approve</option>
    <option>Modify</option>
    <option>Cancel</option>
</options>
```

**Handle**:
- Approve → Step 9 (Execute Post-Processing)
- Modify → Iterate, re-present
- Cancel → Abort gracefully

---

### Step 9: Execute Automated Post-Processing

**⚠️ CRITICAL - MANDATORY USE OF SCRIPTS**:
- ✅ MUST use `save_post_processor.py` for ALL file creation
- ❌ NEVER create Rem files manually (Write/Edit tools)
- ❌ NEVER bypass pipeline even if validation fails
- ⚠️ ONLY execute after user approval

**If post-processor fails**:
1. Read error message carefully
2. Fix data format (usually enriched_rems.json)
3. Rerun post-processor
4. DO NOT create files manually as workaround

**Construct complete enriched_rems.json** (Bug 2 fix: merge Step 5 output with session metadata):

```bash
source venv/bin/activate && python scripts/archival/construct_enriched_rems.py \
  --enriched-rems /tmp/enriched_rems.json \
  --session-id "{topic-slug-YYYY-MM-DD}" \
  --title "{Conversation title}" \
  --summary "{2-3 sentence summary of what user learned}" \
  --archived-file "{from Step 1}" \
  --session-type "{learn|ask|review}" \
  --domain "{from Step 2}" \
  --subdomain "{topic-slug}" \
  --isced-path "{from Step 2}" \
  --tags "{comma,separated,tags}" \
  --output /tmp/enriched_rems_complete.json
```

**Data Format Support**:
- Script accepts **both** legacy array format `[{...}]` and standard dict format `{"rems": [...], "session_metadata": {...}}`
- Auto-converts legacy format with warning
- See `docs/architecture/data-formats.md` for complete format specification

**Execute post-processor**:

```bash
source venv/bin/activate && python scripts/archival/save_post_processor.py \
  --enriched-rems /tmp/enriched_rems_complete.json \
  --archived-file "{from Step 1}" \
  --session-type "{learn|ask|review}"
```

**Post-processor automatically executes**:
- **Validation**: Pre-creation checks (preflight_checker + pre_validator_light)
- **File Creation**: Create Knowledge Rems (atomic transaction, N files)
- **Conversation**: Normalize metadata and rename file
- **Updates**: Update existing Rems (review sessions with Type A clarifications)
- **Graph**: Update knowledge graph (backlinks, conversation index, normalize wikilinks, fix bidirectional links)
- **Inferred Links**: Materialize inferred links (optional, with preview)
- **FSRS Sync**: Add Rems to review schedule (automatic)
- **Memory MCP**: Record to MCP (automatic)
- **Navigation**: Update conversation Rem links (bidirectional)
- **Analytics**: Generate analytics & visualizations (automatic)
- **Report**: Display completion report with performance metrics

**Post-processor output**:
```
🚀 Starting /save post-processing workflow
   Processing {N} Rem(s) for session: {title}

📋 Pre-creation Validation
  ✓ Preflight check passed
  ✓ Light validation passed ({N} Rems)

💾 Atomic File Creation
  📝 Normalizing conversation...
  ✓ Normalized: {conversation-file}.md
  📝 Creating Knowledge Rems...
  ✓ Created: {rem1}.md
  ✓ Created: {rem2}.md
  ...
  🔗 Linking conversation to Rems...
  ✓ Updated conversation with {N} Rem links
  ✅ All files written successfully

🔗 Update Knowledge Graph
  ✓ Backlinks updated for {N} Rems
  ✓ Conversation index updated
  ✓ Wikilinks normalized

🔮 Materialize Inferred Links (Optional)
  ⏭️  Skipped (non-interactive mode)

📅 Sync to FSRS Review Schedule
  ✓ FSRS sync completed

🧠 Record to Memory MCP
  ℹ️  MCP recording should be handled by main agent
  ⏭️  Skipped (MCP tools unavailable in subprocess)

📊 Generate Analytics & Visualizations
  ✓ Analytics generated (30-day period)
  ✓ Graph data generated
  ✓ Visualization HTML generated

✅ Completion Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Session: {title}
   Type: {session_type}
   Domain: {domain} > {subdomain}

📝 Files Created:
   • {N} Rem(s):
     - {rem1}.md
     - {rem2}.md
     ...
   • 1 Conversation: {conversation-file}.md

🔗 Graph Updates:
   • Backlinks rebuilt for {N} Rem(s)
   • Conversation index updated
   • Wikilinks normalized

📅 FSRS Review:
   • {N} Rem(s) added to review schedule

📊 Analytics:
   • 30-day statistics updated
   • Knowledge graph visualization regenerated

⏱️  Performance:
   • Total time: {X}s
   • Average: {Y}s per Rem

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ /save workflow completed successfully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next: /review
```

**Exit codes**:
- `0` = Success (all operations completed)
- `1` = Validation failed (no changes made)
- `2` = File creation failed (rollback performed)
- `3` = Post-processing failed (files created but downstream operations failed)

**Error handling**:
- Validation failure → No files created, report errors, suggest fixes
- File creation failure → Automatic rollback, restore previous state
- Post-processing failures → Log warnings, continue (non-blocking)

**Important notes**:
- ✅ Post-processor uses FileWriter for atomic transactions (all-or-nothing guarantee)
- ✅ Rollback on any file creation error (no partial state)
- ✅ All Steps 12-22 automated in single script call
- ✅ Performance metrics included in completion report
- ⚠️  Step 17 (materialize inferred links) skipped in non-interactive mode
- ⚠️  Step 19 (Memory MCP) must be handled by main agent (MCP tools unavailable in subprocess)

---

## Conversation Discovery

**Method 1 (Primary)**: Check current session for substantial multi-turn dialogue (5+ turns, Q-A-follow-up patterns).

**Method 2 (Avoid Duplicates)**: Read `chats/index.json`, filter already archived topics.

**Method 3 (User-Specified)**: Search history for matching keywords, use fuzzy matching, suggest closest matches.

## Important Rules

**DO**: Analyze conversation directly, extract from ACTUAL content, use ultra-minimal template (100-120 tokens/Rem), show previews, wait for approval, run post-processing, use kebab-case filenames, respect user instructions.

**DON'T**: Use `python -c`/heredocs (use scripts), invoke conversation-archiver subagent, hallucinate, create without approval, skip previews, extract wrong amounts (3-7 typical), skip post-processing, archive trivial/duplicate conversations.

## Success Criteria

**Core**: Extract from ACTUAL conversation (no hallucinations), user approval before files, ultra-minimal format (100-120 tokens/Rem), correct ISCED paths, wikilinks normalized, backlinks/indexes updated, stats auto-generated, comprehensive completion report.

**Edge cases**: No conversation (help message), already archived (inform), too short (warn+override), user cancels (graceful exit), modifications (iterate), no inferences (skip materialization), failures (fallback/log/continue).
