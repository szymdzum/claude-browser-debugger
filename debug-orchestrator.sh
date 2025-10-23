#!/bin/bash
# debug-orchestrator.sh - Flexible page debugging with CDP
# Usage: ./debug-orchestrator.sh <URL> [duration] [output-file] [--filter=pattern] \
#        [--summary=text|json|both] [--include-console] [--console-log=path] [--idle=seconds]
#
# Examples:
#   ./debug-orchestrator.sh "https://example.com/register" --summary=both
#   ./debug-orchestrator.sh "https://demo.example/login" 10 --include-console --idle=2
#   ./debug-orchestrator.sh "https://shop.example/checkout" 15 /tmp/checkout.log --summary=json
#   ./debug-orchestrator.sh "https://api.example/data" 15 /tmp/out.log --filter=marketing --include-console

set -e

# Parse arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <URL> [duration] [output-file]"
    echo ""
    echo "Examples:"
    echo "  $0 'https://example.com/register'"
    echo "  $0 'https://demo.example/login' 10"
    echo "  $0 'https://shop.example/checkout' 15 /tmp/checkout-debug.log"
    exit 1
fi

URL="$1"
shift

DURATION=10
OUTPUT_FILE="/tmp/page-debug.log"
SUMMARY_FORMAT="text"
FILTER=""
FILTER_VALUE=""
INCLUDE_CONSOLE=0
CONSOLE_LOG=""
IDLE_TIMEOUT=""

if [ $# -gt 0 ] && [[ $1 != --* ]]; then
    DURATION="$1"
    shift
fi

if [ $# -gt 0 ] && [[ $1 != --* ]]; then
    OUTPUT_FILE="$1"
    shift
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --filter=*)
            FILTER="$1"
            FILTER_VALUE="${1#--filter=}"
            ;;
        --summary=*)
            SUMMARY_FORMAT="${1#--summary=}"
            ;;
        --include-console)
            INCLUDE_CONSOLE=1
            ;;
        --console-log=*)
            CONSOLE_LOG="${1#--console-log=}"
            ;;
        --idle=*)
            IDLE_TIMEOUT="${1#--idle=}"
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
    shift
done

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=9222
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$INCLUDE_CONSOLE" -eq 1 ] && [ -z "$CONSOLE_LOG" ]; then
    if [[ "$OUTPUT_FILE" == *.* ]]; then
        base="${OUTPUT_FILE%.*}"
        ext="${OUTPUT_FILE##*.}"
        if [ "$base" = "$OUTPUT_FILE" ]; then
            CONSOLE_LOG="${OUTPUT_FILE}-console.log"
        else
            CONSOLE_LOG="${base}-console.${ext}"
        fi
    else
        CONSOLE_LOG="${OUTPUT_FILE}-console.log"
    fi
fi

echo "🔧 Debug Configuration:"
echo "   URL: $URL"
echo "   Duration: ${DURATION}s"
echo "   Output: $OUTPUT_FILE"
if [ -n "$FILTER_VALUE" ]; then
    echo "   Filter: $FILTER_VALUE (capturing response bodies)"
fi
if [ "$SUMMARY_FORMAT" != "text" ]; then
    echo "   Summary format: $SUMMARY_FORMAT"
fi
if [ "$INCLUDE_CONSOLE" -eq 1 ]; then
    echo "   Console log: $CONSOLE_LOG"
fi
if [ -n "$IDLE_TIMEOUT" ]; then
    echo "   Idle timeout: ${IDLE_TIMEOUT}s"
fi
echo ""

# Step 1: Clean up any existing Chrome instances
echo "🧹 Cleaning up existing Chrome instances..."
pkill -9 -f "chrome.*${PORT}" 2>/dev/null || true
sleep 1

# Verify port is free
if lsof -i :${PORT} > /dev/null 2>&1; then
    echo "❌ Port ${PORT} is still in use. Please manually kill the process."
    lsof -i :${PORT}
    exit 1
fi

# Step 2: Start Chrome with blank page
echo "🚀 Starting Chrome on port ${PORT}..."
"$CHROME" --headless=new --remote-debugging-port=${PORT} about:blank > /dev/null 2>&1 &
CHROME_PID=$!
echo "   Chrome PID: $CHROME_PID"
sleep 3

# Step 3: Get page ID (filter for actual page, not extensions)
echo "🔍 Getting page ID..."
PAGE_ID=$(curl -s "http://localhost:${PORT}/json" | jq -r '.[] | select(.type == "page") | .id' | head -1)

if [ -z "$PAGE_ID" ] || [ "$PAGE_ID" = "null" ]; then
    echo "❌ Failed to get page ID"
    kill $CHROME_PID 2>/dev/null
    exit 1
fi

echo "   Page ID: $PAGE_ID"
echo ""

# Step 4: Monitor network traffic
echo "📡 Monitoring network traffic for ${DURATION}s..."
echo "   Press Ctrl+C to stop early"
echo ""

# Choose which script to use based on filter
summarize_log() {
    local format="$1"
    local args=("--network" "$OUTPUT_FILE" "--duration" "$DURATION" "--format" "$format")

    if [ -n "$FILTER_VALUE" ]; then
        args+=("--filter" "$FILTER_VALUE")
    fi

    if [ "$INCLUDE_CONSOLE" -eq 1 ]; then
        args+=("--include-console" "--console" "$CONSOLE_LOG")
    fi

    python3 "${SCRIPT_DIR}/summarize.py" "${args[@]}"
}

NETWORK_SCRIPT="${SCRIPT_DIR}/cdp-network.py"
NETWORK_ARGS=("$PAGE_ID" "$URL")

if [ -n "$FILTER_VALUE" ]; then
    NETWORK_SCRIPT="${SCRIPT_DIR}/cdp-network-with-body.py"
    NETWORK_ARGS=("$PAGE_ID" "$URL" "$FILTER")
fi

if [ -n "$IDLE_TIMEOUT" ]; then
    NETWORK_ARGS+=("--idle-timeout=${IDLE_TIMEOUT}")
fi

if [ "$INCLUDE_CONSOLE" -eq 1 ]; then
    echo "🖥️ Monitoring console output..."
    CONSOLE_ARGS=("$PAGE_ID" "$URL")
    if [ -n "$IDLE_TIMEOUT" ]; then
        CONSOLE_ARGS+=("--idle-timeout=${IDLE_TIMEOUT}")
    fi

    set +e
    timeout ${DURATION} python3 "${SCRIPT_DIR}/cdp-console.py" "${CONSOLE_ARGS[@]}" 2>&1 | tee "$CONSOLE_LOG" &
    CONSOLE_JOB=$!
    set -e
fi

timeout ${DURATION} python3 "$NETWORK_SCRIPT" "${NETWORK_ARGS[@]}" 2>&1 | tee "$OUTPUT_FILE" || true

if [ "$INCLUDE_CONSOLE" -eq 1 ]; then
    wait $CONSOLE_JOB || true
fi

# Step 5: Analyze results
if [[ "$SUMMARY_FORMAT" == "text" || "$SUMMARY_FORMAT" == "both" ]]; then
    echo ""
    echo "📊 Analysis Results:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    summarize_log "text"
fi

if [[ "$SUMMARY_FORMAT" == "json" || "$SUMMARY_FORMAT" == "both" ]]; then
    echo ""
    echo "🧮 JSON Summary:"
    summarize_log "json"
fi

echo "💾 Full output saved to: $OUTPUT_FILE"
echo ""

# Step 6: Cleanup
echo "🧹 Cleaning up..."
kill $CHROME_PID 2>/dev/null || true
echo "✅ Done!"
