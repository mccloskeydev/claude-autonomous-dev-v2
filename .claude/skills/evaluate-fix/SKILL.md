---
name: evaluate-fix
description: |
  Evaluate bugs and fix them systematically. Use when: "fix bug", "debug", "evaluate",
  "investigate issue", "fix failing test". Identifies root cause, writes regression test, fixes code.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Evaluate and Fix

Systematically investigate and fix bugs.

## Input
`$ARGUMENTS` - Bug description, issue ID, or "all" to process specs/bugs.md

## Process

### Step 1: Understand the Bug

Read available information:
- specs/bugs.md for bug details
- specs/e2e-results.md for test failures
- Git log for recent changes
- Related test files

Create bug analysis:

```markdown
## Bug Analysis: [Bug Title]

**Reported:** [timestamp]
**Symptoms:** What the user/test sees
**Expected:** What should happen
**Actual:** What happens instead

**Reproduction Steps:**
1. Step 1
2. Step 2
3. ...

**Related Files:**
- src/module.py (suspected)
- tests/test_module.py (failing)
```

### Step 2: Reproduce the Bug

Run the failing test or reproduce manually:

```bash
# Run specific failing test
pytest tests/test_module.py::TestClass::test_name -v

# Or run full suite to see failure
pytest -v
```

**Confirm the bug exists** before proceeding.

### Step 3: Identify Root Cause

Use systematic debugging:

#### Check recent changes
```bash
git log --oneline -10
git diff HEAD~3
```

#### Add debug logging (temporary)
```python
print(f"DEBUG: value = {value}")  # Remove after fixing
```

#### Trace the execution
```python
import traceback
traceback.print_stack()
```

#### Check assumptions
- Are inputs valid?
- Are dependencies correct?
- Is state properly initialized?

Document findings:

```markdown
**Root Cause:**
The bug occurs because X doesn't handle Y case.
Specifically, in src/module.py line 42, the condition
`if value > 0` should be `if value >= 0` to handle zero.
```

### Step 4: Write Regression Test

**Before fixing**, write a test that captures the bug:

```python
def test_handles_zero_value(self):
    """Regression test for bug: zero value not handled."""
    result = process(0)  # This should work but currently fails
    assert result == "zero_handled"
```

Run it to confirm it fails:
```bash
pytest tests/test_module.py::test_handles_zero_value -v
```

### Step 5: Fix the Code

Make the **minimal change** to fix the bug:

```python
# Before
if value > 0:
    return process_positive(value)

# After
if value >= 0:  # Fixed: now handles zero
    return process_non_negative(value)
```

### Step 6: Verify the Fix

1. **Run the regression test:**
```bash
pytest tests/test_module.py::test_handles_zero_value -v
```

2. **Run full test suite:**
```bash
pytest -v
```

3. **Run linter/type checker:**
```bash
ruff check .
pyright
```

All must pass.

### Step 7: Clean Up

Remove any debug code:
- print statements
- debug logging
- temporary files

### Step 8: Commit the Fix

```bash
git add -A
git commit -m "fix: handle zero value in process function

- Add check for value >= 0 (was > 0)
- Add regression test: test_handles_zero_value

Fixes: Bug report from E2E test"
```

### Step 9: Update Bug Tracker

Mark bug as fixed in specs/bugs.md:

```markdown
## Bug: Zero value not handled

**Status:** FIXED
**Fixed:** 2026-01-09T12:00:00Z
**Commit:** abc1234
**Regression Test:** test_handles_zero_value
```

## Troubleshooting

### Can't reproduce
- Check environment differences
- Try clean state (fresh git clone)
- Check for flaky tests (run multiple times)

### Fix breaks other tests
- The fix is too broad
- Related code needs updating
- Consider if original behavior was depended on

### Same bug keeps appearing
- Root cause not fully identified
- Related bugs exist
- Add more comprehensive tests

## Output

1. Bug analysis in specs/bugs.md
2. Regression test in tests/
3. Fix committed with clear message
4. Bug marked as FIXED
5. Entry in specs/progress.md
