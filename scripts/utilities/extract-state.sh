#!/bin/bash
# extract-state.sh - Unified state extraction helper
# Usage: ./extract-state.sh [PORT] [OUTPUT_DIR]
#
# Extracts all relevant page state (DOM, Redux, forms, localStorage, cookies)
# in a single command without manual CDP command construction.
#
# Examples:
#   ./extract-state.sh
#   ./extract-state.sh 9222
#   ./extract-state.sh 9222 /tmp/my-test-state

set -euo pipefail

# T013: Parameter parsing
PORT="${1:-9222}"
OUTPUT_DIR="${2:-/tmp/state-extract-$(date +%Y%m%d-%H%M%S)}"

# T015: Create output directory
mkdir -p "$OUTPUT_DIR"

# T014: Chrome connectivity validation
echo "= Validating Chrome connection on port $PORT..."
WS_URL=$(curl -s "http://localhost:${PORT}/json" 2>/dev/null | jq -r '.[0].webSocketDebuggerUrl' 2>/dev/null || echo "")

if [ -z "$WS_URL" ] || [ "$WS_URL" = "null" ]; then
    echo ""
    echo "L Chrome not running on port $PORT"
    echo ""
    echo "=¡ Recovery:"
    echo "   - Start Chrome with CDP: chrome --remote-debugging-port=$PORT"
    echo "   - Or use debug-orchestrator.sh to launch headed mode"
    echo ""

    # Generate error summary.json
    cat > "$OUTPUT_DIR/summary.json" <<EOF
{
  "exitCode": 2,
  "outputDirectory": "$OUTPUT_DIR",
  "error": "Chrome not running on port $PORT",
  "results": {},
  "successCount": 0,
  "totalCount": 0
}
EOF
    exit 2
fi

echo " Connected to Chrome on port $PORT"
echo ""

