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

# ============================================================================
# Helper Functions (T004, T005: Foundational infrastructure)
# ============================================================================

# Generate JSON error message with recovery hints
generate_error_json() {
    local code="$1"
    local message="$2"
    local recovery="$3"

    cat <<EOF
{
  "status": "error",
  "code": "$code",
  "message": "$message",
  "recovery": "$recovery"
}
EOF
}

# Fetch WebSocket URL from CDP
fetch_websocket_url() {
    local port="$1"
    curl -s "http://localhost:${port}/json" | jq -r '.[0].webSocketDebuggerUrl' 2>/dev/null
}

# Generate success JSON
generate_success_json() {
    local data="$1"
    echo "$data" | jq '. + {status: "success"}' 2>/dev/null
}

# FR-008: Cleanup function for graceful session termination (T020)
cleanup_function() {
    local exit_code=${1:-0}

    echo ""
    echo "🧹 Cleaning up session..."

    # Stop monitors gracefully (SIGTERM)
    if [ -n "$NETWORK_JOB" ] && kill -0 "$NETWORK_JOB" 2>/dev/null; then
        echo "   Stopping network monitor (PID: $NETWORK_JOB)..."
        kill -TERM "$NETWORK_JOB" 2>/dev/null || true
        wait "$NETWORK_JOB" 2>/dev/null || true
    fi

    if [ "$INCLUDE_CONSOLE" -eq 1 ] && [ -n "$CONSOLE_JOB" ] && kill -0 "$CONSOLE_JOB" 2>/dev/null; then
        echo "   Stopping console monitor (PID: $CONSOLE_JOB)..."
        kill -TERM "$CONSOLE_JOB" 2>/dev/null || true
        wait "$CONSOLE_JOB" 2>/dev/null || true
    fi

    # Extract final DOM snapshot if Chrome is still running
    if [ -n "$CHROME_PID" ] && kill -0 "$CHROME_PID" 2>/dev/null; then
        echo "   Extracting final DOM state..."

        # Determine DOM output file path
        if [[ "$OUTPUT_FILE" == *.* ]]; then
            base="${OUTPUT_FILE%.*}"
            base="${base%-network}"  # Remove -network suffix
            DOM_FILE="${base}-dom.html"
        else
            DOM_FILE="${OUTPUT_FILE%-network.log}-dom.html"
        fi

        # Extract DOM via CDP
        if [ -n "$WS_URL" ]; then
            echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
                | websocat -n1 -B 1048576 "$WS_URL" 2>/dev/null \
                | jq -r '.result.result.value' > "$DOM_FILE" 2>/dev/null || true

            if [ -f "$DOM_FILE" ] && [ -s "$DOM_FILE" ]; then
                echo "   ✅ DOM saved to: $DOM_FILE"
            fi
        fi
    fi

    # Generate summary report
    if [ -f "$OUTPUT_FILE" ]; then
        echo "   Generating summary report..."

        # Determine summary file path
        if [[ "$OUTPUT_FILE" == *.* ]]; then
            base="${OUTPUT_FILE%.*}"
            base="${base%-network}"
            SUMMARY_FILE="${base}-summary.txt"
        else
            SUMMARY_FILE="${OUTPUT_FILE%-network.log}-summary.txt"
        fi

        # Generate summary using cdp-summarize.py
        python3 "${COLLECTORS_DIR}/cdp-summarize.py" \
            --network "$OUTPUT_FILE" \
            --duration "$DURATION" \
            --format text > "$SUMMARY_FILE" 2>/dev/null || true

        if [ -f "$SUMMARY_FILE" ] && [ -s "$SUMMARY_FILE" ]; then
            echo "   ✅ Summary saved to: $SUMMARY_FILE"
        fi
    fi

    # Terminate Chrome
    if [ -n "$CHROME_PID" ] && kill -0 "$CHROME_PID" 2>/dev/null; then
        echo "   Stopping Chrome (PID: $CHROME_PID)..."
        kill "$CHROME_PID" 2>/dev/null || true
    fi

    # FR-010: Display all output file locations
    echo ""
    echo "📁 Session artifacts preserved:"
    if [ -f "$OUTPUT_FILE" ]; then
        echo "   Network log: $OUTPUT_FILE"
    fi
    if [ "$INCLUDE_CONSOLE" -eq 1 ] && [ -f "$CONSOLE_LOG" ]; then
        echo "   Console log: $CONSOLE_LOG"
    fi
    if [ -n "$DOM_FILE" ] && [ -f "$DOM_FILE" ]; then
        echo "   Final DOM: $DOM_FILE"
    fi
    if [ -n "$SUMMARY_FILE" ] && [ -f "$SUMMARY_FILE" ]; then
        echo "   Summary: $SUMMARY_FILE"
    fi

    if [ "$MODE" = "headed" ] && [ -n "$RESOLVED_PROFILE" ]; then
        echo ""
        echo "   💡 Note: Persistent profile kept at: $RESOLVED_PROFILE"
        echo "   To clean: rm -rf $RESOLVED_PROFILE"
    fi

    echo ""
    echo "✅ Session cleanup complete!"

    exit "$exit_code"
}

