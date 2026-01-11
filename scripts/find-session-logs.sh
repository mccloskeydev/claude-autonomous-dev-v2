#!/bin/bash
# Find Session Logs
# Finds and displays session logs associated with a git commit
#
# Usage:
#   ./scripts/find-session-logs.sh <commit-sha>    # Find session that created commit
#   ./scripts/find-session-logs.sh --list          # List all sessions
#   ./scripts/find-session-logs.sh --latest        # Show latest session
#   ./scripts/find-session-logs.sh --format md <session-file>  # Convert to markdown

set -euo pipefail

LOGS_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}/logs/sessions"
INDEX_FILE="${CLAUDE_PROJECT_DIR:-$(pwd)}/logs/index.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Find session by commit SHA
find_by_commit() {
    local commit="$1"
    local short_commit=$(git rev-parse --short "$commit" 2>/dev/null || echo "$commit")

    # Check index first
    if [[ -f "$INDEX_FILE" ]]; then
        local session=$(jq -r --arg c "$short_commit" '.[$c] // empty' "$INDEX_FILE")
        if [[ -n "$session" ]]; then
            echo -e "${GREEN}Found in index:${NC} $session"
            show_session "$LOGS_DIR/$session"
            return 0
        fi
    fi

    # Fallback: search session files
    echo -e "${YELLOW}Searching session files...${NC}"
    for f in "$LOGS_DIR"/*.jsonl; do
        if [[ -f "$f" ]] && grep -q "\"$short_commit\"" "$f"; then
            echo -e "${GREEN}Found in:${NC} $(basename "$f")"
            show_session "$f"
            return 0
        fi
    done

    echo -e "${RED}No session found for commit $commit${NC}"
    return 1
}

# List all sessions
list_sessions() {
    echo -e "${BLUE}=== Session Logs ===${NC}"
    echo ""

    if [[ ! -d "$LOGS_DIR" ]] || [[ -z "$(ls -A "$LOGS_DIR" 2>/dev/null)" ]]; then
        echo "No session logs found."
        return
    fi

    printf "%-40s %-10s %-10s %s\n" "SESSION FILE" "START" "END" "COMMITS"
    printf "%-40s %-10s %-10s %s\n" "------------" "-----" "---" "-------"

    for f in "$LOGS_DIR"/*.jsonl; do
        [[ -f "$f" ]] || continue
        local name=$(basename "$f")
        local start_head=$(head -1 "$f" 2>/dev/null | jq -r '.head // "?"')
        local end_head=$(tail -1 "$f" 2>/dev/null | jq -r '.head // "?"')
        local commit_count=$(grep -c '"type":"input"' "$f" 2>/dev/null || echo "0")
        printf "%-40s %-10s %-10s %s inputs\n" "$name" "$start_head" "$end_head" "$commit_count"
    done
}

# Show latest session
show_latest() {
    local latest=$(ls -t "$LOGS_DIR"/*.jsonl 2>/dev/null | head -1)
    if [[ -n "$latest" ]]; then
        echo -e "${BLUE}Latest session:${NC} $(basename "$latest")"
        show_session "$latest"
    else
        echo "No session logs found."
    fi
}

# Show session details
show_session() {
    local file="$1"
    echo ""
    echo -e "${BLUE}=== Session: $(basename "$file") ===${NC}"
    echo ""

    while IFS= read -r line; do
        local type=$(echo "$line" | jq -r '.type')
        local ts=$(echo "$line" | jq -r '.ts')
        local ts_short=$(echo "$ts" | cut -d'T' -f2 | cut -d'Z' -f1)

        case "$type" in
            start)
                local head=$(echo "$line" | jq -r '.head')
                local branch=$(echo "$line" | jq -r '.branch')
                local modified=$(echo "$line" | jq -r '.modified_files')
                echo -e "${GREEN}[$ts_short] SESSION START${NC}"
                echo "  Branch: $branch @ $head"
                echo "  Modified files: $modified"
                echo ""
                ;;
            input)
                local content=$(echo "$line" | jq -r '.content')
                local head=$(echo "$line" | jq -r '.head')
                echo -e "${YELLOW}[$ts_short] USER INPUT${NC} (@ $head)"
                echo "$content" | sed 's/^/  > /'
                echo ""
                ;;
            end)
                local head=$(echo "$line" | jq -r '.head')
                local start_head=$(echo "$line" | jq -r '.start_head')
                local commits=$(echo "$line" | jq -r '.commits')
                echo -e "${GREEN}[$ts_short] SESSION END${NC}"
                echo "  Range: $start_head → $head"
                if [[ -n "$commits" ]] && [[ "$commits" != "" ]]; then
                    echo "  Commits created:"
                    echo "$commits" | sed 's/^/    /'
                fi
                ;;
        esac
    done < "$file"
}

# Convert session to markdown
to_markdown() {
    local file="$1"
    local output="${file%.jsonl}.md"

    echo "# Session Log" > "$output"
    echo "" >> "$output"
    echo "**File:** $(basename "$file")" >> "$output"
    echo "" >> "$output"

    while IFS= read -r line; do
        local type=$(echo "$line" | jq -r '.type')
        local ts=$(echo "$line" | jq -r '.ts')

        case "$type" in
            start)
                local head=$(echo "$line" | jq -r '.head')
                local branch=$(echo "$line" | jq -r '.branch')
                echo "## Session Start" >> "$output"
                echo "- **Time:** $ts" >> "$output"
                echo "- **Branch:** $branch" >> "$output"
                echo "- **HEAD:** $head" >> "$output"
                echo "" >> "$output"
                ;;
            input)
                local content=$(echo "$line" | jq -r '.content')
                echo "### User Input ($ts)" >> "$output"
                echo '```' >> "$output"
                echo "$content" >> "$output"
                echo '```' >> "$output"
                echo "" >> "$output"
                ;;
            end)
                local head=$(echo "$line" | jq -r '.head')
                local commits=$(echo "$line" | jq -r '.commits')
                echo "## Session End" >> "$output"
                echo "- **Time:** $ts" >> "$output"
                echo "- **HEAD:** $head" >> "$output"
                if [[ -n "$commits" ]]; then
                    echo "- **Commits:**" >> "$output"
                    echo '```' >> "$output"
                    echo "$commits" >> "$output"
                    echo '```' >> "$output"
                fi
                ;;
        esac
    done < "$file"

    echo -e "${GREEN}Created:${NC} $output"
}

# Main
case "${1:-}" in
    --list|-l)
        list_sessions
        ;;
    --latest)
        show_latest
        ;;
    --format)
        if [[ "${2:-}" == "md" ]] && [[ -n "${3:-}" ]]; then
            to_markdown "$3"
        else
            echo "Usage: $0 --format md <session-file>"
            exit 1
        fi
        ;;
    --help|-h|"")
        echo "Usage:"
        echo "  $0 <commit-sha>              Find session that created commit"
        echo "  $0 --list                    List all sessions"
        echo "  $0 --latest                  Show latest session"
        echo "  $0 --format md <file>        Convert session to markdown"
        ;;
    *)
        find_by_commit "$1"
        ;;
esac
