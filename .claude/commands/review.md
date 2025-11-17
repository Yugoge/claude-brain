---
description: "Interactive review session using spaced repetition (FSRS algorithm)"
allowed-tools: Read, Bash, Task, TodoWrite
argument-hint: "[domain | [[rem-id]]]"
---

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

```bash
source venv/bin/activate && python scripts/review/run_review.py [args]
```

This script now ALWAYS shows a comprehensive timeline first:
- **PAST (Overdue)**: All overdue reviews with days overdue
- **TODAY**: Reviews due today
- **FUTURE (Next 7 days)**: Upcoming reviews with domain breakdown
- **Summary**: Total counts, time estimates

Then displays filtered review session and outputs JSON data for next steps.

**Timeline-only mode** (skip review session):
```bash
source venv/bin/activate && python scripts/review/run_review.py --timeline
```

**Custom lookahead** (show next 14 days instead of 7):
```bash
source venv/bin/activate && python scripts/review/run_review.py --days 14
```

**Note**: Path resolution prefers `.md` and falls back to `.rem.md` when content still uses the legacy extension.

### Step 2: Conduct Review Session (Main Agent Dialogue Loop)

**ARCHITECTURE**: Main agent (you) conducts the review dialogue directly with the user. Review-master is a **consultant agent** that provides JSON guidance.

**For each Rem in the session, follow this loop**:

#### 2.1 Consult Review-Master for Guidance

```
Use Task tool:
- subagent_type: "review-master"
- model: "haiku"  # Fast model for JSON consultation
- description: "Get Socratic question guidance for Rem {N}/{total}"
- prompt: "
  You are a consultant providing JSON guidance for FSRS review.

  Review this Rem and provide Socratic question guidance:

  {
    \"rem_data\": {
      \"id\": \"{rem_id}\",
      \"title\": \"{rem_title}\",
      \"path\": \"{full_path_to_rem_file}\",
      \"domain\": \"{domain}\",
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
      \"mode\": \"{mode}\"
    }
  }

  Return JSON guidance as specified in your instructions.
  "
```

**Review-master returns**:
```json
{
  "review_guidance": {
    "rem_id": "...",
    "socratic_question": {
      "primary_question": "...",
      "expected_concepts": [...],
      "hints_if_struggling": [...]
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

#### 2.2 Present Question to User (First-Person Voice)

**Parse JSON guidance and ask question naturally**:

```
Let's review: {rem_title}

{context_scenario if provided}

{primary_question from JSON}
```

**Voice Guidelines**:
- ✅ Direct first-person: "Let me test your understanding..."
- ✅ Natural teaching tone: "Can you explain..."
- ❌ Never third-person: "The review-master asks..."
- ❌ No meta-commentary: "I'm consulting the agent..."

#### 2.3 Listen to User Response

Wait for user to answer the question.

#### 2.4 Evaluate Response Quality

**Compare user response to quality_assessment_guide from JSON**:

- Check if user mentioned expected_concepts
- Assess recall speed and accuracy
- Note if hints were needed

**Observe quality indicators**:
- Rating 4: Matches rating_4_indicators from JSON
- Rating 3: Matches rating_3_indicators from JSON
- Rating 2: Matches rating_2_indicators from JSON
- Rating 1: Matches rating_1_indicators from JSON

#### 2.5 Provide Feedback and Ask for Self-Rating

**If response is strong** (Quality 3-4):
```
{Positive feedback}

{Optional: Ask follow_up_if_strong question from JSON}

How would you rate your recall? (1-4)
1 = Again (forgot), 2 = Hard (struggled), 3 = Good (recalled with thought), 4 = Easy (instant)
```

**If response is weak** (Quality 1-2):
```
{Encouraging feedback}

{Provide first hint from hints_if_struggling array}

[If still struggling, provide additional hints]

How would you rate your recall? (1-4)
```

**User Self-Rating**: User provides rating (1-4)

**If user disputes your assessment**: Accept their rating (FSRS adapts to user feedback)

#### 2.6 Update FSRS Schedule

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
- Rating 2: "You got it with effort. Keep practicing."
- Rating 3: "🎉 Good retention! Perfect difficulty level."
- Rating 4: "Too easy! I'll make it harder next time."

#### 2.7 Move to Next Rem

**Progress indicator**:
```
[{N}/{total}] {N} reviewed, {remaining} remaining
```

**Repeat steps 2.1-2.7 for all Rems in session.**

**Early Exit Handling**:
- If user stops early (e.g., "stop", "enough"), break loop
- Show partial session summary (see Step 3)
- Save progress - already-reviewed Rems have updated schedules

---

### Step 3: Post-Session Summary

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
- Sessions should be 15-20 Rems maximum (avoid fatigue)
- Always update schedule.json after each Rem
- Log all sessions to history.json for analytics
- FSRS learns from your performance - more reviews = better scheduling
- Use `/save` after review to capture new concepts from your questions
- FSRS Algorithm Benefits: 30-50% fewer reviews, adaptive difficulty modeling (0-10 scale), personalized scheduling, memory stability tracking
- Goal: Long-term retention through scientifically optimized spaced repetition and active recall
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
