---
name: implement-tdd
description: |
  Test-Driven Development implementation. Use when: "implement", "code", "TDD", "build feature".
  Writes failing test first, then implements code to pass. Commits after each passing test.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Implement with TDD

Implement a feature using strict Test-Driven Development.

## Input
`$ARGUMENTS` - Feature description or ID from specs/features.json

## TDD Cycle

```
   ┌──────────────┐
   │  Write Test  │ ◄── Start here
   │  (RED)       │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │  Run Test    │
   │  (Must Fail) │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │  Write Code  │
   │  (Minimum)   │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │  Run Test    │
   │  (GREEN)     │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │  Refactor    │
   │  (Clean)     │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │   Commit     │
   └──────────────┘
```

## Process

### Step 1: Understand the Feature

Read:
- specs/features.json for feature details
- specs/architecture.md for interface definitions
- Related existing code

Extract:
- What the feature should do
- What files to create/modify
- What tests to write

### Step 2: Write Failing Test (RED)

Create test file if needed, then write test:

```python
# tests/test_feature.py
import pytest
from src.core.feature import FeatureClass

class TestFeature:
    def test_basic_functionality(self):
        """Feature should do X when given Y."""
        # Arrange
        feature = FeatureClass()

        # Act
        result = feature.do_something("input")

        # Assert
        assert result == "expected_output"

    def test_edge_case(self):
        """Feature should handle edge case Z."""
        feature = FeatureClass()

        with pytest.raises(ValueError):
            feature.do_something("")
```

### Step 3: Verify Test Fails (Important!)

Run the test:
```bash
pytest tests/test_feature.py -v
```

**The test MUST fail.** If it passes:
- Test may not be testing the right thing
- Feature may already exist
- Investigate before proceeding

### Step 4: Write Minimum Code (GREEN)

Implement **only** what's needed to pass the test:

```python
# src/core/feature.py
class FeatureClass:
    def do_something(self, input: str) -> str:
        if not input:
            raise ValueError("Input cannot be empty")
        return f"processed_{input}"
```

### Step 5: Run Test Again

```bash
pytest tests/test_feature.py -v
```

**Must pass now.** If it fails:
- Debug the implementation
- Do NOT modify the test to pass
- Fix the code

### Step 6: Refactor (if needed)

With passing tests as safety net:
- Improve naming
- Remove duplication
- Simplify logic

Run tests after each refactor to ensure nothing breaks.

### Step 7: Commit

```bash
git add -A
git commit -m "feat: implement [feature description]

- Add FeatureClass with do_something method
- Handle empty input validation
- Tests: test_basic_functionality, test_edge_case"
```

### Step 8: Update Features.json

Mark the feature as complete:

```json
{
  "id": "F001",
  "passes": true,
  "completed_at": "2026-01-09T12:00:00Z"
}
```

## Rules

1. **Never write code without a failing test first**
2. **Never modify a test to make it pass** - Fix the code instead
3. **Minimum code only** - Don't add features the test doesn't require
4. **Commit after each GREEN** - Creates recovery points
5. **One feature at a time** - Don't mix features in one cycle

## Handling Failures

If test keeps failing after 3 attempts:
1. Check if the test itself is correct
2. Check interface definitions in specs/architecture.md
3. Log the issue to specs/progress.md
4. Move to next feature, return later

## Output

After completing:
1. Passing test in tests/
2. Implementation in src/
3. Git commit with descriptive message
4. Updated specs/features.json
5. Entry in specs/progress.md
