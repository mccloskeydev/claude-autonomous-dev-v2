---
name: build-new-project
description: |
  Main orchestrator for autonomous long-running development. Use when starting a new project
  or feature from scratch. Triggers: "build", "create project", "new project", "implement from scratch".
  Runs full cycle: plan alternatives → architect → TDD implement → test → fix → simplify → iterate.
allowed-tools:
  - Task
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - TodoWrite
  - mcp__puppeteer__puppeteer_navigate
  - mcp__puppeteer__puppeteer_screenshot
---

# Build New Project - Autonomous Development Orchestrator

You are orchestrating a **long-running autonomous development session**. Your goal is to fully implement the requested feature/project through iterative refinement.

## Input
The user provides: `$ARGUMENTS` - A description of what to build.

## Phase 0: Initialize

1. **Create specs/features.json** if it doesn't exist:
```json
{
  "project": "$ARGUMENTS",
  "created": "<timestamp>",
  "features": []
}
```

2. **Create specs/progress.md** for session logging:
```markdown
# Development Progress

## Project: $ARGUMENTS
Started: <timestamp>

---
```

3. **Read project.config.json** to determine stack and commands.

## Phase 1: Planning (Use /project:plan)

Spawn a subagent with the `plan-alternatives` skill:

```
Task: Plan implementation for "$ARGUMENTS"

Generate 3+ distinct approaches. For each:
- Architecture overview
- Pros and cons
- Complexity estimate
- Risk assessment

Select the best approach with clear rationale.
Save to specs/plan.md
```

Wait for subagent completion. Read specs/plan.md.

## Phase 2: Architecture (Use /project:architect)

Spawn a subagent with the `architect` skill:

```
Task: Create detailed architecture for the selected plan.

Based on specs/plan.md, produce:
- File structure with all files to create/modify
- Interface definitions (types, protocols, contracts)
- Data flow diagrams (as mermaid)
- Dependencies list
- Test strategy

Save to specs/architecture.md
Add all features to specs/features.json with passes: false
```

Wait for subagent completion. Read specs/architecture.md.

## Phase 3: Implementation Loop (TDD)

For each feature in specs/features.json where passes == false:

1. **Spawn implement-tdd subagent**:
```
Task: Implement feature: "<feature description>"

Follow TDD:
1. Write failing test first
2. Implement minimum code to pass
3. Run tests
4. If failing, debug and fix
5. Commit with descriptive message
6. Update specs/features.json: set passes: true
```

2. **After each feature**, verify with test-e2e if it's user-facing.

3. **Track progress** in specs/progress.md.

## Phase 4: Evaluation

After implementing core features:

1. Run full test suite
2. Run type checker
3. Run linter
4. If web app, run E2E tests with Puppeteer
5. Document any failures in specs/bugs.md

## Phase 5: Bug Fixing

For each bug in specs/bugs.md:

1. **Spawn evaluate-fix subagent**:
```
Task: Fix bug: "<bug description>"

1. Reproduce the issue
2. Identify root cause
3. Write regression test
4. Fix the code
5. Verify test passes
6. Commit fix
```

## Phase 6: Simplification

After all tests pass:

1. **Spawn simplify subagent**:
```
Task: Simplify and refactor the codebase

1. Remove dead code
2. Reduce complexity
3. Improve naming
4. Add minimal documentation
5. Ensure tests still pass
```

## Phase 7: Final Verification

1. Run all tests with coverage
2. Run E2E tests if applicable
3. Verify all features in specs/features.json have passes: true
4. Update specs/progress.md with completion summary

## Completion Criteria

Output `<promise>CYCLE_COMPLETE</promise>` when ALL conditions are met:
- All features in specs/features.json have passes: true
- Test coverage >= threshold from project.config.json
- No known bugs in specs/bugs.md (or all fixed)
- Linter passes
- Type checker passes

## If Blocked

After 3 failed attempts at the same issue:
1. Document the blocker in specs/blockers.md
2. Move to next feature
3. Return to blocker later with fresh context

After 10 iterations without progress:
1. Run /project:checkpoint to save state
2. Output summary of what's complete vs blocked
3. Request human intervention

## Remember

- **Commit frequently** - Each passing test = commit
- **Use subagents** - Keep main context clean
- **Update features.json** - This drives the loop
- **Log everything** - specs/progress.md is your memory
