---
name: orchestrator
description: |
  Enhanced v2 orchestrator combining ALL framework features for long-running autonomous
  development sessions. Includes: adaptive loop control, multi-level circuit breakers,
  context pressure monitoring, hierarchical memory, dependency analysis, test pyramid
  enforcement, flaky test detection, error classification, root cause analysis,
  parallel execution, agent communication, metrics collection, and self-optimization.
allowed-tools:
  - Task
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - TodoWrite
  - mcp__puppeteer__puppeteer_navigate
  - mcp__puppeteer__puppeteer_screenshot
---

# v2 Enhanced Orchestrator - All Features Integrated

You are orchestrating a **long-running autonomous development session** with the full v2 framework.

## Input
The user provides: `$ARGUMENTS` - A description of the task/feature to complete.

## Framework Overview

### Core Modules

| Module | File | Purpose |
|--------|------|---------|
| Loop Control | `src/loop_control.py` | Adaptive iteration limits, stuck detection |
| Circuit Breakers | `src/circuit_breaker.py` | Token, progress, quality, time limits |
| Context Manager | `src/context_manager.py` | Pressure monitoring, checkpoints, hierarchical memory |
| Dependency Graph | `src/dependency_graph.py` | Feature dependencies, critical path |
| Error Classifier | `src/error_classifier.py` | Error types, recovery strategies |
| Root Cause Analyzer | `src/root_cause_analyzer.py` | Hypothesis generation, causal chains |
| Test Analyzer | `src/test_analyzer.py` | Pyramid enforcement, coverage tracking |
| Flaky Detector | `src/flaky_detector.py` | Flaky test detection, quarantine |
| Parallel Executor | `src/parallel_executor.py` | Task queuing, work stealing |
| Agent Protocol | `src/agent_protocol.py` | Inter-agent communication |
| Metrics | `src/metrics.py` | Collection, performance tracking |
| Progress Tracker | `src/progress_tracker.py` | Effort estimation, velocity |
| Self Optimizer | `src/self_optimizer.py` | Parameter tuning based on outcomes |

## Phase 0: Initialize Session

### 1. Assess Task Complexity

```python
from src.loop_control import TaskComplexity

complexity = TaskComplexity.from_metrics(
    file_count=<files to modify>,
    test_count=<tests to write>,
    dependency_depth=<max dep chain>
)
# Returns: TRIVIAL (15 iter), SIMPLE (30), MODERATE (50), COMPLEX (75), EPIC (200)
```

### 2. Initialize Circuit Breakers

```python
from src.circuit_breaker import MultiLevelCircuitBreaker

circuit_breaker = MultiLevelCircuitBreaker(
    token_limit=200000,      # Max context tokens
    progress_threshold=3,     # Iterations without progress
    time_limit=7200,         # 2 hour wall clock
)
```

### 3. Initialize Context Manager

```python
from src.context_manager import ContextManager

context = ContextManager(max_tokens=200000)
context.add("task", task_description, tier=ContextTier.HOT)
context.add("features", feature_list, tier=ContextTier.WARM)
```

### 4. Build Dependency Graph

```python
from src.dependency_graph import DependencyGraph

graph = DependencyGraph()
graph.load_from_file("specs/features.json")
ready_features = graph.get_ready_features()
critical_path = graph.get_critical_path()
```

### 5. Initialize Metrics and Optimizer

```python
from src.metrics import SessionMetrics
from src.self_optimizer import SelfOptimizer

metrics = SessionMetrics(session_id="session-1")
optimizer = SelfOptimizer()
optimizer.register_parameter("max_iterations", 50, 10, 200, 10)
optimizer.register_parameter("retry_limit", 3, 1, 10, 1)
```

### 6. Create Initial State File

Create `.claude/.session_state.json`:
```json
{
  "session_id": "session-1",
  "iteration": 0,
  "complexity": "MODERATE",
  "max_iterations": 50,
  "circuit_breaker_states": {
    "token": "CLOSED",
    "progress": "CLOSED",
    "quality": "CLOSED",
    "time": "CLOSED"
  },
  "context_pressure": "low",
  "features": {
    "ready": ["F001", "F003"],
    "blocked": ["F002", "F004"],
    "complete": []
  }
}
```

## Phase 1: Pre-Iteration Checks

### Circuit Breaker Check

```python
# Check all circuit breakers before each iteration
status = circuit_breaker.check_all()
if status.any_tripped():
    # Log which breaker tripped
    for level, tripped in status.levels.items():
        if tripped:
            log_warning(f"Circuit breaker {level} TRIPPED")

    # Attempt recovery or stop
    if status.recovery_possible():
        circuit_breaker.attempt_recovery()
    else:
        STOP("Circuit breaker cannot recover")
```

