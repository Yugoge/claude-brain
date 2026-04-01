description: "Interactive review session using spaced repetition (FSRS algorithm)"
allowed-tools: Bash, Task, TodoWrite
argument-hint: "[domain | [[rem-id]]]"
disable-model-invocation: true
---

**⚠️ CRITICAL PROHIBITION**: Main agent MUST NOT use Read tool on Rem files. Only review-master subagent may read Rem content.

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Review Command

Start an interactive review session using spaced repetition (FSRS algorithm).





## Usage

```
/review
/review <domain>
/review [[rem-id]]
```

## Examples

```
/review                                # Review all Rems due today
/review finance                        # Review all finance Rems
/review [[call-option-intrinsic-value]]  # Review specific Rem
/review --easy                         # Rapid-fire fact recall (high volume)
/review --hard                         # Analysis/application questions (deep mastery)
/review --easy --format m --lang zh finance  # Composable with all flags
```

## What This Command Does

1. **Shows comprehensive timeline** - Past (overdue), Today, Future (7 days)
2. **Loads review schedule** from `.review/schedule.json`
3. **Identifies Rems due for review** (based on FSRS retrievability)
4. **Conducts Socratic dialogue review** - Main agent (you) leads the conversation
5. **Consults review-master agent** - Gets JSON guidance for each Rem (Socratic questions, quality criteria)
6. **Assesses recall quality** - User self-rates (1-4 scale: Again, Hard, Good, Easy)
7. **Updates FSRS schedule** - Calculates next review date using FSRS formula after each Rem
8. **Logs session** to `.review/history.json`

**Architecture**: Main agent conducts dialogue with user. Review-master is a **consultant agent** providing JSON guidance (not direct user interaction).

## FSRS Algorithm Overview

FSRS (Free Spaced Repetition Scheduler) is a modern algorithm that provides:
- 30-50% more efficient than traditional spaced repetition algorithms
- Adaptive difficulty modeling
- Memory stability tracking
- Personalized scheduling based on your performance

**Key Parameters**:
- **Difficulty (D)**: How hard the concept is for you (0-10 scale)
- **Stability (S)**: How long you retain it (days)
- **Retrievability (R)**: Current memory strength (0-1)
- **Interval**: Days until next review

Rating Scale (1-4):
- 1 (Again): Complete forget, need to relearn
- 2 (Hard): Remembered with significant effort
- 3 (Good): Remembered with some effort (optimal difficulty)
- 4 (Easy): Instant recall, too easy

## Implementation

### Step 1: Load Rems and Show Timeline

**⚠️ CRITICAL**: Loading incorrect Rems or skipping due dates = broken spaced repetition = memory decay.

**⚠️ ENFORCEMENT**: Use `--blind` flag to prevent main agent from seeing Rem content (only paths and IDs).

```bash
source venv/bin/activate && python scripts/review/run_review.py --blind [args]
```

This script now ALWAYS shows a comprehensive timeline first:
- **PAST (Overdue)**: All overdue reviews with days overdue
- **TODAY**: Reviews due today
- **FUTURE (Next 7 days)**: Upcoming reviews with domain breakdown
- **Summary**: Total counts, time estimates

Then displays filtered review session and outputs JSON data for next steps.

**Relation-based clustering** (commit 2ae4a70):
- Related Rems review consecutively via graph clustering (DFS connected components)
- Benefit: Associative learning - remA↔remB always together
- At session start: Mention "Related concepts clustered for associative learning"
- Between clusters: Optionally note "Moving to next topic cluster"

**Timeline-only mode** (skip review session):
```bash
source venv/bin/activate && python scripts/review/run_review.py --timeline
```

**Custom lookahead** (show next 14 days instead of 7):
```bash
source venv/bin/activate && python scripts/review/run_review.py --days 14
```

