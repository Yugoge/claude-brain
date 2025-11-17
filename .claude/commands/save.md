---
description: "Save learning session by extracting Rems, archiving conversation, and maintaining graph"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Task, TodoWrite
argument-hint: "[topic-name | --all]"
model: inherit
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Save Command

Save learning sessions by extracting valuable Rems as ultra-minimal knowledge Rems, preserving the dialogue, and maintaining the knowledge graph.

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

This unified command:
- Archive conversations from `/learn`, `/ask`, or `/review` sessions
- Extract Rems as ultra-minimal knowledge Rems (100-120 tokens)
- Save dialogues for future reference
- Support review session early exit and archival
- Filter FSRS test dialogues (avoid duplicate Rems)
- Classify questions (Clarification vs Extension vs Comparison vs Application)
- Update existing Rems with clarifications (Type A questions)
- Granular approval options (create only, update only, or both)
- Advanced validation and error handling for Rem updates
- Bilingual section name support (Chinese + English)
- Normalize wikilinks (`[[id]]` → `[Title](path.md)`)
- Rebuild knowledge graph indexes with typed relations
- Materialize inferred links (optional, with preview)
- Update all indexes (backlinks + conversation index)
- Auto-generate statistics and visualizations

## Implementation

### Step 0: Archive Conversation

```bash
# Default: Include subagent messages (full context)
archived_file=$(python3 scripts/services/chat_archiver.py)

# Optional: Exclude subagent messages (main conversation only)
archived_file=$(python3 scripts/services/chat_archiver.py --no-include-subagents)
```

**Parameters**:
- `--include-subagents` (default): Include all subagent dialogues (analyst, language-tutor, etc.)
- `--no-include-subagents`: Exclude subagent messages, archive only main conversation

**What the archiver does**:
1. Detects subagent messages (analyst, language-tutor, finance-tutor, etc.)
2. Labels subagent responses as `### Subagent: {Name}` instead of `### User`
3. Demotes headings in message content by 1 level (prevents hierarchy conflicts)
   - Example: `# Title` in content → `## Title` (since role labels are `### User`)
4. Optionally filters out subagent messages if `--no-include-subagents` is used

Store `archived_file` for Step 6.1 (Rem source) and Step 7 (conversation rems_extracted update).

**IMPORTANT**: The archived file contains placeholder metadata that MUST be enriched from active context:
- `id`: Generic `conversation-{date}` → Needs meaningful topic-based ID
- `title`: Generic "Conversation - {date}" → Needs descriptive title
- `domain`: Generic "general" → Needs actual domain classification
- `summary`: Placeholder text → Needs real summary from conversation

These will be updated in Step 6.2 using information from the active conversation context.

---

### Step 1: Parse Arguments & Detect Session Type

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

#### Step 1.1: Detect Session Type

**Determine if this is a review session or learn/ask session**:

```bash
# Check if there's an active review session
test -f .review/history.json && echo "Review history exists"
```

