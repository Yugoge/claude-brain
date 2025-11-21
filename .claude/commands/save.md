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


### Step 1: Archive Conversation

```bash
# Default: Include subagent messages (full context)
archived_file=$(python3 scripts/services/chat_archiver.py)

# Optional: Exclude subagent messages (main conversation only)
archived_file=$(python3 scripts/services/chat_archiver.py --no-include-subagents)
```

**Parameters**:
- `--include-subagents` (default): Include all subagent dialogues (analyst, language-tutor, finance-tutor, programming-tutor, medicine-tutor, law-tutor, science-tutor, journalist, etc.)
- `--no-include-subagents`: Exclude subagent messages, archive only main conversation

**Archiver behavior**: Detects subagents, labels responses as `### Subagent: {Name}`, demotes headings by 1 level, optionally filters with `--no-include-subagents`.

Store `archived_file` for Step 13 (Rem source) and Step 7 (conversation rems_extracted update).

**IMPORTANT**: The archived file contains placeholder metadata that MUST be enriched from active context:
- `id`: Generic `conversation-{date}` → Needs meaningful topic-based ID
- `title`: Generic "Conversation - {date}" → Needs descriptive title
- `domain`: Generic "general" → Needs actual domain classification
- `summary`: Placeholder text → Needs real summary from conversation

These will be updated in Step 14 using information from the active conversation context.

---

### Step 2: Parse Arguments & Detect Session Type

Extract arguments from `$ARGUMENTS`:

**Possible cases**:

1. **No arguments** (empty `$ARGUMENTS`)
   - Archive the most recent substantial conversation
   - Must identify the last meaningful dialogue in session

2. **Topic name** (e.g., `$ARGUMENTS = "python-gil"`)
   - Archive conversation about specific topic
   - Search session for matching topic

3. **--all flag** (e.g., `$ARGUMENTS = "--all"`)
   - Archive all recent unarchived conversations
   - Batch processing mode

**YOU MUST** handle all three cases correctly.

---

### Step 3: Session Validation

**⚠️ CRITICAL**: Comprehensive validation determines workflow viability. Failures here prevent incorrect extraction.

**IMPORTANT**: `session_detector.py` and `concept_extractor.py` are library modules imported by `save_orchestrator.py`. Do NOT run them as standalone CLI scripts.

**Validation is performed automatically by save_orchestrator** (executed in subsequent steps). The orchestrator:
- Detects session type with confidence scoring (FSRS patterns, turns, keywords, Rem refs)
- Validates conversation meets archival criteria (token limits, duplicates, length)
- Returns `session_type`, `rems_reviewed`, `confidence`, `fsrs_progress_saved`

**Validation checks**:
1. **Token Limit**: Max 150k (warns at 100k) → Exit code 2 if exceeded
2. **Duplicates**: Jaccard 60% similarity → Non-blocking warning
3. **Length**: Min 3 substantial turns → Exit code 1 if too short
4. **Confidence**: Session type confidence must be ≥50%

**Exit codes**:
- `0` = Pass → Continue to Step 4
- `1` = Too short → Skip archival
- `2` = Token limit → Block with error

**If validation fails**:
```
This conversation doesn't meet archival criteria:
- Reason: [Too short | Token exceeded | Low confidence]

Archival requires:
- 3+ substantial turns
- Token count <150k (current: {N}k)
- Session type confidence ≥50%
```

**Manual fallback** (if orchestrator fails):
```bash
# Simple checks
test -f .review/history.json && echo "review" || echo "learn"
# Manual: Count turns, check chats/index.json, verify content
```

---

### Step 4: Filter FSRS Test Dialogues (Review Sessions Only)

**If session_type == "review"**, filter out FSRS test portions to avoid duplicate Rem creation:

**FSRS Test Patterns** (indicators of testing dialogue, not new learning):

**FSRS Test Pattern Detection**:

Detect review test dialogues using pattern matching:
- Rating prompts: "Rate your recall.*1-4", "How well did you remember"
- Test questions: "What is [[rem-id]]", "Explain [[rem-id]]"
- FSRS feedback: "Next review.*days", "Stability.*increased"

Segment conversation into FSRS test portions vs learning portions. Only extract Rems from learning segments.

This prevents:
- ❌ Creating duplicate Rems for already-reviewed concepts
- ❌ Extracting test questions as "new concepts"
- ❌ Confusing FSRS feedback with learning content