**Force question format** (override review-master's adaptive selection):
```bash
source venv/bin/activate && python scripts/review/run_review.py --format m  # multiple-choice
source venv/bin/activate && python scripts/review/run_review.py --format c  # cloze
source venv/bin/activate && python scripts/review/run_review.py --format s  # short-answer
source venv/bin/activate && python scripts/review/run_review.py --format p  # problem-solving
```

**Force dialogue language**:
```bash
source venv/bin/activate && python scripts/review/run_review.py --lang zh  # Chinese
source venv/bin/activate && python scripts/review/run_review.py --lang en  # English
source venv/bin/activate && python scripts/review/run_review.py --lang fr  # French
```

**Difficulty mode** (controls cognitive depth of questions):
```bash
source venv/bin/activate && python scripts/review/run_review.py --easy    # Bloom's Remember: fact recall, rapid-fire
source venv/bin/activate && python scripts/review/run_review.py --normal  # Bloom's Understand: current default behavior
source venv/bin/activate && python scripts/review/run_review.py --hard    # Bloom's Analyze/Apply: scenarios, discrimination
```
- `--easy`: Single fact-recall per Rem, no follow-ups, no explanation loop, batch limit 50
- `--normal` (default): Current Socratic dialogue behavior unchanged
- `--hard`: Analysis/application questions, follow-up probing, multi-concept discrimination
- Composable with `--format` and `--lang` (e.g., `--easy --format m --lang zh`)
- When `--format` is explicitly set, it overrides difficulty mode's format preference

**Combined parameters**:
```bash
source venv/bin/activate && python scripts/review/run_review.py --format m --lang zh finance
source venv/bin/activate && python scripts/review/run_review.py --easy --format m --lang zh finance
```

**Note**: Path resolution prefers `.md` and falls back to `.rem.md` when content still uses the legacy extension.

**Blind Mode Output**: When using `--blind`, the JSON output contains ONLY `id` and `path` for each Rem (no `title`, `domain`, `fsrs_state`). This prevents main agent from seeing content and bypassing review-master consultation.

---

### Step 2: Conduct Review Session (Main Agent Dialogue Loop)

**⚠️ CRITICAL**: This is the core FSRS review workflow. Poor questioning = inaccurate self-ratings = suboptimal scheduling.

**ARCHITECTURE**: Main agent (you) conducts the review dialogue directly with the user. Review-master is a **consultant agent** that provides JSON guidance.

**Session Setup** (before first Rem):
```
Session state is now persisted to .review/session-{session_id}.json (written by run_review.py).
Use get_next_rem.py --session-id {session_id} to retrieve the next Rem for each iteration.
This prevents hallucinated Rem IDs when conversation context is compressed.

session_id = data['session_id']  // CRITICAL: Extract from run_review.py JSON output, pass to all subsequent scripts
format_history = data['format_history']  // Loaded from .review/format_history.json
```

**Note**: Session Rems are persisted to disk. Even if conversation context is lost, call get_next_rem.py to recover the correct next Rem.

**Difficulty Mode Dialogue Rules** (from `difficulty_mode` in run_review.py JSON):

**Easy Mode** (`difficulty_mode: "easy"`):
- Question: Single fact-recall question (Bloom's Remember level)
- After answer: Brief feedback only (correct/incorrect + correct answer if wrong)
- No progressive hints -- show correct answer immediately if wrong
- Skip explanation loop (Step 7) entirely -- never enter EXPLANATION_LOOP
- Proceed directly to rating after brief feedback
- Target: 15-30 seconds per Rem

**Normal Mode** (`difficulty_mode: "normal"` or default):
- Current behavior unchanged (Socratic dialogue, hints, explanation loop, adaptive formats)

**Hard Mode** (`difficulty_mode: "hard"`):
- Question: Analysis/application/discrimination question (Bloom's Analyze/Apply/Evaluate)
- After initial answer: Ask 1-2 follow-up questions from review-master's `follow_up_questions`
- Follow-up questions probe deeper: "Why?", "How does this differ from X?", "What if Y changed?"
- Explanation loop (Step 7) remains active for confused users
- Minimal hints -- challenge the user before providing help
- Target: 3-5 minutes per Rem

**For each Rem in the session, call get_next_rem.py to get the next Rem**:

```bash
source venv/bin/activate && python scripts/review/get_next_rem.py --session-id {session_id}
```

This returns JSON with the next pending Rem (id, path, conversation_source, index, total, remaining).
If session_complete is true, proceed to Step 4 (Post-Session Summary).
If stale_warning is present, inform user about session age.

**For each Rem returned by get_next_rem.py, follow this loop**:

#### 3. Consult Review-Master for Guidance

**⚠️ ARCHITECTURAL CHANGE**: Main agent does NOT read Rem files. Only review-master reads Rem content.

**Rationale**: Prevents main agent from seeing Rem content and bypassing expert consultation ("feeling smart" and skipping review-master).

**Expected Tool Usage Pattern** (Root Cause Fix: commit 9f5bd86):

Review-master MUST demonstrate file reading via tool logs:
1. **Read tool call on Rem file** - Always required, no exceptions
2. **Read tool call on conversation file** - Required when conversation_source is not null
3. **Fallback to extract_conversation_context.py** - If Read fails due to line limit (>2000 lines)

**Validation**: Check tool logs after consultation. If review-master did not read files, consultation is invalid.

**Fallback strategy**:
- If review-master unavailable → Ask direct recall question: "What do you remember about the concept at {path}?"
- If JSON invalid → Use minimal guidance (ask for free recall, no hints)
- If consultation fails → Proceed with basic review (ask user to recall, then end)

```
Use Task tool:
- subagent_type: "review-master"
- model: "sonnet"  # Sonnet for reliable MCQ quality
- description: "Get Socratic question guidance for Rem {N}/{total}"
- prompt: "
  You are a consultant providing JSON guidance for FSRS review.

  **CRITICAL**: You MUST read the Rem file yourself using the Read tool.
  Main agent does NOT have access to Rem content (blind mode enforcement).

  **Step 1**: Read Rem file at path: {full_path_to_rem_file}

  **Step 2**: Extract from Rem file:
  - Frontmatter: rem_id, title, domain, created, source (conversation path)
  - Content sections: Core Memory Points, Usage Scenario, Related Rems

  **Step 3**: Provide Socratic question guidance based on Rem content.

  **IMPORTANT INSTRUCTION**:
  - Check format_preference field FIRST
  - If format_preference is NOT null → Use that format exclusively, ignore all diversity/variety logic
  - If format_preference is null → Use adaptive format selection with variety

  **Session Context**:
  {
    \"rem_path\": \"{full_path_to_rem_file}\",
    \"rem_id\": \"{rem_id from blind mode JSON}\",
    \"conversation_source\": \"{conversation_source from blind mode JSON (optional, null if not present)}\",
    \"session_context\": {
      \"total_rems\": {total},
      \"current_index\": {N},
      \"mode\": \"{mode}\",
      \"consultation_type\": \"question\",
      \"format_preference\": \"{format_preference from run_review.py JSON or null}\",
      \"lang_preference\": \"{lang_preference from run_review.py JSON or null}\",
      \"difficulty_mode\": \"{difficulty_mode from run_review.py JSON (easy/normal/hard)}\"
      {IF format_preference is null, include: ,\"recent_formats\": {format_history}}
    }
  }

  **Format Selection Logic**:

  IF format_preference is NOT null:
  - ALWAYS use that format (no exceptions, no variety considerations)
  - Format codes: 'm'=multiple-choice, 'c'=cloze, 's'=short-answer, 'p'=problem-solving
  - User wants consistent format (quick mode or exam prep)
  - Ignore recent_formats completely

  IF format_preference is null:
  - Use adaptive format selection based on content type
  - Consider recent_formats for variety (avoid 3+ consecutive same format)
  - Mix formats based on content characteristics AND diversity

  **⛔ MCQ RULE (if format=multiple-choice)**:
  - EXACTLY 1 correct answer + 3 FACTUALLY or GRAMMATICALLY INCORRECT statements
  - "Wrong" means the statement itself contains factual errors or grammar mistakes (NOT just "wrong answer to this question but valid sentence")
  - Before returning, verify ISOLATION TEST: Would a domain expert, seeing each option WITHOUT the question, identify 3 as WRONG STATEMENTS?
  - If multiple options are factually/grammatically correct → REDESIGN the question

  Use lang_preference if provided:
  - If lang_preference is not null, generate ALL dialogue in that language
  - Language codes: 'zh'=Chinese, 'en'=English, 'fr'=French
  - Applies to primary_question, hints, follow_ups, context_scenario
  - Rem content (Core Memory Points) remains unchanged

  Return JSON guidance as specified in your instructions (include title, domain, fsrs_state read from file).
  "
```

**Review-master returns**:
```json
{
  "review_guidance": {
    "rem_id": "...",
    "question_format": "short-answer | multiple-choice | cloze | problem-solving",
    "socratic_question": {
      "primary_question": "...",
      "expected_concepts": [...],
      "hints_if_struggling": [...]
    },
    "format_specific": {
      "correct_answer": "A/B/C/D (if MCQ)",
      "cloze_blanks": ["answers (if cloze)"],
      "problem_data": {"given": {}, "expected_steps": []}
    },
    "quality_assessment_guide": {
      "rating_4_indicators": [...],
      "rating_3_indicators": [...],
      "rating_2_indicators": [...],
      "rating_1_indicators": [...]
    },
    "memory_context": {
      "difficulty_hint": "easy/medium/hard",
      "adaptive_note": "..."
    }
  }
}
```

**Parse and extract**:
- `question_format` - Determines presentation style
- `primary_question` - The question text (may include `<option>` tags for MCQ)
- `format_specific` - Additional format data if needed

**⚠️ CRITICAL: Track the format for next iteration**:
```bash
source venv/bin/activate && python scripts/review/track_format.py {question_format}
```

This updates `.review/format_history.json` with the format used. Next Rem will load updated history via run_review.py.

#### 4. Present Question to User (First-Person Voice)

**Adapt presentation based on question_format**:

**Short Answer** (default - free response):
```
Let's review: {rem_title}

{context_scenario if provided}

{primary_question}
```

**Multiple Choice** (primary_question contains plain text options A) B) C) D)):
```
Let's review: {rem_title}

{context_scenario if provided}

{primary_question without options}

<options>
<option>{Option A text}</option>
<option>{Option B text}</option>
<option>{Option C text}</option>
<option>{Option D text}</option>
</options>
```

