#!/usr/bin/env bash
#
# Subagent Complete Hook
# Runs when a subagent finishes - logs results and notifies
#

set -e

# Read stdin for subagent info
SUBAGENT_INFO=$(cat)

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROGRESS_FILE="$PROJECT_ROOT/specs/progress.md"

# Extract subagent details
SUBAGENT_NAME=$(echo "$SUBAGENT_INFO" | jq -r '.subagent_name // "unknown"' 2>/dev/null || echo "unknown")
RESULT_SUMMARY=$(echo "$SUBAGENT_INFO" | jq -r '.result_summary // ""' 2>/dev/null || echo "")

# Log to progress file
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
{
    echo ""
    echo "### Subagent: $SUBAGENT_NAME"
    echo "**Completed:** $TIMESTAMP"
    if [[ -n "$RESULT_SUMMARY" ]]; then
        echo "**Result:** $RESULT_SUMMARY"
    fi
} >> "$PROGRESS_FILE"

# Desktop notification (if available)
if command -v notify-send &> /dev/null; then
    notify-send "Claude Subagent Complete" "$SUBAGENT_NAME finished" 2>/dev/null || true
elif command -v osascript &> /dev/null; then
    osascript -e "display notification \"$SUBAGENT_NAME finished\" with title \"Claude Subagent Complete\"" 2>/dev/null || true
fi

exit 0