# Display ready notification for headed mode (T007-T012: US1)
display_ready_notification() {
    local url="$1"
    local duration="$2"
    local output_file="$3"
    local chrome_pid="$4"
    local ws_url="$5"
    local profile="$6"
    local include_console="$7"

    local timeout_minutes=$((duration / 60))

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 CHROME WINDOW IS NOW OPEN AND READY!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📍 URL: $url"
    echo "⏱️  Session timeout: ${timeout_minutes} minutes (${duration}s)"

    if [ "$include_console" -eq 1 ]; then
        echo "🔍 Monitoring: Network + Console logs"
    else
        echo "🔍 Monitoring: Network logs"
    fi

    echo "💾 Output: $output_file"
    echo ""
    echo "🔧 Debug Info:"
    echo "   Chrome PID: $chrome_pid"
    echo "   Profile: $profile"
    echo ""
    echo "💬 You can now interact with the page."
    echo "   When you're done, let me know and I'll extract the final state."
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

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
SKIP_VALIDATION="false"

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
        --skip-validation)
            SKIP_VALIDATION="true"
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
    shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COLLECTORS_DIR="${REPO_ROOT}/scripts/collectors"

# FR-009: Generate unique session ID (timestamp + PID) for file naming
SESSION_ID=$(date +%Y%m%d-%H%M%S)-$$

# FR-008: Set up SIGINT trap for graceful cleanup (T019)
trap 'cleanup_function 130' SIGINT

# Verify collector scripts exist before proceeding (FR-002)
REQUIRED_COLLECTORS=(
    "${COLLECTORS_DIR}/cdp-network.py"
    "${COLLECTORS_DIR}/cdp-network-with-body.py"
    "${COLLECTORS_DIR}/cdp-summarize.py"
)

if [ "$INCLUDE_CONSOLE" -eq 1 ]; then
    REQUIRED_COLLECTORS+=("${COLLECTORS_DIR}/cdp-console.py")
fi

for collector in "${REQUIRED_COLLECTORS[@]}"; do
    if [ ! -f "$collector" ]; then
        generate_error_json \
            "COLLECTOR_MISSING" \
            "Required collector script not found: $collector" \
            "Verify repository structure: ls -la ${COLLECTORS_DIR}/"
        echo ""
        exit 1
    fi
done

# FR-009: Inject SESSION_ID into output file paths for uniqueness
if [[ "$OUTPUT_FILE" == *.* ]]; then
    base="${OUTPUT_FILE%.*}"
    ext="${OUTPUT_FILE##*.}"
    OUTPUT_FILE="${base}-${SESSION_ID}-network.${ext}"
else
    OUTPUT_FILE="${OUTPUT_FILE}-${SESSION_ID}-network.log"
fi

if [ "$INCLUDE_CONSOLE" -eq 1 ] && [ -z "$CONSOLE_LOG" ]; then
    if [[ "$OUTPUT_FILE" == *.* ]]; then
        base="${OUTPUT_FILE%.*}"
        # Remove -network suffix if present and replace with -console
        base="${base%-network}"
        ext="${OUTPUT_FILE##*.}"
        CONSOLE_LOG="${base}-console.${ext}"
    else
        CONSOLE_LOG="${OUTPUT_FILE%-network.log}-console.log"
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

# ============================================================================
# URL Validation Function
# ============================================================================

