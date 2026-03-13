# hooks

Workflow enforcement hooks for Claude Code slash commands.

---

## Overview

These hooks implement a **mandatory step-by-step workflow system** for slash commands.
When a `/command` is invoked, the agent is required to track progress through a
predefined checklist using `TodoWrite`, one step at a time, in order.

---

## Hook Files

Naming convention: `{event}-{function}.{ext}` — prefix maps to Claude Code hook event.

| File | Event | Trigger | Role |
|------|-------|---------|------|
| `session-info.sh` | SessionStart | Session open | Display env info, git status, and tool quick reference |
| `session-git-init.sh` | SessionStart | Session open | Auto-initialize git repo if missing |
| `prompt-workflow.py` | UserPromptSubmit | Every user message | Phase A: inject checklist on `/cmd`. Phase B: inject progress reminder. |
| `pretool-workflow-gate.py` | PreToolUse | Before every tool call | Block all tools (except `TodoWrite`/`ToolSearch`) until workflow is acknowledged |
| `pretool-bash-safety.sh` | PreToolUse (Bash) | Before Bash calls | Block/warn on dangerous commands (rm -rf, force push, secret file writes) |
| `posttool-todo-tracker.py` | PostToolUse (TodoWrite) | After every `TodoWrite` | Persist valid todo state to todos file |
| `posttool-todo-count.py` | PostToolUse (TodoWrite) | After every `TodoWrite` | Block if step count doesn't match canonical list |
| `posttool-todo-sequence.py` | PostToolUse (TodoWrite) | After every `TodoWrite` | Block if steps skipped, reordered, or multiple completed at once |
| `posttool-git-checkpoint.sh` | PostToolUse (Write/Edit) | After file writes | Auto-commit when 10+ files accumulated |
| `posttool-git-warn.sh` | PostToolUse (git commit) | After git commits | Warn if untracked files remain after commit |
| `stop-workflow-enforce.py` | Stop | Session end | Block session stop if workflow incomplete |
| `stop-git-commit.sh` | Stop | Session end | Auto-commit and push all pending changes |

---

## State Machine

All state is stored in two files per session:

**Todos file** (official progress):
```
~/.claude/todos/{session_id}-agent-{session_id}.json
```

**Bookmark file** (lock state + metadata):
```
.claude/workflow-{session_id}.json
```

### Bookmark fields

| Field | Type | Description |
|-------|------|-------------|
| `command` | string | Slash command name (e.g. `"dev"`) |
| `todo_acknowledged` | bool | True after first successful `TodoWrite` call |
| `lock_reason` | string | `""` (unlocked) / `"sequence_violation"` / `"count_mismatch"` |
| `last_todos` | list | Pre-violation todo state (baseline for sequence fix hints) |

### Lock/unlock rules

- **Lock set**: PostToolUse hooks write `lock_reason` + `todo_acknowledged=False` when a violation is detected
- **Lock cleared**: PreToolUse hook clears `lock_reason` on every `TodoWrite` call (before PostToolUse re-evaluates)
- **Always allowed**: `TodoWrite` (to fix violations) and `ToolSearch` (to load tool schemas)
- **No deadlock possible**: agent can always recover via `TodoWrite` or look up schemas via `ToolSearch`

---

## 8 Workflow Scenarios

---

### Scenario 1 — Happy Path

Agent follows the workflow correctly, one step at a time.

```
User: /mycommand

[UserPromptSubmit hook]
  Phase A: writes todos file (N pending steps)
           writes bookmark: {command, todo_acknowledged: false}
           prints: "CHECKLIST PRE-INITIALIZED" + first TodoWrite JSON

Agent: TodoWrite([step1=in_progress, step2..N=pending])

[PreToolUse] tool=TodoWrite -> sets todo_acknowledged=true, clears lock_reason -> allow
[PostToolUse count] N steps passed, N expected -> allow
[PostToolUse sequence] first call, saves baseline to last_todos -> allow

Agent: (does step 1 work)

Agent: TodoWrite([step1=completed, step2=in_progress, step3..N=pending])

[PostToolUse sequence] 1 newly completed, step1 was in_progress -> valid -> allow

... repeat until all steps completed ...

[Stop hook] all steps completed -> allow session end
```

---

### Scenario 2 — Not Started (agent ignores checklist)

Agent tries to use other tools before calling `TodoWrite`.

```
User: /mycommand

[Phase A] prints checklist + first TodoWrite JSON

Agent: Read("some-file.txt")   <- ignores checklist

[PreToolUse]
  bookmark exists, todo_acknowledged=false, no lock_reason
  EXIT 2 (block)
  stderr: "CHECKLIST NOT STARTED: /mycommand workflow is active.
           Call TodoWrite to initialize the checklist before using other tools.
           Call TodoWrite with this exact todos array: [...]"

Agent must call TodoWrite before any other tool is allowed.
```