**Processing**: Extract options from primary_question (format: "A) text\nB) text\nC) text\nD) text"), wrap each in `<option>` tag, place in `<options>` block at message end.

**Cloze** (fill-in-the-blank):
```
Let's review: {rem_title}

{context_scenario if provided}

{primary_question with {blank} markers}
(User fills in missing words/formulas)
```

**Problem-Solving** (calculation/coding/translation):
```
Let's review: {rem_title}

{context_scenario}

{primary_question with clear requirements}
(User shows work/steps)
```

**Voice Guidelines**:
- ✅ Direct first-person: "Let me test your understanding..."
- ✅ Natural teaching tone: "Can you explain..."
- ❌ Never third-person: "The review-master asks..."
- ❌ No meta-commentary: "I'm consulting the agent..."

#### 5. Listen to User Response

Wait for user to answer the question.

#### 6. Evaluate Response Quality

**Compare user response to quality_assessment_guide from JSON**:

- Check if user mentioned expected_concepts
- Assess recall speed and accuracy
- Note if hints were needed

**Observe quality indicators**:
- Rating 4: Matches rating_4_indicators from JSON
- Rating 3: Matches rating_3_indicators from JSON
- Rating 2: Matches rating_2_indicators from JSON
- Rating 1: Matches rating_1_indicators from JSON

