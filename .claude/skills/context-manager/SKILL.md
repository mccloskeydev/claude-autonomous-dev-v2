---
name: context-manager
description: |
  Automatic context pressure monitoring and checkpointing. Manages hierarchical memory
  (hot/warm/cold tiers), monitors context usage, triggers automatic checkpoints when
  pressure is high, and provides context compression and restoration.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
---

# Context Manager - Intelligent Context Management

You are the context manager for long-running autonomous development sessions. Your role is to monitor context pressure and manage memory efficiently.

## Context Pressure Levels

| Level | Usage | Action |
|-------|-------|--------|
| Low | < 30% | Continue normally |
| Medium | 30-70% | Start demoting stale context |
| High | 70-90% | Create checkpoint, compress |
| Critical | > 90% | Immediate checkpoint, clear warm/cold |

## Hierarchical Memory Tiers

### Hot Tier (< 3 minutes old)
Current task context:
- Active feature being implemented
- Current test being written
- Immediate decisions

### Warm Tier (3 min - 30 min old)
Recent decisions:
- Completed features
- Past test results
- Architecture decisions made

### Cold Tier (30 min - 24 hours)
Archived context:
- Completed session summaries
- Historical decisions
- Reference information

## Automatic Checkpointing

Checkpoint when:
1. Context pressure >= 70%
2. Before major context switch
3. Before risky operations
4. Periodically (every 30 iterations)

## Using the Python Module

```python
from src.context_manager import ContextManager, ContextTier, ContextPressure

# Create manager
manager = ContextManager(max_tokens=100000)

# Add context entries
manager.add("current_feature", "Login system", tier=ContextTier.HOT)
manager.add("architecture", "REST API design", tier=ContextTier.WARM)

# Check pressure
pressure = manager.pressure
print(f"Usage: {pressure.percentage:.1f}%")
print(f"Level: {pressure.level}")

if pressure.should_checkpoint:
    checkpoint = manager.create_checkpoint(
        session_id="session-123",
        progress_summary="Completed login, starting dashboard"
    )

# Demote stale entries
manager.demote_stale()

# Compress if needed
manager.compress()

# Get summary
summary = manager.get_summary()
print(f"Hot: {summary['hot_count']}, Warm: {summary['warm_count']}")

# Restore from checkpoint
manager.restore_checkpoint(Path("checkpoint.json"))
```

## Checkpoint Format

```json
{
  "session_id": "session-123",
  "progress_summary": "What was accomplished",
  "created_at": 1704067200.0,
  "hot_context": {
    "current_task": "Implementing feature X",
    "current_file": "src/feature.py"
  },
  "warm_context": {
    "completed_features": ["A", "B", "C"],
    "decisions": ["Used REST", "Chose PostgreSQL"]
  },
  "cold_context": {
    "session_start": "2024-01-01T00:00:00Z",
    "initial_plan": "..."
  }
}
```

## Context Pressure Monitoring

The pre-compact hook checks context pressure before Claude Code compacts:

```bash
# .claude/hooks/pre-compact.sh
# Automatically creates checkpoint before compaction
```

## Workflow

1. **Monitor** - Track token usage continuously
2. **Demote** - Move stale entries to lower tiers
3. **Checkpoint** - Save state when pressure is high
4. **Compress** - Reduce token usage of verbose entries
5. **Clear** - Remove cold tier if critical
6. **Restore** - Load from checkpoint after compaction

## Best Practices

1. **Always checkpoint before risky operations**
2. **Demote stale entries frequently** - Keep hot tier small
3. **Use compression for verbose context** - Truncate long values
4. **Keep checkpoints organized** - Clean up old ones
5. **Restore context after /clear** - Don't lose progress

## Integration with Loop Control

```python
from src.loop_control import LoopController
from src.context_manager import ContextManager

controller = LoopController()
manager = ContextManager()

# Each iteration
manager.add("iteration", controller.state.iteration, tier=ContextTier.HOT)

# Check if should checkpoint
if manager.should_checkpoint():
    checkpoint = manager.create_checkpoint(
        session_id=f"auto-{controller.state.iteration}",
        progress_summary=f"Iteration {controller.state.iteration}"
    )
    # Optionally clear warm tier to free space
    manager.clear_tier(ContextTier.WARM)
```

## File Locations

- Checkpoints: `.claude/checkpoints/`
- State file: `.claude/.context_state.json`
- Config: `project.config.json` (max_tokens setting)
