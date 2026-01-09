# Build New Project

Start a full autonomous development cycle for a new project or feature.

## Arguments
$ARGUMENTS - Description of what to build

## Instructions

Activate the `build-new-project` skill and execute the full development cycle:

1. **Initialize** specs/features.json and specs/progress.md
2. **Plan** - Generate 3+ approaches, select best
3. **Architect** - Create detailed technical design
4. **Implement** - TDD implementation of all features
5. **Test** - E2E testing if applicable
6. **Fix** - Address any bugs found
7. **Simplify** - Refactor for clarity
8. **Verify** - Final quality checks

Output `<promise>CYCLE_COMPLETE</promise>` when ALL conditions are met:
- All features pass
- Test coverage >= threshold
- No unfixed bugs
- Quality checks pass

Use subagents to keep main context clean. Commit after each passing test.
