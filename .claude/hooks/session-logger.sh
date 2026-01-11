#!/bin/bash
# Session Logger Hook
# Logs CLI input/output with git association for debugging
#
# Usage: Called by Claude Code hooks (UserPromptSubmit, Stop)
# Args: $1 = event type (start, input, end)
#       $2 = content (optional, for input events)

set -euo pipefail

LOGS_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}/logs/sessions"
INDEX_FILE="${CLAUDE_PROJECT_DIR:-$(pwd)}/logs/index.json"

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Get current git state
get_git_head() {
    git rev-parse --short HEAD 2>/dev/null || echo "no-git"
}

get_git_branch() {
    git branch --show-current 2>/dev/null || echo "detached"
}

get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

get_timestamp_for_filename() {
    date +"%Y-%m-%dT%H-%M-%S"
}

# Session file is determined by SESSION_ID env var or created on first call
get_session_file() {
    local session_id="${CLAUDE_SESSION_ID:-$$}"
    local head=$(get_git_head)

    # Check if we already have a session file for this session
    local existing=$(ls -1 "$LOGS_DIR"/*-"$session_id".jsonl 2>/dev/null | head -1)
    if [[ -n "$existing" ]]; then
        echo "$existing"
        return
    fi

    # Create new session file
    local ts=$(get_timestamp_for_filename)
    echo "$LOGS_DIR/${ts}-${head}-${session_id}.jsonl"
}

# Log an entry
log_entry() {
    local type="$1"
    local session_file=$(get_session_file)
    local ts=$(get_timestamp)
    local head=$(get_git_head)
    local branch=$(get_git_branch)

    case "$type" in
        start)
            # Log session start with git state
            local modified_files=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
            echo "{\"ts\":\"$ts\",\"type\":\"start\",\"head\":\"$head\",\"branch\":\"$branch\",\"modified_files\":$modified_files}" >> "$session_file"
            ;;
        input)
            # Log user input (from stdin or $2)
            local content="${2:-}"
            if [[ -z "$content" ]] && [[ -p /dev/stdin ]]; then
                content=$(cat)
            fi
            # Escape content for JSON
            content=$(echo "$content" | jq -Rs '.')
            echo "{\"ts\":\"$ts\",\"type\":\"input\",\"head\":\"$head\",\"content\":$content}" >> "$session_file"
            ;;
        end)
            # Log session end with commit range
            local start_head=$(head -1 "$session_file" 2>/dev/null | jq -r '.head // empty')
            local commits=""
            if [[ -n "$start_head" ]] && [[ "$start_head" != "$head" ]]; then
                commits=$(git log --oneline "$start_head".."$head" 2>/dev/null | jq -Rs '.')
            else
                commits='""'
            fi
            echo "{\"ts\":\"$ts\",\"type\":\"end\",\"head\":\"$head\",\"start_head\":\"$start_head\",\"commits\":$commits}" >> "$session_file"

            # Update index for commit lookup
            update_index "$session_file" "$start_head" "$head"
            ;;
    esac
}

# Update the index file for commit-to-session lookup
update_index() {
    local session_file="$1"
    local start_head="$2"
    local end_head="$3"

    # Get commits created in this session
    if [[ -n "$start_head" ]] && [[ "$start_head" != "$end_head" ]]; then
        local commits=$(git log --format="%h" "$start_head".."$end_head" 2>/dev/null)

        # Initialize index if needed
        if [[ ! -f "$INDEX_FILE" ]]; then
            echo '{}' > "$INDEX_FILE"
        fi

        # Add each commit to index
        local session_name=$(basename "$session_file")
        for commit in $commits; do
            local tmp=$(mktemp)
            jq --arg c "$commit" --arg s "$session_name" '.[$c] = $s' "$INDEX_FILE" > "$tmp" && mv "$tmp" "$INDEX_FILE"
        done
    fi
}

# Main
EVENT_TYPE="${1:-}"

case "$EVENT_TYPE" in
    start|input|end)
        log_entry "$EVENT_TYPE" "${2:-}"
        ;;
    *)
        echo "Usage: $0 {start|input|end} [content]" >&2
        exit 1
        ;;
esac
