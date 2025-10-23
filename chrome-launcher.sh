#!/bin/bash
# chrome-launcher.sh - Start Chrome with debugging enabled
# Implements contract defined in LAUNCHER_CONTRACT.md

set -euo pipefail

# Default values
MODE=""
PORT="9222"
PROFILE=""
URL="about:blank"

# Parse arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --mode=*)
            MODE="${1#--mode=}"
            ;;
        --port=*)
            PORT="${1#--port=}"
            ;;
        --profile=*)
            PROFILE="${1#--profile=}"
            ;;
        --url=*)
            URL="${1#--url=}"
            ;;
        *)
            echo '{"status":"error","code":"INVALID_ARGUMENT","message":"Unknown argument: '"$1"'","recovery":"See LAUNCHER_CONTRACT.md for usage"}' >&1
            exit 1
            ;;
    esac
    shift
done

# Validate required arguments
if [ -z "$MODE" ]; then
    echo '{"status":"error","code":"MISSING_ARGUMENT","message":"--mode is required","recovery":"Use --mode=headless or --mode=headed"}' >&1
    exit 1
fi

if [ "$MODE" != "headless" ] && [ "$MODE" != "headed" ]; then
    echo '{"status":"error","code":"INVALID_MODE","message":"Mode must be headless or headed","recovery":"Use --mode=headless or --mode=headed"}' >&1
    exit 1
fi

# Helper function to output JSON and exit
error_exit() {
    local code="$1"
    local message="$2"
    local recovery="$3"
    local exit_code="${4:-1}"

    jq -n \
        --arg status "error" \
        --arg code "$code" \
        --arg message "$message" \
        --arg recovery "$recovery" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1

    exit "$exit_code"
}

# Detect Chrome binary
echo "Detecting Chrome binary..." >&2

if [[ "$OSTYPE" == "darwin"* ]]; then
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if [ ! -f "$CHROME" ]; then
        error_exit "CHROME_NOT_FOUND" \
            "Chrome not found at $CHROME" \
            "Install Chrome: brew install --cask google-chrome" \
            1
    fi
elif command -v google-chrome &> /dev/null; then
    CHROME="google-chrome"
elif command -v google-chrome-stable &> /dev/null; then
    CHROME="google-chrome-stable"
elif command -v chromium-browser &> /dev/null; then
    CHROME="chromium-browser"
elif command -v chromium &> /dev/null; then
    CHROME="chromium"
else
    error_exit "CHROME_NOT_FOUND" \
        "Chrome/Chromium not found in PATH" \
        "Install Chrome: apt-get install google-chrome-stable (Linux)" \
        1
fi

echo "Found Chrome: $CHROME" >&2

# Port resolution
RESOLVED_PORT=""

if [ "$PORT" = "auto" ]; then
    echo "Finding free port in range 9222-9299..." >&2

    for port in {9222..9299}; do
        if ! lsof -i ":$port" > /dev/null 2>&1; then
            RESOLVED_PORT="$port"
            echo "Found free port: $RESOLVED_PORT" >&2
            break
        fi
    done

    if [ -z "$RESOLVED_PORT" ]; then
        error_exit "PORT_RANGE_EXHAUSTED" \
            "All ports in range 9222-9299 are busy" \
            "pkill -f 'chrome.*922[0-9]' && sleep 1" \
            2
    fi
else
    # Check if specific port is available
    if lsof -i ":$PORT" > /dev/null 2>&1; then
        BUSY_PID=$(lsof -ti ":$PORT" | head -1)
        error_exit "PORT_BUSY" \
            "Port $PORT is already in use by PID $BUSY_PID" \
            "pkill -f 'chrome.*$PORT' && sleep 1, or use --port=auto" \
            2
    fi
    RESOLVED_PORT="$PORT"
    echo "Using port: $RESOLVED_PORT" >&2
fi

# Profile resolution
RESOLVED_PROFILE=""

if [ -z "$PROFILE" ]; then
    # Use defaults based on mode
    if [ "$MODE" = "headless" ]; then
        RESOLVED_PROFILE="/tmp/chrome-headless-$$"
    else
        RESOLVED_PROFILE="$HOME/.chrome-debug-profile"
    fi
elif [ "$PROFILE" = "none" ]; then
    RESOLVED_PROFILE="/tmp/chrome-headless-$$"
else
    RESOLVED_PROFILE="$PROFILE"
fi