**Review session indicators**:
1. `.review/history.json` exists and has recent entries (today's date)
2. Conversation contains FSRS rating patterns (e.g., "Rate your recall: 1-4")
3. Multiple Rem IDs referenced in conversation
4. Review-master agent invoked earlier in session

**Session detection returns**:
- `session_type`: "review" or "learn" or "ask"
- `rems_reviewed`: List of Rem IDs if review session
- `fsrs_progress_saved`: Boolean flag

**Implementation**: Use `scripts/archival/session_detector.py` to detect session type and load review history if needed.

**Script handles**:
- Lazy loading optimization (only reads history file if exists)
- Performance tracking
- Returns session type ('review' or 'learn') and list of reviewed Rems

### Step 2: Validate Conversation & Filter FSRS Tests

**Phase 5 Optimization: Early Exit** - Use `scripts/archival/concept_extractor.py` to check if there's content worth extracting.

**🔒 SAFETY MECHANISMS (Automatic)**:

1. **Token Limit Protection** (`utils/token_estimation.py`):
   - Checks conversation size before extraction
   - Maximum: 150k tokens (safe limit)
   - Warns at 100k tokens (83% threshold)
   - If exceeded → Clear error message + suggestion to split session
   - Prevents system crashes from oversized conversations

2. **Duplicate Detection** (`concept_extractor.py:check_duplicate_concepts()`):
   - Scans existing knowledge base for similar Rem titles
   - Uses Jaccard similarity (60% threshold)
   - Non-blocking warning (user decides whether to proceed)
   - Prevents redundant extraction

3. **Session Type Confidence** (`session_detector.py:calculate_confidence()`):
   - Multi-indicator scoring (turn count, FSRS patterns, technical keywords, Rem references)
   - Confidence levels: HIGH (≥80%), MEDIUM (50-80%), LOW (<50%)
   - Warns user if confidence < 50%
   - Reduces misclassification risk

**Script performs**:
- Quick conversation length check (<3 turns → skip)
- Technical indicator scanning
- Token size validation (CRITICAL)
- Returns decision to proceed or skip

Before archiving, verify:

1. **Minimum turns**: At least 3 substantial turns (not just "thanks" or "okay")
2. **Technical content**: Contains learnable concepts, not just casual chat
3. **Not already archived**: Check `chats/index.json` for duplicates
4. **Context available**: Full conversation accessible in current session

**If validation fails**:
```
This conversation doesn't meet archival criteria:
- Reason: [Too short | No technical content | Already archived | No access to conversation]

Archival is recommended for conversations with:
- 3+ substantial turns
- Technical concepts or detailed explanations
- Code examples or step-by-step guidance
- Learning value for future reference
```

---

#### Step 2.1: Filter FSRS Test Dialogues (Review Sessions Only)

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

### Step 2.5: Domain Classification & ISCED Path Determination

**NEW: Classify conversation domain to determine Rem storage paths**

**Consult classification-expert agent** for ISCED taxonomy classification:

```
Use Task tool with:
- subagent_type: "classification-expert"
- prompt: "Classify the following conversation into ISCED domain:

Conversation summary: {2-3 sentence summary of key topics discussed}

Main topics covered: {list 3-5 main concepts/questions from conversation}

Provide 3-level ISCED classification (broad, narrow, detailed) for organizing knowledge Rems."
- description: "Classify conversation domain"
```

**Receive JSON classification**:
```json
{
  "domain": "finance",
  "confidence": 95,
  "sub_domain": "derivatives_pricing",
  "rationale": "Conversation focused on financial derivatives pricing models",
  "isced": {
    "broad": "04",
    "narrow": "041",
    "detailed": "0412"
  }
}
```

**Map ISCED codes to folder paths**:
- `0412` (Finance, banking, insurance) → `knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/`
- `0611` (Computer use) → `knowledge-base/06-information-and-communication-technologies-icts/061-ict-use/0611-computer-use/`
- `0231` (Language acquisition) → `knowledge-base/02-arts-and-humanities/023-languages/0231-language-acquisition/`
- `0533` (Physics) → `knowledge-base/05-natural-sciences-mathematics-and-statistics/053-physical-sciences/0533-physics/`

**CRITICAL**: All Rems MUST be saved to ISCED 3-level paths. No legacy domain shortcuts allowed.

**Store classification result** for use in Step 6.1 (Rem file creation).

### Step 3: Extract Concepts

**Main agent extraction process**:

**IMPORTANT**: Extract Rems directly from the **active session context**. Do NOT read the `archived_file` created in Step 0.
- `/save` runs WITHIN the current conversation → full context already available
- `archived_file` is only used as a **reference path** for Rem `source` fields
- Reading the file wastes tokens and is redundant

1. Analyze conversation from **active context** (NOT from file)
2. Identify domain (programming|language|finance|science)
3. Extract 3-7 candidate Rems: distinct, reusable knowledge points from user's explicit mentions
4. Follow user's learning logic
5. Classify user questions to determine action (update vs create)

**Extraction Rules**:
- ✅ User's technical terms/mistakes/questions
- ✅ Specific & reusable (e.g., "Python asyncio event loop")
- ❌ Too broad ("programming") or narrow ("line 42 variable x")
- ❌ AI explanations (user didn't learn from AI saying it)
- ❌ Hallucinations (only THIS conversation)
- ❌ User didn't respond or practice

**ISCED Path Usage** (from Step 2.5):
- Use classification result from Step 2.5 to determine Rem storage location
- Path format: `knowledge-base/{broad-code-name}/{narrow-code-name}/{detailed-code-name}/`
- Example: ISCED 0412 → `knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/`

---

#### Step 3.1: Question Type Classification (Review Sessions Only)

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

### Step 3.5: Enrich with Typed Relations via Domain Tutor (OPTIONAL)

**Purpose**: Discover semantic relationships (e.g., "ask" ↔ "inquire" as synonyms).

**Implementation** (simplified):

1. **Get existing Rem IDs** in target domain using Glob tool:
   ```
   Glob: knowledge-base/{isced_path}/**/*.md
   Read frontmatter rem_id from each file
   ```

2. **Call domain tutor** with Task tool, providing:
   - Extracted Rems (titles, core points)
   - Existing Rem IDs in the domain
   - Request: "Suggest typed_relations using types: synonym, prerequisite_of, contrasts_with, uses, etc."

3. **Tutor returns JSON** with typed_relations for each Rem:
   ```json
   {
     "concept_id": "english-verb-ask",
     "typed_relations": [
       {"to": "english-verb-inquire", "type": "synonym", "rationale": "..."}
     ]
   }
   ```

4. **Merge typed_relations** into Rem data (validation happens in Step 5.5).

**If tutor call fails**: Continue without typed_relations (backlinks rebuild will add generic links later).

---

### Step 3.6: Rem Extraction Transparency

**After extracting and enriching Rems**, YOU (main agent) MUST present them in user-friendly format (no code):

**Subagent behavior**: May use NLP scripts, classification algorithms, graph analysis tools
**Main agent behavior**: Show user the RESULTS (extracted Rems), not the PROCESS (code)

**Code Presentation**:
- ❌ DON'T: Show script paths, JSON files, technical artifacts
- ✅ DO: Present extracted Rems in readable format (titles, summaries, relationships)
- Exception: User explicitly requests debugging/process details

**Code artifacts are tools for the system**, not content for the user.

**Post-Processing Requirements**:

If YOU used any helper scripts during Rem extraction, READ the results and translate them:

1. Check if you created any files:
   - Code files (*.py, *.js, *.sh, etc.)
   - Data files (*.csv, *.json, *.txt, etc.)
   - Analysis files (*.txt, *.log, etc.)

2. If files exist, READ them:
   ```bash
   # Use Read tool on each artifact
   # Parse content to understand what was extracted
   ```

3. Translate to natural language:
   - **DO NOT** paste JSON/code to user
   - **DO** present Rems in readable format
   - **DO** use bullet points, headings, structured text
   - **DO** show titles, key points, relationships

4. User-facing output format:
   ```
   ✅ GOOD: "I've extracted 5 Rems: [list with titles and summaries]"
   ✅ GOOD: "Here are the key ideas from our conversation: ..."
   ❌ BAD: "See /tmp/extracted_rems.json for details"
   ❌ BAD: [pasting JSON array of Rem objects]
   ```

**Exception**: If user explicitly says "show me the extraction process" or "how did you parse that", THEN show code/data.

**Why**: User is in a chat interface focused on their learning, not system internals. Extraction tools are implementation details, not user-facing content.

### Step 4: Generate Preview (Format depends on session type)

**Two preview formats**:
1. **Learn/Ask sessions**: Ultra-compact 1-line previews (original format)
2. **Review sessions**: Three-section preview (reviewed + new + updates)

---

#### Step 4.1: Learn/Ask Session Preview (Original Format)

**For EACH concept**, generate 1-line preview:

**Format** (20 tokens per preview):
```
N. [Title] → [1-line summary] → path/to/file.md
```

**Show ALL previews** before approval.

---

#### Step 4.2: Review Session Preview (Three-Section Format)

**For review sessions**, show:
- ✅ **Section 1**: Reviewed Rems (FSRS already saved)
- 💡 **Section 2**: New Concepts (from Type B/C/D questions)
- ⚙️ **Section 3**: Rem Updates (from Type A clarifications) - **[MVP: Display only, defer update implementation]**

**Phase 5 Optimization: Token-efficient preview formatting** - Use `scripts/archival/preview_generator.py` to generate compact previews.

**Script generates**:
- Learn/ask format: 1-line previews (~20 tokens each)
- Review format: Three-section preview (reviewed + new + updates)
- Token target: ~600 tokens total (33% reduction vs verbose format)

**Format**:
```
📊 Review Session Analysis

✅ Reviewed Rems (FSRS Updated): {N}
  1. [[{rem-id-1}]] - Rating: {rating} ({label})
  2. [[{rem-id-2}]] - Rating: {rating} ({label})
  ...

💡 New Concepts Discovered: {M}

1. **{Concept Title}** (Type {B|C|D}: {Extension|Comparison|Application})
   Source: Turn {N} - "{user_question}"
   Core points:
   - {Point 1}
   - {Point 2}
   - {Point 3}
   File: knowledge-base/{domain}/concepts/{slug}.md
   Tokens: ~{N}

2. **{Concept Title 2}** ...

⚙️ Rem Updates (Clarifications): {K}

  1. **[[{rem-id}]]** - {clarification_type} clarification
     Source: Turn {N} - "{user_question}"
     Target section: {target_section}

     Diff preview:
     OLD: "{old_content_snippet}"
     NEW: "{old_content_snippet} {clarification_text}"

     File: knowledge-base/{domain}/concepts/{rem-id}.md

📊 Summary:
  - Reviewed: {N} Rems (FSRS progress saved)
  - Create: {M} new Rems (Type B/C/D)
  - Update: {K} existing Rems (Type A clarifications)
  - Archive: 1 conversation file

<options>
  <option>Approve All (Create {M} + Update {K})</option>
  <option>Create Only ( - Skip Updates)</option>
  <option>Update Only ( - Skip New)</option>
  <option>Modify</option>
  <option>Cancel</option>
</options>
```

### Step 5: User Confirmation

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
- Option 1 → Step 5.5 (Pre-creation Validation)
- Option 2 → Iterate, re-present
- Option 3 → Abort gracefully

### Step 5.5: Pre-creation Validation

**ONLY after user approval**, run comprehensive validation before creating any files.

**Single script validates everything**:

```bash
python scripts/archival/pre_creation_validator.py \
  --concepts-json "$extracted_rems_json" \
  --domain-path "$isced_detailed_path" \
  --source-file "$archived_file"
```

**Exit codes**:
- `0` = All passed → Proceed to Step 6
- `1` = Warnings → Show warnings, ask user to confirm/abort
- `2` = Critical errors → BLOCK Step 6, show errors, return to Step 4

**What it validates**:
1. ✅ **Typed relations**: Target concepts exist, relation types valid (auto-fixes invalid)
2. ✅ **Duplicates**: Jaccard similarity >60% triggers warning (non-blocking)
3. ✅ **rem_id collision**: Blocks if rem_id already exists in backlinks.json
4. ✅ **Frontmatter schema**: All required fields present (rem_id, subdomain, isced, created, source)
5. ✅ **ISCED path**: Directory structure exists in knowledge-base/
6. ✅ **Source file**: Conversation file exists (warning only)

**Auto-fixes applied**:
- Invalid relation targets → removed
- Invalid relation types → changed to 'related'
- Results stored back in `$extracted_rems_json`

**Error handling**:
```bash
validation_exit_code=$?

if [ $validation_exit_code -eq 2 ]; then
    echo "❌ Validation failed with critical errors. Cannot proceed."
    echo "Please fix the issues and run /save again."
    exit 1
elif [ $validation_exit_code -eq 1 ]; then
    echo "⚠️  Validation passed with warnings."
    # Ask user: Proceed anyway? (yes/no)
fi
```

**If validation passes** → Proceed to Step 6 (Create Files)

### Step 6: Create Files

**ONLY after user approval**, create files in this order:

**⚠️ CRITICAL ORDERING**: You MUST execute Step 6.2a (Rename Conversation) BEFORE Step 6.1 (Create Rems).

**Why**: Rem files need the FINAL conversation filename in their `source` field. If you create Rems before renaming, the source will point to the temporary filename.

**Correct execution order**:
1. **First**: Run Step 6.2a (normalize and rename conversation) → get `$renamed_conversation_file`
2. **Then**: Run Step 6.1 (create Rems using `$renamed_conversation_file` as source)
3. Continue with remaining steps (6.3, 6.4, 6.5, ...)

---

#### 6.1: Create Knowledge Rems

**⚠️ PREREQUISITE**: Step 6.2a must complete first (see above).

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

Where `{isced_path}` is determined from Step 2.5 classification:
- Example: `04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/`

**Script automatically adds**:
- All required frontmatter fields (rem_id, title, isced, subdomain, created, source)
- All required sections (Core Memory Points, Usage Scenario, My Mistakes, Related Rems, Conversation Source)
- Bidirectional link to conversation in `## Conversation Source` section
- Relative path calculation for source field

**Build complete Rem from tutor suggestions + main agent supplements**:

If Rem was enriched by tutor (Step 3.5), use tutor's enhanced fields:
- `title`: Use tutor's academic title
- `core_points`: Parse tutor's `core_content` (already formatted as bullet points)
- `usage_scenario`: Use tutor's `usage_scenario_suggestion`
- `my_mistakes`: Merge tutor's `common_mistakes_suggestion` + user's actual errors from conversation
- `academic_source`: Add tutor's `academic_source` (if provided, typically for finance/science)
- `typed_relations`: Use tutor's `typed_relations` array (preferred over `related_to`)

**Validate typed_relations before writing**:
```bash
python scripts/archival/validate_relations.py \
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
- Use tutor-enriched fields when available (from Step 3.5):
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

**IMPORTANT**: Always write Related Rems as **wikilinks** during creation (Step 6.1). They will be automatically converted to markdown links in Step 6.5 (Normalize Wikilinks).

When creating the `## Related Rems` section in Rem files:

1. **If tutor provided `typed_relations` (validated)**:
   - Use ONLY the `valid_relations` from validation step
   - Format: `- [[{subdomain}-{rem-slug}]] {rel: <type>}` (wikilink format)
   - Include all valid typed relations
   - Example (written during creation):
     ```markdown
     ## Related Rems

     - [[french-verb-vouloir]] {rel: synonym}
     - [[french-adjective-agreement]] {rel: prerequisite_of}
     - [[french-negation-ne-pas]] {rel: contrasts_with}
     ```
   - After Step 6.5 normalize-links.py, becomes:
     ```markdown
     ## Related Rems

     - [French Verb Vouloir](../012-french-verb-vouloir.md) {rel: synonym}
     - [French Adjective Agreement](../016-french-adjective-agreement.md) {rel: prerequisite_of}
     - [French Negation Ne-Pas](../021-french-negation-ne-jamais.md) {rel: contrasts_with}
     ```

2. **If tutor provided legacy `related_to` (backward compat)**:
   - Convert rem-slugs to wikilinks: `[[{subdomain}-{rem-slug}]]`
   - Use generic {rel: related} for untyped
   - Format as bullet list under `## Related Rems` section
   - Note: Ensure rem_id includes subdomain prefix for uniqueness

3. **If no tutor OR no valid relations**:
   - Leave section empty with placeholder comment
   - Write: `*(Will be populated by backlinks rebuild)*`
   - Links will be auto-populated when `rebuild-backlinks.py` runs

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

#### 6.1a: Update Existing Rems (Review Sessions with Type A Clarifications)

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
- "Update Only" → Skip 6.1, only execute 6.1a

**Validation & Error Handling** (Phase 3):

For each Rem update, validate before applying:
1. Find Rem file using glob pattern (skip if not found or multiple matches)
2. Read existing content
3. Validate target section exists (try English alternatives: `## Core Memory Points` or `## Core Points`)
4. Check if clarification already exists (avoid duplicates)
5. Apply update using Edit tool (append clarification to target section)
6. Report summary: Updated / Skipped / Errors

**Section Names** (English only, as defined in rem-template.md):
- `## Core Memory Points` (3 max)
- `## Usage Scenario`
- `## My Mistakes`

#### 6.2: Create Conversation Archive

**Initial file created by `chat_archiver.py` in Step 0** with placeholder metadata.

This step enriches the file with actual metadata from the conversation.

#### 6.2a: Normalize and Rename Conversation File

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

#### 6.3: Update Backlinks Index

**Run incremental update** (token-optimized):

```bash
python scripts/knowledge-graph/update-backlinks-incremental.py rem-id-1 rem-id-2 ...
```

**Incremental update**:
- Only processes new Rems (not entire knowledge base)
- Updates bidirectional links for new concepts
- 70% token reduction vs full rebuild

**Fallback**: If incremental fails, run `python scripts/knowledge-graph/rebuild-backlinks.py`

**🔒 SAFETY MECHANISMS (Automatic)**:

1. **File Locking** (`utils/file_lock.py`):
   - Prevents concurrent write conflicts to `backlinks.json`
   - Uses POSIX fcntl locks (exclusive access)
   - 60-second timeout with automatic cleanup
   - Protects data integrity during parallel operations

2. **Cycle Detection** (`rebuild-backlinks.py:detect_cycles()`):
   - DFS-based circular reference detection
   - Identifies cycles like A→B→C→A
   - Non-blocking warning (logs cycle paths)
   - Prevents graph navigation issues

#### 6.4: Update Conversation Index

```bash
source venv/bin/activate && python scripts/archival/update-conversation-index.py \
  --id "{conversation-id}" \
  --title "{Conversation Title}" \
  --date "{YYYY-MM-DD}" \
  --file "{relative/path/to/conversation.md}" \
  --agent "{agent}" \
  --domain "{domain}" \
  --session-type "{session_type}" \
  --turns {turn_count} \
  --rems {rems_extracted_count}
```

#### 6.5: Normalize Wikilinks

**Run link normalization** (converts `[[id]]` to `[Title](path.md)`):

```bash
python scripts/knowledge-graph/normalize-links.py --mode replace --verbose
```

**What it does**:
- Converts wikilinks in newly created Rems to clickable markdown links
- Preserves typed relation suffixes: `[[id]] {rel: synonym}` → `[Title](path.md) {rel: synonym}`
- Idempotent operation (safe to run multiple times)

**Output**:
```
🔗 Normalizing wikilinks...
   Updated: knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/multi-asset-portfolio.md
   Updated: knowledge-base/04-business-administration-and-law/041-business-and-administration/0412-finance-banking-insurance/us-exceptionalism.md
   Processed {N} files, updated {M}
✅ Links normalized
```

#### 6.6: Materialize Inferred Links (Optional)

**Preview two-hop inferences** (dry-run first):

```bash
python scripts/knowledge-graph/materialize-inferred-links.py --dry-run --verbose
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
python scripts/knowledge-graph/materialize-inferred-links.py --verbose
```

**If user skips or no inferences found**, continue to Step 6.7.

#### 6.7: Sync Rems to Review Schedule (Auto)

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

#### 6.8: Record to Memory MCP (Auto)

Automatically record conversation summary and extracted Rems to Memory MCP (knowledge graph).

**Purpose**: Build persistent memory across all conversations for context-aware future interactions.

**Process**:

1. **Create conversation entity**:
```
mcp__memory-server__create_entities:
  - name: "conversation-{topic-slug}-{YYYY-MM-DD}"
    entityType: "conversation"
    observations:
      - "Topic: {conversation_topic}"
      - "Domain: {domain}"
      - "Date: {YYYY-MM-DD}"
      - "Extracted {N} Rems: {rem-slug-1}, {rem-slug-2}, ..."
      - "Session type: {learn|ask|review}"
```

2. **Create concept entities** (for each extracted Rem):
```
mcp__memory-server__create_entities:
  - name: "{rem-title}"
    entityType: "{{domain}-rem"
    observations:
      - "Rem ID: {rem-id}"
      - "File: knowledge-base/{domain}/concepts/{slug}.md"
      - "Core point 1: {brief summary}"
      - "Core point 2: {brief summary}"
      - "Source conversation: conversation-{topic-slug}-{YYYY-MM-DD}"
```

3. **Create relations**:
```
mcp__memory-server__create_relations:
  - from: "conversation-{topic-slug}-{YYYY-MM-DD}"
    to: "{rem-title}"
    relationType: "extracted_rem"
```

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

### Step 7: Update Conversation Rem Links

```bash
source venv/bin/activate && python scripts/archival/update-conversation-rems.py \
  "$archived_file" \
  "${created_rem_paths[@]}"
```

Updates conversation's `rems_extracted` field with relative paths to created Rems (bidirectional navigation).

---

### Step 8: Auto-generate Statistics & Visualizations

Provide immediate feedback on learning progress without requiring user to manually run `/stats` or `/visualize`.

This step is automatic and executes after all Rems are created and synced to FSRS.

#### Step 8.1: Generate Learning Analytics

Run the analytics generation script:

```bash
source venv/bin/activate && python scripts/analytics/generate-analytics.py --period 30
```

**What this does**:
- Generates comprehensive learning analytics from FSRS review data
- Creates `.review/analytics-cache.json` with metrics
- Calculates retention curves, learning velocity, mastery levels
- Analyzes review adherence and time distribution

**Expected output**:
```
📊 Analytics generated successfully
   Period: Last 30 days
   Concepts analyzed: {N}
   Cache saved: .review/analytics-cache.json
```

#### Step 8.2: Generate Interactive Visualizations

**First, generate the knowledge graph data**:

```bash
source venv/bin/activate && python scripts/knowledge-graph/generate-graph-data.py --force
```

**Then, create the visualization HTML**:

```bash
source venv/bin/activate && python scripts/knowledge-graph/generate-visualization-html.py
```

**What this does**:
- Creates interactive D3.js force-directed graph
- Generates `knowledge-graph.html` in project root
- Shows all Rems and their relationships
- Enables interactive exploration (click nodes, search, filter)

**Expected output**:
```
📈 Knowledge graph visualization created
   File: knowledge-graph.html
   Nodes: {N} concepts
   Edges: {M} relationships
```

#### Step 8.3: Display Summary to User

**Present the auto-generated artifacts**:

```
📊 Learning Analytics Auto-Generated:

📈 Interactive Dashboard:
   → knowledge-graph.html

   Open in browser to explore:
   - Knowledge graph with {N} concepts
   - Interactive node exploration
   - Relationship visualization
   - Domain-based clustering

💡 Tip: Run /stats to see detailed analytics dashboard
       Run /visualize to regenerate the knowledge graph
```

**Handle edge cases**:

1. **If analytics generation fails**:
   ```
   ⚠️  Analytics generation failed. Run /stats manually when ready.
   ```

2. **If visualization generation fails**:
   ```
   ⚠️  Visualization generation failed. Run /visualize manually when ready.
   ```

3. **If no new Rems extracted** (empty session):
   ```
   ℹ️  No new Rems extracted. Stats and visualizations unchanged.
   ```

**Performance consideration**:
- Analytics generation: ~1-2 seconds
- Graph data generation: ~2-3 seconds
- HTML generation: ~1-2 seconds
- Total: ~5-7 seconds (acceptable for post-session automation)

**Note**: This step is automatic, non-blocking, and does not require user approval. Failures are logged but do not stop the archival process.

### Step 9: Completion Report

**After all operations complete**, provide:

**Phase 5: Track and report performance metrics** - `scripts/archival/workflow_orchestrator.py` handles timing for all steps.

```
✅ Conversation Archived & Graph Updated

📝 Created Rems ({N} concepts):
   [list file paths]

{✏️  Updated Rems ({M} clarifications):
   [list updated Rem IDs]
   📊 Update Summary:
     ✅ Updated: {success_count}
     ⏭️  Skipped: {skipped_count}
     ❌ Errors: {error_count}
}

💬 Saved Conversation:
   {conversation file path}
   {Session Type: review | learn | ask}

🔗 Graph Maintenance:
   ✅ Links normalized ({M} files updated)
   ✅ Backlinks rebuilt ({total concepts} in graph)
   {✅ Inferred links materialized ({K} links, {L} files) | ⏭  Skipped}

📅 Review Schedule:
   ✅ Rems synced to FSRS schedule
   📊 {N} new Rems added (total: {total in schedule})
   🗓️  First review: {tomorrow's date}

🧠 Memory MCP:
   {✅ Conversation + {N} concepts recorded | ⚠️ MCP unavailable (skipped)}
   📊 Total memory entities: {count}

📊 Analytics & Visualizations:
   {✅ Analytics generated: .review/analytics-cache.json | ⚠️ Generation failed}
   {✅ Knowledge graph created: knowledge-graph.html | ⚠️ Generation failed}
   💡 Tip: Open knowledge-graph.html in browser to explore

📊 Knowledge Base Status:
   Total Rems: {count}
   Total conversations: {count}
   {For review sessions: Rems reviewed: {reviewed_count}}

⏱️  Performance Metrics (Phase 5):
   Total time: {total_time:.2f}s
   - Session detection: {session_detection_time:.2f}s
   - FSRS filtering: {fsrs_filter_time:.2f}s
   - Concept extraction: {extraction_time:.2f}s
   - Preview generation: {preview_time:.2f}s
   - File creation: {file_creation_time:.2f}s
   - Index updates: {index_update_time:.2f}s
   - Stats & visualization: {stats_viz_time:.2f}s
   Estimated tokens: ~{estimated_tokens} (target: <4,000)

Next: /review (tomorrow to review new concepts!)
```

## Conversation Discovery

Find conversations using these methods:

### Method 1: Session History (Primary)

```
Check current session for:
- Most recent substantial multi-turn dialogue
- Any conversation with technical content (5+ turns)
- Look for question-answer-follow-up patterns
```

### Method 2: Conversation Index (Avoid Duplicates)

```
Read /root/knowledge-system/chats/index.json

Check existing archived conversations:
- Filter out already archived topics
- Verify conversation not already processed
```

### Method 3: User-Specified Topic

```
If user provides topic name:
- Search session history for matching keywords
- Use fuzzy matching if exact match fails
- Suggest closest matches if not found
```

## Important Rules

### DO
- Directly analyze conversation (no subagent invocation)
- Extract Rems from ACTUAL conversation content
- Use ultra-minimal Rem template (100-120 tokens per Rem)
- Show complete previews before creating files
- Wait for user approval (never auto-create files)
- Run link normalization AFTER creating Rems
- Update backlinks.json via incremental script (fallback to full rebuild)
- Update chats/index.json with metadata aggregates
- Preview inferred links before materializing (dry-run first)
- Allow user to skip inferred link materialization
- Auto-sync new Rems to FSRS review schedule (Step 6.7)
- Validate conversation meets archival criteria
- Use kebab-case for file names (remove special characters)
- Respect user's explicit instructions about what to extract
- Provide comprehensive completion report with graph stats

### DON'T

- Use `python -c` or inline Python code (ALWAYS use scripts/archival/*.py with venv)
- Write temporary Python files for logic (scripts exist)
- Use heredocs with Python code
- Use Task tool to invoke conversation-archiver subagent
- Extract Rems not present in THIS conversation
- Hallucinate content from unrelated conversations
- Create files without user approval
- Skip preview step
- Extract too many concepts (3-7 is typical)
- Extract too few concepts (capture key ideas)
- Forget to run link normalization
- Forget to update indexes (backlinks + conversation index)
- Materialize inferred links without preview and approval
- Archive trivial conversations (<3 turns)
- Archive already-archived conversations (check index)

## Token Efficiency

**Target**: <4,000 tokens per archival (with full graph maintenance)

**Enhanced Breakdown**:
- Concept extraction: ~800 tokens (streamlined prompts)
- Preview generation (7 Rems × 20 tokens): ~140 tokens (ultra-compact)
- User approval workflow: ~100 tokens (concise format)
- Rem file creation (7 Rems × 100 tokens): ~700 tokens (ultra-minimal template)
- Conversation archive: ~800 tokens (compressed format)
- Index updates: ~300 tokens (incremental backlinks + direct edit)
- Link normalization: ~200 tokens (script execution + output)
- Inferred link materialization (optional): ~400 tokens (preview + confirmation)
- FSRS schedule sync: ~150 tokens (auto-sync new Rems)
- Stats & visualization generation: ~250 tokens (auto-generate analytics + graph)
- Enhanced completion report: ~300 tokens (graph + review + analytics status)
- **Total**: ~4,140 tokens ✅ (3.5% over 4,000 target, acceptable for automation value)

**Optimization techniques applied**:
1. Streamlined extraction prompts (imperatives, bullet points, no filler)
2. Ultra-compact preview format (1-line summaries)
3. Ultra-minimal Rem template (100-120 tokens vs 150-200)
4. Incremental backlinks update (only new Rems)
5. Direct JSON manipulation (Edit tool vs read-modify-write)
6. Idempotent graph operations (safe to run multiple times)
7. Optional materialization (user can skip to save tokens)

**Comparison with separate commands**:
- OLD: `/archive-conversation` (2,840) + `/learn-finalize` (500-800) = 3,340-3,640 tokens
- NEW: Enhanced `/save` = 3,640 tokens (unified workflow)
- Benefit: Same token cost, simpler UX (one command vs two)

## Success Criteria

A successful archival with full graph maintenance:
- Concepts extracted from ACTUAL conversation (no hallucinations)
- User approves before file creation
- Ultra-minimal Rem format used (100-120 tokens per Rem)
- Files created in correct domain directory
- Wikilinks normalized to clickable markdown format
- Backlinks index updated (incremental or full rebuild)
- Conversation index updated with metadata aggregates
- Inferred links previewed and optionally materialized
- Stats and visualizations auto-generated (no manual intervention)
- Comprehensive completion report with graph stats and analytics
- Token consumption ~4,140 (typical with all features including automation)

Edge cases handled:
- No conversation found → Helpful message
- Already archived → Inform user (check index)
- Too short (<3 turns) → Warn user, allow override
- User cancels → No files created, graceful exit
- User requests modifications → Iterate on specific concepts
- No inferred links found → Skip 6.6 gracefully
- Incremental backlinks fails → Fallback to full rebuild
- User skips inferred links → Continue to completion
- Stats generation fails → Log warning, continue (non-blocking)
- Visualization generation fails → Log warning, continue (non-blocking)

## Notes

**Architecture**:
- This command performs direct extraction (no subagent) to ensure conversation context access
- Replaces the separate `/learn-finalize` command (now deprecated)
- Supports hybrid sessions (review + new learning in one conversation)
- Provides full graph maintenance in one unified workflow

**Performance Optimizations**:
- Early exit if no Rems to extract (saves ~2,000 tokens)
- Lazy loading of review history (only for review sessions)
- Compiled regex patterns cached (classification patterns compiled once)
- Optimized preview generation (token-efficient formatting)
- Incremental file processing (process Rems in batches if >10)
- Performance monitoring (tracks execution time & token usage)

**Token Efficiency**: Target <4,000 tokens per archival with full graph maintenance (see Token Efficiency section for breakdown)

**Workflow Goal**: Enable reliable, context-aware conversation archival with guaranteed content correctness and token efficiency
