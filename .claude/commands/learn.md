---
description: "Interactive learning with Socratic dialogue"
allowed-tools: Read, Bash, Write, Task, TodoWrite
argument-hint: "[file-path]"
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Learn Command

Start an interactive learning session with a material using Socratic dialogue.





### Step 0: Initialize Workflow Checklist

**Load todos from**: `scripts/todo/learn.py`

Execute via venv:
```bash
source venv/bin/activate && python scripts/todo/learn.py
```

Use output to create TodoWrite with all workflow steps.

**Rules**: Mark `in_progress` before each step, `completed` after. NEVER skip steps.

---


## Usage

```
/learn <file-path>
```

## Examples

```
/learn learning-materials/finance/options-trading.pdf
/learn learning-materials/programming/python-async.md
/learn learning-materials/language/french-grammar.epub
```

## What This Command Does

1. **Detects material type** (PDF/PPT/EPUB/Word/Excel/Markdown)
2. **Loads or creates progress file** (`.progress.md`)
3. **Launches appropriate tutor agent**:
   - Books/PDFs/Reports → `book-tutor`
   - Language materials → `language-tutor`
   - Finance materials → `finance-tutor`
   - Programming materials → `programming-tutor`
   - Medicine materials → `medicine-tutor`
   - Law materials → `law-tutor`
   - Science materials → `science-tutor`
4. **Starts Socratic dialogue** teaching session
5. **Tracks progress** at page/chapter/concept level

## Implementation

You are the **orchestrator** for this command. Your job:

### Step 1: Validate Input & Check File Size + Content Type

**⚠️ CRITICAL**: This step prevents oversized files from causing API errors. Incorrect content type detection = wrong extraction workflow = failed learning session.

**File Validation**:
- Verify file exists and is in `learning-materials/` directory
- Run `scripts/learning-materials/check-file-size.py {file_path} --analyze-content --json` to get size and content type
- Parse JSON result for `safe`, `content_type`, `total_pages`, `recommendation`

**Content Type Detection** (PDF only):
- **image_heavy**: Picture books, visual materials → Text preview + 1 page visual study
- **text_heavy**: Textbooks, articles → 5-10 pages at a time
- **mixed**: Adaptive chunking (3-5 pages)

**Safety Checks**:
- If `safe: false` and `recommendation: must_chunk`:
  - Large files (>10MB): Exit with options (extract TOC, choose pages, or start with first 10%)
  - User selects option and continues with selected extraction strategy
  - Proceed to PDF token estimation (see below)

**PDF Token Estimation** (within Step 1):
- Determine chunk size: image_heavy=1 page, text_heavy=10 pages, mixed=5 pages
- Run `source venv/bin/activate && python scripts/learning-materials/estimate_tokens.py '{file_path}' 0 {chunk_size}`
- If exit code 0: Read `.tokens.json`, check total_tokens < 180000
- If exit code != 0 or tokens >= 180000: Reduce chunk size or exit with compression instructions
- If safe: Continue to Step 2

### Step 2: Detect Material Type & Domain

**Material Type Mapping**:
- `.pdf` → pdf, `.epub` → epub, `.pptx` → ppt, `.docx` → word, `.md` → markdown, `.xlsx` → excel

**Domain Detection**:
- Extract from file path (e.g., `learning-materials/finance/` → "finance")

### Step 3: Load or Create Progress File

**Progress File Location**: `{file_path}.progress.md` (replace extension)

**If exists**:
- Read progress file
- Display: Title, Current Position, Progress Percentage, Last Session Date
- Ask user to continue

**If new**:
- Create progress file from template
- Display: "Starting new material: {title}"

### Step 4: Image-Heavy PDF Workflow (2-Phase Approach)

**Trigger**: If `content_type == 'image_heavy'` and `safe == false`

**Phase 1: Text Preview (Fast)**:
- Run `scripts/learning-materials/extract-pdf-chunk.py {file} --mode pages --pages 1-{total} --text-only --json`
- Parse JSON for `char_count` and `content`
- If `char_count > 100`: Show first 500 chars preview
- If `char_count ≤ 100`: Warn "No extractable text (pure image content)"
- Display page count and prompt user for page selection (e.g., "1-5", "10", "1-3,7-9")

**Phase 2: Visual Study (1 Page at a Time)**:
- Parse user's page range selection
- For each page: Use Step 5 (Dynamic Single-Page PDF Extraction) below
- Load with full images, then cleanup temp file immediately

### Step 5: Dynamic Single-Page PDF Extraction (Zero-Pollution Visual Study)

**Purpose**: Load single PDF pages with full visual content using temporary files

