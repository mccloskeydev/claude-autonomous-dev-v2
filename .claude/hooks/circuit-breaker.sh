#!/usr/bin/env bash
#
# Circuit Breaker Hook
# Multi-level circuit breaker checks for autonomous development sessions
#
# Levels:
#   1. Token - Approaching context limit
#   2. Progress - No meaningful changes
#   3. Quality - Tests degrading
#   4. Time - Wall clock limits
#
# Exit codes:
#   0 = All clear, continue
#   1 = Warning (logged)
#   2 = Tripped (stop)
#

set -e

# Configuration
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CONFIG_FILE="$PROJECT_ROOT/project.config.json"
PROGRESS_FILE="$PROJECT_ROOT/specs/progress.md"
FEATURES_FILE="$PROJECT_ROOT/specs/features.json"
CB_STATE_FILE="$PROJECT_ROOT/.claude/.circuit_breaker_state.json"
SESSION_START_FILE="$PROJECT_ROOT/.claude/.session_start"

# Load config
if [[ -f "$CONFIG_FILE" ]]; then
    MAX_DURATION=$(jq -r '.circuit_breaker.max_duration_seconds // 7200' "$CONFIG_FILE")
    NO_PROGRESS_THRESHOLD=$(jq -r '.circuit_breaker.no_progress_threshold // 3' "$CONFIG_FILE")
    TOKEN_THRESHOLD_PCT=$(jq -r '.circuit_breaker.token_threshold_pct // 90' "$CONFIG_FILE")
    OUTPUT_DECLINE_THRESHOLD=$(jq -r '.circuit_breaker.output_decline_threshold // 70' "$CONFIG_FILE")
else
    MAX_DURATION=7200
    NO_PROGRESS_THRESHOLD=3
    TOKEN_THRESHOLD_PCT=90
    OUTPUT_DECLINE_THRESHOLD=70
fi

# Initialize session start time if needed
if [[ ! -f "$SESSION_START_FILE" ]]; then
    date +%s > "$SESSION_START_FILE"
fi
SESSION_START=$(cat "$SESSION_START_FILE")

# Initialize state file if needed
if [[ ! -f "$CB_STATE_FILE" ]]; then
    echo '{
        "no_progress_count": 0,
        "test_failures_trend": [],
        "last_check_time": 0,
        "warnings": []
    }' > "$CB_STATE_FILE"
fi

# Load state
NO_PROGRESS_COUNT=$(jq -r '.no_progress_count // 0' "$CB_STATE_FILE")
WARNINGS=()

# Function to log
log_cb() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] CB [$level]: $message" >> "$PROGRESS_FILE"
}

# Function to update state
update_state() {
    local no_progress="$1"
    local warnings_json="$2"

    cat > "$CB_STATE_FILE" << EOF
{
    "no_progress_count": $no_progress,
    "last_check_time": $(date +%s),
    "warnings": $warnings_json
}
EOF
}

#
# Level 1: Time Circuit Breaker
#
check_time() {
    local now=$(date +%s)
    local elapsed=$((now - SESSION_START))
    local pct=$((elapsed * 100 / MAX_DURATION))

    if [[ $elapsed -ge $MAX_DURATION ]]; then
        log_cb "TIME" "Time limit exceeded: ${elapsed}s >= ${MAX_DURATION}s"
        echo "CIRCUIT_BREAKER_TRIPPED: Time limit exceeded"
        exit 2
    fi

    if [[ $pct -ge 80 ]]; then
        local remaining=$((MAX_DURATION - elapsed))
        log_cb "TIME" "Warning: ${pct}% time used, ${remaining}s remaining"
        WARNINGS+=("Time: ${pct}% used")
    fi
}

#
# Level 2: Progress Circuit Breaker
#
check_progress() {
    # Check recent git changes
    local changes=$(git diff --stat HEAD~1 2>/dev/null | wc -l || echo "0")

    if [[ "$changes" -eq 0 ]]; then
        NO_PROGRESS_COUNT=$((NO_PROGRESS_COUNT + 1))

        if [[ $NO_PROGRESS_COUNT -ge $NO_PROGRESS_THRESHOLD ]]; then
            log_cb "PROGRESS" "No progress for ${NO_PROGRESS_COUNT} iterations"
            echo "CIRCUIT_BREAKER_TRIPPED: No progress detected"
            exit 2
        fi

        WARNINGS+=("Progress: No changes for ${NO_PROGRESS_COUNT} iterations")
    else
        NO_PROGRESS_COUNT=0
    fi
}

#
# Level 3: Quality Circuit Breaker
#
check_quality() {
    # Run tests and check results
    local test_cmd=$(jq -r '.test_command // "pytest -v"' "$CONFIG_FILE" 2>/dev/null || echo "pytest -v")

    # Quick test run to get status
    local test_output
    test_output=$($test_cmd 2>&1) || true

    # Count failures
    local failed=$(echo "$test_output" | grep -c "FAILED" || echo "0")

    if [[ "$failed" -gt 0 ]]; then
        WARNINGS+=("Quality: $failed test(s) failing")
    fi
}

#
# Level 4: Feature Progress Check
#
check_features() {
    if [[ -f "$FEATURES_FILE" ]]; then
        local incomplete=$(jq '[.features[] | select(.passes == false)] | length' "$FEATURES_FILE" 2>/dev/null || echo "0")
        local total=$(jq '.features | length' "$FEATURES_FILE" 2>/dev/null || echo "0")

        if [[ "$incomplete" -gt 0 ]]; then
            log_cb "FEATURES" "Progress: $((total - incomplete))/${total} features complete"
        fi
    fi
}

# Run checks
check_time
check_progress
check_quality
check_features

# Update state
warnings_json=$(printf '%s\n' "${WARNINGS[@]}" | jq -R . | jq -s .)
update_state "$NO_PROGRESS_COUNT" "$warnings_json"

# Report warnings
if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    log_cb "WARNING" "Warnings: ${WARNINGS[*]}"
    echo "CIRCUIT_BREAKER_WARNING: ${WARNINGS[*]}"
    exit 1
fi

# All clear
exit 0