### Step 5: Domain Classification & ISCED Path Determination

**⚠️ CRITICAL**: This step determines where Rems will be stored. Incorrect classification = wrong directory = broken knowledge graph.

**Purpose**: Classify conversation into UNESCO ISCED taxonomy to determine correct storage path for Rems.

**Step-by-step execution**:

1. **Analyze conversation context** to extract key topics:
   - Identify 3-5 main concepts discussed
   - Summarize conversation focus in 2-3 sentences
   - Note technical domain (finance, programming, language, science, etc.)

2. **Call classification-expert agent** with Task tool:
   - Provide conversation summary (2-3 sentences) and 3-5 main topics
   - Request 3-level ISCED classification (broad, narrow, detailed)
   - Agent returns JSON with `domain`, `isced` codes, and `confidence` score
   - Common codes: 0412 (finance), 0611 (programming), 0231 (language), 0533 (physics)

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
- Step 6: Extract Concepts (determine subdomain)
- Step 8: Enrich with Typed Relations (load existing concepts from domain)
- Step 13: Create Knowledge Rems (determine file paths)

**CRITICAL**: All Rems MUST be saved to ISCED 3-level paths. No legacy domain shortcuts allowed.

### Step 6: Extract Concepts

**Main agent extraction process**:

**IMPORTANT**: Extract Rems from **active session context** (NOT from `archived_file`). The file is only used for Rem `source` field paths.

