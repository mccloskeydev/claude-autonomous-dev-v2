# Comprehensive Research: Making Claude Code Long-Running for Autonomous Software Development

**Research Date:** January 9, 2026
**Purpose:** Strategies to achieve continuous, multi-hour autonomous development loops with Claude Code

---

## Executive Summary

Your desired workflow (plan → alternatives → architect → implement → test → evaluate → fix → comprehensive tests → simplify → iterate) **is achievable** with the right combination of:

1. **Ralph Wiggum Plugin** - Official Anthropic plugin for autonomous loops
2. **Hooks System** - For quality gates and loop continuation
3. **Skills** - For reusable, scoped workflows
4. **Subagents** - For context isolation and parallel execution
5. **Progress Files** - For multi-session state persistence
6. **Git Worktrees** - For parallel agent execution

The key insight from Boris Cherny (Claude Code creator): He runs **5 Claudes in parallel** and uses the **ralph-wiggum plugin** for long-running tasks. Native support for "long-running" and "swarm" features is coming (currently at demo stage).

---

## Part 1: Core Strategies for Long-Running Sessions

### 1.1 The Ralph Wiggum Technique (Official Plugin)

**Source:** [Official Anthropic Plugin](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum)

The most battle-tested approach for continuous autonomous loops.

#### Installation
```bash
/plugin install ralph-wiggum@claude-plugins-official
```

#### How It Works
1. You run `/ralph-loop "Your task" --completion-promise "DONE" --max-iterations 50`
2. Claude works on the task
3. Claude tries to exit → Stop hook blocks exit
4. Stop hook feeds the **same prompt back**
5. Claude sees its previous work (git history, modified files)
6. Loop continues until completion promise detected or max iterations

#### Best Practice Prompt Structure
```
Build feature X with the following phases:

Phase 1: Write failing tests for requirements
Phase 2: Implement minimum code to pass tests
Phase 3: Refactor for clarity
Phase 4: Add edge case tests
Phase 5: Final cleanup and documentation

After each phase, commit your progress.
When ALL phases complete and tests pass:
Output: <promise>COMPLETE</promise>

If blocked after 15 iterations:
- Document blocking issues
- List attempted approaches
- Suggest alternatives
```

#### Safety Controls
- `--max-iterations 50` - **Always set this** as your safety net
- `--completion-promise "COMPLETE"` - Exact string match to exit
- `/cancel-ralph` - Emergency stop command

#### Real Results
- Y Combinator hackathon: 6 repositories shipped overnight for $297 API cost
- Geoffrey Huntley: Built entire programming language over 3 months with one prompt

---

### 1.2 Anthropic's Multi-Context Window Pattern

