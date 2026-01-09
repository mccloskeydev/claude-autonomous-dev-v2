# Checkpoint

Save current session state for handoff or recovery.

## Arguments
$ARGUMENTS - Optional reason for checkpoint (e.g., "before refactor")

## Instructions

Activate the `checkpoint` skill:

1. Gather git status and recent commits
2. Read specs/*.md files for current state
3. Create structured handoff document
4. Save to specs/checkpoint-{timestamp}.md
5. Commit the checkpoint
6. Update specs/progress.md

Use before:
- Context compaction (/compact)
- Clearing context (/clear)
- Major refactors
- End of work session