---

### Scenario 3 — Template Hidden After First Acknowledgment

JSON template is shown only until the agent has successfully called `TodoWrite` once.

```
User: /mycommand

[Phase A] todo_acknowledged=false -> prints full JSON template

Agent: TodoWrite([step1=in_progress, ...])
  -> todo_acknowledged set to true

User: (sends follow-up message)

[Phase B]
  todo_acknowledged=true
  prints: "ACTIVE WORKFLOW: 0/N steps completed. Currently in_progress: Step 1"
  NO JSON template (agent already knows how to call TodoWrite)
```

Once acknowledged, Phase B shows only a progress summary — not the full JSON hint.
This prevents repetitive boilerplate in long sessions.

---

### Scenario 4 — Count Mismatch on First Call

Agent calls `TodoWrite` with fewer steps than the canonical list requires.

```
User: /mycommand  (canonical: 5 steps)

Agent: TodoWrite([step1, step2])  <- only 2 steps

[PostToolUse count]
  2 != 5 -> VIOLATION
  sets lock_reason="count_mismatch", todo_acknowledged=false
  stderr: "TODO COUNT MISMATCH: /mycommand requires 5 steps but TodoWrite called with 2."

[todos file NOT written] (tracker skips bad-count writes)

[Phase B on next user message]
  lock_reason="count_mismatch"
  fetches canonical list from todo script (todos file doesn't exist yet)
  prints: "WORKFLOW LOCKED (count_mismatch): ...
           Call TodoWrite with ALL 5 canonical steps: [...]"

[PreToolUse on next non-TodoWrite tool]
  lock_reason set -> blocks all tools
  hint uses canonical script output -> shows full correct step list
```

---

### Scenario 5 — Count Mismatch Mid-Progress

Agent has completed some steps correctly, then calls `TodoWrite` with wrong count.

```
User: /mycommand  (canonical: 5 steps)

Agent: TodoWrite([1=in_progress, 2,3,4,5=pending])    <- correct, saved
Agent: TodoWrite([1=completed, 2=in_progress, 3,4,5=pending])  <- correct, saved

Agent: TodoWrite([1=completed, 2=completed])   <- only 2 steps!

[PostToolUse count]
  2 != 5 -> VIOLATION
  sets lock_reason="count_mismatch"

[todos file] still holds last VALID state: [1=completed, 2=in_progress, 3,4,5=pending]
(tracker only writes valid-count calls)

[Phase B on next user message]
  lock_reason="count_mismatch"
  reads todos file (exists, has valid state)
  prints: "WORKFLOW LOCKED (count_mismatch):
           Call TodoWrite with ALL 5 steps: [1=completed, 2=in_progress, 3,4,5=pending]"

Agent recovers by re-submitting all 5 steps with preserved progress.
```

---

### Scenario 6 — Sequence Violation

Agent tries to skip a step, complete multiple steps at once, or reorder steps.

```
User: /mycommand

Agent: TodoWrite([1=in_progress, 2,3,4,5=pending])
  <- valid; baseline saved to bookmark.last_todos

Agent: (does step 1 work)

Agent: TodoWrite([1=completed, 2=completed, 3=in_progress, 4,5=pending])
  <- tries to complete 2 steps at once!

[PostToolUse sequence]
  newly_completed = {1, 2} -> len > 1 -> VIOLATION
  fresh-reads bookmark (handles race with concurrent tracker hook)
  sets: todo_acknowledged=false, lock_reason="sequence_violation"
  last_todos stays as pre-violation baseline: [1=in_progress, 2..5=pending]
  stderr: "STEP SEQUENCE VIOLATION: Completed 2 steps in one call (max 1)"

[Phase B on next user message]
  lock_reason="sequence_violation"
  reads last_todos from bookmark (pre-violation state)
  computes fix: step1=completed, step2=in_progress
  prints: "WORKFLOW LOCKED (sequence_violation):
           complete 'Step 1' first, then advance ONE step at a time.
           Call TodoWrite with this exact todos array:
           [1=completed, 2=in_progress, 3,4,5=pending]"

[PreToolUse on next non-TodoWrite tool]
  lock_reason set -> blocks
  hint uses build_sequence_fix_call(last_todos) -> correct recovery JSON

Agent must call TodoWrite with the fix JSON to unlock.
```

**Why `last_todos` instead of the todos file?**
PostToolUse hooks may run concurrently. The tracker hook may write the violating state
to the todos file before the sequence hook detects it. `last_todos` in the bookmark
always holds the last *valid* baseline, so hints always show the correct recovery
state — not the violating one.

---

### Scenario 7 — Phase B Resume After New User Message

User sends a new message mid-workflow; agent must resume where it left off.

