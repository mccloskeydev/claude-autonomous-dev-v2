---
name: simplify
description: |
  Simplify and refactor code while maintaining test coverage. Use when: "simplify", "refactor",
  "clean up", "reduce complexity", "improve code". Removes dead code, improves naming, reduces duplication.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Simplify

Refactor code for clarity and simplicity while keeping tests green.

## Input
`$ARGUMENTS` - File/module to simplify, or "all" for full codebase

## Philosophy

> "Perfection is achieved not when there is nothing more to add,
> but when there is nothing left to take away." - Antoine de Saint-Exupery

## Process

### Step 1: Baseline Tests

Run full test suite and save results:

```bash
pytest -v > specs/test-baseline.txt 2>&1
```

**All tests must pass before refactoring.**

### Step 2: Identify Simplification Targets

Look for:

#### Dead Code
```bash
# Find unused imports (Python)
ruff check --select F401 .

# Find unused variables
ruff check --select F841 .
```

#### Duplication
```bash
# Look for similar patterns
grep -rn "def process" src/
```

#### Complexity
```bash
# Check cyclomatic complexity (if radon installed)
radon cc src/ -a -nc

# Check function length
wc -l src/**/*.py
```

Create simplification plan:

```markdown
## Simplification Targets

### Dead Code
- [ ] src/utils.py: unused import `json` (line 3)
- [ ] src/service.py: unused variable `temp` (line 42)

### Duplication
- [ ] src/api/users.py and src/api/items.py: similar validation logic

### Complexity
- [ ] src/processor.py: `process_data()` has 8 branches, consider splitting

### Naming
- [ ] src/core.py: `x` should be `item_count`
- [ ] src/handlers.py: `do_thing()` should be `handle_request()`
```

### Step 3: Simplify Incrementally

**One change at a time.** After each change:

1. Run tests
2. If pass, commit
3. If fail, revert

#### Remove Dead Code

```python
# Before
import json  # UNUSED
from typing import Optional

def process(data):
    temp = data.copy()  # UNUSED
    return transform(data)

# After
from typing import Optional

def process(data):
    return transform(data)
```

#### Extract Common Logic

```python
# Before (in users.py)
def validate_user(data):
    if not data.get('email'):
        raise ValueError("Email required")
    if not data.get('name'):
        raise ValueError("Name required")

# Before (in items.py - duplicated)
def validate_item(data):
    if not data.get('name'):
        raise ValueError("Name required")
    if not data.get('price'):
        raise ValueError("Price required")

# After (in validators.py)
def require_fields(data: dict, fields: list[str]) -> None:
    for field in fields:
        if not data.get(field):
            raise ValueError(f"{field.title()} required")

# Usage
def validate_user(data):
    require_fields(data, ['email', 'name'])

def validate_item(data):
    require_fields(data, ['name', 'price'])
```

#### Reduce Complexity

```python
# Before (complex)
def process_data(data):
    if data.type == 'A':
        if data.status == 'active':
            return handle_active_a(data)
        else:
            return handle_inactive_a(data)
    elif data.type == 'B':
        if data.status == 'active':
            return handle_active_b(data)
        else:
            return handle_inactive_b(data)
    else:
        return handle_unknown(data)

# After (dispatch table)
HANDLERS = {
    ('A', 'active'): handle_active_a,
    ('A', 'inactive'): handle_inactive_a,
    ('B', 'active'): handle_active_b,
    ('B', 'inactive'): handle_inactive_b,
}

def process_data(data):
    key = (data.type, data.status)
    handler = HANDLERS.get(key, handle_unknown)
    return handler(data)
```

#### Improve Naming

```python
# Before
def calc(x, y, z):
    return x * y + z

# After
def calculate_total_price(unit_price: float, quantity: int, tax: float) -> float:
    return unit_price * quantity + tax
```

### Step 4: Verify No Regression

After all simplifications:

```bash
# Run full test suite
pytest -v

# Compare to baseline
diff specs/test-baseline.txt <(pytest -v 2>&1)

# Run type checker
pyright

# Run linter
ruff check .
```

### Step 5: Commit

```bash
git add -A
git commit -m "refactor: simplify codebase

- Remove unused imports and variables
- Extract common validation logic to validators.py
- Simplify process_data with dispatch table
- Improve variable naming in calculate_total_price

No functional changes. All tests passing."
```

## Rules

1. **Never break tests** - If a test fails, revert immediately
2. **One type of change per commit** - Don't mix dead code removal with renaming
3. **Don't change behavior** - Simplification is NOT adding features
4. **Keep it readable** - Clever code is not simple code
5. **Document trade-offs** - If a simplification has downsides, note them

## What NOT to Simplify

- **Don't remove error handling** (it's there for a reason)
- **Don't inline everything** (some abstractions aid readability)
- **Don't optimize prematurely** (readability > micro-optimizations)
- **Don't remove comments that explain "why"**

## Output

1. Cleaner code with same behavior
2. All tests still passing
3. Commits for each simplification type
4. Entry in specs/progress.md