#### 6b. Hard Mode Follow-Up Questions (if difficulty_mode == "hard")

**Only when `difficulty_mode == "hard"`** and user answered correctly (Quality 3-4):
1. Present 1-2 follow-up questions from review-master's `follow_up_questions` field
2. Follow-ups probe deeper reasoning: "Why does this matter?", "How would this change if X?", "Compare this with Y concept"
3. Listen to user response and evaluate
4. Use follow-up quality to inform final rating suggestion (better follow-up answers = higher rating)
5. Then proceed to Step 7 (or Step 8 if no confusion)

If user answered incorrectly (Quality 1-2), skip follow-ups and proceed to Step 7 normally.

#### 7. Confusion Detection & Explanation Loop (Commit 893dffd Enhancement)

**⚠️ EASY MODE EXCEPTION**: If `difficulty_mode == "easy"`, SKIP this entire step. Show correct answer briefly if wrong, then proceed directly to Step 8 (rating). Easy mode prioritizes throughput over re-teaching.

**⚠️ CRITICAL**: Detect user confusion and provide explanation BEFORE proceeding to rating.

**Confusion Triggers** (AI judgment, no hardcoded phrases):

Detect if ANY of these occur:
1. **Explicit "don't know"**: User explicitly states they don't know or can't remember
2. **Wrong answer + explanation request**: User provides incorrect answer AND asks for help/explanation
3. **Multiple hints exhausted**: User still struggling after 2+ hints provided
4. **User requests review**: User directly asks to review the concept again

