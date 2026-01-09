# Claude Autonomous Development Framework v2 Specification

## Background

Version 1 of this framework was built in 9 minutes. It implements the core concepts from research on long-running Claude Code sessions (see ai-docs/research-analysis.md).

## Goal for v2

Build a **self-improving, longer-running, more comprehensive** autonomous development framework that:

1. **Runs longer** - Target: 2+ hours of continuous autonomous work
2. **Handles more complexity** - Multi-feature, multi-file projects
3. **Self-corrects better** - Smarter circuit breakers, better recovery
4. **Produces higher quality** - More thorough testing, better code
5. **Is more extensible** - Easy to add new skills, workflows

## Key Improvements Required

### 1. Enhanced Loop Control

**Current limitation:** Simple iteration counter and basic quality gate.

**v2 should have:**
- Adaptive iteration limits based on task complexity
- Multi-level circuit breakers:
  - Token-level (approaching context limit)
  - Progress-level (no meaningful changes)
  - Quality-level (tests degrading)
  - Time-level (wall clock limits)
- Intelligent backoff when stuck
- Automatic context checkpointing before compaction

### 2. Smarter Context Management

**Current limitation:** Basic subagent usage, manual checkpoints.

**v2 should have:**
- Automatic context pressure monitoring
- Progressive disclosure of context (load only what's needed)
- Hierarchical memory:
  - Hot context (current task)
  - Warm context (recent decisions)
  - Cold context (archived checkpoints)
- Auto-checkpoint before context > 70%
- Semantic compression of progress logs

### 3. Better Progress Tracking

**Current limitation:** Simple features.json with passes: true/false.

**v2 should have:**
- Dependency graph between features
- Priority scoring (critical path analysis)
- Effort estimation and tracking
- Blocker detection and routing
- Parallel execution planning
- Gantt-style progress visualization (mermaid)

### 4. Improved Testing Strategy

**Current limitation:** TDD cycle, basic E2E.

**v2 should have:**
- Test pyramid enforcement (unit > integration > E2E)
- Mutation testing integration
- Property-based testing support
- Coverage trend tracking (not just current %)
- Flaky test detection and quarantine
- Test impact analysis (which tests for which changes)

### 5. Advanced Error Recovery

**Current limitation:** Simple retry, circuit breaker.

**v2 should have:**
- Error classification (syntax, logic, environment, flaky)
- Strategy selection per error type
- Root cause analysis automation
- Similar error detection (have we seen this before?)
- Escalation paths (when to ask human)
- Recovery playbooks per error category

### 6. Multi-Agent Orchestration

**Current limitation:** Sequential subagent spawning.

**v2 should have:**
- Parallel agent execution where safe
- Agent communication protocol
- Work stealing for load balancing
- Consensus mechanism for conflicting changes
- Agent specialization and routing
- Swarm coordination for large refactors

### 7. Self-Improvement Capabilities

**v2 should have:**
- Metric collection on own performance
- Skill effectiveness tracking
- Prompt optimization based on outcomes
- Pattern library of successful approaches
- Learning from failures (what not to do)
- Version comparison (v2 vs v1 benchmarks)

## Technical Implementation

### New Skills Required

1. **orchestrator** - High-level workflow coordination
2. **context-manager** - Automatic context pressure handling
3. **dependency-analyzer** - Feature dependency graph
4. **parallel-executor** - Multi-agent coordination
5. **error-classifier** - Smart error handling
6. **metrics-collector** - Performance tracking
7. **self-optimizer** - Prompt/workflow improvement

### New Hooks Required

1. **PreCompact** - Auto-checkpoint before compaction
2. **ContextPressure** - Trigger when context > threshold
3. **AgentSpawn** - Coordinate parallel agents
4. **ErrorOccurred** - Route to error classifier

### Enhanced Data Structures

#### features.json v2
```json
{
  "version": "2.0",
  "project": "...",
  "features": [{
    "id": "F001",
    "description": "...",
    "priority": 1,
    "effort_estimate": "medium",
    "effort_actual": null,
    "dependencies": ["F000"],
    "blocks": ["F002", "F003"],
    "status": "in_progress",
    "progress_pct": 45,
    "tests": {
      "unit": ["test_a.py"],
      "integration": [],
      "e2e": []
    },
    "errors_encountered": [],
    "attempts": 1,
    "assigned_agent": null
  }]
}
```

#### metrics.json
```json
{
  "session_id": "...",
  "started": "...",
  "iterations": 0,
  "tokens_used": 0,
  "features_completed": 0,
  "tests_written": 0,
  "bugs_fixed": 0,
  "errors_by_type": {},
  "time_by_phase": {},
  "context_checkpoints": 0
}
```

## Success Criteria

v2 is successful when it can:

1. [ ] Run for 2+ hours without human intervention on a medium complexity project
2. [ ] Complete a 10+ feature project from scratch
3. [ ] Achieve 90%+ test coverage automatically
4. [ ] Recover from at least 5 different error types automatically
5. [ ] Produce cleaner code than v1 (measured by complexity metrics)
6. [ ] Use 20% fewer tokens per feature than v1 (context efficiency)
7. [ ] Successfully use parallel agents for independent work
8. [ ] Self-report accurate metrics on its own performance

## Constraints

- Must be backwards compatible with v1 skills (can run v1 commands)
- Must work with Claude Code Max subscription (rate limit aware)
- Must not require external services beyond Puppeteer MCP
- Must be portable (work on any machine with Claude Code)

## Deliverables

1. Enhanced skill set (all v1 skills + new v2 skills)
2. Improved hooks with context management
3. New data structures (features v2, metrics)
4. Comprehensive test suite for the framework itself
5. Documentation and migration guide from v1
6. Benchmark results comparing v1 vs v2

## How to Build This

Use the v1 framework to build v2:

1. Start with `/project:build-new-project` pointing to this spec
2. Let it plan the implementation phases
3. Implement incrementally with TDD
4. Test each improvement against v1 baseline
5. Iterate until all success criteria met

The framework building a better version of itself is the ultimate test of its capabilities.
