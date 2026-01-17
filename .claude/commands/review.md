---
description: "Interactive review session using spaced repetition (FSRS algorithm)"
allowed-tools: Read, Bash, Task, TodoWrite
argument-hint: "[domain | [[rem-id]]]"
---

**⚠️ CRITICAL**: Use TodoWrite to track workflow phases. Mark in_progress before each phase, completed immediately after.

# Review Command

Start an interactive review session using spaced repetition (FSRS algorithm).





### Step 0: Initialize Workflow Checklist

**Load todos from**: `scripts/todo/review.py`

Execute via venv:
```bash
source venv/bin/activate && python scripts/todo/review.py
```

Use output to create TodoWrite with all workflow steps.

**Rules**: Mark `in_progress` before each step, `completed` after. NEVER skip steps.

---


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

```bash
source venv/bin/activate && python scripts/review/run_review.py [args]
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

**Combined parameters**:
```bash
source venv/bin/activate && python scripts/review/run_review.py --format m --lang zh finance
```

**Note**: Path resolution prefers `.md` and falls back to `.rem.md` when content still uses the legacy extension.

### Step 2: Read Rem File Content

**⚠️ CRITICAL**: Always read Rem file before consulting review-master or asking questions.

**For each Rem in session**:

```
Use Read tool: {rem_path_from_run_review_json}
```

**Parse and validate**:
- Frontmatter: `rem_id`, `title`, `domain`, `created`, **`source`** (conversation path)
- Content sections: Core Memory Points, Usage Scenario, Related Rems
- Check for missing/incomplete content

**Extract conversation path** (commit 893dffd enhancement):
```
If Rem frontmatter contains 'source' field:
  conversation_source = frontmatter['source']
Else:
  conversation_source = null
```

**Purpose**: Verify Rem content before generating questions. Ensures questions align with actual knowledge structure, not just JSON guidance assumptions. Conversation source provides original learning context for review-master.

**Integration**: Pass Rem content AND conversation_source to review-master for context-aware question generation (Step 4).

---

### Step 3: Conduct Review Session (Main Agent Dialogue Loop)

**⚠️ CRITICAL**: This is the core FSRS review workflow. Poor questioning = inaccurate self-ratings = suboptimal scheduling.

**ARCHITECTURE**: Main agent (you) conducts the review dialogue directly with the user. Review-master is a **consultant agent** that provides JSON guidance.

**Session Setup** (before first Rem):
```
Load session tracking from run_review.py JSON output:
  format_history = data['format_history']  // Loaded from .review/format_history.json
  session_rem_ids = []  // Track Rems reviewed (for logging)
```

**Note**: format_history is populated by run_review.py from persistent state file. This fixes the stateless architecture issue introduced in commit 3ed6b6f.

**For each Rem in the session, follow this loop**:

#### 4. Consult Review-Master for Guidance

**Fallback strategy**:
- If review-master unavailable → Ask direct recall question: "What do you remember about {Rem title}?"
- If JSON invalid → Use minimal guidance (ask for free recall, no hints)
- If consultation fails → Proceed with basic review (show Rem content after user attempts recall)

```
Use Task tool:
- subagent_type: "review-master"
- model: "haiku"  # Fast model for JSON consultation
- description: "Get Socratic question guidance for Rem {N}/{total}"
- prompt: "
  You are a consultant providing JSON guidance for FSRS review.

  Review this Rem and provide Socratic question guidance:

  **IMPORTANT INSTRUCTION**:
  - Check format_preference field FIRST
  - If format_preference is NOT null → Use that format exclusively, ignore all diversity/variety logic
  - If format_preference is null → Use adaptive format selection with variety

  {
    \"rem_data\": {
      \"id\": \"{rem_id}\",
      \"title\": \"{rem_title}\",
      \"path\": \"{full_path_to_rem_file}\",
      \"domain\": \"{domain}\",
      \"conversation_source\": \"{conversation_source or null}\",
      \"fsrs_state\": {
        \"difficulty\": {difficulty},
        \"stability\": {stability},
        \"retrievability\": {retrievability},
        \"review_count\": {review_count}
      }
    },
    \"session_context\": {
      \"total_rems\": {total},
      \"current_index\": {N},
      \"mode\": \"{mode}\",
      \"consultation_type\": \"question\",
      \"format_preference\": \"{format_preference from run_review.py JSON or null}\",
      \"lang_preference\": \"{lang_preference from run_review.py JSON or null}\"
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

  Use lang_preference if provided:
  - If lang_preference is not null, generate ALL dialogue in that language
  - Language codes: 'zh'=Chinese, 'en'=English, 'fr'=French
  - Applies to primary_question, hints, follow_ups, context_scenario
  - Rem content (Core Memory Points) remains unchanged

  Return JSON guidance as specified in your instructions.
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