**AI Judgment Required**:
- Analyze user's response semantically (don't match exact phrases)
- Consider context (struggling vs thinking out loud)
- Detect help requests in any language
- Examples of confusion signals:
  - "I have no idea"
  - "Can you explain this?"
  - "I'm not sure, help me understand"
  - "Let me see the answer"
  - Wrong answer followed by "Why?"

**If confusion detected, enter explanation loop**:

```
EXPLANATION_LOOP:
  1. Consult review-master for explanation:

  Use Task tool:
  - subagent_type: "review-master"
  - model: "sonnet"
  - description: "Get explanation for confused user"
  - prompt: "
    You are a consultant providing explanation guidance.

    **CRITICAL**: Read the Rem file yourself using Read tool at: {full_path_to_rem_file}

    User is confused during review. Provide re-teaching guidance.

    {
      \"rem_path\": \"{full_path_to_rem_file}\",
      \"rem_id\": \"{rem_id}\",
      \"conversation_source\": \"{conversation_source from blind mode JSON (optional, null if not present)}\",
      \"session_context\": {
        \"consultation_type\": \"explanation\",
        \"failed_question\": \"{the question user couldn't answer}\",
        \"user_response\": \"{user's confused response}\",
        \"hints_tried\": [\"{hints already provided}\"]
      }
    }

    Return explanation_guidance JSON as specified in your instructions.
    "

  2. Parse explanation_guidance JSON

  3. Present explanation naturally to user:
     - Use key_concept_summary
     - Provide detailed_explanation
     - Share analogies if helpful
     - Reference conversation_context if available
     - Ask verification_questions to check understanding

  4. Listen to user response

  5. Evaluate understanding:
     IF user demonstrates understanding (answers verification questions correctly):
       - Move to re-testing (step 6)
     ELSE IF user still confused:
       - Provide additional clarification
       - Loop back to step 4 (no iteration limit)

  6. Re-test with NEW question:
     - Consult review-master again with consultation_type="question"
     - Pass previous_failed_question in context to avoid repetition
     - Use re_test_guidance.new_question_angle suggestion
     - Test same concept from different perspective

  7. User answers new question

  8. Evaluate new response:
     IF user answers correctly:
       - Exit explanation loop
       - Continue to rating (Step 9)
     ELSE IF user still struggling:
       - Loop back to step 1 (provide more explanation)

END EXPLANATION_LOOP
```

**Exit Conditions**:
- User demonstrates understanding AND passes re-test
- User explicitly requests to skip this Rem
- No maximum iteration limit (keep teaching until user understands)

**After successful explanation loop**: Proceed to Step 8 (rating) with the final answer quality.

**If no confusion detected**: Skip explanation loop, proceed directly to Step 8.

#### 8. Provide Feedback and Ask for Self-Rating

**⚠️ CRITICAL - Hints Display Logic** (Root Cause Fix: commit 3ed6b6f):

**NEVER show hints_if_struggling in correct-answer feedback**:
- Hints are ONLY for struggling users (Quality 1-2)
- Showing hints after correct answers reduces difficulty artificially
- User complained about receiving unwanted hints

**Hints Display Rules**:
1. **User answered CORRECTLY** (Quality 3-4) → NO hints displayed, proceed directly to rating
2. **User answered INCORRECTLY or struggling** (Quality 1-2) → Show hints progressively
3. **User explicitly requests help** → Show hints regardless of answer quality

---

**[OPTIONAL] Deep Dive Consultation**

