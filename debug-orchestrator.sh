#!/bin/bash
# debug-orchestrator.sh - Flexible page debugging with CDP
# Usage: ./debug-orchestrator.sh <URL> [duration] [output-file] [--filter=pattern] \
#        [--summary=text|json|both] [--include-console] [--console-log=path] [--idle=seconds]
#
# Examples:
#   ./debug-orchestrator.sh "http://localhost:3000/customer/register?redirectTo=%2F" --summary=both
#   ./debug-orchestrator.sh "http://localhost:3000/login" 10 --include-console --idle=2
#   ./debug-orchestrator.sh "http://localhost:3000/checkout" 15 /tmp/checkout.log --summary=json
#   ./debug-orchestrator.sh "http://localhost:3000/register" 15 /tmp/out.log --filter=marketingChannels --include-console

set -e

# Parse arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <URL> [duration] [output-file]"
    echo ""
    echo "Examples:"
    echo "  $0 'http://localhost:3000/customer/register?redirectTo=%2F'"
    echo "  $0 'http://localhost:3000/login' 10"
    echo "  $0 'http://localhost:3000/checkout' 15 /tmp/checkout-debug.log"
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
    python3 - "$OUTPUT_FILE" "${CONSOLE_LOG}" "$DURATION" "$FILTER_VALUE" "$format" "$INCLUDE_CONSOLE" <<'PY'
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

log_path = Path(sys.argv[1])
console_path_arg = sys.argv[2]
duration = float(sys.argv[3])
filter_value = sys.argv[4]
output_format = sys.argv[5]
include_console = sys.argv[6] == '1'

events = []
requests = []
responses = []
failures = []
request_by_id = {}
methods = Counter()
status_codes = Counter()
hosts = Counter()

if log_path.exists():
    for raw_line in log_path.read_text().splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        events.append(data)
        event_type = data.get('event')

        if event_type == 'request':
            requests.append(data)
            request_by_id[data.get('requestId')] = data
            method = data.get('method') or 'UNKNOWN'
            methods[method] += 1
            url = data.get('url')
            if url:
                host = urlparse(url).netloc
                if host:
                    hosts[host] += 1

        elif event_type == 'response':
            responses.append(data)
            status = str(data.get('status'))
            status_codes[status] += 1
            url = data.get('url')
            if url:
                host = urlparse(url).netloc
                if host:
                    hosts[host] += 1

        elif event_type == 'failed':
            failures.append(data)

report = {
    "meta": {
        "log_path": str(log_path),
        "console_log": console_path_arg or None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": duration,
        "filter": filter_value or None,
        "total_events": len(events),
        "unique_hosts": len(hosts),
    },
    "network": {
        "request_count": len(requests),
        "response_count": len(responses),
        "failure_count": len(failures),
        "methods": dict(methods),
        "status_codes": dict(status_codes),
        "top_requests": [],
        "failures": [],
    },
}

seen_urls = set()
for request in requests:
    url = request.get('url')
    if not url or url in seen_urls:
        continue
    seen_urls.add(url)
    report["network"]["top_requests"].append({
        "method": request.get('method'),
        "url": url,
    })
    if len(report["network"]["top_requests"]) == 10:
        break

for failure in failures[:10]:
    request = request_by_id.get(failure.get('requestId'), {})
    report["network"]["failures"].append({
        "error": failure.get('errorText'),
        "url": request.get('url'),
        "method": request.get('method'),
        "requestId": failure.get('requestId'),
    })

console_report = {
    "entry_count": 0,
    "levels": {},
    "sample_errors": [],
}

if include_console and console_path_arg:
    console_path = Path(console_path_arg)
    if console_path.exists():
        level_counts = Counter()
        sample_errors = []
        for raw_line in console_path.read_text().splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                entry = json.loads(stripped)
            except json.JSONDecodeError:
                continue

            level = (entry.get('type') or '').lower()
            if not level:
                continue

            level_counts[level] += 1

            if level in {'error', 'exception'} and len(sample_errors) < 5:
                sample_errors.append({
                    'message': entry.get('message'),
                    'url': entry.get('url'),
                    'lineNumber': entry.get('lineNumber'),
                })

        console_report = {
            "entry_count": sum(level_counts.values()),
            "levels": dict(level_counts),
            "sample_errors": sample_errors,
        }

if output_format == "json":
    summary = {
        "meta": report["meta"],
        "network": report["network"],
    }
    if include_console:
        summary["console"] = console_report
    print(json.dumps(summary, indent=2))
else:
    print(f"   Total Requests:  {report['network']['request_count']}")
    print(f"   Total Responses: {report['network']['response_count']}")
    print(f"   Failed Requests: {report['network']['failure_count']}")
    print("")

    top_requests = report["network"]["top_requests"]
    if top_requests:
        print("📥 Top 10 Requests:")
        for item in top_requests:
            print(f"   {item.get('method', 'UNKNOWN')} {item.get('url', '-')}")
        print("")

    status_items = sorted(report["network"]["status_codes"].items())
    if status_items:
        print("📤 Response Status Codes:")
        for status, count in status_items:
            print(f"      {count} {status}")
        print("")

    failures = report["network"]["failures"]
    if failures:
        print("❌ Failed Requests:")
        for failure in failures:
            error = failure.get('error') or 'Unknown error'
            url = failure.get('url')
            if url:
                print(f"   {error} [{url}]")
            else:
                print(f"   {error}")
        print("")

    if include_console:
        print("🖥️ Console Summary:")
        print(f"   Entries: {console_report['entry_count']}")
        if console_report['levels']:
            print("   Levels:")
            for level, count in sorted(console_report['levels'].items()):
                print(f"      {level}: {count}")
        if console_report['sample_errors']:
            print("   Sample Errors:")
            for error in console_report['sample_errors']:
                message = error.get('message') or '(no message)'
                location = ''
                if error.get('url'):
                    location = f" [{error['url']}"
                    if error.get('lineNumber') is not None:
                        location += f":{error['lineNumber']}"
                    location += "]"
                print(f"      {message}{location}")
        print("")
PY
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