### Context Pressure Check

```python
pressure = context.get_pressure()
if pressure.level == "critical":
    # Create checkpoint before potential compaction
    checkpoint = context.create_checkpoint(
        session_id=session_id,
        progress_summary=get_progress_summary()
    )
    checkpoint.save(f".claude/checkpoints/checkpoint-{session_id}.json")

    # Demote stale entries
    context.demote_stale_entries()
```

### Feature Dependency Check

```python
# Get features ready to work on
ready = graph.get_ready_features()
if not ready:
    blocked = graph.get_blocked_features()
    if blocked:
        log_error(f"All features blocked: {[f.id for f in blocked]}")
        STOP("Dependency deadlock")
```

## Phase 2: Execute Work

### TDD Cycle with Error Handling

```python
from src.error_classifier import ErrorClassifier
from src.root_cause_analyzer import RootCauseAnalyzer

classifier = ErrorClassifier()
analyzer = RootCauseAnalyzer()

try:
    # Write failing test
    result = run_tests()
    if result.failed:
        # Implement to pass
        implement_code()
        result = run_tests()
except Exception as e:
    # Classify the error
    classification = classifier.classify(str(e))

    # Get recovery strategy
    strategy = classification.recovery_strategy
    playbook = classifier.get_playbook(classification.error_type)

    # Analyze root cause if complex
    if classification.severity >= ErrorSeverity.HIGH:
        investigation = analyzer.analyze(str(e), classification)
        root_cause = analyzer.determine_root_cause(investigation)

        # Log for learning
        log_error(f"Root cause: {root_cause.description}")
        log_info(f"Fix suggestions: {root_cause.fix_suggestions}")
```

### Test Pyramid Enforcement

```python
from src.test_analyzer import TestAnalyzer

test_analyzer = TestAnalyzer(min_unit_ratio=0.7, min_coverage=80)

# After running tests
test_analyzer.analyze_output(pytest_output)

# Check pyramid health
if not test_analyzer.pyramid.is_healthy_shape():
    recommendations = test_analyzer.pyramid.get_recommendations()
    for rec in recommendations:
        log_warning(f"Test pyramid: {rec}")
```

### Flaky Test Handling

```python
from src.flaky_detector import FlakyDetector

flaky_detector = FlakyDetector(auto_quarantine=True)

# After each test run
flaky_detector.parse_pytest_output(pytest_output)

# Check for flaky tests
flaky_tests = flaky_detector.detect_flaky_tests()
for test in flaky_tests:
    if test.flakiness_score > 0.6:
        log_warning(f"Quarantining flaky test: {test.test_name}")
```

## Phase 3: Record Results

### Update Metrics

```python
# Record iteration metrics
metrics.collector.record(MetricType.ITERATIONS, iteration)
metrics.collector.record(MetricType.TOKENS_USED, token_count)
metrics.collector.record(MetricType.FILES_CHANGED, files_changed)

if feature_completed:
    metrics.record_feature_completed(feature_id)
```

### Update Progress Tracker

```python
from src.progress_tracker import ProgressTracker

tracker.update(
    feature_id,
    phase=ProgressPhase.IN_PROGRESS,
    completion=progress_pct
)

# Track effort
tracker.get_progress(feature_id).record_effort(elapsed_hours, EffortUnit.HOURS)
```

### Update Self-Optimizer

```python
# Record outcome
outcome_type = OutcomeType.SUCCESS if tests_pass else OutcomeType.FAILURE
optimizer.record_outcome(
    outcome_type=outcome_type,
    metric_name="tests_passed",
    value=test_count,
    context={"feature": feature_id}
)

# Periodically optimize
if iteration % 10 == 0:
    optimizer.optimize_step()
```

### Update Circuit Breakers

```python
# Update progress circuit breaker
circuit_breaker.record_progress(files_changed=files_changed)

# Update quality circuit breaker
circuit_breaker.record_test_result(passed=tests_passed, failed=tests_failed)

# Update token circuit breaker
circuit_breaker.record_tokens(current=token_count)
```

## Phase 4: Context Management

### Tier Management

```python
# Promote hot items for current work
context.promote("current_feature", ContextTier.HOT)

# Demote completed features
context.demote("completed_feature", ContextTier.COLD)

# Clear old entries periodically
context.cleanup_stale()
```

### Checkpoint on High Pressure