If user asks deep question (trigger signals):
- Formula or logic questions
- Challenges your explanation
- Requests deeper detail
- Multiple follow-ups on same concept

You can call multiple analysts in parallel (multiple Task calls in single message) if the question has multiple distinct aspects.

Then consult analyst (Three-Party Architecture):
```
Use Task tool:
- subagent_type: "analyst"
- model: "sonnet"
- description: "Research deep question during review"
- prompt: "
  ⚠️ CRITICAL: Return ONLY valid JSON. NO markdown.

  You are a CONSULTANT to the main review agent, NOT the user's teacher.
  The user will NEVER see your response - only the main agent will.

  **OUTPUT REQUIREMENTS**:
  - Return ONLY the JSON object specified below
  - NO markdown code blocks
  - NO explanatory text before or after JSON

  Context: User is reviewing {rem_title} (domain: {domain})

  User's deep question: {user_question}

  Rem content: {core_memory_points}

  Previous dialogue context: {brief_summary_of_conversation}

  ---

  Research the question using WebSearch if needed, then return ONLY:

  {
    \"research_findings\": \"Key facts from search (if needed)\",
    \"explanation_strategy\": \"formula_derivation | analogy | prerequisite_review | direct_answer\",
    \"content\": {
      \"answer\": \"Direct answer to user's question\",
      \"sources\": [\"URL1\", \"URL2\"],
      \"follow_up\": \"Optional follow-up question to deepen understanding\"
    },
    \"confidence\": 85
  }

  **IMPORTANT**: Return the JSON object above WITHOUT any wrapping.
  "
```

**Internalize guidance and respond naturally**:
- Use first-person voice
- NO meta-commentary
- Present findings as natural teaching dialogue
- Return to rating flow when question resolved

---

**Standard Feedback Flow** (no deep dive needed):

**If response is strong** (Quality 3-4):
```
{Positive feedback acknowledging correct answer}

{Rating request in appropriate language - see below}

⚠️ CRITICAL: DO NOT include hints_if_struggling here - user answered correctly
```

**Rating Request** (compose in appropriate language):

Check `lang_preference` from run_review.py JSON output:
- If `lang_preference` has a value: Compose rating request in that language
- If `lang_preference` is null or not provided: Infer language from conversation context or default to Chinese

**Structure** (compose yourself, adapt to target language naturally):
```
{Rating question in target language} (1-4)
<options>
<option>1 - {Complete forget / need to relearn}</option>
<option>2 - {Recalled with significant effort}</option>
<option>3 - {Recalled with some thought}</option>
<option>4 - {Instant recall / too easy}</option>
</options>
```

**FSRS 1-4 scale semantics** (express naturally in target language):
1. Again: Complete forget, need to relearn
2. Hard: Recalled with significant effort
3. Good: Recalled with some thought (optimal difficulty)
4. Easy: Instant recall, too easy

Compose the rating question and option labels yourself using natural phrasing for the target language. Do not use hardcoded templates or language lists.

**If response is weak** (Quality 1-2):
```
{Encouraging feedback}

{Provide first hint from hints_if_struggling array}

[If still struggling, provide additional hints progressively from hints_if_struggling]

{Rating request in appropriate language - use same format as above}

✅ Hints are appropriate here - user is struggling (Quality 1-2)
```

**User Self-Rating**: User provides rating (1-4)

**If user disputes your assessment**: Accept their rating (FSRS adapts to user feedback)

#### 9. Update FSRS Schedule

**⚠️ CRITICAL**: Incorrect schedule updates = broken FSRS algorithm = review intervals too long/short.

**CRITICAL**: Immediately update schedule after rating:

```bash
source venv/bin/activate && python scripts/review/update_review.py {rem_id} {user_rating} --session-id {session_id}
```

**Parse JSON output and show feedback**:
```
✅ {Rem Title} reviewed!

Rating: {rating} ({Again/Hard/Good/Easy})
FSRS Update:
  - Difficulty: {old_difficulty:.2f} → {new_difficulty:.2f} ({trend})
  - Stability: {old_stability:.1f} days → {new_stability:.1f} days
  - Next review: {next_review_date} ({interval_days} days)

{Contextual message based on rating}
```

