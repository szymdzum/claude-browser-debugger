#!/bin/bash
# smoke-test-cleanup.sh - Validate cleanup-chrome.sh functionality
# Tests: Port cleanup, process termination, JSON contract

set -e

echo "🧪 Smoke Test: cleanup-chrome.sh"
echo "=================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLEANUP_SCRIPT="${SCRIPT_DIR}/scripts/cleanup-chrome.sh"
LAUNCHER_SCRIPT="${SCRIPT_DIR}/chrome-launcher.sh"

# Test 1: Cleanup when no Chrome is running
echo "Test 1: Cleanup with no running Chrome processes"
RESULT=$("$CLEANUP_SCRIPT" 9222)
STATUS=$(echo "$RESULT" | jq -r '.status')
PORT_STATUS=$(echo "$RESULT" | jq -r '.port_status')
PROCESSES_KILLED=$(echo "$RESULT" | jq -r '.processes_killed | length')

if [ "$STATUS" = "success" ] && [ "$PORT_STATUS" = "released" ] && [ "$PROCESSES_KILLED" = "0" ]; then
    echo "✅ PASS: Cleanup with no processes returns success with empty processes_killed array"
else
    echo "❌ FAIL: Expected success with 0 processes_killed, got status=$STATUS, port_status=$PORT_STATUS, count=$PROCESSES_KILLED"
    exit 1
fi

# Test 2: Launch Chrome and cleanup
echo ""
echo "Test 2: Cleanup running Chrome instance"
LAUNCH_RESULT=$("$LAUNCHER_SCRIPT" --mode=headless --url=about:blank 2>&1 | grep -E '^\{')
CHROME_PID=$(echo "$LAUNCH_RESULT" | jq -r '.pid')

if [ -z "$CHROME_PID" ] || [ "$CHROME_PID" = "null" ]; then
    echo "❌ FAIL: Could not launch Chrome"
    exit 1
fi

echo "  Launched Chrome with PID: $CHROME_PID"

# Verify Chrome is running
if ! kill -0 "$CHROME_PID" 2>/dev/null; then
    echo "❌ FAIL: Chrome PID $CHROME_PID is not running"
    exit 1
fi

# Cleanup Chrome
CLEANUP_RESULT=$("$CLEANUP_SCRIPT" 9222)
CLEANUP_STATUS=$(echo "$CLEANUP_RESULT" | jq -r '.status')
CLEANUP_PORT_STATUS=$(echo "$CLEANUP_RESULT" | jq -r '.port_status')
CLEANUP_PROCESSES=$(echo "$CLEANUP_RESULT" | jq -r '.processes_killed | length')

if [ "$CLEANUP_STATUS" != "success" ]; then
    echo "❌ FAIL: Cleanup failed with status=$CLEANUP_STATUS"
    echo "$CLEANUP_RESULT" | jq .
    exit 1
fi

if [ "$CLEANUP_PORT_STATUS" != "released" ]; then
    echo "❌ FAIL: Port not released, port_status=$CLEANUP_PORT_STATUS"
    exit 1
fi

if [ "$CLEANUP_PROCESSES" -lt 1 ]; then
    echo "❌ FAIL: Expected at least 1 process killed, got $CLEANUP_PROCESSES"
    exit 1
fi

# Verify port is actually released
if lsof -ti :9222 >/dev/null 2>&1; then
    echo "❌ FAIL: Port 9222 still occupied after cleanup"
    lsof -ti :9222
    exit 1
fi

# Verify Chrome process is dead
if kill -0 "$CHROME_PID" 2>/dev/null; then
    echo "❌ FAIL: Chrome PID $CHROME_PID still running after cleanup"
    exit 1
fi

echo "✅ PASS: Cleanup terminated $CLEANUP_PROCESSES process(es) and released port 9222"

# Test 3: Validate JSON contract
echo ""
echo "Test 3: Validate JSON contract structure"
REQUIRED_FIELDS=("status" "port" "port_status" "processes_killed" "cleanup_time_ms")

for field in "${REQUIRED_FIELDS[@]}"; do
    VALUE=$(echo "$CLEANUP_RESULT" | jq -r ".$field")
    if [ "$VALUE" = "null" ]; then
        echo "❌ FAIL: Missing required field: $field"
        exit 1
    fi
done

echo "✅ PASS: All required JSON fields present (status, port, port_status, processes_killed, cleanup_time_ms)"

echo ""
echo "=================================="
echo "✅ All smoke tests passed!"
echo ""
