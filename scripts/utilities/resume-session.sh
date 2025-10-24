#!/bin/bash
set -euo pipefail

# resume-session.sh - Restore Chrome debug session from saved state
# Purpose: Load session file and export environment variables for continued debugging
# Usage: ./resume-session.sh <session-file>

# ============================================================================
# Parameter Parsing
# ============================================================================

if [ $# -lt 1 ]; then
    echo "Usage: $0 <session-file>" >&2
    echo "" >&2
    echo "Arguments:" >&2
    echo "  session-file : Path to saved session JSON file" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 /tmp/cdp-session-20251024_131100.json" >&2
    echo "" >&2
    echo "The script exports these environment variables:" >&2
    echo "  CHROME_PID, WS_URL, PAGE_ID, TARGET_URL, CDP_PORT, PROFILE_PATH" >&2
    exit 2
fi

SESSION_FILE="$1"

# ============================================================================
# Validation
# ============================================================================

# Validate session file exists
if [ ! -f "$SESSION_FILE" ]; then
    jq -nc \
        --arg status "error" \
        --arg code "SESSION_NOT_FOUND" \
        --arg message "Session file not found: $SESSION_FILE" \
        --arg recovery "Launch Chrome and save session: ./chrome-launcher.sh --mode=headed && ./scripts/save-session.sh \$CHROME_PID" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# Validate session file is valid JSON
if ! jq empty "$SESSION_FILE" 2>/dev/null; then
    jq -nc \
        --arg status "error" \
        --arg code "SESSION_CORRUPT" \
        --arg message "Session file is not valid JSON: $SESSION_FILE" \
        --arg recovery "Re-save session or delete corrupted file: rm $SESSION_FILE" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# ============================================================================
# Load Session Variables
# ============================================================================

echo "Loading session from $SESSION_FILE..." >&2

# Load session variables using direct jq assignment
CHROME_PID=$(jq -r '.chrome_pid // empty' "$SESSION_FILE")
WS_URL=$(jq -r '.ws_url // empty' "$SESSION_FILE")
PAGE_ID=$(jq -r '.page_id // empty' "$SESSION_FILE")
TARGET_URL=$(jq -r '.target_url // empty' "$SESSION_FILE")
CDP_PORT=$(jq -r '.port // empty' "$SESSION_FILE")
PROFILE_PATH=$(jq -r '.profile // empty' "$SESSION_FILE")
TIMESTAMP=$(jq -r '.timestamp // empty' "$SESSION_FILE")

# Validate required fields are not null or empty
MISSING_FIELDS=()
[ -z "$CHROME_PID" ] || [ "$CHROME_PID" = "null" ] && MISSING_FIELDS+=("chrome_pid")
[ -z "$WS_URL" ] || [ "$WS_URL" = "null" ] && MISSING_FIELDS+=("ws_url")
[ -z "$PAGE_ID" ] || [ "$PAGE_ID" = "null" ] && MISSING_FIELDS+=("page_id")
[ -z "$TARGET_URL" ] || [ "$TARGET_URL" = "null" ] && MISSING_FIELDS+=("target_url")
[ -z "$CDP_PORT" ] || [ "$CDP_PORT" = "null" ] && MISSING_FIELDS+=("port")

if [ ${#MISSING_FIELDS[@]} -gt 0 ]; then
    MISSING_LIST=$(IFS=, ; echo "${MISSING_FIELDS[*]}")
    jq -nc \
        --arg status "error" \
        --arg code "SESSION_INCOMPLETE" \
        --arg message "Session file missing required fields: $MISSING_LIST" \
        --arg recovery "Re-save session from running Chrome instance" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# ============================================================================
# Validate Chrome Process
# ============================================================================

echo "Validating Chrome PID $CHROME_PID..." >&2

# Validate Chrome PID is still alive
if ! kill -0 "$CHROME_PID" 2>/dev/null; then
    jq -nc \
        --arg status "error" \
        --arg code "SESSION_STALE" \
        --arg message "Chrome process $CHROME_PID from session is not running (session saved at $TIMESTAMP)" \
        --arg recovery "Launch Chrome and save new session: ./chrome-launcher.sh --mode=headed && ./scripts/save-session.sh \$!" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# Calculate session age in seconds
if [ -n "$TIMESTAMP" ] && [ "$TIMESTAMP" != "null" ]; then
    SAVED_EPOCH=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$TIMESTAMP" +%s 2>/dev/null || echo "0")
    CURRENT_EPOCH=$(date -u +%s)
    SESSION_AGE_SECONDS=$((CURRENT_EPOCH - SAVED_EPOCH))
else
    SESSION_AGE_SECONDS=0
fi

echo "Session age: ${SESSION_AGE_SECONDS}s" >&2

# ============================================================================
# Export Session Variables
# ============================================================================

# Export for sourcing by caller
export CHROME_PID
export WS_URL
export PAGE_ID
export TARGET_URL
export CDP_PORT
export PROFILE_PATH

echo "Session resumed successfully" >&2
echo "  Chrome PID: $CHROME_PID" >&2
echo "  Target URL: $TARGET_URL" >&2
echo "  WebSocket: $WS_URL" >&2
echo "" >&2
echo "Environment variables exported:" >&2
echo "  CHROME_PID=$CHROME_PID" >&2
echo "  WS_URL=$WS_URL" >&2
echo "  PAGE_ID=$PAGE_ID" >&2
echo "  TARGET_URL=$TARGET_URL" >&2
echo "  CDP_PORT=$CDP_PORT" >&2
echo "  PROFILE_PATH=$PROFILE_PATH" >&2

# ============================================================================
# Success Response
# ============================================================================

jq -nc \
    --arg status "success" \
    --arg session_file "$SESSION_FILE" \
    --argjson chrome_pid "$CHROME_PID" \
    --arg ws_url "$WS_URL" \
    --arg page_id "$PAGE_ID" \
    --arg target_url "$TARGET_URL" \
    --argjson session_age_seconds "$SESSION_AGE_SECONDS" \
    '{status: $status, session_file: $session_file, chrome_pid: $chrome_pid, ws_url: $ws_url, page_id: $page_id, target_url: $target_url, session_age_seconds: $session_age_seconds}' >&1

exit 0