# T021: Track success/failure for each source
declare -A results
declare -a errors
sources=("dom" "redux" "forms" "localStorage" "cookies")
success_count=0
total_count=${#sources[@]}

# T025: User-friendly output
echo "= Extracting page state..."
echo ""

# T016: Extract DOM
echo -n "   DOM... "
DOM_EXPRESSION='document.documentElement.outerHTML'
if echo "{\"id\":1,\"method\":\"Runtime.evaluate\",\"params\":{\"expression\":\"$DOM_EXPRESSION\",\"returnByValue\":true}}" \
    | websocat -n1 -B 2097152 "$WS_URL" 2>/dev/null \
    | jq -r '.result.result.value' > "$OUTPUT_DIR/dom.html" 2>/dev/null && [ -s "$OUTPUT_DIR/dom.html" ]; then
    DOM_SIZE=$(wc -c < "$OUTPUT_DIR/dom.html" | tr -d ' ')
    echo " ($(numfmt --to=iec-i --suffix=B $DOM_SIZE 2>/dev/null || echo "${DOM_SIZE} bytes"))"
    results[dom]="success"
    ((success_count++))
else
    echo "L Failed"
    results[dom]="failed"
    errors+=('{"source":"dom","error":"DOM extraction failed","suggestion":"Check if page is loaded"}')
fi

# T017: Extract Redux state
echo -n "   Redux state... "
REDUX_EXPRESSION='JSON.stringify(window.__EXPOSED_REDUX_STORE__?.getState() || null)'
REDUX_RESULT=$(echo "{\"id\":2,\"method\":\"Runtime.evaluate\",\"params\":{\"expression\":\"$REDUX_EXPRESSION\",\"returnByValue\":true}}" \
    | websocat -n1 "$WS_URL" 2>/dev/null \
    | jq -r '.result.result.value' 2>/dev/null || echo "null")

if [ "$REDUX_RESULT" != "null" ] && [ -n "$REDUX_RESULT" ]; then
    echo "$REDUX_RESULT" > "$OUTPUT_DIR/redux-state.json"
    REDUX_SIZE=$(wc -c < "$OUTPUT_DIR/redux-state.json" | tr -d ' ')
    echo " ($(numfmt --to=iec-i --suffix=B $REDUX_SIZE 2>/dev/null || echo "${REDUX_SIZE} bytes"))"
    results[redux]="success"
    ((success_count++))
else
    echo "   Not available"
    results[redux]="not_available"
    errors+=('{"source":"redux","error":"window.__EXPOSED_REDUX_STORE__ is undefined","suggestion":"Run inject-redux.js before extraction or use parse-redux-logs.py"}')
fi

# T018: Extract form data
echo -n "   Form data... "
FORM_EXPRESSION='JSON.stringify(Array.from(document.querySelectorAll("input, select, textarea")).map(el => ({name: el.name, id: el.id, value: el.value, type: el.type || el.tagName.toLowerCase()})))'
if echo "{\"id\":3,\"method\":\"Runtime.evaluate\",\"params\":{\"expression\":\"$FORM_EXPRESSION\",\"returnByValue\":true}}" \
    | websocat -n1 "$WS_URL" 2>/dev/null \
    | jq -r '.result.result.value' > "$OUTPUT_DIR/form-data.json" 2>/dev/null && [ -s "$OUTPUT_DIR/form-data.json" ]; then
    FIELD_COUNT=$(jq 'length' "$OUTPUT_DIR/form-data.json" 2>/dev/null || echo 0)
    echo " ($FIELD_COUNT fields)"
    results[forms]="success"
    ((success_count++))
else
    echo "L Failed"
    results[forms]="failed"
    errors+=('{"source":"forms","error":"Form data extraction failed","suggestion":"Check if page has form elements"}')
fi

# T019: Extract localStorage
echo -n "   localStorage... "
LOCALSTORAGE_EXPRESSION='JSON.stringify(Object.fromEntries(Object.entries(localStorage)))'
if echo "{\"id\":4,\"method\":\"Runtime.evaluate\",\"params\":{\"expression\":\"$LOCALSTORAGE_EXPRESSION\",\"returnByValue\":true}}" \
    | websocat -n1 "$WS_URL" 2>/dev/null \
    | jq -r '.result.result.value' > "$OUTPUT_DIR/localstorage.json" 2>/dev/null && [ -s "$OUTPUT_DIR/localstorage.json" ]; then
    KEY_COUNT=$(jq 'keys | length' "$OUTPUT_DIR/localstorage.json" 2>/dev/null || echo 0)
    echo " ($KEY_COUNT keys)"
    results[localStorage]="success"
    ((success_count++))
else
    echo "L Failed"
    results[localStorage]="failed"
    errors+=('{"source":"localStorage","error":"localStorage extraction failed","suggestion":"Check if page has localStorage access"}')
fi

# T020: Extract cookies
echo -n "   Cookies... "
if echo '{"id":5,"method":"Network.getAllCookies"}' \
    | websocat -n1 "$WS_URL" 2>/dev/null \
    | jq -r '.result.cookies' > "$OUTPUT_DIR/cookies.json" 2>/dev/null && [ -s "$OUTPUT_DIR/cookies.json" ]; then
    COOKIE_COUNT=$(jq 'length' "$OUTPUT_DIR/cookies.json" 2>/dev/null || echo 0)
    echo " ($COOKIE_COUNT cookies)"
    results[cookies]="success"
    ((success_count++))
else
    echo "L Failed"
    results[cookies]="failed"
    errors+=('{"source":"cookies","error":"Cookie extraction failed","suggestion":"Check CDP Network domain is enabled"}')
fi

echo ""

# T022: Generate summary.json
RESULTS_JSON=$(printf '%s\n' "${!results[@]}" "${results[@]}" | jq -nR '[inputs] as $lines | ($lines | length / 2) as $n | reduce range(0; $n) as $i ({}; . + {($lines[$i]): $lines[$i + $n]})')

# Build errors array JSON
if [ ${#errors[@]} -gt 0 ]; then
    ERRORS_JSON=$(printf '%s\n' "${errors[@]}" | jq -s '.')
else
    ERRORS_JSON="[]"
fi

# T023: Determine exit code
if [ "$success_count" -eq "$total_count" ]; then
    EXIT_CODE=0
elif [ "$success_count" -gt 0 ]; then
    EXIT_CODE=1
else
    EXIT_CODE=2
fi

# Write summary
cat > "$OUTPUT_DIR/summary.json" <<EOF
{
  "exitCode": $EXIT_CODE,
  "outputDirectory": "$OUTPUT_DIR",
  "results": $RESULTS_JSON,
  "successCount": $success_count,
  "totalCount": $total_count,
  "errors": $ERRORS_JSON
}
EOF

# T025: Final user-friendly output
echo "=Â State saved to: $OUTPUT_DIR"
echo ""

if [ "$success_count" -eq "$total_count" ]; then
    echo " All extractions successful!"
elif [ "$success_count" -gt 0 ]; then
    echo "   Partial success: $success_count/$total_count sources extracted"
    echo "   See $OUTPUT_DIR/summary.json for details"
else
    echo "L All extractions failed"
    echo "   See $OUTPUT_DIR/summary.json for details"
fi

echo ""

exit $EXIT_CODE
