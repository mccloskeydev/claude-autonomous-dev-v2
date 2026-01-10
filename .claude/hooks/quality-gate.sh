#!/usr/bin/env bash
#
# Quality Gate Stop Hook
# Runs when Claude tries to stop - checks if work is actually complete
#
# Exit codes:
#   0 = Allow stop (work complete)
#   2 = Block stop and continue (work incomplete)
#

set -e

# Read stdin for session info
SESSION_INFO=$(cat)

# Configuration
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CONFIG_FILE="$PROJECT_ROOT/project.config.json"
FEATURES_FILE="$PROJECT_ROOT/specs/features.json"
PROGRESS_FILE="$PROJECT_ROOT/specs/progress.md"
ITERATION_FILE="$PROJECT_ROOT/.claude/.iteration_count"

# Load config
if [[ -f "$CONFIG_FILE" ]]; then
    MAX_ITERATIONS=$(jq -r '.max_iterations // 50' "$CONFIG_FILE")
    COMPLETION_PROMISE=$(jq -r '.completion_promise // "CYCLE_COMPLETE"' "$CONFIG_FILE")
    CB_NO_PROGRESS=$(jq -r '.circuit_breaker.no_progress_threshold // 3' "$CONFIG_FILE")
    CB_SAME_ERROR=$(jq -r '.circuit_breaker.same_error_threshold // 5' "$CONFIG_FILE")
else
    MAX_ITERATIONS=50
    COMPLETION_PROMISE="CYCLE_COMPLETE"
    CB_NO_PROGRESS=3
    CB_SAME_ERROR=5
fi

# Track iterations
if [[ -f "$ITERATION_FILE" ]]; then
    CURRENT_ITERATION=$(cat "$ITERATION_FILE")
else
    CURRENT_ITERATION=0
fi
CURRENT_ITERATION=$((CURRENT_ITERATION + 1))
echo "$CURRENT_ITERATION" > "$ITERATION_FILE"

# Function to log progress
log_progress() {
    local message="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] Iteration $CURRENT_ITERATION: $message" >> "$PROGRESS_FILE"
}

# Check for completion promise in Claude's last response
LAST_RESPONSE=$(echo "$SESSION_INFO" | jq -r '.stop_response // ""' 2>/dev/null || echo "")
if echo "$LAST_RESPONSE" | grep -q "$COMPLETION_PROMISE"; then
    log_progress "Completion promise detected. Allowing stop."
    rm -f "$ITERATION_FILE"
    exit 0
fi

# Check max iterations
if [[ $CURRENT_ITERATION -ge $MAX_ITERATIONS ]]; then
    log_progress "Max iterations ($MAX_ITERATIONS) reached. Forcing stop."
    rm -f "$ITERATION_FILE"
    echo "MAX_ITERATIONS reached. Review progress in specs/progress.md"
    exit 0
fi

# Check for incomplete features
if [[ -f "$FEATURES_FILE" ]]; then
    INCOMPLETE=$(jq '[.features[] | select(.passes == false)] | length' "$FEATURES_FILE" 2>/dev/null || echo "0")
    if [[ "$INCOMPLETE" -gt 0 ]]; then
        log_progress "Found $INCOMPLETE incomplete features. Continuing..."
        echo "CONTINUE: $INCOMPLETE features still incomplete"
        exit 2
    fi
fi

# Circuit breaker: Check for no progress (no file changes)
RECENT_CHANGES=$(git diff --stat HEAD~1 2>/dev/null | wc -l || echo "0")
if [[ "$RECENT_CHANGES" -eq 0 ]]; then
    NO_PROGRESS_FILE="$PROJECT_ROOT/.claude/.no_progress_count"
    if [[ -f "$NO_PROGRESS_FILE" ]]; then
        NO_PROGRESS_COUNT=$(cat "$NO_PROGRESS_FILE")
    else
        NO_PROGRESS_COUNT=0
    fi
    NO_PROGRESS_COUNT=$((NO_PROGRESS_COUNT + 1))
    echo "$NO_PROGRESS_COUNT" > "$NO_PROGRESS_FILE"

    if [[ $NO_PROGRESS_COUNT -ge $CB_NO_PROGRESS ]]; then
        log_progress "Circuit breaker: No progress for $CB_NO_PROGRESS iterations. Forcing stop."
        rm -f "$NO_PROGRESS_FILE"
        echo "CIRCUIT_BREAKER: No progress detected. Manual intervention needed."
        exit 0
    fi
else
    rm -f "$PROJECT_ROOT/.claude/.no_progress_count" 2>/dev/null || true
fi

# Run tests to verify state
TEST_CMD=$(jq -r '.test_command // "pytest -v"' "$CONFIG_FILE" 2>/dev/null || echo "pytest -v")
if $TEST_CMD > /dev/null 2>&1; then
    log_progress "Tests passing. Checking coverage..."

    # Check coverage if available
    COVERAGE_CMD=$(jq -r '.test_coverage_command // ""' "$CONFIG_FILE" 2>/dev/null || echo "")
    COVERAGE_THRESHOLD=$(jq -r '.coverage_threshold // 80' "$CONFIG_FILE" 2>/dev/null || echo "80")

    if [[ -n "$COVERAGE_CMD" ]]; then
        COVERAGE=$($COVERAGE_CMD 2>/dev/null | grep -oP 'TOTAL.*?\K\d+(?=%)' | head -1 || echo "100")
        if [[ "$COVERAGE" -lt "$COVERAGE_THRESHOLD" ]]; then
            log_progress "Coverage ($COVERAGE%) below threshold ($COVERAGE_THRESHOLD%). Continuing..."
            echo "CONTINUE: Coverage $COVERAGE% < $COVERAGE_THRESHOLD%"
            exit 2
        fi
    fi

    log_progress "All checks passed. Allowing stop."
    rm -f "$ITERATION_FILE"
    exit 0
else
    log_progress "Tests failing. Continuing to fix..."
    echo "CONTINUE: Tests still failing"
    exit 2
fi
