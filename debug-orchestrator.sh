#!/bin/bash
# debug-orchestrator.sh - Flexible page debugging with CDP
# Usage: ./debug-orchestrator.sh <URL> [duration] [output-file] [--filter=pattern] \
#        [--summary=text|json|both] [--include-console] [--console-log=path] [--idle=seconds] \
#        [--mode=headless|headed] [--port=number|auto] [--profile=path|none]
#
# Examples:
#   ./debug-orchestrator.sh "https://example.com/register" --summary=both
#   ./debug-orchestrator.sh "https://demo.example/login" 10 --include-console --idle=2
#   ./debug-orchestrator.sh "https://shop.example/checkout" 15 /tmp/checkout.log --summary=json
#   ./debug-orchestrator.sh "https://api.example/data" 15 /tmp/out.log --filter=marketing --include-console
#   ./debug-orchestrator.sh "http://localhost:3000/signin" --mode=headed --include-console

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

DURATION=""
OUTPUT_FILE="/tmp/page-debug.log"
SUMMARY_FORMAT="text"
FILTER=""
FILTER_VALUE=""
INCLUDE_CONSOLE=0
CONSOLE_LOG=""
IDLE_TIMEOUT=""
MODE="headless"
PORT="9222"
PROFILE=""

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
        --mode=*)
            MODE="${1#--mode=}"
            ;;
        --port=*)
            PORT="${1#--port=}"
            ;;
        --profile=*)
            PROFILE="${1#--profile=}"
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
    shift
done

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

# Set default duration based on mode if not specified
if [ -z "$DURATION" ]; then
    if [ "$MODE" = "headed" ]; then
        DURATION=3600  # 1 hour for interactive debugging
    else
        DURATION=10    # 10 seconds for headless automation
    fi
fi

echo "🔧 Debug Configuration:"
echo "   URL: $URL"
echo "   Mode: $MODE"
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

# Step 1: Launch Chrome using chrome-launcher.sh
echo "🚀 Launching Chrome..."

LAUNCHER_ARGS=(
    --mode="$MODE"
    --port="$PORT"
    --url="$URL"
)

if [ -n "$PROFILE" ]; then
    LAUNCHER_ARGS+=(--profile="$PROFILE")
fi

LAUNCHER_OUTPUT=$("${SCRIPT_DIR}/chrome-launcher.sh" "${LAUNCHER_ARGS[@]}" 2>&1)

# Separate stderr (diagnostics) from stdout (JSON)
LAUNCHER_STDERR=$(echo "$LAUNCHER_OUTPUT" | grep -v "^{" || true)
LAUNCHER_JSON=$(echo "$LAUNCHER_OUTPUT" | grep "^{" | tail -1)

# Show launcher diagnostics
if [ -n "$LAUNCHER_STDERR" ]; then
    echo "$LAUNCHER_STDERR" >&2
fi

# Parse JSON output
STATUS=$(echo "$LAUNCHER_JSON" | jq -r '.status' 2>/dev/null || echo "error")

if [ "$STATUS" != "success" ]; then
    echo ""
    echo "❌ Chrome launch failed"

    CODE=$(echo "$LAUNCHER_JSON" | jq -r '.code' 2>/dev/null || echo "UNKNOWN")
    MESSAGE=$(echo "$LAUNCHER_JSON" | jq -r '.message' 2>/dev/null || echo "Unknown error")
    RECOVERY=$(echo "$LAUNCHER_JSON" | jq -r '.recovery' 2>/dev/null || echo "No recovery available")

    echo "   Error: $CODE"
    echo "   Message: $MESSAGE"
    echo ""
    echo "💡 Recovery:"
    echo "   $RECOVERY"
    echo ""
    exit 1
fi

# Extract connection info
RESOLVED_PORT=$(echo "$LAUNCHER_JSON" | jq -r '.port')
PAGE_ID=$(echo "$LAUNCHER_JSON" | jq -r '.page_id')
CHROME_PID=$(echo "$LAUNCHER_JSON" | jq -r '.pid')
RESOLVED_PROFILE=$(echo "$LAUNCHER_JSON" | jq -r '.profile')

echo ""
echo "✅ Chrome launched successfully"
echo "   PID: $CHROME_PID"
echo "   Port: $RESOLVED_PORT"
echo "   Page ID: $PAGE_ID"
if [ "$MODE" = "headed" ]; then
    echo "   Profile: $RESOLVED_PROFILE"
    echo "   💡 You can now interact with the visible Chrome window"
fi
echo ""

# Step 2: Monitor network traffic
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

    python3 "${SCRIPT_DIR}/cdp-summarize.py" "${args[@]}"
}

NETWORK_SCRIPT="${SCRIPT_DIR}/cdp-network.py"
NETWORK_ARGS=("$PAGE_ID" "$URL" "--port=${RESOLVED_PORT}")

if [ -n "$FILTER_VALUE" ]; then
    NETWORK_SCRIPT="${SCRIPT_DIR}/cdp-network-with-body.py"
    NETWORK_ARGS=("$PAGE_ID" "$URL" "$FILTER" "--port=${RESOLVED_PORT}")
fi

if [ -n "$IDLE_TIMEOUT" ]; then
    NETWORK_ARGS+=("--idle-timeout=${IDLE_TIMEOUT}")
fi

if [ "$INCLUDE_CONSOLE" -eq 1 ]; then
    echo "🖥️ Monitoring console output..."
    CONSOLE_ARGS=("$PAGE_ID" "$URL" "--port=${RESOLVED_PORT}")
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

# Step 3: Analyze results
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

# Step 4: Cleanup
echo "🧹 Cleaning up..."
kill $CHROME_PID 2>/dev/null || true

if [ "$MODE" = "headed" ]; then
    echo "   💡 Note: Persistent profile kept at: $RESOLVED_PROFILE"
    echo "   To clean: rm -rf $RESOLVED_PROFILE"
fi

echo "✅ Done!"