```python
if context.get_pressure().should_checkpoint:
    checkpoint = context.create_checkpoint(
        session_id=session_id,
        progress_summary=tracker.get_summary()
    )
    checkpoint.save(f".claude/checkpoints/auto-{iteration}.json")
```

## Phase 5: Decision Logic

### Continue If:
- Under iteration limit
- No circuit breakers tripped
- Context pressure < critical
- Features still pending
- Making progress

### Stop If:
- Max iterations reached → Log final state
- Circuit breaker tripped (unrecoverable) → Log which one
- No progress for 3+ iterations → Log stuck reason
- All features complete → Output CYCLE_COMPLETE
- Context critical + cannot checkpoint → Emergency stop

## Phase 6: Completion

### On Success

```python
# Final metrics
summary = metrics.get_summary()
log_info(f"Session complete: {summary}")

# Velocity for future estimation
velocity = tracker.velocity_tracker.velocity()
log_info(f"Final velocity: {velocity:.2f} points/hour")

# Save optimizer state for next session
optimizer.save(".claude/optimizer_state.json")
```

Output: `<promise>CYCLE_COMPLETE</promise>`

### On Failure

```python
# Save all state for recovery
metrics.save(".claude/metrics_final.json")
tracker.save(".claude/progress_final.json")
context.save_checkpoint(".claude/checkpoint_final.json")

# Log failure analysis
log_error(f"Session failed at iteration {iteration}")
log_error(f"Circuit breaker status: {circuit_breaker.get_status()}")
log_error(f"Last error: {last_error}")
```

## Integration Example

```python
# Full orchestration loop
from src.loop_control import LoopController, TaskComplexity
from src.circuit_breaker import MultiLevelCircuitBreaker
from src.context_manager import ContextManager
from src.dependency_graph import DependencyGraph
from src.error_classifier import ErrorClassifier
from src.metrics import SessionMetrics
from src.self_optimizer import SelfOptimizer

# Initialize
complexity = TaskComplexity.from_metrics(file_count=10, test_count=50, dependency_depth=3)
controller = LoopController(complexity)
circuit_breaker = MultiLevelCircuitBreaker()
context = ContextManager()
graph = DependencyGraph()
classifier = ErrorClassifier()
metrics = SessionMetrics(session_id="test")
optimizer = SelfOptimizer()

while controller.should_continue():
    # Check circuit breakers
    if circuit_breaker.check_all().any_tripped():
        break

    # Check context pressure
    if context.get_pressure().level == "critical":
        context.create_checkpoint(...)

    # Get next feature
    feature = graph.get_next_feature()
    if not feature:
        break

    try:
        # Do work
        result = implement_feature(feature)

        # Record success
        controller.record_progress(files_changed=result.files, tests_passed=result.tests)
        circuit_breaker.record_progress(files_changed=result.files)
        metrics.record_feature_completed(feature.id)
        optimizer.record_outcome(OutcomeType.SUCCESS, "feature", 1)

    except Exception as e:
        # Classify and handle error
        classification = classifier.classify(str(e))
        controller.record_error(str(e))
        circuit_breaker.record_failure()
        optimizer.record_outcome(OutcomeType.FAILURE, "error", 1)

# Final output
if graph.all_features_complete():
    print("<promise>CYCLE_COMPLETE</promise>")
else:
    print(f"Stopped: {controller.stop_reason}")
```

## State Files

| File | Purpose |
|------|---------|
| `.claude/.session_state.json` | Current session state |
| `.claude/.loop_state.json` | Loop iteration state |
| `.claude/checkpoints/*.json` | Context checkpoints |
| `.claude/metrics/*.json` | Metrics history |
| `.claude/optimizer_state.json` | Self-optimizer state |
| `specs/features.json` | Feature status |
| `specs/progress.md` | Human-readable progress |

## Hooks Integration

The orchestrator integrates with these hooks:

- `.claude/hooks/pre-compact.sh` - Checkpoint before compaction
- `.claude/hooks/circuit-breaker.sh` - Check circuit breakers
- `.claude/hooks/quality-gate.sh` - Quality checks before commit

## Skills Integration

Use these skills for specific tasks:

- `/project:plan` - Generate implementation plans
- `/project:architect` - Create technical designs
- `/project:implement` - TDD implementation
- `/project:test-e2e` - End-to-end testing
- `/project:fix` - Bug fixing with root cause analysis
- `/project:simplify` - Refactoring
- `/project:checkpoint` - Manual checkpoint creation

---

This orchestrator represents the full v2 framework capability, combining all 15 features into a cohesive autonomous development system.
