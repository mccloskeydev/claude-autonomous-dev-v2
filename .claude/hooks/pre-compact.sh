#!/usr/bin/env bash
#
# Pre-Compact Hook
# Runs before Claude Code compacts context
# Creates automatic checkpoint to preserve progress
#
# Exit codes:
#   0 = Continue with compaction
#   Non-zero = Abort (not recommended)
#

set -e

# Configuration
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CHECKPOINT_DIR="$PROJECT_ROOT/.claude/checkpoints"
PROGRESS_FILE="$PROJECT_ROOT/specs/progress.md"
FEATURES_FILE="$PROJECT_ROOT/specs/features.json"
SESSION_FILE="$PROJECT_ROOT/.claude/.session_id"

# Ensure checkpoint directory exists
mkdir -p "$CHECKPOINT_DIR"

# Generate session ID if not exists
if [[ -f "$SESSION_FILE" ]]; then
    SESSION_ID=$(cat "$SESSION_FILE")
else
    SESSION_ID="session-$(date +%Y%m%d-%H%M%S)"
    echo "$SESSION_ID" > "$SESSION_FILE"
fi

# Get timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
CHECKPOINT_FILE="$CHECKPOINT_DIR/checkpoint-$SESSION_ID-$TIMESTAMP.json"

# Gather hot context (current state)
HOT_CONTEXT="{}"
if [[ -f "$FEATURES_FILE" ]]; then
    # Get features in progress
    IN_PROGRESS=$(jq -c '[.features[] | select(.status == "in_progress") | {id: .id, description: .description}]' "$FEATURES_FILE" 2>/dev/null || echo "[]")
    HOT_CONTEXT=$(jq -n --argjson features "$IN_PROGRESS" '{features_in_progress: $features}')
fi

# Gather warm context (recent progress)
WARM_CONTEXT="{}"
if [[ -f "$PROGRESS_FILE" ]]; then
    # Get last 50 lines of progress
    RECENT_PROGRESS=$(tail -n 50 "$PROGRESS_FILE" | head -c 2000)
    WARM_CONTEXT=$(jq -n --arg progress "$RECENT_PROGRESS" '{recent_progress: $progress}')
fi

# Get completion stats
COMPLETED=$(jq '[.features[] | select(.passes == true)] | length' "$FEATURES_FILE" 2>/dev/null || echo "0")
TOTAL=$(jq '.features | length' "$FEATURES_FILE" 2>/dev/null || echo "0")
PROGRESS_SUMMARY="$COMPLETED/$TOTAL features complete"

# Create checkpoint JSON
cat > "$CHECKPOINT_FILE" << EOF
{
  "session_id": "$SESSION_ID",
  "created_at": $(date +%s),
  "progress_summary": "$PROGRESS_SUMMARY",
  "hot_context": $HOT_CONTEXT,
  "warm_context": $WARM_CONTEXT,
  "cold_context": {}
}
EOF

# Log the checkpoint
echo "$(date '+%Y-%m-%d %H:%M:%S') Pre-compact checkpoint: $CHECKPOINT_FILE" >> "$PROGRESS_FILE"

# Clean up old checkpoints (keep last 10)
cd "$CHECKPOINT_DIR"
ls -t checkpoint-*.json 2>/dev/null | tail -n +11 | xargs -r rm -f

# Exit successfully to allow compaction
exit 0