validate_url() {
    local url=$1
    local start_time=$(python3 -c "import time; print(int(time.time() * 1000))")

    # FR-004: Detect localhost URLs for lenient validation
    local is_localhost=0
    if [[ "$url" =~ ^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?(/.*)?$ ]]; then
        is_localhost=1
    fi

    if [ $is_localhost -eq 1 ]; then
        echo "🔍 Validating URL: $url (localhost - lenient validation)" >&2
    else
        echo "🔍 Validating URL: $url" >&2
    fi

    # Execute curl and capture both status code and exit code
    local http_code
    http_code=$(curl --max-time 5 --connect-timeout 3 --location --silent \
        --output /dev/null --write-out "%{http_code}" "$url" 2>&1)
    local curl_exit=$?

    local end_time=$(python3 -c "import time; print(int(time.time() * 1000))")
    local validation_time=$((end_time - start_time))

    # Check curl exit code first (network-level errors)
    if [ $curl_exit -ne 0 ]; then
        echo "❌ URL validation failed" >&2
        case $curl_exit in
            6)
                echo "   Error: DNS resolution failed for $url" >&2
                echo "   Recovery: Check URL and network connection, or use --skip-validation to bypass" >&2
                ;;
            7)
                echo "   Error: Connection refused to $url" >&2
                echo "   Recovery: Check if server is running, or use --skip-validation to bypass" >&2
                ;;
            28)
                echo "   Error: Connection timeout after 5 seconds for $url" >&2
                echo "   Recovery: Check URL and network connection, or use --skip-validation to bypass" >&2
                ;;
            35)
                echo "   Error: SSL/TLS handshake failed for $url" >&2
                echo "   Recovery: Check certificate validity, or use --skip-validation to bypass" >&2
                ;;
            *)
                echo "   Error: curl failed with exit code $curl_exit for $url" >&2
                echo "   Recovery: Check URL and network connection, or use --skip-validation to bypass" >&2
                ;;
        esac
        return 1
    fi

    # Check HTTP status code (application-level errors)
    # FR-004: Localhost URLs accept any HTTP status (200-599)
    # FR-005, FR-011: Remote URLs require 200-399, hard stop on 404 and other errors (400-599)
    if [[ "$http_code" =~ ^[23][0-9][0-9]$ ]]; then
        echo "✅ URL validation passed (HTTP $http_code) in ${validation_time}ms" >&2
        return 0
    elif [ $is_localhost -eq 1 ]; then
        # Localhost: Accept any HTTP status code (lenient validation)
        if [[ "$http_code" =~ ^[45][0-9][0-9]$ ]]; then
            echo "✅ URL validation passed (HTTP $http_code - localhost lenient mode) in ${validation_time}ms" >&2
            return 0
        else
            echo "❌ URL validation failed" >&2
            echo "   HTTP Status: $http_code" >&2
            echo "   Error: Unexpected HTTP response from localhost" >&2
            echo "   Recovery: Verify dev server is running or use --skip-validation" >&2
            return 1
        fi
    elif [[ "$http_code" =~ ^404$ ]]; then
        # Remote URL: Hard stop on 404
        echo "❌ URL validation failed - HARD STOP" >&2
        echo "   HTTP Status: 404 Not Found" >&2
        echo "   Error: The URL $url does not exist on the server" >&2
        echo "   Recovery:" >&2
        echo "     1. Verify the URL is correct (check spelling, path)" >&2
        echo "     2. Verify the server is running and the resource exists" >&2
        echo "     3. Use --skip-validation ONLY if you need to generate a new page ID" >&2
        echo "" >&2
        echo "   ⚠️  Chrome will NOT be launched. Fix the URL before proceeding." >&2
        return 1
    elif [[ "$http_code" =~ ^[45][0-9][0-9]$ ]]; then
        # Remote URL: Hard stop on other 4xx/5xx errors
        echo "❌ URL validation failed - HARD STOP" >&2
        echo "   HTTP Status: $http_code" >&2
        echo "   Error: URL returned client/server error" >&2
        echo "   Recovery:" >&2
        echo "     1. Verify the URL is correct and accessible" >&2
        echo "     2. Check server logs or status" >&2
        echo "     3. Use --skip-validation to bypass (not recommended)" >&2
        echo "" >&2
        echo "   ⚠️  Chrome will NOT be launched. Fix the URL before proceeding." >&2
        return 1
    else
        echo "❌ URL validation failed" >&2
        echo "   HTTP Status: $http_code" >&2
        echo "   Error: Unexpected HTTP response" >&2
        echo "   Recovery: Verify URL or use --skip-validation" >&2
        return 1
    fi
}