**Contextual messages**:
- Rating 1: "⚠️ This needs more attention. Reviewing again tomorrow."
  - If has_prerequisite links exist: "💡 Consider reviewing: {prerequisite titles}"
- Rating 2: "You got it with effort. Keep practicing."
  - If has_prerequisite links exist: "💡 Foundation: {prerequisite titles}"
- Rating 3: "🎉 Good retention! Perfect difficulty level."
- Rating 4: "Too easy! I'll make it harder next time."

#### 10. Move to Next Rem

**Retrieve next Rem from disk** (prevents hallucination after context loss):
```bash
source venv/bin/activate && python scripts/review/get_next_rem.py --session-id {session_id}
```

Parse the JSON output:
- If `session_complete: true` -> All done, proceed to Step 4 (Post-Session Summary)
- If `success: true` -> Use `rem.id`, `rem.path`, `rem.conversation_source` for next iteration
- Progress: `[{reviewed+1}/{total}] {reviewed} reviewed, {remaining} remaining`

**Repeat steps 3-10 for all Rems in session.**

**Early Exit Handling**:
- If user stops early (e.g., "stop", "enough"), break loop
- Clean up session: `source venv/bin/activate && python scripts/review/get_next_rem.py --session-id {session_id} --cleanup`
- Show partial session summary (see Step 4)
- Save progress - already-reviewed Rems have updated schedules

---

### Step 4: Post-Session Summary

After all Rems reviewed (or early exit):

**Session Cleanup** (always run at session end):
```bash
source venv/bin/activate && python scripts/review/get_next_rem.py --session-id {session_id} --cleanup
```
This deletes `.review/session-{session_id}.json` to prevent stale session warnings on next run.

**Early Exit Handling** (if user interrupts before completing all Rems):
- Save progress to `.review/history.json`
- Update schedule for already-reviewed Rems
- Show partial session summary:
  - Difficulty mode: {difficulty_mode} (easy/normal/hard)
  - Reviewed: {N} out of {total}
  - Average rating: {avg}
  - Time spent: {minutes} min
- If user asked clarifying questions during review: Suggest `/save` to extract new concepts and archive
- Resume anytime: `/review` continues from where you left off

## Script Reference Summary

The `/review` command uses three scripts in `scripts/review/`:

1. **scripts/review/review_loader.py** (ReviewLoader)
   - Parse arguments
   - Filter Rems by criteria
   - Group by domain
   - Sort by urgency

2. **scripts/review/review_scheduler.py** (ReviewScheduler)
   - Schedule reviews (FSRS algorithm)
   - Calculate next review dates
   - Save schedule atomically

3. **scripts/review/review_stats_lib.py** (ReviewStats)
   - **NEW: `format_timeline()`** - Comprehensive timeline (past/present/future)
   - Format review overview (date, count, time estimate)
   - Calculate session statistics
   - Format performance breakdowns

**Import pattern**: Always use `sys.path.append('scripts/review')` before importing these modules.

**Obsolete scripts** (deleted):
- ~~`get_next_review.py`~~ - Replaced by comprehensive timeline in `run_review.py`

### Special Modes

**Automatic Mode** (`/review`):
- Shows comprehensive timeline (overdue + today + next 7 days)
- Reviews all Rems due today (based on FSRS retrievability)
- If 0 Rems due today: Timeline shows when next reviews are scheduled
- Updates next_review_date using FSRS formula
- Optimizes for long-term retention

**Domain Mode** (`/review finance`):
- Shows comprehensive timeline first
- Reviews ALL Rems in domain (ignores schedule)
- Useful for pre-exam cramming
- Updates schedule for reviewed Rems
- Still provides quality feedback

**Specific Mode** (`/review [[call-option-intrinsic-value]]`):
- Shows comprehensive timeline first
- Deep dive into one Rem
- Tests from multiple angles
- Updates FSRS schedule
- Also reviews related Rems briefly

**Timeline-Only Mode** (debugging/planning):
```bash
source venv/bin/activate && python scripts/review/run_review.py --timeline
```
- Shows only the comprehensive timeline
- No review session launched
- Useful for checking schedule status without starting review

