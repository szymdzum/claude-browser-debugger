#!/bin/bash
# smoke-test-headed.sh - Validate headed Chrome CDP functionality
# Tests that headed mode with --user-data-dir works correctly

set -euo pipefail

# Configuration
TEST_PORT=9999
TEST_PROFILE="/tmp/chrome-smoke-test-$$"
TEST_TIMEOUT=10
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    pkill -f "chrome.*${TEST_PORT}" 2>/dev/null || true
    rm -rf "$TEST_PROFILE" 2>/dev/null || true
}

trap cleanup EXIT

echo "========================================"
echo "Headed Chrome CDP Smoke Test"
echo "========================================"
echo ""

# Step 1: Check Chrome version
echo "1. Checking Chrome version..."
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ ! -f "$CHROME_PATH" ]; then
    echo -e "${RED}✗ Chrome not found at: $CHROME_PATH${NC}"
    exit 1
fi

CHROME_VERSION=$("$CHROME_PATH" --version)
echo -e "${GREEN}✓ Found: $CHROME_VERSION${NC}"

# Check if Chrome 136+
VERSION_NUM=$(echo "$CHROME_VERSION" | grep -oE '[0-9]+' | head -1)
if [ "$VERSION_NUM" -ge 136 ]; then
    echo -e "${YELLOW}  Note: Chrome $VERSION_NUM requires --user-data-dir for headed CDP${NC}"
fi
echo ""

# Step 2: Launch headed Chrome with user-data-dir
echo "2. Launching headed Chrome..."
echo "   Port: $TEST_PORT"
echo "   Profile: $TEST_PROFILE"

"$CHROME_PATH" \
    --user-data-dir="$TEST_PROFILE" \
    --remote-debugging-port="$TEST_PORT" \
    --no-first-run \
    --no-default-browser-check \
    "about:blank" \
    > /dev/null 2>&1 &

CHROME_PID=$!
echo -e "${GREEN}✓ Chrome launched (PID: $CHROME_PID)${NC}"
echo ""

# Step 3: Wait for Chrome to be ready
echo "3. Waiting for Chrome to be ready..."
MAX_ATTEMPTS=10
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s "http://localhost:${TEST_PORT}/json" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Chrome DevTools endpoint responding${NC}"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 1
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}✗ Chrome failed to start within ${MAX_ATTEMPTS} seconds${NC}"
    exit 1
fi
echo ""

# Step 4: Get page ID
echo "4. Getting page ID..."
PAGE_ID=$(curl -s "http://localhost:${TEST_PORT}/json" | jq -r '.[0].id')

if [ -z "$PAGE_ID" ] || [ "$PAGE_ID" = "null" ]; then
    echo -e "${RED}✗ Failed to get page ID${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Page ID: $PAGE_ID${NC}"
echo ""

# Step 5: Test CDP Runtime.evaluate
echo "5. Testing CDP Runtime.evaluate..."

TEST_SCRIPT=$(cat <<'EOF'
import argparse
import asyncio
import json
import sys

import websockets

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--page-id", dest="page_id", required=True)
args = parser.parse_args()

async def test_cdp():
    ws_url = f'ws://localhost:{args.port}/devtools/page/{args.page_id}'

    try:
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps({
                'id': 1,
                'method': 'Runtime.evaluate',
                'params': {
                    'expression': '2 + 2',
                    'returnByValue': True
                }
            }))

            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            result = json.loads(response)

            if 'result' in result and 'result' in result['result']:
                value = result['result']['result'].get('value')
                if value == 4:
                    print('SUCCESS')
                    return 0
                else:
                    print(f'WRONG_RESULT:{value}')
                    return 1
            else:
                print('NO_RESULT')
                return 1

    except asyncio.TimeoutError:
        print('TIMEOUT')
        return 1
    except Exception as e:
        print(f'ERROR:{e}')
        return 1

sys.exit(asyncio.run(test_cdp()))
EOF
)

TEST_RESULT=$($PYTHON_BIN -c "$TEST_SCRIPT" --port "$TEST_PORT" --page-id "$PAGE_ID" 2>&1 || echo "FAILED")

if [ "$TEST_RESULT" = "SUCCESS" ]; then
    echo -e "${GREEN}✓ CDP Runtime.evaluate working correctly${NC}"
    echo "  Expression: 2 + 2"
    echo "  Result: 4 ✓"
else
    echo -e "${RED}✗ CDP test failed: $TEST_RESULT${NC}"

    if [ "$TEST_RESULT" = "TIMEOUT" ]; then
        echo ""
        echo -e "${YELLOW}Possible causes:${NC}"
        echo "  - Chrome 136+ without --user-data-dir (security policy)"
        echo "  - Network firewall blocking localhost connections"
        echo "  - Chrome DevTools protocol disabled"
    fi

    exit 1
fi
echo ""

# Step 6: Test with a more complex command
echo "6. Testing DOM access..."

DOM_TEST_SCRIPT='document.title || "about:blank"'
DOM_RESULT=$($PYTHON_BIN -c "
import asyncio
import websockets
import json

async def test_dom():
    ws_url = 'ws://localhost:${TEST_PORT}/devtools/page/${PAGE_ID}'
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            'id': 2,
            'method': 'Runtime.evaluate',
            'params': {
                'expression': '''${DOM_TEST_SCRIPT}''',
                'returnByValue': True
            }
        }))
        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
        result = json.loads(response)
        print(result['result']['result']['value'])

asyncio.run(test_dom())
" 2>&1)

if [ -n "$DOM_RESULT" ]; then
    echo -e "${GREEN}✓ DOM access working${NC}"
    echo "  Page title: \"$DOM_RESULT\""
else
    echo -e "${RED}✗ DOM access failed${NC}"
    exit 1
fi
echo ""

# Success!
echo "========================================"
echo -e "${GREEN}✓ All tests passed!${NC}"
echo "========================================"
echo ""
echo "Summary:"
echo "  Chrome Version: $CHROME_VERSION"
echo "  Profile: $TEST_PROFILE"
echo "  CDP Port: $TEST_PORT"
echo "  Runtime.evaluate: ✓"
echo "  DOM Access: ✓"
echo ""
echo -e "${GREEN}Headed Chrome CDP is working correctly!${NC}"

exit 0
