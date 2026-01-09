#!/usr/bin/env bash
#
# Post-Edit Hook
# Runs after any file edit/write to maintain code quality
#

set -e

# Read stdin for tool info
TOOL_INFO=$(cat)

# Get the edited file path
FILE_PATH=$(echo "$TOOL_INFO" | jq -r '.file_path // ""' 2>/dev/null || echo "")

if [[ -z "$FILE_PATH" ]] || [[ ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# Configuration
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CONFIG_FILE="$PROJECT_ROOT/project.config.json"

# Determine file type and run appropriate formatter
EXT="${FILE_PATH##*.}"

case "$EXT" in
    py)
        # Python: format with ruff
        if command -v ruff &> /dev/null; then
            ruff format "$FILE_PATH" 2>/dev/null || true
            ruff check --fix "$FILE_PATH" 2>/dev/null || true
        fi
        ;;
    ts|tsx|js|jsx)
        # TypeScript/JavaScript: format with prettier or biome
        if command -v bunx &> /dev/null; then
            bunx biome format --write "$FILE_PATH" 2>/dev/null || \
            bunx prettier --write "$FILE_PATH" 2>/dev/null || true
        elif command -v npx &> /dev/null; then
            npx prettier --write "$FILE_PATH" 2>/dev/null || true
        fi
        ;;
    json)
        # JSON: format with jq or prettier
        if command -v jq &> /dev/null; then
            TMP_FILE=$(mktemp)
            jq '.' "$FILE_PATH" > "$TMP_FILE" 2>/dev/null && mv "$TMP_FILE" "$FILE_PATH" || rm -f "$TMP_FILE"
        fi
        ;;
    md)
        # Markdown: no auto-formatting (preserve intentional formatting)
        ;;
esac

exit 0