# ============================================================================
# Pre-flight URL Validation
# ============================================================================

if [ "$SKIP_VALIDATION" != "true" ]; then
    if ! validate_url "$URL"; then
        echo "" >&2
        echo "💡 Tip: Use --skip-validation to bypass URL validation for intentionally unreachable URLs" >&2
        exit 1
    fi
    echo "" >&2
else
    echo "⚠️  URL validation skipped (--skip-validation flag)" >&2
    echo "" >&2
fi

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
WS_URL=$(fetch_websocket_url "$RESOLVED_PORT")

# T008-T012: Display appropriate notification based on mode
if [ "$MODE" = "headed" ]; then
    # Headed mode: Show prominent ready notification
    display_ready_notification "$URL" "$DURATION" "$OUTPUT_FILE" "$CHROME_PID" "$WS_URL" "$RESOLVED_PROFILE" "$INCLUDE_CONSOLE"
else
    # Headless mode: Show minimal success message
    echo ""
    echo "✅ Chrome launched successfully"
    echo "   PID: $CHROME_PID"
    echo "   Port: $RESOLVED_PORT"
    echo "   Page ID: $PAGE_ID"
    echo ""
fi

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

    python3 "${COLLECTORS_DIR}/cdp-summarize.py" "${args[@]}"
}

NETWORK_SCRIPT="${COLLECTORS_DIR}/cdp-network.py"
NETWORK_ARGS=("$PAGE_ID" "$URL" "--port=${RESOLVED_PORT}")

if [ -n "$FILTER_VALUE" ]; then
    NETWORK_SCRIPT="${COLLECTORS_DIR}/cdp-network-with-body.py"
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
    timeout ${DURATION} python3 "${COLLECTORS_DIR}/cdp-console.py" "${CONSOLE_ARGS[@]}" 2>&1 | tee "$CONSOLE_LOG" &
    CONSOLE_JOB=$!
    set -e

    # FR-006: Verify console monitor PID
    sleep 0.5  # Brief delay to allow process startup
    if ! kill -0 $CONSOLE_JOB 2>/dev/null; then
        # FR-007: Provide clear error message with command details
        echo "" >&2
        echo "❌ Console monitor failed to start" >&2
        echo "   Command: python3 ${COLLECTORS_DIR}/cdp-console.py ${CONSOLE_ARGS[*]}" >&2
        echo "   Check log: $CONSOLE_LOG" >&2
        echo "" >&2
        echo "💡 Recovery:" >&2
        echo "   - Verify Python websockets installed: pip3 install websockets --break-system-packages" >&2
        echo "   - Check CDP port accessibility: curl -s http://localhost:${RESOLVED_PORT}/json" >&2
        exit 1
    fi
    echo "✅ Console monitor started (PID: $CONSOLE_JOB)"
fi

timeout ${DURATION} python3 "$NETWORK_SCRIPT" "${NETWORK_ARGS[@]}" 2>&1 | tee "$OUTPUT_FILE" &
NETWORK_JOB=$!

# FR-006: Verify network monitor PID
sleep 0.5  # Brief delay to allow process startup
if ! kill -0 $NETWORK_JOB 2>/dev/null; then
    # FR-007: Provide clear error message with command details
    echo "" >&2
    echo "❌ Network monitor failed to start" >&2
    echo "   Command: python3 $NETWORK_SCRIPT ${NETWORK_ARGS[*]}" >&2
    echo "   Check log: $OUTPUT_FILE" >&2
    echo "" >&2
    echo "💡 Recovery:" >&2
    echo "   - Verify Python websockets installed: pip3 install websockets --break-system-packages" >&2
    echo "   - Check CDP port accessibility: curl -s http://localhost:${RESOLVED_PORT}/json" >&2

    # Kill console monitor if it was started
    if [ "$INCLUDE_CONSOLE" -eq 1 ]; then
        kill $CONSOLE_JOB 2>/dev/null || true
    fi
    exit 1
fi
echo "✅ Network monitor started (PID: $NETWORK_JOB)"

# Wait for network monitor to complete
wait $NETWORK_JOB || true

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

# Step 4: Cleanup - Use centralized cleanup function
cleanup_function 0