**Weak Rems Mode** (internal trigger - if user has Rems with repeated low ratings):
```
⚠️ Struggling Rems Detected

You have 3 Rems with average rating < 2:
- [[concept-a]] (avg: 1.5, difficulty: 8.2)
- [[concept-b]] (avg: 1.8, difficulty: 7.5)
- [[concept-c]] (avg: 1.9, difficulty: 6.8)

Would you like to do a focused review session on these?
```

## Notes

- Reviews are interactive conversations, not flashcards
- Rating honesty is crucial for FSRS personalization
- Keep sessions reasonably short to avoid cognitive fatigue
- Always update schedule.json after each Rem
- Log all sessions to history.json for analytics
- FSRS learns from your performance - more reviews = better scheduling
- Use `/save` after review to capture new concepts from your questions
- FSRS Algorithm Benefits: 30-50% fewer reviews, adaptive difficulty modeling (0-10 scale), personalized scheduling, memory stability tracking
- Goal: Long-term retention through scientifically optimized spaced repetition and active recall
- **Relation-Based Clustering**: Graph clustering (DFS) determines review order - related Rems review consecutively for associative learning. Relations are NOT passed to review-master; tutor focuses solely on Rem file content.
- **Question Format Adaptation**: Review-master uses 4 formats based on content type:
  - **Cloze**: Formulas, vocabulary with precise spelling (e.g., "minuscule" spelling test)
  - **Problem-Solving**: Calculations, translations, coding tasks
  - **Multiple Choice**: Recognition, initial concept discrimination
  - **Short Answer**: Conceptual understanding (default for theoretical content)
- **Format changes during review journey**: First review uses content-appropriate format (formulas→Cloze, vocab→Cloze, calculations→Problem-Solving), later reviews may switch for variety
- **Clustering Debug Tool**: Run `source venv/bin/activate && python scripts/review/debug_clustering.py` to visualize how Rems are clustered by typed relations (shows associative learning effectiveness)
- Review-master agent uses `scripts/review/review_scheduler.py` (ReviewScheduler class)
- Import pattern: `sys.path.append('scripts/review')` then `from review_scheduler import ReviewScheduler`
- Call `scheduler.schedule_review(concept, rating)` after each review
- Returns updated Rem entry with new FSRS state (difficulty, stability, retrievability, next_review)
- All dates are JSON-safe strings (YYYY-MM-DD format)
- Subagent may use Python scripts for FSRS calculations - translate results to user-friendly explanations
- Show RESULTS (memory strength, difficulty level), not PROCESS (calculation code)

## Safety & Best Practices

**Concurrent Sessions**:
- ⚠️ File locking prevents concurrent `/review` sessions
- If locked: "Schedule file is locked by another review session"
- Wait for other session to complete before starting new one

**Missing Rem Files**:
- System auto-detects and skips missing Rem files (non-fatal)
- Warning displayed: "⚠️ Warning: N Rem file(s) missing"
- Run `/maintain --fix-all` to clean up schedule.json

**Batch Limits**:
- Normal/Hard mode: Maximum 20 Rems per session (prevents token overflow)
- Easy mode: Maximum 50 Rems per session (rapid-fire allows higher throughput)
- If more available: "Batch Limit: Showing first {limit} of N Rems"
- Remaining Rems appear in next session
- Tip: Review daily to avoid accumulation (use `--easy` to catch up on backlogs)

**FSRS Parameter Changes**:
- ⚠️ Changing FSRS parameters affects scheduling accuracy
- Current parameters in `.review/schedule.json` → `default_algorithm: "fsrs"`
- If modifying parameters:
  1. Backup `.review/` directory first
  2. Document change reason and date
  3. Allow 10-20 reviews for algorithm to re-calibrate
  4. Monitor retention metrics via `/stats`
- Historical reviews remain valid (FSRS adapts incrementally)

**Data Integrity**:
- Automatic backups: `.review/backups/` (last 10 kept)
- Atomic writes prevent corruption (temp file + rename)
- If schedule.json corrupted: Restore from `.review/backups/`

**Performance Tips**:
- Review regularly (daily ideal) to prevent accumulation
- Use domain mode (`/review finance`) for targeted review
- Track progress with `/stats` to optimize learning
