#!/bin/bash
# run_dual_path_validation.sh - Dual-path CI validation for migration safety
#
# Purpose: Run Bash and Python implementations side-by-side, compare outputs,
# and fail CI on divergence beyond thresholds
#
# Task: T070 [US5] - Migration Safety with Parallel Testing
#
# Usage:
#   ./run_dual_path_validation.sh <test-url> [duration]
#
# Exit codes:
#   0: Both implementations passed and outputs match within thresholds
#   1: One or both implementations failed to execute
#   2: Outputs diverged beyond acceptable thresholds (>5% DOM diff)
#   3: Script usage error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
TEST_URL="${1:-}"
DURATION="${2:-15}"
DOM_THRESHOLD="5.0"           # Hard fail if >5% DOM difference (FR-034)
TIMING_THRESHOLD="50.0"       # Soft warn if >50% timing difference
OUTPUT_DIR="/tmp/dual-path-validation-$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    cat <<EOF
Usage: $0 <test-url> [duration]

Run Bash and Python implementations side-by-side for migration safety validation.

Arguments:
    test-url    URL to test (e.g., https://example.com)
    duration    Duration in seconds (default: 15)

Examples:
    $0 https://example.com/page
    $0 https://example.com/page 30

Exit codes:
    0: Outputs match within thresholds
    1: Implementation execution failed
    2: Outputs diverged beyond thresholds
    3: Usage error
EOF
}

# Validate arguments
if [ -z "$TEST_URL" ]; then
    echo "Error: test-url is required" >&2
    usage
    exit 3
fi

echo "=== Dual-Path Migration Safety Validation ==="
echo "Test URL: $TEST_URL"
echo "Duration: ${DURATION}s"
echo "DOM Threshold: ${DOM_THRESHOLD}%"
echo "Timing Threshold: ${TIMING_THRESHOLD}%"
echo ""

# Create output directories
mkdir -p "$OUTPUT_DIR"/{bash,python}

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    # Kill any remaining Chrome processes from tests
    pkill -f "chrome.*9222" 2>/dev/null || true
    pkill -f "chrome.*9223" 2>/dev/null || true
    # Clean Chrome profiles
    rm -rf "$OUTPUT_DIR" 2>/dev/null || true
    rm -rf /tmp/bash-chrome-profile-$$ /tmp/python-chrome-profile-$$ 2>/dev/null || true
}

trap cleanup EXIT INT TERM

# Run Bash implementation
echo "[1/4] Running Bash implementation..."
BASH_OUTPUT="$OUTPUT_DIR/bash"
BASH_LOG="$BASH_OUTPUT/orchestrator.log"

cd "$REPO_ROOT"
if ! ./scripts/core/debug-orchestrator.sh \
    "$TEST_URL" \
    "$DURATION" \
    "$BASH_LOG" \
    --mode=headless \
    --port=9222 \
    --profile=/tmp/bash-chrome-profile-$$ \
    --include-console \
    --summary=json \
    > "$BASH_OUTPUT/stdout.log" 2> "$BASH_OUTPUT/stderr.log"; then

    echo -e "${RED}✗ Bash implementation failed${NC}"
    echo "Stdout: $(cat "$BASH_OUTPUT/stdout.log")"
    echo "Stderr: $(cat "$BASH_OUTPUT/stderr.log")"
    exit 1
fi

echo -e "${GREEN}✓ Bash implementation completed${NC}"

# Extract outputs
BASH_DOM="$BASH_OUTPUT/dom.html"
BASH_CONSOLE="$BASH_OUTPUT/console.jsonl"
BASH_SUMMARY="$BASH_OUTPUT/summary.json"

# Verify Bash outputs exist
if [ ! -f "$BASH_DOM" ]; then
    echo -e "${RED}✗ Bash DOM output not found: $BASH_DOM${NC}"
    exit 1
fi

# Run Python implementation
echo ""
echo "[2/4] Running Python implementation..."
PYTHON_OUTPUT="$OUTPUT_DIR/python"

cd "$REPO_ROOT"
if ! python3 -m scripts.cdp.cli.main orchestrate \
    headless \
    "$TEST_URL" \
    --duration "$DURATION" \
    --output "$PYTHON_OUTPUT/orchestrator.log" \
    --chrome-port 9223 \
    --profile /tmp/python-chrome-profile-$$ \
    --include-console \
    --summary json \
    > "$PYTHON_OUTPUT/stdout.log" 2> "$PYTHON_OUTPUT/stderr.log"; then

    echo -e "${RED}✗ Python implementation failed${NC}"
    echo "Stdout: $(cat "$PYTHON_OUTPUT/stdout.log")"
    echo "Stderr: $(cat "$PYTHON_OUTPUT/stderr.log")"
    exit 1
fi

echo -e "${GREEN}✓ Python implementation completed${NC}"