1. Analyze active context, identify domain, extract 3-7 candidate Rems (distinct, reusable knowledge from user's mentions)
2. Follow user's learning logic, classify questions (update vs create)

**Extraction Rules**: ✅ User's terms/mistakes/questions, specific & reusable. ❌ Too broad/narrow, AI explanations, hallucinations, user didn't practice.

**ISCED Path Usage** (from Step 5):
- Use classification result from Step 5 to determine Rem storage location
- Path format: `knowledge-base/{broad-code-name}/{narrow-code-name}/{detailed-code-name}/`
- Example: ISCED 0412 → `knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/`

---

### Step 7: Question Type Classification (Review Sessions Only)

**If session_type == "review"**, classify each user question:

**Question Types** :
- **Type A (Clarification)**: "Can you clarify" → **Update existing Rem**
- **Type B (Extension)**: "What about", "What if" → **Create new Rem**
- **Type C (Comparison)**: "X vs Y", "compare" → **Create comparison Rem**
- **Type D (Application)**: "In practice", "How to use" → **Create application Rem**

Classify using pattern matching on user questions. Extract clarification content (2-3 concise sentences, <100 tokens) from assistant responses.

Map clarification type to target Rem section:
- Definition clarification → `## Core Memory Points`
- Example clarification → `## Usage Scenario`
- Usage clarification → `## Usage Scenario`

### Step 8: Enrich with Typed Relations via Domain Tutor (MANDATORY)

**⚠️ MANDATORY - DO NOT SKIP**: This step is required for [programming|language|finance|science] domains.

**Purpose**: Discover typed relations (synonym, prerequisite_of, contrasts_with, etc.) between new and existing concepts.

**Candidate Rems JSON Schema** (create before calling orchestrator):
```json
[{"rem_id": "rem-slug", "title": "Title", "core_points": ["p1", "p2", "p3"]}]
```
- Use `"rem_id"` field (unified standard since 2025-11-07)
- Main agent creates this JSON from extracted concepts

**Execution Method**: Use orchestrator script:

```bash
source venv/bin/activate && python scripts/archival/workflow_orchestrator.py \
  --domain "$domain" \
  --isced-path "$isced_detailed_path" \
  --candidate-rems candidate_rems.json
```

**Script automatically**:
1. Loads existing concepts from domain
2. Extracts valid concept_id list for validation
3. Builds tutor prompt with **CRITICAL** ID constraints
4. Outputs prompt for Task tool call

**Tutor prompt includes**:
- "**CRITICAL**: Use EXACT concept_id values" warning
- "**Valid concept_id values**" list (all available IDs)
- Explicit rules: "DO NOT create composite, normalized, or descriptive IDs"

**Then**:
1. Call Task tool with `{domain}-tutor` using output prompt
2. Save tutor JSON response to `tutor_response.json`
3. Re-run orchestrator with `--tutor-response tutor_response.json`
4. **Script validates tutor response** (checks all IDs match valid list)
5. Script merges typed_relations into candidate Rems

**Output**: `enriched_rems.json` with typed_relations added (all IDs validated)

**Fallback**: If tutor unavailable → Use original candidate Rems (empty typed_relations)

**Quality improvements expected**:
- Language: Merge isolated words into systematic concepts
- Finance: Add theoretical frameworks and formulas
- Programming: Focus on design patterns vs syntax

---

### Step 9: Rem Extraction Transparency

**After extracting and enriching Rems**, YOU (main agent) MUST present them in user-friendly format (no code):

**Subagent behavior**: May use NLP scripts, classification algorithms, graph analysis tools
**Main agent behavior**: Show user the RESULTS (extracted Rems), not the PROCESS (code)

**Code Presentation**:
- ❌ DON'T: Show script paths, JSON files, technical artifacts
- ✅ DO: Present extracted Rems in readable format (titles, summaries, relationships)
- Exception: User explicitly requests debugging/process details

**Code artifacts are tools for the system**, not content for the user.

**Post-Processing**: If helper scripts used, READ results and present in natural language (titles, summaries, relationships). ❌ Don't paste JSON/code. ✅ Present readable bullet points. Exception: User requests debugging details.

### Step 10: Generate Preview (Format depends on session type)

**Two preview formats**:
1. **Learn/Ask sessions**: Ultra-compact 1-line previews (format: `N. [Title] → [1-line summary] → path/to/file.md`)
2. **Review sessions**: Three-section preview (reviewed Rems + new concepts + updates). Use `scripts/archival/preview_generator.py` for generation.

**Show ALL previews** before user approval.

### Step 11: User Confirmation

Wait for explicit approval before creating files.

**Present**:
```
📊 [Topic] | [domain] | [N] concepts

[Ultra-compact previews from Step 4]

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
- Option 1 → Step 12 (Pre-creation Validation)
- Option 2 → Iterate, re-present
- Option 3 → Abort gracefully

### Step 12: Pre-creation Validation

**⚠️ MANDATORY - DO NOT SKIP**: This step prevents collisions, duplicates, and broken relations. Skipping this risks corrupting the knowledge graph.

**ONLY after user approval**, run two-stage validation:

**Stage 1**: `preflight_checker.py` (mandatory for core domains) → Exit 0=Pass, 1=Warnings, 2=BLOCK (re-run Step 9)

**Stage 2**: `pre_validator_light.py` → Validates rem_id uniqueness, typed relations targets, duplicates (Jaccard >60%). Exit 0=Pass, 1=Warnings, 2=Critical.

**If both pass** → Proceed to Step 13

### Step 13: Create Knowledge Rems

**ONLY after user approval**, create files in this order:

**⚠️ CRITICAL ORDERING**: You MUST execute Step 14 (Process Conversation Archive) BEFORE creating Rems.

**Why**: Rem files need the FINAL conversation filename in their `source` field. If you create Rems before renaming, the source will point to the temporary filename.

**Correct execution order**:
1. **First**: Run Step 14 (Process Conversation Archive) → get `$renamed_conversation_file`
2. **Then**: Create Rems using `$renamed_conversation_file` as source (this step)
3. Continue with remaining steps

---

**⚠️ PREREQUISITE**: Step 14 must complete first (see above).

**Use `create-rem-file.py` script** to generate standardized Rem files with all required sections.

For each Rem:

```bash
source venv/bin/activate && python scripts/archival/create-rem-file.py \
  --rem-id "{rem-id}" \
  --title "{rem-title}" \
  --isced "{isced_path}" \
  --subdomain "{subdomain}" \
  --core-points '["{point1}", "{point2}", "{point3}"]' \
  --usage-scenario "{usage_text}" \
  --mistakes '["{mistake1}", "{mistake2}"]' \
  --related-rems '[]' \
  --conversation-file "{archived_file}" \
  --conversation-title "{conversation_title}" \
  --output-path "knowledge-base/{isced_path}/{NNN}-{subdomain}-{rem-slug}.md"
```

Where:
- `{NNN}` = 3-digit sequence number (001, 002, 003, ..., incremented within subdomain)
- `{subdomain}` = subdomain classification (french, equity-derivatives, csharp, etc.)
- `{rem-slug}` = kebab-case concept title
- `{rem-id}` = `{subdomain}-{rem-slug}` (for global uniqueness)

**FILENAME FORMAT RULE (2025-11-04 corrected)**:
- ✅ CORRECT: `020-equity-derivatives-theta-time-value-decay.md`
- ❌ WRONG: `equity-derivatives-020-theta-time-value-decay.md`

**Filename generation logic**:
1. Determine next sequential number for this subdomain (scan existing files, find max number + 1)
2. Format: `f"{number:03d}-{subdomain}-{slugified_title}.md"`
3. Example: If equity-derivatives has files 001-019, next is `020-equity-derivatives-{rem}.md`

Where `{isced_path}` is determined from Step 6 classification:
- Example: `04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/`

**Script auto-adds**: Frontmatter (rem_id, title, isced, subdomain, created, source), all sections, bidirectional conversation link, relative paths.

**Build complete Rem from tutor suggestions + main agent supplements**:

If Rem was enriched by tutor (Step 9), use tutor's enhanced fields:
- `title`: Use tutor's academic title
- `core_points`: Parse tutor's `core_content` (already formatted as bullet points)
- `usage_scenario`: Use tutor's `usage_scenario_suggestion`
- `my_mistakes`: Merge tutor's `common_mistakes_suggestion` + user's actual errors from conversation
- `academic_source`: Add tutor's `academic_source` (if provided, typically for finance/science)
- `typed_relations`: Use tutor's `typed_relations` array (preferred over `related_to`)

**Validate typed_relations before writing**:
```bash
source venv/bin/activate && python scripts/archival/validate_relations.py \
  --relations-json '{tutor_typed_relations_json}' \
  --domain-path "{isced_detailed_path}" \
  --verbose
```

This validation:
- Filters out relations to non-existent concepts
- Checks relation type validity (synonym, prerequisite_of, etc.)
- Returns valid_relations + invalid_relations

Main agent supplements missing fields:
- `isced`: Full ISCED slug from folder path
- `subdomain`: Subdomain classification (e.g., "french", "equity-derivatives", "csharp")
- `created`: Today's date (YYYY-MM-DD)
- `source`: Relative path from Rem to conversation (`os.path.relpath(archived_file, rem_dir)`)
- `rem_id`: Format as `{subdomain}-{rem-slug}` for global uniqueness
  - Example: tutor's `concept_id: "theta-decay"` + subdomain `"equity-derivatives"` → `rem_id: "equity-derivatives-theta-decay"`
  - Ensures uniqueness across different subdomains with similar concept names

**Use ultra-minimal template** (100-120 tokens):
- Use English-only section headers as defined in template (e.g., "Core Memory Points", not bilingual)
- 3 core points max (not 3-5)
- Remove learning_audit field
- Remove session reference section (just source field)
- Keep: title, isced, subdomain, created, source, related, mistakes, usage

**Naming**: kebab-case, remove special chars, concise

**Rem file format**: Follow the template at `knowledge-base/_templates/rem-template.md`

**Key requirements**:
- Ultra-minimal format (100-120 tokens per Rem)
- Use ISCED code field instead of legacy domain field
- 3 core points maximum (not 3-5)
- Include: title, core points, usage scenario, mistakes, related Rems
- Use tutor-enriched fields when available (from Step 9):
  - `title` from tutor's academic title
  - `core_points` from tutor's `core_content`
  - `usage_scenario` from tutor's `usage_scenario_suggestion`
  - `my_mistakes` merge tutor's suggestions + user's actual errors
  - `related` from tutor's `related_to` list

**Handling Conversation Source Section:**

After the `## Related Rems` section, ALWAYS add a `## Conversation Source` section:

```markdown
## Conversation Source

→ See: [Conversation Title](relative/path/to/conversation.md)
```

Where:
- Conversation Title = extracted from conversation frontmatter title field
- Relative path = calculated from rem directory to conversation file using `os.path.relpath()`

**Example:**
```markdown
## Conversation Source

→ See: [French Review Session - Grammar](../../../../chats/2025-10/french-review-session-conversation-2025-10-28.md)
```

**Handling Related Rems Section:**

**IMPORTANT**: Always write Related Rems as **wikilinks** during creation (Step 13). They will be automatically converted to markdown links in Step 16 (Update Knowledge Graph).

When creating the `## Related Rems` section in Rem files:

1. **If tutor provided `typed_relations`**: Use `valid_relations`, format as `- [[{subdomain}-{rem-slug}]] {rel: <type>}` (wikilinks). Step 16 converts to markdown links.
2. **If tutor provided legacy `related_to`**: Convert to wikilinks `[[{subdomain}-{rem-slug}]]` with generic `{rel: related}`
3. **If no relations**: Write `*(Will be populated by backlinks rebuild)*`

**Logging invalid relations**:
- If validation filtered out invalid relations, log for monitoring:
  ```
  ⚠️  Tutor quality note: {N} invalid relations filtered
      (concepts not found or invalid types)
  ```
- This helps track tutor quality over time

3. **CRITICAL RULE - Never confuse metadata with content**:
   - ❌ **WRONG**: `→ See: chats/2025-10/conversation.md` (this is source metadata)
   - ✅ **RIGHT**: `[[related-rem]] {rel: type}` (actual related Rem)
   - The `source` field belongs ONLY in frontmatter YAML, NEVER in body sections
   - Source conversation is metadata (where Rem came from), not a related concept
   - Related Rems are OTHER knowledge Rems in the knowledge base, not conversation archives

**Why this matters:**
- `source` in frontmatter = provenance metadata (which conversation created this Rem)
- `## Related Rems` in body = bidirectional links to other knowledge concepts
- Mixing these two creates broken navigation and defeats the knowledge graph

### Step 14: Process Conversation Archive

**Initial file created by `chat_archiver.py` in Step 1** with placeholder metadata. This step enriches and normalizes the file.

**Run normalization script** to update front matter and rename file to standard format:

```bash
python3 scripts/archival/normalize_conversation.py "$archived_file" \
  --id "{topic-slug}-{YYYY-MM-DD}" \
  --title "{Conversation Title}" \
  --session-type "{learn|ask|review}" \
  --agent "{analyst|main}" \
  --domain "{domain}" \
  --concepts '["rem-1", "rem-2", ...]' \
  --tags '["tag1", "tag2", ...]' \
  --summary "{2-3 sentence summary}"
```

**Script automatically**:
- Updates all front matter fields
- Adds Metadata section to document
- Replaces summary placeholder with actual summary
- Renames file: `claude-{date}-{time}-{slug}.md` → `{topic}-conversation-{date}.md`

**Output**: Returns new file path for subsequent steps

```bash
archived_file=$(python3 scripts/archival/normalize_conversation.py ...)
```

### Step 15: Update Existing Rems (Review Sessions with Type A Clarifications)

**If session_type == "review" AND user approved Rem updates**, update existing Rem files:

**For each Rem update** in `rems_to_update`:

1. **Read existing Rem file**:
```bash
Read knowledge-base/{domain}/concepts/{rem-id}.md
```

2. **Locate target section** (from `target_section` field):
   - `## Core Memory Points` - For definition clarifications
   - `## Usage Scenario` - For usage/example clarifications
   - `## My Mistakes` - For correction clarifications

3. **Append clarification** to target section:

Use existing script:

```bash
source venv/bin/activate && python scripts/archival/update_rem_clarification.py \
  "$rem_id" \
  "$clarification_text" \
  --section "$target_section"
```

4. **Update frontmatter** (optional - add modification timestamp):
```yaml
---
modified: {YYYY-MM-DD}
clarifications_added: [{date}, ...]
---
```

**Update Process**:
- Read existing Rem
- Locate target section (## Core Memory Points / ## Usage Scenario / ## My Mistakes)
- Append clarification with blank line separator
- Use Edit tool (preserves existing content)

**Important notes**:
- ✅ Use **Edit tool**, not Write (preserves existing content)
- ✅ Append to section, don't replace
- ✅ Add blank line before new content for readability
- ✅ Preserve all existing Rem structure (frontmatter, other sections)
- ✅ Update backlinks remain intact (no link rewriting needed)

**Handle user options**:
- "Approve All" → Update all Rems
- "Create Only" → Skip this step (no updates)
- "Update Only" → Skip Step 13, only execute Step 15

**Validation**: Find file (glob), read content, check section exists, avoid duplicates, append with Edit tool. Report: Updated/Skipped/Errors. Sections: Core Memory Points, Usage Scenario, My Mistakes.

### Step 16: Update Knowledge Graph

**Run three graph maintenance operations sequentially**:

```bash
# 1. Update backlinks (incremental, fallback to full rebuild)
source venv/bin/activate && python scripts/knowledge-graph/update-backlinks-incremental.py rem-id-1 rem-id-2 ...

# 2. Update conversation index
source venv/bin/activate && python scripts/archival/update-conversation-index.py \
  --id "{conversation-id}" --title "{Conversation Title}" --date "{YYYY-MM-DD}" \
  --file "{relative/path/to/conversation.md}" --agent "{agent}" --domain "{domain}" \
  --session-type "{session_type}" --turns {turn_count} --rems {rems_extracted_count}

# 3. Normalize wikilinks to markdown links
source venv/bin/activate && python scripts/knowledge-graph/normalize-links.py --mode replace --verbose
```

**Backlinks**: Incremental (70% token savings), fallback to full rebuild, file locking, cycle detection.

**Wikilinks**: `[[id]]` → `[Title](path.md)`, preserves typed relations, idempotent.

**Output**: ✅ Backlinks updated, ✅ Index updated, 🔗 Links normalized

### Step 17: Materialize Inferred Links (Optional)

**Preview two-hop inferences** (dry-run first):

```bash
source venv/bin/activate && python scripts/knowledge-graph/materialize-inferred-links.py --dry-run --verbose
```

**If inferences found**, present preview to user:

```
🧠 Found {N} potential inferred links:

📝 rem-1.md
  + [[related-rem]] {rel: inferred, via: intermediate-rem}

📝 rem-2.md
  + [[another-rem]] {rel: inferred, via: bridge-rem}

⚠️  WARNING: This will modify {M} Rem files

Materialize these inferred links?
```

**Options**:
```xml
<options>
    <option>Materialize</option>
    <option>Skip</option>
</options>
```

**If user approves**, run actual materialization:
```bash
source venv/bin/activate && python scripts/knowledge-graph/materialize-inferred-links.py --verbose
```

**If user skips or no inferences found**, continue to Step 18.

### Step 18: Sync Rems to Review Schedule (Auto)

Automatically add newly created Rems to the review schedule using FSRS.

```bash
source venv/bin/activate && python scripts/utilities/scan-and-populate-rems.py --verbose --yes
```

**This ensures**:
- New Rems are immediately available for review
- FSRS initial state created (difficulty, stability, retrievability)
- First review scheduled (typically tomorrow)
- No manual `/sync-rems` required

**Script Output**: Lists new Rems found, total count, first review date

**Note**: This step is automatic and does not require user approval (idempotent operation).

**🔒 SAFETY MECHANISM (Automatic)**:

- **File Locking** (`utils/file_lock.py`):
  - Prevents concurrent write conflicts to `schedule.json`
  - Uses atomic write (temp file → rename)
  - 30-second timeout with retry logic
  - Protects FSRS data from corruption during parallel sync operations

### Step 19: Record to Memory MCP (Auto)

**⚠️ MANDATORY - DO NOT SKIP**: This step builds persistent memory for future context-aware interactions.

Automatically record conversation summary and extracted Rems to Memory MCP (knowledge graph).

**Purpose**: Build persistent memory across all conversations for context-aware future interactions.

**Process**: Create conversation entity + concept entities + relations using MCP tools (`mcp__memory-server__create_entities`, `mcp__memory-server__create_relations`)

**Fallback behavior**:
- If external memory MCP unavailable: Use internal memory only (graceful degradation)
- If both MCPs fail: Log error but continue (don't block archival process)
- Error handling: Try-catch around MCP operations, report status in completion

**Output**:
```
🧠 Memory MCP Update:
   ✅ Conversation entity created
   ✅ {N} concept entities created
   ✅ {N} relations established
   📊 Total memory entities: {count}
```

**Error output** (if MCP fails):
```
⚠️  Memory MCP Update:
   ❌ External MCP unavailable (connection refused)
   ✅ Internal MCP updated successfully
   OR
   ❌ Both MCPs failed - memory not persisted (check MCP server status)
```

**Note**: This step is automatic and does not require user approval. Memory recording happens in background.

---

### Step 20: Update Conversation Rem Links

**⚠️ CRITICAL**: This step completes bidirectional links between conversations and Rems. Skipping breaks navigation.

**Run update script** to add Rem links to conversation file:

```bash
source venv/bin/activate && python scripts/archival/update-conversation-rems.py \
  "$archived_file" \
  "${created_rem_paths[@]}"
```

**What this does**:
- Updates conversation's `rems_extracted` frontmatter field with relative paths to all created Rems
- Enables bidirectional navigation (Rem → Conversation, Conversation → Rems)
- Required for complete knowledge graph integrity

---

### Step 21: Generate Analytics & Visualizations

**⚠️ MANDATORY - DO NOT SKIP**: This step provides immediate feedback on learning progress and knowledge graph state.

Provide immediate feedback on learning progress without requiring user to manually run `/stats` or `/visualize`.

This step is automatic and executes after all Rems are created and synced to FSRS.

**Run analytics and visualization generation in sequence**:

```bash
# 1. Generate learning analytics
source venv/bin/activate && python scripts/analytics/generate-analytics.py --period 30

# 2. Generate knowledge graph data
source venv/bin/activate && python scripts/knowledge-graph/generate-graph-data.py --force

# 3. Create interactive visualization HTML
source venv/bin/activate && python scripts/knowledge-graph/generate-visualization-html.py
```

**Output**: Analytics (FSRS metrics → `.review/analytics-cache.json`), graph data (nodes/edges), visualization (D3.js → `knowledge-graph.html`).

**Expected output**:
```
📊 Analytics generated (Period: Last 30 days, Concepts: {N})
📈 Knowledge graph created (Nodes: {N}, Edges: {M})
   File: knowledge-graph.html
```

**Handle edge cases**:
1. **If analytics generation fails**: `⚠️ Analytics generation failed. Run /stats manually when ready.`
2. **If visualization generation fails**: `⚠️ Visualization generation failed. Run /visualize manually when ready.`
3. **If no new Rems extracted**: `ℹ️ No new Rems extracted. Stats and visualizations unchanged.`

**Performance consideration**: Total ~5-7 seconds (acceptable for post-session automation)

**Note**: This step is automatic, non-blocking, and does not require user approval. Failures are logged but do not stop the archival process.

---

### Step 22: Display Completion Report

**Completion report** (Phase 5 metrics via `workflow_orchestrator.py`):

```
✅ Conversation Archived & Graph Updated

📝 Created Rems ({N}): [paths]
{✏️  Updated Rems ({M}): [IDs] | ✅ {success} ⏭️ {skipped} ❌ {errors}}
💬 Conversation: {path} | {session_type}
🔗 Graph: Links normalized ({M} files), Backlinks rebuilt ({total}){, Inferred ({K} links, {L} files) | ⏭️}
📅 FSRS: {N} synced (total: {total}), First review: {date}
🧠 Memory MCP: {✅ {N} concepts | ⚠️ Unavailable}
📊 Analytics: {✅ analytics-cache.json | ⚠️ Failed}, {✅ knowledge-graph.html | ⚠️ Failed}
📊 Status: {total_rems} Rems, {total_convs} conversations{, {reviewed} reviewed}

⏱️  Performance: {total}s (detection {X}s, FSRS {X}s, extraction {X}s, preview {X}s, creation {X}s, index {X}s, stats {X}s)

Next: /review
```

## Conversation Discovery

**Method 1 (Primary)**: Check current session for substantial multi-turn dialogue (5+ turns, Q-A-follow-up patterns).

**Method 2 (Avoid Duplicates)**: Read `chats/index.json`, filter already archived topics.

**Method 3 (User-Specified)**: Search history for matching keywords, use fuzzy matching, suggest closest matches.

## Important Rules

**DO**: Analyze conversation directly, extract from ACTUAL content, use ultra-minimal template (100-120 tokens/Rem), show previews, wait for approval, run Steps 16-22 post-processing, use kebab-case filenames, respect user instructions.

**DON'T**: Use `python -c`/heredocs (use scripts), invoke conversation-archiver subagent, hallucinate, create without approval, skip previews, extract wrong amounts (3-7 typical), skip Steps 16-22, archive trivial/duplicate conversations.

## Success Criteria

**Core**: Extract from ACTUAL conversation (no hallucinations), user approval before files, ultra-minimal format (100-120 tokens/Rem), correct ISCED paths, wikilinks normalized, backlinks/indexes updated, stats auto-generated, comprehensive completion report.

**Edge cases**: No conversation (help message), already archived (inform), too short (warn+override), user cancels (graceful exit), modifications (iterate), no inferences (skip Step 17), failures (fallback/log/continue).
