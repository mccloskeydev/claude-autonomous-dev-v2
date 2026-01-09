---
name: checkpoint
description: |
  Save session state for handoff or recovery. Use when: "checkpoint", "save state", "handoff",
  "about to compact", "preserve context". Creates structured handoff document for session continuity.
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
---

# Checkpoint

Save current session state for handoff or recovery.

## Input
`$ARGUMENTS` - Optional: reason for checkpoint (e.g., "before refactor", "end of day")

## When to Checkpoint

- Before context compaction (/compact)
- Before /clear
- At natural breakpoints
- When switching tasks
- End of work session
- Before risky operations

## Process

### Step 1: Gather State

Collect all relevant context:

```bash
# Git status
git status --short

# Recent commits
git log --oneline -10

# Modified files
git diff --name-only

# Staged files
git diff --cached --name-only
```

### Step 2: Read Progress Files

- specs/features.json (feature status)
- specs/progress.md (session log)
- specs/bugs.md (outstanding issues)
- specs/plan.md (current plan)

### Step 3: Create Handoff Document

Write to `specs/checkpoint-{timestamp}.md`:

```markdown
# Session Checkpoint

**Created:** 2026-01-09T12:00:00Z
**Reason:** $ARGUMENTS

## Current State

### Active Task
[What was being worked on]

### Progress Summary
- Completed: X features
- In Progress: Y features
- Blocked: Z features

### Recent Decisions
1. Decision and rationale
2. Decision and rationale

## Git State

### Uncommitted Changes
```
file1.py - modified
file2.py - new file
```

### Recent Commits
```
abc1234 feat: implement user login
def5678 test: add login tests
```

## Outstanding Items

### Bugs (Unfixed)
- Bug 1: description
- Bug 2: description

### TODOs
- [ ] Task 1
- [ ] Task 2

### Blockers
- Blocker 1: reason and attempted solutions

## Context for Next Session

### What to Do Next
1. Immediate next step
2. Following step

### Important Notes
- Note about implementation detail
- Note about edge case discovered

### Files to Review
- src/important.py - contains main logic
- tests/test_important.py - tests for above

## How to Resume

1. Read this checkpoint file
2. Review specs/features.json for status
3. Run `git status` to see any uncommitted work
4. Run tests: `pytest -v`
5. Continue from "What to Do Next"
```

### Step 4: Commit Checkpoint

```bash
git add specs/checkpoint-*.md
git commit -m "checkpoint: save session state

Reason: $ARGUMENTS
Features completed: X
In progress: Y
"
```

### Step 5: Update Progress

Add to specs/progress.md:

```markdown
---

## Checkpoint: [timestamp]

**Reason:** $ARGUMENTS
**File:** specs/checkpoint-{timestamp}.md

Next session should start by reading the checkpoint file.
```

## Resume Command

To resume from checkpoint, create `/project:resume` that:

1. Finds most recent checkpoint file
2. Reads and summarizes state
3. Continues from "What to Do Next"

## Automatic Checkpoints

The quality-gate hook creates mini-checkpoints in specs/progress.md after each iteration. Full checkpoints should be created:

- Every 10 iterations
- Before major phase transitions
- When context usage > 70%

## Output

1. Checkpoint file in specs/
2. Git commit with checkpoint
3. Updated progress log
4. Summary of saved state
