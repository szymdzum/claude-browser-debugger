#!/bin/bash
# debug-orchestrator.sh - Flexible page debugging with CDP
# Usage: ./debug-orchestrator.sh <URL> [duration] [output-file] [--filter=pattern]
#
# Examples:
#   ./debug-orchestrator.sh "http://localhost:3000/customer/register?redirectTo=%2F"
#   ./debug-orchestrator.sh "http://localhost:3000/login" 10
#   ./debug-orchestrator.sh "http://localhost:3000/checkout" 15 /tmp/checkout-debug.log
#   ./debug-orchestrator.sh "http://localhost:3000/register" 15 /tmp/out.log --filter=marketingChannels

set -e

# Parse arguments
URL="${1}"
DURATION="${2:-10}"
OUTPUT_FILE="${3:-/tmp/page-debug.log}"
FILTER=""

# Check if last argument is a filter
for arg in "$@"; do
    if [[ "$arg" == --filter=* ]]; then
        FILTER="$arg"
    fi
done

if [ -z "$URL" ]; then
    echo "Usage: $0 <URL> [duration] [output-file]"
    echo ""
    echo "Examples:"
    echo "  $0 'http://localhost:3000/customer/register?redirectTo=%2F'"
    echo "  $0 'http://localhost:3000/login' 10"
    echo "  $0 'http://localhost:3000/checkout' 15 /tmp/checkout-debug.log"
    exit 1
fi

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=9222
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Debug Configuration:"
echo "   URL: $URL"
echo "   Duration: ${DURATION}s"
echo "   Output: $OUTPUT_FILE"
if [ -n "$FILTER" ]; then
    FILTER_VALUE=$(echo "$FILTER" | cut -d= -f2)
    echo "   Filter: $FILTER_VALUE (capturing response bodies)"
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
if [ -n "$FILTER" ]; then
    timeout ${DURATION} python3 "${SCRIPT_DIR}/cdp-network-with-body.py" \
        "$PAGE_ID" \
        "$URL" \
        "$FILTER" \
        2>&1 | tee "$OUTPUT_FILE" || true
else
    timeout ${DURATION} python3 "${SCRIPT_DIR}/cdp-network.py" \
        "$PAGE_ID" \
        "$URL" \
        2>&1 | tee "$OUTPUT_FILE" || true
fi

# Step 5: Analyze results
echo ""
echo "📊 Analysis Results:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REQUEST_COUNT=$(grep 'event.*request' "$OUTPUT_FILE" 2>/dev/null | wc -l | tr -d ' ')
RESPONSE_COUNT=$(grep 'event.*response' "$OUTPUT_FILE" 2>/dev/null | wc -l | tr -d ' ')
FAILED_COUNT=$(grep 'event.*failed' "$OUTPUT_FILE" 2>/dev/null | wc -l | tr -d ' ')

echo "   Total Requests:  $REQUEST_COUNT"
echo "   Total Responses: $RESPONSE_COUNT"
echo "   Failed Requests: $FAILED_COUNT"
echo ""

if [ "$REQUEST_COUNT" -gt 0 ]; then
    echo "📥 Top 10 Requests:"
    grep 'event.*request' "$OUTPUT_FILE" 2>/dev/null | \
        jq -r '"\(.method) \(.url)"' | \
        head -10 | \
        sed 's/^/   /'
    echo ""
fi

if [ "$RESPONSE_COUNT" -gt 0 ]; then
    echo "📤 Response Status Codes:"
    grep 'event.*response' "$OUTPUT_FILE" 2>/dev/null | \
        jq -r '.status' | \
        sort | uniq -c | \
        sed 's/^/   /'
    echo ""
fi

if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "❌ Failed Requests:"
    grep 'event.*failed' "$OUTPUT_FILE" 2>/dev/null | \
        jq -r '.errorText' | \
        sed 's/^/   /'
    echo ""
fi

echo "💾 Full output saved to: $OUTPUT_FILE"
echo ""

# Step 6: Cleanup
echo "🧹 Cleaning up..."
kill $CHROME_PID 2>/dev/null || true
echo "✅ Done!"
