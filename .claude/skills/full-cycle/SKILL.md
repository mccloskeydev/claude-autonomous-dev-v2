---
name: full-cycle
description: |
  Run complete development cycle on a single feature. Use when: "full cycle", "complete feature",
  "end-to-end implementation". Runs: plan → architect → implement → test → fix → simplify.
allowed-tools:
  - Task
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - TodoWrite
---

# Full Development Cycle

Execute all development phases for a single feature.

## Input
`$ARGUMENTS` - Feature description

## Cycle Overview

```
   ┌─────────────────────────────────────────────────────────┐
   │                    FULL CYCLE                            │
   │                                                          │
   │  ┌────────┐   ┌───────────┐   ┌───────────┐            │
   │  │  PLAN  │ → │ ARCHITECT │ → │ IMPLEMENT │            │
   │  └────────┘   └───────────┘   └─────┬─────┘            │
   │                                      │                   │
   │                                      ▼                   │
   │  ┌──────────┐   ┌──────┐   ┌────────────┐              │
   │  │ SIMPLIFY │ ← │ FIX  │ ← │ TEST (E2E) │              │
   │  └────┬─────┘   └──────┘   └────────────┘              │
   │       │                                                  │
   │       ▼                                                  │
   │  ┌──────────┐                                           │
   │  │ COMPLETE │                                           │
   │  └──────────┘                                           │
   └─────────────────────────────────────────────────────────┘
```

## Process

### Phase 1: Planning
**Skill:** plan-alternatives
**Goal:** Generate approaches, select best

```
Spawn subagent: plan-alternatives
Input: "$ARGUMENTS"
Output: specs/plan.md
```

Wait for completion, then verify specs/plan.md exists.

### Phase 2: Architecture
**Skill:** architect
**Goal:** Detailed technical design

```
Spawn subagent: architect
Input: "Create architecture for: $ARGUMENTS"
Output: specs/architecture.md, specs/features.json
```

Wait for completion, verify both files exist.

### Phase 3: Implementation
**Skill:** implement-tdd
**Goal:** TDD implementation of all features

For each feature in specs/features.json where passes == false:

```
Spawn subagent: implement-tdd
Input: "Implement feature: {feature.description}"
Output: Code + tests committed
```

After each subagent completes:
- Verify git commit was made
- Update specs/features.json if not already updated
- Log to specs/progress.md

### Phase 4: E2E Testing (if applicable)
**Skill:** test-e2e
**Goal:** Browser-based verification

If project has web interface:

```
Spawn subagent: test-e2e
Input: "Test feature: $ARGUMENTS"
Output: specs/e2e-results.md
```

### Phase 5: Bug Fixing
**Skill:** evaluate-fix
**Goal:** Fix any discovered bugs

If specs/bugs.md has entries with status != FIXED:

```
For each unfixed bug:
    Spawn subagent: evaluate-fix
    Input: "Fix bug: {bug.title}"
```

### Phase 6: Simplification
**Skill:** simplify
**Goal:** Clean up the implementation

```
Spawn subagent: simplify
Input: "Simplify: files changed for $ARGUMENTS"
```

### Phase 7: Final Verification

Run all checks:

```bash
# Tests
pytest -v

# Type checking
pyright

# Linting
ruff check .

# Coverage
pytest --cov --cov-fail-under=80
```

### Completion

Update specs/progress.md:

```markdown
## Feature Complete: $ARGUMENTS

**Completed:** [timestamp]

### Summary
- Plan: specs/plan.md
- Architecture: specs/architecture.md
- Features implemented: X
- Tests added: Y
- Bugs fixed: Z
- Final coverage: XX%

### Commits
- abc123: Initial implementation
- def456: Add tests
- ghi789: Fix edge case
- jkl012: Simplify
```

Output: `<promise>CYCLE_COMPLETE</promise>`

## Iteration Handling

If tests fail after implementation:
1. Log failure to specs/bugs.md
2. Continue to Phase 5 (Fix)
3. Return to Phase 4 (E2E) after fixes
4. Maximum 3 fix iterations before flagging for manual review

## Time Estimates

| Phase | Typical Duration |
|-------|------------------|
| Plan | 2-5 minutes |
| Architect | 5-10 minutes |
| Implement | 10-30 minutes per feature |
| E2E Test | 5-10 minutes |
| Fix | 5-15 minutes per bug |
| Simplify | 5-10 minutes |

Total: 30-90 minutes for typical feature

## Output

1. Complete, tested feature implementation
2. Documentation in specs/
3. All tests passing
4. Clean, simplified code
5. Git history with clear commits