```
User: /mycommand

Agent: TodoWrite([1=in_progress, 2,3=pending])  <- step 1 in progress

User: "also please add X"

[Phase B — UserPromptSubmit hook]
  todos file exists, not all completed
  todo_acknowledged=true, no lock_reason
  prints: "ACTIVE WORKFLOW: 0/3 steps completed.
           Currently in_progress: Step 1
           Complete the work above, THEN call TodoWrite — copy the JSON below EXACTLY:
           [1=completed, 2=in_progress, 3=pending]"
```

The progress reminder keeps the agent on track even after interruptions or new instructions.

---

### Scenario 8 — Agent Confused About TodoWrite Format

Agent calls `TodoWrite` with wrong parameter type (e.g., `todos` passed as a JSON string
instead of an array). Claude Code schema validation fires *before* any hooks run.

```
Agent: TodoWrite(todos='[{"content":"...","status":"pending"}]')
  <- todos is a string, not an array

[Claude Code schema validation]
  InputValidationError: "todos type is expected as array but provided as string"
  hooks never triggered (schema validation fires first)

[Phase A output — always includes schema reminder]
  "TodoWrite usage: TodoWrite(todos=[...]) — todos MUST be a JSON array (not a string)."
  "Each item: {"content": "...", "activeForm": "...", "status": "pending|in_progress|completed"}"

[All block messages — include ToolSearch escape hatch]
  "(If you need the TodoWrite parameter schema, use ToolSearch — it is always allowed.)"

Recovery path:
  1. Agent uses ToolSearch to load the TodoWrite schema
  2. Agent calls TodoWrite correctly with array argument
```

`ToolSearch` is the designated escape hatch — it is *always* allowed through PreToolUse
(special-cased, does not set `todo_acknowledged`), so a confused agent can always
self-recover without manual intervention.

---

## Sequence Rules (enforced by posttool-todo-sequence.py)

| Rule | Description |
|------|-------------|
| Max 1 newly completed per call | Cannot mark 2+ steps as completed in a single `TodoWrite` |
| No pending to completed | Each step must pass through `in_progress` before `completed` |
| Max 1 in_progress at a time | Cannot have two steps simultaneously in_progress |
| Steps completed in order | Cannot start step N if any earlier step is still pending |

---

## Directory Structure

```
hooks/
├── README.md                          <- this file (synced to every project)
│
├── session-info.sh                    <- SessionStart: env info + tool quick reference
├── session-git-init.sh                <- SessionStart: auto-init git repo
│
├── prompt-workflow.py                 <- UserPromptSubmit: Phase A/B checklist injection
│
├── pretool-workflow-gate.py           <- PreToolUse(*): workflow gate / lock enforcement
├── pretool-bash-safety.sh             <- PreToolUse(Bash): dangerous command guard
│
├── posttool-todo-tracker.py           <- PostToolUse(TodoWrite): persist todo state
├── posttool-todo-count.py             <- PostToolUse(TodoWrite): validate step count
├── posttool-todo-sequence.py          <- PostToolUse(TodoWrite): validate step order
├── posttool-git-checkpoint.sh         <- PostToolUse(Write/Edit): auto-checkpoint commit
├── posttool-git-warn.sh               <- PostToolUse(git commit): warn untracked files
│
├── stop-workflow-enforce.py           <- Stop: block if workflow incomplete
├── stop-git-commit.sh                 <- Stop: auto-commit + push all changes
│
└── git-hooks/                         <- git-level hooks (pre-commit, post-commit)
```

### Deployment

- `~/.claude/hooks/` — global source (kept in sync, **not registered**)
- Each project's `.claude/hooks/` — local copy, registered via `$CLAUDE_PROJECT_DIR/.claude/hooks/`

To sync a single project after updating global hooks:
```bash
cp ~/.claude/hooks/session-info.sh          .claude/hooks/
cp ~/.claude/hooks/prompt-workflow.py       .claude/hooks/
# ... etc for each file
```

---

## Todo Script Convention

Each slash command using this system must have a corresponding todo script:

```
scripts/todo/<command>.py            (project-level)
~/.claude/scripts/todo/<command>.py  (global fallback)
```

The script prints a JSON array of step objects to stdout:

```python
#!/usr/bin/env python3
import json

steps = [
    {"content": "Step 1: Do X", "activeForm": "Step 1: Doing X", "status": "pending"},
    {"content": "Step 2: Do Y", "activeForm": "Step 2: Doing Y", "status": "pending"},
]
print(json.dumps(steps, ensure_ascii=False))
```

The count hook compares `len(TodoWrite.todos)` against `len(script_output)` on every call.

---

*Last updated: 2026-03-12 — hooks renamed to session/prompt/pretool/posttool/stop- prefix scheme*
