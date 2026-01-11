# Claude Autonomous Development Framework

This project is configured for **long-running autonomous development sessions**.

## Quick Reference

### Main Commands
| Command | Purpose |
|---------|---------|
| `/project:build-new-project "<desc>"` | Full autonomous cycle |
| `/project:full-cycle "<feature>"` | Single feature cycle |
| `/project:checkpoint` | Save state for handoff |

### Phase Commands
| Command | Purpose |
|---------|---------|
| `/project:discovery "<task>"` | Analyze requirements & ask questions |
| `/project:plan "<task>"` | Generate & evaluate approaches |
| `/project:architect "<plan>"` | Detailed technical design |
| `/project:implement "<feature>"` | TDD implementation |
| `/project:test-e2e` | Browser/E2E testing |
| `/project:evaluate` | Find bugs & issues |
| `/project:fix "<bug>"` | Systematic bug fixing |
| `/project:simplify` | Refactor & clean up |

## Development Workflow

### Standard Cycle
```
Discover → Plan → Architect → Implement (TDD) → Test → Fix → Simplify → Verify
```

### Discovery Phase (NEW)
Before planning, ensure we understand:
- **What** is the actual problem?
- **Why** does this problem exist?
- **Who** is affected?
- **What** does success look like?
- **What** constraints exist?

Use `/project:discovery` or the RequirementsAnalyzer module.

### Autonomous Loop Behavior
1. You work on tasks iteratively
2. Stop hook checks: tests pass? coverage met? features complete?
3. If incomplete, loop continues automatically
4. Progress tracked in `specs/progress.md`
5. Features tracked in `specs/features.json`

### When to Commit
- After each passing test (TDD cycle)
- After each bug fix
- After simplification
- Before risky changes

## Context Management

### Use Subagents For
- Research and documentation lookup (researcher)
- Writing tests (tester)
- Code review (reviewer)

### Checkpoint When
- Context usage > 70%
- Before major refactors
- End of work session
- Before risky operations

### Clear Context When
- Starting unrelated task
- After completing a major feature
- When responses become generic

## Code Standards

### Python
- Use type hints on all functions
- Prefer `dataclass` or `pydantic` for data models
- Use `ruff` for formatting and linting
- Use `pytest` for testing

### TypeScript
- Use strict mode
- Prefer `bun` for tooling
- Use `biome` or `prettier` for formatting
- Write tests alongside implementation

## File Structure

```
specs/
├── features.json    # Feature status tracking
├── progress.md      # Session log
├── requirements.md  # Problem & requirements (from discovery)
├── plan.md          # Current plan
├── architecture.md  # Technical design
├── bugs.md          # Bug tracking
└── checkpoint-*.md  # Session handoffs

logs/
└── sessions/        # CLI input/output logs (git-associated)

ai-docs/             # External documentation
src/                 # Source code
tests/               # Test files
```

## Session Logging

All CLI sessions are automatically logged with git commit association.

### Log Files
- **Location:** `logs/sessions/{timestamp}-{sha}-{session}.jsonl`
- **Contents:** User inputs, timestamps, git HEAD at each input
- **Index:** `logs/index.json` maps commits to sessions

### Finding Logs by Commit
```bash
# Find which session created a commit
./scripts/find-session-logs.sh abc123f

# List all sessions
./scripts/find-session-logs.sh --list

# Show latest session
./scripts/find-session-logs.sh --latest

# Convert to markdown
./scripts/find-session-logs.sh --format md logs/sessions/file.jsonl
```

### What's Logged
- User prompts with timestamps
- Git HEAD SHA at each input (track changes as they happen)
- Session start/end markers
- Commits created during session

## Quality Gates

Before completing any feature:
- [ ] All tests pass
- [ ] Type checker passes
- [ ] Linter passes
- [ ] Coverage >= 80%
- [ ] E2E tests pass (if web)

## Troubleshooting

### Loop Won't Stop
1. Check `specs/features.json` - all passes: true?
2. Check test output - all passing?
3. Use `/cancel-loop` to force stop

### Context Degradation
1. Run `/project:checkpoint`
2. Run `/clear`
3. Run `/project:resume` or reference checkpoint

### Tests Keep Failing
1. Check `specs/progress.md` for patterns
2. Consider simpler approach
3. Break feature into smaller parts

## Safety Limits

- Max iterations: 50 (configurable in project.config.json)
- Circuit breaker: 3 loops without progress
- Circuit breaker: 5 loops with same error

## Remember

- **Commit often** - Git history is your safety net
- **Use subagents** - Keep main context clean
- **Update features.json** - This drives the loop
- **Log everything** - `specs/progress.md` is memory
