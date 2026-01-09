---
name: plan-alternatives
description: |
  Generate multiple implementation approaches and select the best one.
  Use when: planning new features, evaluating options, "plan", "alternatives", "approaches".
  Returns a structured plan with selected approach and rationale.
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - WebSearch
  - WebFetch
context: fork
---

# Plan Alternatives

Generate 3+ distinct implementation approaches for a task, evaluate each, and select the best.

## Input
`$ARGUMENTS` - The task/feature to plan

## Process

### Step 1: Understand Requirements

Read any existing context:
- specs/*.md for existing designs
- CLAUDE.md for project conventions
- README.md for project overview
- Existing code for patterns

### Step 2: Research (if needed)

If the task involves unfamiliar technology:
- Search for best practices
- Look for existing solutions
- Check documentation

### Step 3: Generate Approaches

Create **at least 3 distinct approaches**. For each approach:

```markdown
### Approach N: [Name]

**Overview:** Brief description

**Architecture:**
- Component A does X
- Component B does Y
- Data flows: A → B → C

**Implementation Steps:**
1. First step
2. Second step
3. ...

**Pros:**
- Pro 1
- Pro 2

**Cons:**
- Con 1
- Con 2

**Complexity:** Low / Medium / High

**Risk Assessment:**
- Risk 1: Mitigation
- Risk 2: Mitigation

**Estimated Scope:** Small (< 1 day) / Medium (1-3 days) / Large (3+ days)
```

### Step 4: Evaluation Matrix

Create a comparison:

| Criterion | Approach 1 | Approach 2 | Approach 3 |
|-----------|------------|------------|------------|
| Simplicity | | | |
| Maintainability | | | |
| Performance | | | |
| Testability | | | |
| Time to implement | | | |

### Step 5: Selection

Choose the best approach with clear rationale:

```markdown
## Selected Approach: [Name]

**Rationale:**
We selected this approach because:
1. Reason 1
2. Reason 2
3. Reason 3

**Trade-offs accepted:**
- Accepting X in exchange for Y
```

## Output

Save the complete plan to `specs/plan.md`:

```markdown
# Implementation Plan: [Task Name]

Generated: [timestamp]

## Overview
[Brief summary of the task]

## Requirements
- Requirement 1
- Requirement 2

## Approaches Considered

### Approach 1: [Name]
...

### Approach 2: [Name]
...

### Approach 3: [Name]
...

## Evaluation
[Matrix]

## Selected Approach: [Name]

### Rationale
...

### Implementation Steps
1. Step 1
2. Step 2
...

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

## Quality Checklist

Before completing, verify:
- [ ] At least 3 approaches generated
- [ ] Each approach has pros, cons, and risks
- [ ] Selection rationale is clear
- [ ] Implementation steps are actionable
- [ ] specs/plan.md is saved