**Source:** [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

For tasks spanning **hours or days** across multiple context windows.

#### Two-Agent Architecture

**Initializer Agent** (runs once):
```markdown
Create:
1. init.sh - Script to bootstrap environment and run basic tests
2. claude-progress.txt - Log of all agent activities between sessions
3. features.json - 200+ granular features with `passes: false`
4. Initial git commit documenting baseline
```

**Coding Agent** (runs repeatedly):
```markdown
Each session:
1. Run `pwd` to verify working directory
2. Read git logs and claude-progress.txt for context
3. Select highest-priority feature with passes: false
4. Run init.sh to start dev server
5. Implement ONE feature only
6. Test with browser automation (not just unit tests)
7. If passes, set passes: true and commit
8. Update claude-progress.txt with what was done
9. Leave codebase in clean, mergeable state
```

#### Critical Pattern: Feature List JSON
```json
{
  "features": [
    {
      "category": "functional",
      "description": "User can create new todo item",
      "steps": ["Click add button", "Enter text", "Press submit"],
      "passes": false
    }
  ]
}
```

**Key constraint:** Agents can ONLY modify the `passes` field - prevents premature "done" declarations.

---

### 1.3 Hooks Configuration for Autonomous Loops

**Source:** [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)

#### Hook Types
| Hook | When It Fires | Use Case |
|------|---------------|----------|
| `PreToolUse` | Before tool execution | Block dangerous commands, modify inputs |
| `PostToolUse` | After tool completion | Auto-format, run linters |
| `Stop` | When agent finishes | Quality gates, loop continuation |
| `UserPromptSubmit` | When user submits | Inject context |
| `PermissionRequest` | Permission check | Auto-approve safe operations |
| `SubagentStop` | Subagent finishes | Collect results |
| `SessionEnd` | Session terminates | Cleanup, notifications |

#### Example: Quality Gate Stop Hook
```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "npm test && npm run lint && echo 'QUALITY_PASSED'"
          }
        ]
      }
    ]
  }
}
```

**Exit code 2** from Stop hook = blocks stoppage and forces continuation (use carefully to avoid infinite loops).

#### Example: Auto-Format on Edit
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "prettier --write \"$CLAUDE_FILE_PATH\""
          }
        ]
      }
    ]
  }
}
```

---

### 1.4 Circuit Breaker Patterns (Preventing Runaway Loops)

**Source:** [ralph-claude-code](https://github.com/frankbria/ralph-claude-code)

Essential safety mechanisms:

| Threshold | Action |
|-----------|--------|
| `MAX_CONSECUTIVE_TEST_LOOPS=3` | Exit if only running tests |
| `MAX_CONSECUTIVE_DONE_SIGNALS=2` | Exit on repeated "done" claims |
| `CB_NO_PROGRESS_THRESHOLD=3` | Open circuit after 3 loops with no file changes |
| `CB_SAME_ERROR_THRESHOLD=5` | Open circuit after 5 loops with same error |
| `CB_OUTPUT_DECLINE_THRESHOLD=70%` | Open circuit if output shrinks by >70% |

---

## Part 2: Context Management Strategies

### 2.1 The Context Decay Problem

Each compaction loses information. After several: "summary of a summary of a summary."

**Symptoms of context decay:**
- Generic responses
- Forgetting previous decisions
- Degraded code quality
- Repeating solved problems

### 2.2 Proactive Context Management

#### Use `/clear` Aggressively
```
Pro tip: use /clear often. Every time you start something new,
clear the chat. You don't need that history eating your tokens.
```

#### Subagents for Heavy Research
Subagents have **isolated 200k context windows**. Use them for:
- Documentation fetching
- Large codebase exploration
- Multi-file analysis

```markdown
# In CLAUDE.md
When researching or exploring:
- Use subagents to prevent context pollution
- Have subagent return only relevant findings
- Keep main context clean for implementation
```

#### The Handoff Protocol
**Source:** [Continuous-Claude-v2](https://github.com/parcadei/Continuous-Claude-v2)

Before context fills:
1. Create structured handoff summary
2. Clear context completely
3. Resume with handoff loaded

```markdown
## Handoff Template
### Current Progress
- [x] Completed items
- [ ] Pending items

### Key Decisions Made
1. Decision and rationale

### Active Blockers
- Issue and attempted solutions