**Workflow** (`load_pdf_page_visually` function):
1. Run `scripts/learning-materials/extract-pdf-page-for-reading.py '{pdf}' {page_num} --json`
2. Parse JSON for `success`, `temp_file`, `file_size_mb`
3. If failed: Show error, return None
4. If success: Read `temp_file` with Read tool (SAFE - only 1 page inside)
5. Return page content and temp_file path for cleanup

**Cleanup** (`cleanup_temp_pdf` function):
- Delete temp file immediately after use: `source venv/bin/activate && python scripts/learning-materials/cleanup-leaked-pdf-temps.py --force`
- Must be called after every page load

**Learning Loop Pattern**:
- Initialize session state (start time, pages processed, timing array)
- Set Ctrl+C handler to save checkpoint and exit gracefully
- For each selected page:
  - Show progress indicator (page X/Y, estimated time remaining)
  - Load page with `load_pdf_page_visually`
  - Teach from page content (Socratic dialogue)
  - Track timing for ETA calculation
  - Checkpoint every 10 pages
  - **Always** cleanup temp file in `finally` block
- Update final progress with session stats

**Performance**: ~2s per page (0.5s extraction + 1.5s read), acceptable for picture books

### Step 6: Smart Material Loading (Size-Aware)

**⚠️  PDF READING PROTOCOL (MANDATORY) ⚠️**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULE FOR ALL PDF FILES:

❌ NEVER: Read(file_path="document.pdf", offset=X, limit=Y)
❌ NEVER: read_file("document.pdf")
❌ NEVER: Use Read tool directly on ANY .pdf file

✅ ALWAYS: Use scripts/learning-materials/extract-pdf-chunk.py for ALL PDF content extraction
✅ ALWAYS: Use --text-only for preview/browsing
✅ ALWAYS: Use visual mode (without --text-only) for deep study

WHY: Read tool's offset/limit parameters work on TEXT LINES, not PDF PAGES.
     Calling Read(file.pdf, offset=1, limit=1) loads THE ENTIRE PDF regardless
     of parameters, causing API Error 413 (request too large).

CORRECT WORKFLOW:
  # Text preview (fast, no images)
  run_bash(f"source venv/bin/activate && python scripts/learning-materials/extract-pdf-chunk.py '{file}' --mode pages --pages 1-10 --text-only --json")

  # Visual study (with images, 1 page at a time for image-heavy PDFs)
  run_bash(f"source venv/bin/activate && python scripts/learning-materials/extract-pdf-chunk.py '{file}' --mode pages --pages 5-5 --json")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Large PDFs** (chunked mode):
- **First time**: Extract TOC with `--mode toc --json`, display title/pages/outline, prompt user for starting chunk
- **Continuing**: Calculate chunk pages from current position, extract with `--mode pages --pages {range} --json`

**Small files or non-PDF**:
- **PPT**: `scripts/learning-materials/parse-ppt.py {file}`
- **EPUB**: `scripts/learning-materials/parse-epub.py {file}`
- **PDF (safe)**: `scripts/learning-materials/extract-pdf-chunk.py '{file}' --mode pages --pages 1-{total} --json` (NEVER use Read on PDFs!)
- **First time**: Extract TOC and update progress file

### Step 7: Determine Chunk to Learn

- Get `current_position` from progress file (e.g., "Page 42", "Chapter 3")
- Calculate chunk boundaries using semantic strategy (break at section/paragraph)
- Extract chunk: `content[chunk_start:chunk_end]`
- **If loading new chunk mid-session**: Triggers re-consultation (PHASE 2 STEP 2)

### Step 8: Segment Content for Progressive Display

**Purpose**: Break chunk into teachable micro-segments to ensure full coverage

