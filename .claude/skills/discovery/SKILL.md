---
name: discovery
description: |
  Analyze task descriptions for completeness and ask targeted questions to fill gaps.
  Use when starting any new feature or project. Ensures we understand the "what" and "why"
  before jumping to "how". Triggers: "discover", "requirements", "understand problem".
  Outputs specs/requirements.md with structured problem analysis.
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
context: fork
---

# Discovery Phase

Ensure we understand the **what** and **why** of a problem before planning the **how**.

## Purpose

The Discovery phase prevents premature implementation by validating:
- **What** is the actual problem?
- **Why** does this problem exist? (root cause/context)
- **Who** is affected and how?
- **What** does success look like?
- **What** constraints exist?

## Input
`$ARGUMENTS` - A task description or feature request to analyze

## Process

### Step 1: Analyze Completeness

Use the RequirementsAnalyzer to assess the task description:

```python
from src.requirements_analyzer import RequirementsAnalyzer

analyzer = RequirementsAnalyzer()
result = analyzer.analyze("$ARGUMENTS")

print(f"Completeness Score: {result.score.total}/100")
print(f"Needs Discovery: {result.needs_discovery()}")
```

**Score Interpretation:**
- 80+: Excellent - proceed directly to planning
- 60-79: Good - can proceed, may ask 1-2 questions
- 40-59: Fair - ask 2-3 questions before proceeding
- <40: Incomplete - ask up to 4 questions

### Step 2: Identify Gaps

Check which requirement categories are missing:

| Category | Priority | What It Answers |
|----------|----------|-----------------|
| Problem | 1 (highest) | What specific issue are we solving? |
| Success Criteria | 2 | How do we know when we've succeeded? |
| Stakeholders | 3 | Who is affected by this change? |
| Context | 4 | What's the background/existing system? |
| Constraints | 5 | What limits do we have? |

### Step 3: Ask Targeted Questions (If Needed)

**Only ask questions when the completeness score is below 60.**

When questions are needed, present them in this format:

```
+-------------------------------------------------------------+
| [ ] Problem                                                  |
|                                                              |
| What specific problem are we trying to solve?                |
|                                                              |
|  1. User pain point                                          |
|     Users are struggling with something specific             |
|  2. System limitation                                        |
|     The system can't do something it needs to                |
|  3. Business need                                            |
|     Business requires new capability                         |
|  4. Technical issue                                          |
|     Performance, security, or reliability problem            |
|  > 5. [Type your own answer]                                 |
|                                                              |
+-------------------------------------------------------------+
```

**Question Guidelines:**
- Maximum 4 questions at a time
- Prioritize by category (Problem > Success > Stakeholders > Context > Constraints)
- Always include "Other" option for custom responses
- Skip categories that already have sufficient information

### Step 4: Generate Requirements Document

After gathering information, create `specs/requirements.md`:

```markdown
# Requirements

Generated: [timestamp]
Completeness Score: [score]/100

## Problem Statement

[Clear description of the problem being solved]

## Success Criteria

- [Measurable criterion 1]
- [Measurable criterion 2]
- [Measurable criterion 3]

## Stakeholders

- **Primary:** [Who is most affected]
- **Secondary:** [Who else is impacted]
- **Technical:** [Teams involved in implementation]

## Context

[Background information about the current system, technology stack,
existing solutions, and why this problem exists now]

## Constraints

- **Timeline:** [Deadline or time budget]
- **Technical:** [Technology requirements or limitations]
- **Resources:** [Budget or team constraints]
- **Compatibility:** [Integration requirements]

## Open Questions

- [Any remaining questions that couldn't be answered]

## Next Steps

Ready for planning phase. Recommended approach:
1. [First suggestion based on requirements]
```

## Output

### specs/requirements.md
Structured requirements document with all five categories.

### Console Output
```
Discovery Phase Complete!

Completeness Score: [score]/100

Summary:
- Problem: [Identified/Needs clarification]
- Success Criteria: [Defined/Needs clarification]
- Stakeholders: [Identified/Needs clarification]
- Context: [Provided/Needs clarification]
- Constraints: [Defined/Needs clarification]

Requirements saved to: specs/requirements.md
Ready to proceed to: /project:plan
```

## When to Skip Discovery

Discovery can be skipped when:
- Score >= 80 (comprehensive description provided)
- Urgent bug fix with clear reproduction steps
- Explicitly requested by user ("skip discovery")

In these cases, document what was provided and note any gaps:

```markdown
# Requirements (Auto-generated)

*Discovery phase was skipped due to: [reason]*

## Provided Information
[Summary of what was given]

## Potential Gaps
- [What might be missing but wasn't clarified]
```

## Question Templates by Category

### Problem Questions
1. "What specific problem are we trying to solve?"
   - User pain point
   - System limitation
   - Business need
   - Technical issue

### Success Criteria Questions
1. "What does success look like for this task?"
   - Measurable metric
   - User outcome
   - Business outcome
   - Technical outcome

### Stakeholder Questions
1. "Who is affected by this change?"
   - End users
   - Internal teams
   - Business stakeholders
   - External partners

### Context Questions
1. "What is the context for this task?"
   - New feature (building from scratch)
   - Enhancement (improving existing)
   - Bug fix (fixing broken)
   - Refactor (improving code)

### Constraint Questions
1. "What constraints should we be aware of?"
   - Time constraint
   - Technical constraint
   - Resource constraint
   - Compatibility constraint

## Quality Checklist

Before completing discovery:
- [ ] Problem statement is clear and specific
- [ ] At least 2 measurable success criteria exist
- [ ] Primary stakeholders identified
- [ ] Technical context understood
- [ ] Key constraints documented
- [ ] specs/requirements.md saved

## Integration with Workflow

Discovery is **Phase 0** of the development workflow:

```
Discover -> Plan -> Architect -> Implement -> Test -> Fix -> Simplify -> Verify
```

After discovery completes successfully, trigger the planning phase:
- If automated: Proceed to `/project:plan` with requirements
- If manual: Output "Ready for: /project:plan '$ARGUMENTS'"
