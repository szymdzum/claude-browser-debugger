#!/bin/bash
set -euo pipefail

# save-session.sh - Persist Chrome debug session state for recovery
# Purpose: Save Chrome PID, WebSocket URL, and page metadata to JSON file
# Usage: ./save-session.sh <chrome-pid> [port] [output-file]

# ============================================================================
# Parameter Parsing
# ============================================================================

if [ $# -lt 1 ]; then
    echo "Usage: $0 <chrome-pid> [port] [output-file]" >&2
    echo "" >&2
    echo "Arguments:" >&2
    echo "  chrome-pid  : Chrome process ID to save" >&2
    echo "  port        : Debug port (default: 9222)" >&2
    echo "  output-file : Session file path (default: /tmp/cdp-session-TIMESTAMP.json)" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 12345" >&2
    echo "  $0 12345 9222" >&2
    echo "  $0 12345 9222 /tmp/my-session.json" >&2
    exit 2
fi

CHROME_PID="$1"
PORT="${2:-9222}"

# Generate filename timestamp (YYYYMMDD_HHMMSS)
FILE_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT="${3:-/tmp/cdp-session-${FILE_TIMESTAMP}.json}"

# ============================================================================
# Validation
# ============================================================================

# Validate Chrome PID is alive
if ! kill -0 "$CHROME_PID" 2>/dev/null; then
    jq -nc \
        --arg status "error" \
        --arg code "CHROME_NOT_RUNNING" \
        --arg message "Chrome process $CHROME_PID is not running" \
        --arg recovery "Launch Chrome first: ./chrome-launcher.sh --mode=headed" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# ============================================================================
# Fetch Chrome Session Information
# ============================================================================

echo "Fetching session information from Chrome PID $CHROME_PID on port $PORT..." >&2

# Fetch CDP endpoint data
CDP_RESPONSE=$(curl -s "http://localhost:${PORT}/json" 2>&1) || {
    jq -nc \
        --arg status "error" \
        --arg code "CHROME_NOT_RESPONDING" \
        --arg message "Chrome PID $CHROME_PID not responding to http://localhost:${PORT}/json" \
        --arg recovery "Check if Chrome crashed: ps aux | grep $CHROME_PID" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
}

# Validate JSON response
if ! echo "$CDP_RESPONSE" | jq empty 2>/dev/null; then
    jq -nc \
        --arg status "error" \
        --arg code "CHROME_NOT_RESPONDING" \
        --arg message "Invalid JSON response from Chrome CDP endpoint" \
        --arg recovery "Check if Chrome is running with debug port: lsof -ti :${PORT}" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# Extract first page information
WS_URL=$(echo "$CDP_RESPONSE" | jq -r '.[0].webSocketDebuggerUrl // empty')
PAGE_ID=$(echo "$CDP_RESPONSE" | jq -r '.[0].id // empty')
TARGET_URL=$(echo "$CDP_RESPONSE" | jq -r '.[0].url // empty')
PAGE_COUNT=$(echo "$CDP_RESPONSE" | jq 'length')

# Validate required fields
if [ -z "$WS_URL" ] || [ "$WS_URL" = "null" ]; then
    jq -nc \
        --arg status "error" \
        --arg code "NO_PAGES_FOUND" \
        --arg message "Chrome running but no pages available on port $PORT" \
        --arg recovery "Navigate to a URL in Chrome or check port number" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# Detect profile path (best effort - may not be available from CDP)
# Try to detect from process command line
PROFILE=$(ps -p "$CHROME_PID" -o command= | grep -o '\--user-data-dir=[^ ]*' | cut -d= -f2 || echo "")
if [ -z "$PROFILE" ]; then
    # Fallback: use common default paths
    if pgrep -f "chrome.*--headless" >/dev/null 2>&1; then
        PROFILE="/tmp/chrome-headless-${CHROME_PID}"
    else
        PROFILE="$HOME/.chrome-debug-profile"
    fi
fi

# Generate ISO 8601 UTC timestamp for session content
CONTENT_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ============================================================================
# Write Session File
# ============================================================================

echo "Writing session to $OUTPUT..." >&2

# Create session JSON
jq -nc \
    --argjson chrome_pid "$CHROME_PID" \
    --arg ws_url "$WS_URL" \
    --arg page_id "$PAGE_ID" \
    --arg target_url "$TARGET_URL" \
    --argjson port "$PORT" \
    --arg profile "$PROFILE" \
    --arg timestamp "$CONTENT_TIMESTAMP" \
    '{
        chrome_pid: $chrome_pid,
        ws_url: $ws_url,
        page_id: $page_id,
        target_url: $target_url,
        port: $port,
        profile: $profile,
        timestamp: $timestamp
    }' > "$OUTPUT" || {
    jq -nc \
        --arg status "error" \
        --arg code "FILE_WRITE_FAILED" \
        --arg message "Cannot write to session file: $OUTPUT" \
        --arg recovery "Check directory permissions: ls -ld $(dirname $OUTPUT)" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
}

echo "Session saved successfully" >&2

# ============================================================================
# Success Response
# ============================================================================

jq -nc \
    --arg status "success" \
    --arg session_file "$OUTPUT" \
    --argjson chrome_pid "$CHROME_PID" \
    --argjson page_count "$PAGE_COUNT" \
    --arg timestamp "$CONTENT_TIMESTAMP" \
    '{status: $status, session_file: $session_file, chrome_pid: $chrome_pid, page_count: $page_count, timestamp: $timestamp}' >&1

exit 0