#### 5. Present Question to User (First-Person Voice)

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

#### 6. Listen to User Response

Wait for user to answer the question.

#### 7. Evaluate Response Quality

**Compare user response to quality_assessment_guide from JSON**:

- Check if user mentioned expected_concepts
- Assess recall speed and accuracy
- Note if hints were needed

**Observe quality indicators**:
- Rating 4: Matches rating_4_indicators from JSON
- Rating 3: Matches rating_3_indicators from JSON
- Rating 2: Matches rating_2_indicators from JSON
- Rating 1: Matches rating_1_indicators from JSON

#### 8. Confusion Detection & Explanation Loop (Commit 893dffd Enhancement)

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
  - model: "haiku"
  - description: "Get explanation for confused user"
  - prompt: "
    You are a consultant providing explanation guidance.

    User is confused during review. Provide re-teaching guidance.

    {
      \"rem_data\": {
        \"id\": \"{rem_id}\",
        \"title\": \"{rem_title}\",
        \"path\": \"{full_path_to_rem_file}\",
        \"conversation_source\": \"{conversation_source or null}\",
        \"domain\": \"{domain}\",
        \"fsrs_state\": {...}
      },
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

**After successful explanation loop**: Proceed to Step 9 (rating) with the final answer quality.

**If no confusion detected**: Skip explanation loop, proceed directly to Step 9.

#### 9. Provide Feedback and Ask for Self-Rating

**⚠️ CRITICAL - Hints Display Logic** (Root Cause Fix: commit 3ed6b6f):

**NEVER show hints_if_struggling in correct-answer feedback**:
- Hints are ONLY for struggling users (Quality 1-2)
- Showing hints after correct answers reduces difficulty artificially
- User complained: "你给我提示了哥" (You gave me hints, bro)

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
- model: "haiku"
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

#### 10. Update FSRS Schedule

**⚠️ CRITICAL**: Incorrect schedule updates = broken FSRS algorithm = review intervals too long/short.

**CRITICAL**: Immediately update schedule after rating:

```bash
source venv/bin/activate && python scripts/review/update_review.py {rem_id} {user_rating}
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

#### 11. Move to Next Rem

**Progress indicator**:
```
[{N}/{total}] {N} reviewed, {remaining} remaining
```

**Repeat steps 4-11 for all Rems in session.**

**Early Exit Handling**:
- If user stops early (e.g., "stop", "enough"), break loop
- Show partial session summary (see Step 4)
- Save progress - already-reviewed Rems have updated schedules

---

### Step 4: Post-Session Summary

After all Rems reviewed (or early exit):

**Early Exit Handling** (if user interrupts before completing all Rems):
- Save progress to `.review/history.json`
- Update schedule for already-reviewed Rems
- Show partial session summary:
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
- Maximum 20 Rems per session (prevents token overflow)
- If more available: "📊 Batch Limit: Showing first 20 of N Rems"
- Remaining Rems appear in next session
- Tip: Review daily to avoid accumulation

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