### Next Steps
1. Immediate next action
2. Following action
```

### 2.3 CLAUDE.md Best Practices

**Location hierarchy:**
1. `~/.claude/CLAUDE.md` - Global (all projects)
2. `./CLAUDE.md` or `./.claude/CLAUDE.md` - Project
3. `./.claude/CLAUDE.local.md` - Private (gitignored)
4. `./.claude/rules/*.md` - Scoped rules

**Key principles:**
- Keep under 500 lines
- Use imports: `@path/to/file.md`
- Prefer pointers over copies (reference files, not paste content)
- Be specific: "Use 2-space indentation" not "Format properly"

#### Example CLAUDE.md for Autonomous Work
```markdown
# Project: MyApp

## Development Workflow
1. Always run tests before committing
2. Use subagents for codebase exploration
3. Commit after each completed feature

## Quality Gates
- All tests must pass before PR
- No console.log in production code
- TypeScript strict mode required

## When Stuck
After 2 failed attempts at same problem:
1. Document what was tried
2. Run /compact or /clear
3. Try alternative approach

## File References
- Architecture: @docs/architecture.md
- API Schema: @docs/api-schema.md
```

---

## Part 3: Parallel Execution Patterns

### 3.1 Git Worktrees for Multi-Agent Parallelism

**Source:** [Anthropic Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)

Run multiple Claudes without file conflicts.

#### Setup
```bash
# Create worktrees for parallel features
git worktree add ../myproject-feature-a feature-a
git worktree add ../myproject-feature-b feature-b

# Open separate terminals for each
cd ../myproject-feature-a && claude
cd ../myproject-feature-b && claude
```

#### Boris Cherny's Workflow
```
"I run 5 Claudes in parallel in my terminal. I number my tabs 1-5,
and use system notifications to know when a Claude needs input."
```

### 3.2 Background Task Pattern (& operator)

```bash
# Send task to web background
> analyze this entire codebase and generate documentation &

# Continue working locally while it runs

# Later, retrieve with teleport
claude --teleport <session-id>
```

### 3.3 Helper Tools

| Tool | Purpose |
|------|---------|
| [ccswitch](https://github.com/ksred/ccswitch) | Manage worktrees in `~/.ccswitch/worktrees/` |
| [Crystal](https://github.com/stravu/crystal) | Desktop app for parallel AI sessions |
| [ccpm](https://github.com/automazeio/ccpm) | GitHub Issues + worktrees for coordination |
| [ccswarm](https://github.com/nwiizo/ccswarm) | Rust-native multi-agent orchestration |

---

## Part 4: Skills Architecture

### 4.1 Skill Structure

```
.claude/skills/my-skill/
├── SKILL.md          # Required: metadata + instructions
├── references/       # Documentation loaded as needed
├── scripts/          # Executable utilities
└── assets/           # Templates, images
```

#### SKILL.md Template
```yaml
---
name: "tdd-loop"
description: "Test-driven development loop: write tests, implement, verify, iterate"
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
hooks:
  Stop:
    - matcher: ""
      command: "npm test"
---

# TDD Loop Skill

## When to Use
Invoke when implementing new features or fixing bugs.

## Workflow
1. Write failing test for expected behavior
2. Implement minimum code to pass
3. Run tests
4. If failing, debug and fix
5. Refactor for clarity
6. Repeat until all tests pass
```

### 4.2 Hot Reload (v2.1.0+)

Skills in `~/.claude/skills/` or `.claude/skills/` now **activate immediately** without restarting - iterate rapidly on skill development.

### 4.3 Context Isolation for Skills

```yaml
---
context: fork
---
```

Skill runs in isolated sub-agent context, preventing main conversation pollution.

---

## Part 5: Orchestration Tools Comparison

| Tool | Best For | Key Feature |
|------|----------|-------------|
| **Ralph Wiggum** | Simple continuous loops | Official Anthropic plugin |
| **claude-flow** | Enterprise microservices | 100+ MCP tools, Queen-led swarm |
| **SuperClaude** | Solo developers | @include system, `/magic` UI generation |
| **ccswarm** | Rust projects | Type-state pattern, zero shared state |
| **BMAD Method** | Junior engineer onboarding | Enforced Plan→Architect→Implement→Review |

### Recommendation for Your Workflow

For your 11-step loop (plan → alternatives → pick best → architect → implement → test → evaluate → fix → comprehensive tests → simplify → iterate):

**Option A: Ralph Wiggum + Custom CLAUDE.md**
- Simplest setup
- Works with subscription or API
- Prompt encodes your full workflow

**Option B: Custom Skills Pipeline**
```
.claude/skills/
├── plan-alternatives/
├── architect-design/
├── implement-tdd/
├── evaluate-fix/
├── simplify-refactor/
└── full-cycle/        # Orchestrates all above
```

**Option C: Multi-Agent with claude-flow**
- For complex projects needing parallel agents
- Higher token usage
- Best with API access

---

## Part 6: Cost & Rate Limit Management

### 6.1 Subscription vs API

| Plan | Cost | Best For |
|------|------|----------|
| Max ($100/mo) | Fixed | Moderate autonomous usage |
| Max ($200/mo) | Fixed | Heavy parallel agents |
| API (Sonnet) | ~$100-200/mo typical | Pay-per-use, batch discounts |
| API (Opus 4.5) | Higher but 48% fewer tokens with effort param | Complex reasoning |

### 6.2 Token Optimization Strategies

1. **Hybrid Models**: Opus for planning, Sonnet/Haiku for implementation
2. **Batch API**: 50% discount for non-urgent tasks
3. **Disable Unused MCPs**: Each adds to system prompt tokens
4. **Aggressive /clear**: Fresh context between tasks
5. **Subagents for Research**: Isolate heavy token consumption
6. **Effort Parameter** (Opus 4.5): Medium effort = 76% fewer tokens

### 6.3 Rate Limit Strategies

On Max plan with parallel loops:
```
Running loops on 2 projects simultaneously exhausts
rate limit window in less than an hour.
```

**Mitigation:**
- Set `--max-iterations` conservatively
- Stagger parallel sessions
- Use background tasks (`&`) for web execution
- Monitor with `/stats`

---

## Part 7: Failure Modes & Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| Stops after 30 min | Natural "done" detection | Use ralph-wiggum Stop hook |
| Context decay | Compaction losses | Handoff protocol, subagents |
| Infinite test loops | Unclear completion criteria | Circuit breakers, max-iterations |
| Premature "done" | Vague success criteria | Feature JSON with 200+ items |
| File conflicts | Parallel agents | Git worktrees |
| Stuck on same error | No circuit breaker | CB_SAME_ERROR_THRESHOLD |
| Token exhaustion | Poor context management | /clear, subagents, CLAUDE.md optimization |

---

## Part 8: Implementation Roadmap

### Phase 1: Basic Continuous Loop (Day 1)

1. Install ralph-wiggum plugin
2. Configure CLAUDE.md with your workflow phases
3. Set up quality gate Stop hooks
4. Test with small feature

### Phase 2: Context Optimization (Week 1)

1. Create skills for each workflow phase
2. Configure subagents for research/exploration
3. Set up handoff protocol for long sessions
4. Add circuit breakers

### Phase 3: Parallel Execution (Week 2)

1. Set up git worktree workflow
2. Configure notification hooks
3. Implement background task patterns
4. Test multi-agent coordination

### Phase 4: Full Automation (Week 3+)

1. Create orchestration skill combining all phases
2. Integrate with CI/CD
3. Add GitHub issue automation
4. Fine-tune based on observed patterns

---

## Part 9: Key Resources

### Official Documentation
- [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Agent Skills Documentation](https://code.claude.com/docs/en/skills)
- [Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Subagents Documentation](https://code.claude.com/docs/en/sub-agents)

### Community Projects
- [ralph-wiggum (Official)](https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum)
- [claude-flow](https://github.com/ruvnet/claude-flow)
- [Continuous-Claude-v2](https://github.com/parcadei/Continuous-Claude-v2)
- [ccswarm](https://github.com/nwiizo/ccswarm)
- [awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills)

### Courses
- [DeepLearning.AI: Claude Code - A Highly Agentic Coding Assistant](https://www.deeplearning.ai/short-courses/claude-code-a-highly-agentic-coding-assistant/) (Andrew Ng + Elie Schoppik)

### Creator Insights
- [Boris Cherny's Workflow Thread](https://x.com/bcherny/status/2007179832300581177)
- [VentureBeat: Creator's Workflow Revealed](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)

---

## Part 10: Your Custom Workflow Configuration

Based on your 11-step requirements, here's a ready-to-use configuration:

### CLAUDE.md Addition
```markdown
# Autonomous Development Workflow

## Full Development Cycle
When building features, follow this cycle:

### 1. Planning Phase
- Generate 3+ alternative approaches
- Document pros/cons of each
- Select best approach with rationale

### 2. Architecture Phase
- Create detailed technical design
- Identify all files to modify
- Define interfaces and data flows

### 3. Implementation Phase (TDD)
- Write failing tests first
- Implement minimum code to pass
- Commit after each test passes

### 4. Evaluation Phase
- Run full test suite
- Test in browser (if web app)
- Document any bugs found

### 5. Fix Phase
- Address each bug systematically
- Re-run tests after each fix
- Commit fixes separately

### 6. Comprehensive Testing
- Add edge case tests
- Add integration tests
- Achieve >80% coverage

### 7. Simplification Phase
- Remove dead code
- Refactor for clarity
- Reduce complexity

### 8. Iteration Decision
- Evaluate against original requirements
- Identify enhancement opportunities
- If incomplete, return to Phase 1

## Completion Criteria
Output <promise>CYCLE_COMPLETE</promise> when:
- All tests pass
- Coverage >80%
- No known bugs
- Code reviewed for simplicity
```

### Ralph Loop Command
```bash
/ralph-loop "Implement [FEATURE_NAME] following the Full Development Cycle in CLAUDE.md. Use subagents for research. Commit after each phase. Output <promise>CYCLE_COMPLETE</promise> when done." --completion-promise "CYCLE_COMPLETE" --max-iterations 100
```

---

## Summary: Top 5 Actions to Take Now

1. **Install ralph-wiggum**: `/plugin install ralph-wiggum@claude-plugins-official`

2. **Configure CLAUDE.md**: Add your workflow phases and completion criteria

3. **Set up hooks**: Quality gates (tests, lint) on Stop event

4. **Use subagents**: Isolate research to preserve main context

5. **Always set --max-iterations**: Your safety net against runaway costs

**The future is coming:** Boris Cherny confirmed "long-running" and "swarm" are active development priorities at Anthropic. What requires plugins today will likely be native features soon.