echo "Using profile: $RESOLVED_PROFILE" >&2

# Create profile directory if it doesn't exist
if [ ! -d "$RESOLVED_PROFILE" ]; then
    echo "Creating profile directory..." >&2
    if ! mkdir -p "$RESOLVED_PROFILE" 2>/dev/null; then
        error_exit "PROFILE_PERMISSION" \
            "Cannot create profile directory: $RESOLVED_PROFILE" \
            "mkdir -p $RESOLVED_PROFILE && chmod 755 $RESOLVED_PROFILE" \
            3
    fi
fi

# Check if profile is locked
if [ -f "$RESOLVED_PROFILE/SingletonLock" ]; then
    echo "Warning: Profile may be locked by another Chrome instance" >&2
    # Try to remove stale lock
    if ! rm -f "$RESOLVED_PROFILE/SingletonLock" 2>/dev/null; then
        error_exit "PROFILE_LOCKED" \
            "Profile directory is locked: $RESOLVED_PROFILE/SingletonLock" \
            "rm -rf $RESOLVED_PROFILE/SingletonLock" \
            3
    fi
fi

# Build Chrome command
CHROME_ARGS=(
    --remote-debugging-port="$RESOLVED_PORT"
    --user-data-dir="$RESOLVED_PROFILE"
    --no-first-run
    --no-default-browser-check
)

if [ "$MODE" = "headless" ]; then
    # Headless mode: use aggressive flags for speed
    CHROME_ARGS+=(
        --headless=new
        --disable-background-networking
        --disable-default-apps
        --disable-extensions
        --disable-sync
        --disable-translate
        --metrics-recording-only
        --safebrowsing-disable-auto-update
    )
else
    # Headed mode: minimal flags for better compatibility
    CHROME_ARGS+=(
        --disable-sync
        --disable-translate
    )
fi

CHROME_ARGS+=("$URL")

# Start Chrome
echo "Starting Chrome..." >&2
echo "Command: $CHROME ${CHROME_ARGS[*]}" >&2

"$CHROME" "${CHROME_ARGS[@]}" > /dev/null 2>&1 &
CHROME_PID=$!

echo "Chrome started with PID: $CHROME_PID" >&2

# Wait for debugging endpoint to be available
echo "Waiting for debugging endpoint..." >&2

MAX_WAIT=10
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$RESOLVED_PORT/json/version" > /dev/null 2>&1; then
        echo "Debugging endpoint is ready" >&2
        break
    fi

    # Check if Chrome process is still running
    if ! kill -0 "$CHROME_PID" 2>/dev/null; then
        error_exit "STARTUP_TIMEOUT" \
            "Chrome process died during startup (PID: $CHROME_PID)" \
            "Check system resources: top, or inspect Chrome logs" \
            5
    fi

    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    # Kill the Chrome process since it's not responding
    kill "$CHROME_PID" 2>/dev/null || true
    error_exit "WEBSOCKET_FAILED" \
        "CDP endpoint did not become available within ${MAX_WAIT}s" \
        "Check if Chrome crashed: ps aux | grep $CHROME_PID" \
        4
fi

# Get page ID
echo "Getting page ID..." >&2

PAGES_JSON=$(curl -s "http://localhost:$RESOLVED_PORT/json")
PAGE_ID=$(echo "$PAGES_JSON" | jq -r '.[] | select(.type == "page") | .id' | head -1)

if [ -z "$PAGE_ID" ] || [ "$PAGE_ID" = "null" ]; then
    # Kill Chrome and exit
    kill "$CHROME_PID" 2>/dev/null || true
    error_exit "PAGE_NOT_FOUND" \
        "No page found after Chrome startup" \
        "Retry launch or check Chrome logs" \
        4
fi

echo "Page ID: $PAGE_ID" >&2

# Build WebSocket URL
WS_URL="ws://localhost:$RESOLVED_PORT/devtools/page/$PAGE_ID"

# Output success JSON
jq -n \
    --arg status "success" \
    --argjson port "$RESOLVED_PORT" \
    --argjson pid "$CHROME_PID" \
    --arg page_id "$PAGE_ID" \
    --arg profile "$RESOLVED_PROFILE" \
    --arg ws_url "$WS_URL" \
    '{
        status: $status,
        port: $port,
        pid: $pid,
        page_id: $page_id,
        profile: $profile,
        ws_url: $ws_url
    }' >&1

echo "Chrome launched successfully" >&2
exit 0