# Extract outputs
PYTHON_DOM="$PYTHON_OUTPUT/dom.html"
PYTHON_CONSOLE="$PYTHON_OUTPUT/console.jsonl"
PYTHON_SUMMARY="$PYTHON_OUTPUT/summary.json"

# Verify Python outputs exist
if [ ! -f "$PYTHON_DOM" ]; then
    echo -e "${RED}✗ Python DOM output not found: $PYTHON_DOM${NC}"
    exit 1
fi

# Compare outputs
echo ""
echo "[3/4] Comparing outputs..."

# Use Python comparison script
COMPARISON_RESULT="$OUTPUT_DIR/comparison.json"

python3 << 'PYEOF' > "$COMPARISON_RESULT"
import sys
import json
sys.path.insert(0, '/Users/szymondzumak/Developer/claude-browser-debugger')

from tests.ci.compare_outputs import compare_dom_html

# Read DOM files
with open('${BASH_DOM}', 'r') as f:
    bash_dom = f.read()

with open('${PYTHON_DOM}', 'r') as f:
    python_dom = f.read()

# Compare
result = compare_dom_html(bash_dom, python_dom, threshold_percent=${DOM_THRESHOLD})

# Output as JSON
print(json.dumps(result.to_dict(), indent=2))
PYEOF

# Parse comparison results
DOM_DIVERGENCE=$(jq -r '.divergence_percent' "$COMPARISON_RESULT")
DOM_PASSED=$(jq -r '.passed' "$COMPARISON_RESULT")

echo ""
echo "=== Comparison Results ==="
echo "DOM Divergence: ${DOM_DIVERGENCE}%"
echo "Threshold: ${DOM_THRESHOLD}%"
echo ""

# Evaluate results
EXIT_CODE=0
REGRESSION_DETECTED="false"

if [ "$DOM_PASSED" = "false" ]; then
    echo -e "${RED}✗ FAIL: DOM divergence (${DOM_DIVERGENCE}%) exceeds threshold (${DOM_THRESHOLD}%)${NC}"
    EXIT_CODE=2
    REGRESSION_DETECTED="true"
else
    echo -e "${GREEN}✓ PASS: DOM outputs match within threshold${NC}"
fi

# T072: Rollback criteria detection (FR-036)
# Track consecutive failures for rollback decision
HISTORY_FILE="$REPO_ROOT/.dual-path-history.json"

echo ""
echo "[4/5] Checking rollback criteria..."

# Record current result in history
python3 << 'HISTEOF'
import json
import os
from datetime import datetime

history_file = '${HISTORY_FILE}'
current_result = {
    "timestamp": datetime.now().isoformat(),
    "url": "${TEST_URL}",
    "dom_passed": ${DOM_PASSED},
    "dom_divergence": ${DOM_DIVERGENCE},
    "regression": ${REGRESSION_DETECTED}
}

# Load existing history
history = []
if os.path.exists(history_file):
    with open(history_file, 'r') as f:
        try:
            history = json.load(f)
        except:
            history = []

# Append current result
history.append(current_result)

# Keep only last 10 runs
history = history[-10:]

# Save updated history
with open(history_file, 'w') as f:
    json.dump(history, f, indent=2)

# Analyze for rollback criteria (FR-036)
recent_runs = history[-3:]  # Last 3 runs
regression_count = sum(1 for r in recent_runs if r.get("regression", False))

rollback_needed = False
rollback_reason = ""

if regression_count >= 2:
    rollback_needed = True
    rollback_reason = f"2+ regressions detected in last 3 runs ({regression_count}/3)"

# Check for critical divergence (>20% = critical bug)
if current_result["dom_divergence"] > 20.0:
    rollback_needed = True
    rollback_reason = f"Critical divergence detected: {current_result['dom_divergence']}% (threshold: 20%)"

# Output rollback decision
rollback_data = {
    "rollback_needed": rollback_needed,
    "reason": rollback_reason,
    "regression_count": regression_count,
    "recent_runs": len(recent_runs)
}

print(json.dumps(rollback_data, indent=2))
HISTEOF

ROLLBACK_NEEDED=$(python3 -c "
import json
with open('${HISTORY_FILE}', 'r') as f:
    history = json.load(f)
recent = history[-3:]
regressions = sum(1 for r in recent if r.get('regression', False))
print('true' if regressions >= 2 or ${DOM_DIVERGENCE} > 20.0 else 'false')
")

if [ "$ROLLBACK_NEEDED" = "true" ]; then
    echo -e "${RED}⚠ ROLLBACK RECOMMENDED: Migration safety criteria not met${NC}"
    echo "Run history: $HISTORY_FILE"
    EXIT_CODE=2
else
    echo -e "${GREEN}✓ Rollback criteria OK${NC}"
fi

echo ""
echo "[5/5] Validation complete"
echo "Full comparison results: $COMPARISON_RESULT"
echo "Bash outputs: $BASH_OUTPUT/"
echo "Python outputs: $PYTHON_OUTPUT/"
echo "Run history: $HISTORY_FILE"

exit $EXIT_CODE
