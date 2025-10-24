#!/bin/bash
set -euo pipefail

# cdp-query.sh - CDP Runtime.evaluate query helper
# Purpose: Execute JavaScript in Chrome via WebSocket without reconstructing websocat commands
# Usage: ./cdp-query.sh <ws-url> <js-expression> [buffer-size]

# ============================================================================
# Parameter Parsing
# ============================================================================

if [ $# -lt 2 ]; then
    echo "Usage: $0 <ws-url> <js-expression> [buffer-size]" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 \"\$WS_URL\" \"document.title\"" >&2
    echo "  $0 \"\$WS_URL\" \"document.documentElement.outerHTML\" 2097152" >&2
    echo "" >&2
    echo "Arguments:" >&2
    echo "  ws-url        : WebSocket debugger URL from Chrome CDP" >&2
    echo "  js-expression : JavaScript expression to evaluate" >&2
    echo "  buffer-size   : Optional buffer size in bytes (default: 2097152 = 2MB)" >&2
    exit 2
fi

WS_URL="$1"
JS_EXPRESSION="$2"
BUFFER_SIZE="${3:-2097152}"  # Default 2MB

START_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")

# ============================================================================
# Dependency Validation
# ============================================================================

if ! command -v websocat >/dev/null 2>&1; then
    jq -nc \
        --arg status "error" \
        --arg code "WEBSOCAT_MISSING" \
        --arg message "websocat command not found - required for CDP queries" \
        --arg recovery "Install websocat: brew install websocat (macOS) or see https://github.com/vi/websocat" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq command not found" >&2
    exit 2
fi

# ============================================================================
# Execute CDP Query
# ============================================================================

echo "Executing CDP query: ${JS_EXPRESSION:0:100}..." >&2

# Construct CDP request (escape quotes in JS expression)
ESCAPED_EXPRESSION=$(echo "$JS_EXPRESSION" | sed 's/"/\\"/g')
CDP_REQUEST="{\"id\":1,\"method\":\"Runtime.evaluate\",\"params\":{\"expression\":\"$ESCAPED_EXPRESSION\",\"returnByValue\":true}}"

# Execute query via websocat
RESPONSE=$(echo "$CDP_REQUEST" | websocat -n1 -B "$BUFFER_SIZE" "$WS_URL" 2>&1) || {
    END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")
    EXECUTION_TIME=$((END_TIME - START_TIME))

    jq -nc \
        --arg status "error" \
        --arg code "WEBSOCKET_CLOSED" \
        --arg message "WebSocket connection to $WS_URL failed or closed" \
        --arg recovery "Re-fetch WebSocket URL: curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl'" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
}

# ============================================================================
# Parse CDP Response
# ============================================================================

# Check if response is valid JSON
if ! echo "$RESPONSE" | jq empty 2>/dev/null; then
    END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")
    EXECUTION_TIME=$((END_TIME - START_TIME))

    jq -nc \
        --arg status "error" \
        --arg code "INVALID_RESPONSE" \
        --arg message "CDP response is not valid JSON: ${RESPONSE:0:200}" \
        --arg recovery "Check Chrome is still running and WebSocket URL is valid" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# Check for CDP error in response
if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    ERROR_MSG=$(echo "$RESPONSE" | jq -r '.error.message')
    ERROR_CODE=$(echo "$RESPONSE" | jq -r '.error.code // "UNKNOWN"')

    END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")
    EXECUTION_TIME=$((END_TIME - START_TIME))

    # Provide context-specific recovery hints
    RECOVERY="Check JavaScript syntax and context availability"
    if [[ "$ERROR_MSG" == *"Cannot find context"* ]]; then
        RECOVERY="Re-fetch WebSocket URL (page may have navigated): curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl'"
    elif [[ "$ERROR_MSG" == *"Execution context was destroyed"* ]]; then
        RECOVERY="Retry after page reload or re-fetch WebSocket URL"
    fi

    jq -nc \
        --arg status "error" \
        --arg code "CDP_ERROR" \
        --arg message "CDP query failed: $ERROR_MSG (code: $ERROR_CODE)" \
        --arg recovery "$RECOVERY" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# ============================================================================
# Extract Result
# ============================================================================

RESULT_VALUE=$(echo "$RESPONSE" | jq -r '.result.result.value // empty')
RESULT_TYPE=$(echo "$RESPONSE" | jq -r '.result.result.type // "undefined"')

END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")
EXECUTION_TIME=$((END_TIME - START_TIME))

echo "CDP query succeeded in ${EXECUTION_TIME}ms" >&2

# ============================================================================
# Success Response
# ============================================================================

# Determine if result is scalar or object
if echo "$RESPONSE" | jq -e '.result.result.value | type' | grep -qE '(object|array)'; then
    # For objects/arrays, output as JSON object
    RESULT_JSON=$(echo "$RESPONSE" | jq -c '.result.result.value')

    jq -nc \
        --arg status "success" \
        --arg expression "$JS_EXPRESSION" \
        --argjson result "$RESULT_JSON" \
        --arg type "$RESULT_TYPE" \
        --argjson execution_time_ms "$EXECUTION_TIME" \
        '{status: $status, expression: $expression, result: $result, type: $type, execution_time_ms: $execution_time_ms}' >&1
else
    # For scalars (string, number, boolean), output as string
    jq -nc \
        --arg status "success" \
        --arg expression "$JS_EXPRESSION" \
        --arg result "$RESULT_VALUE" \
        --arg type "$RESULT_TYPE" \
        --argjson execution_time_ms "$EXECUTION_TIME" \
        '{status: $status, expression: $expression, result: $result, type: $type, execution_time_ms: $execution_time_ms}' >&1
fi

exit 0
