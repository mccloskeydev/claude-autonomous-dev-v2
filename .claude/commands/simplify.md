# Simplify

Refactor code for clarity while maintaining tests.

## Arguments
$ARGUMENTS - File/module to simplify, or "all" for full codebase

## Instructions

Activate the `simplify` skill:

1. Run tests first (must all pass)
2. Identify targets: dead code, duplication, complexity, naming
3. Make one change at a time
4. Run tests after each change
5. If tests pass, commit
6. If tests fail, revert immediately

Do NOT change behavior. Do NOT add features.