**Segmentation strategy**:
- Break chunk into natural segments (paragraph/section level)
- Target: 1-3 paragraphs per segment (200-500 words)
- Preserve semantic boundaries (don't break mid-concept)
- Track segments: `current_segment_index`, `total_segments`

**Segment state**:
- Initialize: `segments = [seg1, seg2, ...]`, `current_index = 0`
- Load segment: `current_segment = segments[current_index]`
- Progression: User says "next" / "continue" → `current_index += 1`

**Completion detection**:
- If `current_index >= len(segments)` → Chunk complete, load next chunk (Step 7)

### Step 9: Select Appropriate Agent

**⚠️ CRITICAL**: Selecting the wrong agent = mismatched domain expertise = poor learning outcomes.

**Agent Mapping**:
- `finance` → finance-tutor
- `programming` → programming-tutor
- `language` → language-tutor
- `medicine` → medicine-tutor
- `law` → law-tutor
- `science` → science-tutor
- `journalism` → journalist
- `default` → book-tutor (books/reports)

**Fallback strategy**:
- If domain unclear → Use book-tutor (general learning)
- If agent unavailable → Use book-tutor as fallback
- If domain mismatch detected mid-session → Consult correct agent and pivot

### Step 10: Domain Focus Constraints

Questions must test DOMAIN SKILLS, not content knowledge.

Domain-specific focus areas for consultation prompts:
- **Language**: Grammar production, collocation patterns, syntax construction, pronunciation practice
- **Finance**: Formula application, risk analysis, valuation methods, market mechanisms
- **Programming**: Syntax patterns, algorithm analysis, debugging, design patterns
- **Science**: Experimental design, calculations, concept application, data interpretation
- **General**: Argument analysis, evidence evaluation, concept connections, logical reasoning

Validate questions test skills, not facts/history. If invalid, re-consult for correction.

### Step 11: Consultation-Based Learning Session

**⚠️ CRITICAL**: This is the core learning workflow. Skipping consultation phases = no Socratic teaching = passive content dump.

**Architecture**: Main agent orchestrates learning using Task tool for expert consultation (book/language/finance/programming/medicine/law/science-tutor). Expert provides JSON guidance (learning plan, Socratic questions, concept extraction). User never sees consultation process - only natural teaching dialogue.

**Code Presentation**: If consultant generates code for exercises/analysis, translate outputs to natural language. User should not see raw scripts unless debugging.

#### PHASE 1: Initial Consultation

**Task Call**:
- Use Task tool with `subagent_type={agent}` (book/language/finance/programming/medicine/law/science-tutor)
- model: "haiku"
- Include in prompt: Material, Current Section, **Current Segment** (from Step 8), Segment Position, Domain Focus Constraints (from Step 10)
- Request JSON: learning_plan, socratic_questioning (domain_focus/question_type/domain_element_tested), **anticipated_follow_ups**, success_criteria
- Parse JSON result

**Required JSON structure**:
```json
{
  "learning_plan": {...},
  "socratic_questioning": {...},
  "anticipated_follow_ups": [
    {"trigger": "user requests examples", "prepared_response": "...", "re_consult_needed": false},
    {"trigger": "user challenges accuracy", "prepared_response": "verify with sources", "re_consult_needed": true}
  ]
}
```

**Fallback**:
- Invalid JSON → Retry once
- Missing fields → Use defaults
- Fails twice → Direct teaching

#### PHASE 2: Socratic Dialogue Execution

**Principle**: ASK, DON'T TELL

- **Default**: Pose questions, not explanations (<200 tokens)
- **With context**: Add minimal framing (<300 tokens)
- **Full explanation**: Only when user explicitly requests (<500 tokens)

**Forbidden (Meta-Commentary)**:
- "I'm using Socratic teaching"
- "Launching book-tutor for interactive learning"
- "Let me consult the expert..."
- Any mention of teaching methods, consultation process, or agent architecture

**Required (Natural Teacher Voice)**:
- Use first-person naturally ("Let me...", "I will...", "We can...")
- Ask questions directly (no announcements about asking questions)
- Natural conversational flow (no meta-commentary about how you're teaching)

**Depth escalation keywords**: "explain in detail", "give me examples", "show me the formula", "why", "I don't understand", "more details", "dive deeper"

**Content Display Rule**:
- User CANNOT see the PDF/book content
- You MUST display content before asking questions

**Multi-Turn Dialogue Loop**:

**Initial Question**:
1. Use consultant's `socratic_questioning.questioning_phases.next_question`
2. Validate question stays in domain focus - if invalid, re-consult for correction
3. **Display FULL current segment to user** (from Step 8: `current_segment`)
   - Show complete segment text (all paragraphs, no truncation)
   - Indicate position: "Segment {current_index+1}/{total_segments}"
4. Ask validated question
5. Wait for user response

**Conversation Flow** (repeat until natural conclusion):

After each user response, apply **Re-Consultation Decision Framework**:

**STEP 1: Check anticipated_follow_ups**
- Match user response against tutor's `anticipated_follow_ups` triggers
- If 80%+ match and `re_consult_needed: false` → Use prepared response
- If match and `re_consult_needed: true` → Proceed to STEP 4
- If no match → Proceed to STEP 2

**STEP 2: Mandatory triggers**
Re-consult immediately if:
- Loading new content chunk (Step 7)
- **User requests next segment** ("next", "continue", "show more", "got it, continue")
- User requests domain-specific examples or verification
- User challenges explanation accuracy
- User expresses confusion after 2+ attempts
- User requests depth expansion

**Segment progression flow**:
- If "next segment" trigger detected:
  - Increment `current_index += 1`
  - If `current_index < len(segments)`: Load next segment, re-consult tutor with new segment
  - If `current_index >= len(segments)`: Chunk complete, trigger Step 7 for new chunk

**STEP 3: Quantify information gap**
Estimate gap relative to tutor's guidance:
- New content needed: >40% beyond guidance → Re-consult
- Topic shift: >50% different content → Re-consult
- Otherwise → STEP 4

**STEP 4: Self-check before responding**
Verify ALL conditions:
- [ ] Covered in tutor guidance or anticipated_follow_ups
- [ ] Not evaluating domain-specific correctness
- [ ] Not making domain claims beyond expertise
- [ ] Confidence ≥70%

If ANY unchecked → Re-consult via Task tool

**STEP 5: Re-consultation prompt**
```
Use Task tool:
- subagent_type: {domain}-tutor
- model: "haiku"
- prompt: "
  Return JSON only (no Markdown).

  User response: {answer}
  Expected: {expected_answer}
  Trigger: {reason}
  Context: {material, section, concept}

  Provide:
  {
    \"evaluation\": {\"correctness\": \"...\", \"evidence\": \"...\"},
    \"next_strategy\": \"continue|reteach|skip_ahead\",
    \"content\": {\"feedback\": \"...\", \"next_question\": \"...\"},
    \"anticipated_follow_ups\": [{\"trigger\": \"...\", \"prepared_response\": \"...\", \"re_consult_needed\": bool}]
  }
  "
```

Internalize JSON → Respond naturally

**Token Budget Tracking**:
- Track cumulative tokens in session state (estimate ~1.5 tokens per word)
- Check budget every 3 dialogue turns
- If tokens > 150000: Warn user, suggest wrapping up
- If tokens > 180000: Force save progress and exit

**Repeat this loop until**:
- ✅ User indicates completion
- ✅ User asks to end session
- ✅ Material chunk completed
- ✅ Token budget exceeded (save and exit)

#### PHASE 3: Outcome Validation

**Purpose**: Evaluate what user truly learned (not just saw) with evidence-based mastery assessment.

**Task call to `{agent}`**:
- Input: Session transcript summary, user responses, struggle count
- Request JSON with mastery-based concept_summary:
  ```json
  {
    "concept_summary": {
      "mastered": [
        {"concept_id": "...", "evidence": "User correctly applied X in 3 contexts..."}
      ],
      "practiced": [
        {"concept_id": "...", "evidence": "User identified Y but made 1 error..."}
      ],
      "introduced_only": [
        {"concept_id": "...", "evidence": "User passively heard Z, no demonstration..."}
      ]
    },
    "success_criteria": {...}
  }
  ```

**Mastery Levels**:
- **mastered**: User demonstrated understanding through correct application, explanation, or self-correction
- **practiced**: User engaged with concept, made attempts, showed partial understanding
- **introduced_only**: User was exposed to concept but showed no active engagement or understanding

**Processing**:
- Display to user: "Mastered X concepts, Practiced Y concepts, Introduced to Z concepts"
- Do NOT update progress file manually - /save workflow handles this automatically in Step 9
- Do NOT write Rems to knowledge-base - user must run `/save` to extract from conversation
- Indexes are auto-updated by PostToolUse hooks when Rem files are modified

### Step 12: Post-Session Actions

- Display completion message: Progress %, new concepts count, next steps
- CRITICAL: Display prominent `/save` reminder with option:

```
Session complete! {X} concepts learned.

⚠️ IMPORTANT: Run `/save` now to extract concepts to knowledge base.
Without this step, your learning won't be saved as Rems.

<options>
  <option>Save Now (/save)</option>
  <option>Later</option>
</options>
```

### Step 13: User-Facing Output

Generate custom welcome summary and greetings based on progress file content and session state.

**For continuation**: Mention position, progress %, last session summary.
**For new material**: Introduce title, type, domain, learning approach.

## Notes

**Socratic Teaching Approach**:
- Teaching method: Ask questions first, explain only when requested
- Default response: Pose questions, not explanations (<200 tokens)
- Full explanation: Only when user explicitly requests (<500 tokens)
- Depth escalation: Triggered by keywords like "explain in detail", "give me examples", "why", "I don't understand"
- Natural voice: First-person teacher voice, no meta-commentary about teaching methods

**Interactive Session Guidelines**:
- This command is interactive - expect user responses during session
- Keep sessions 30-60 minutes of content maximum
- Always update progress file before ending
- If context limit approached, save and prompt to continue next session
- Subagent consultations are backend-only - main agent translates JSON to natural dialogue

**Goal**: Facilitate deep, interactive learning through Socratic dialogue with expert consultation
