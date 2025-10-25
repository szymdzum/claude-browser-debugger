# Troubleshooting Guide

## Overview

This document provides comprehensive troubleshooting guidance for the browser-debugger skill. Covers common issues, error messages, diagnostic procedures, and Chrome version compatibility.

## Table of Contents

- [Prerequisites and Installation](#prerequisites-and-installation)
- [Chrome Launch Issues](#chrome-launch-issues)
- [CDP Connection Issues](#cdp-connection-issues)
- [WebSocket Issues](#websocket-issues)
- [DOM Extraction Issues](#dom-extraction-issues)
- [Port Conflicts](#port-conflicts)
- [Chrome Version Compatibility](#chrome-version-compatibility)
- [Diagnostic Procedures](#diagnostic-procedures)

---

## Prerequisites and Installation

### Issue: "No module named 'websockets'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'websockets'
```

**Solution:**
```bash
# Install Python websockets library
pip3 install websockets --break-system-packages

# Or install in user directory
python3 -m pip install websockets --user

# Verify installation
python3 -c "import websockets; print('websockets installed')"
```

### Issue: "websocat: command not found"

**Symptoms:**
```
bash: websocat: command not found
```

**Recovery:**

Check if Python websockets is available as fallback:
```bash
python3 -c "import websockets" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "Using Python websockets method (see Tool Detection Pattern in cdp-commands.md)"
    # Use Python extraction script
else
    echo "ERROR: Install websocat (brew install websocat) or Python websockets (pip3 install websockets)"
    exit 1
fi
```

**Installation:**
```bash
# macOS
brew install websocat

# Linux with Rust
cargo install websocat

# Verify installation
command -v websocat &>/dev/null && echo "websocat: installed" || echo "websocat: not found"
```

### Issue: "jq: command not found"

**Symptoms:**
```
bash: jq: command not found
```

**Solution:**
```bash
# macOS
brew install jq

# Debian/Ubuntu
apt-get install jq

# Verify installation
jq --version
```

### Prerequisites Check Script

```bash
#!/bin/bash
echo "Checking prerequisites..."

# Check Chrome (required: Chrome 136+)
if chrome --version &>/dev/null; then
    CHROME_VERSION=$(chrome --version)
    echo "✓ Chrome: $CHROME_VERSION"
else
    echo "✗ Chrome: not found"
fi

# Check Python (required: 3.7+)
if python3 --version &>/dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Python: $PYTHON_VERSION"
else
    echo "✗ Python: not found"
fi

# Check jq (required for JSON parsing)
if jq --version &>/dev/null; then
    JQ_VERSION=$(jq --version)
    echo "✓ jq: $JQ_VERSION"
else
    echo "✗ jq: not found"
fi

# Check websocat (primary method - optional)
if command -v websocat &>/dev/null; then
    echo "✓ websocat: installed"
else
    echo "⚠ websocat: not found (optional, will use Python fallback)"
fi

# Check Python websockets (fallback method)
if python3 -c "import websockets" 2>/dev/null; then
    echo "✓ Python websockets: installed"
else
    echo "⚠ Python websockets: not found"
fi
```

---

## Chrome Launch Issues

### Issue: Chrome doesn't start

**Symptoms:**
```
Failed to launch Chrome
```

**Diagnosis:**
```bash
# Check if Chrome is installed
chrome --version

# Check if port is already in use
lsof -i :9222

# Check Chrome processes
ps aux | grep chrome
```

**Solution:**
```bash
# Kill existing Chrome processes
pkill -f "chrome.*9222"

# Try launching manually
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2

# Verify Chrome started
lsof -i :9222
```

### Issue: Chrome starts but exits immediately

**Symptoms:**
Chrome process starts but immediately exits.

**Diagnosis:**
```bash
# Launch Chrome and capture output
chrome --headless=new --remote-debugging-port=9222 https://example.com 2>&1 | tee /tmp/chrome.log &

# Check for error messages
cat /tmp/chrome.log
```

**Common causes:**
- Invalid URL
- Missing dependencies
- Insufficient permissions
- Profile corruption

**Solution:**
```bash
# Try with minimal flags
chrome --headless=new https://example.com

# Use different profile
chrome --headless=new --user-data-dir="/tmp/chrome-test" --remote-debugging-port=9222 https://example.com &
```

### Issue: Headed mode hangs indefinitely

**Symptoms:**
- Chrome window opens
- CDP endpoint accessible
- WebSocket URL valid
- CDP commands never respond (infinite hang)
- No error messages

**Cause:** Chrome 136+ (March 2025) requires `--user-data-dir` for CDP access. This is a security policy to prevent CDP from accessing your default profile where all your passwords and cookies are stored.

**Diagnosis:**
```bash
# Check if you forgot --user-data-dir
ps aux | grep chrome | grep remote-debugging-port

# If you see ONLY --remote-debugging-port without --user-data-dir, that's the issue
```

**Solution:**
Ensure you're using `scripts/core/chrome-launcher.sh` or `python3 -m scripts.cdp.cli.main orchestrate`, which handle this automatically. If launching Chrome manually, always include `--user-data-dir`:

```bash
# Kill Chrome
pkill -f "chrome.*9222"

# ✅ CORRECT - Relaunch with isolated profile
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL
```

**See also:** `docs/guides/chrome-136-incident.md` for complete Chrome 136+ documentation.

### Issue: "Profile in use" error

**Symptoms:**
```
The profile appears to be in use by another Google Chrome process
```

**Solution:**
```bash
# Kill all Chrome processes using that profile
pkill -f "chrome.*chrome-debug-profile"

# Wait for cleanup
sleep 2

# Relaunch
python3 -m scripts.cdp.cli.main orchestrate headed "URL" --include-console

# Or use a different profile path
PROFILE="/tmp/chrome-debug-$(date +%s)"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL
```

---

## CDP Connection Issues

### Issue: "Connection refused" when connecting to CDP

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 9222: Connection refused
```

**Diagnosis:**
```bash
# Check if Chrome is running
lsof -i :9222

# Verify debugging endpoint
curl http://localhost:9222/json

# Check Chrome processes
ps aux | grep chrome | grep remote-debugging
```

**Solution:**
```bash
# If Chrome not running, launch it
python3 -m scripts.cdp.cli.main orchestrate headed "https://example.com" --include-console

# If Chrome running but not responding, restart it
pkill -f "chrome.*9222"
sleep 2
python3 -m scripts.cdp.cli.main orchestrate headed "https://example.com" --include-console
```

### Issue: Chrome responds to HTTP but not WebSocket

**Symptoms:**
- `curl http://localhost:9222/json` returns valid JSON
- WebSocket URL is present
- WebSocket connection times out or hangs

**Diagnosis:**
```bash
# Verify Chrome is running with debugging enabled
ps aux | grep chrome | grep remote-debugging

# Test basic CDP command
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq
```

**Solution for Chrome 136+:**
```bash
# If using Chrome 136+, ensure --user-data-dir is set
pkill -f "chrome.*9222"
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL

# Verify
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq
```

### Issue: CDP returns "Cannot find context with specified id"

**Symptoms:**
```json
{
  "id": 1,
  "error": {
    "code": -32000,
    "message": "Cannot find context with specified id"
  }
}
```

**Cause:** WebSocket URL or page ID is stale (page navigated or refreshed).

**Solution:**
```bash
# Re-fetch WebSocket URL (page navigated)
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)

# Retry command
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'
```

**Prevention:**
Always re-fetch WebSocket URL before each extraction:
```bash
# Before each extraction
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
```

---

## WebSocket Issues

### Issue: Buffer overflow

**Symptoms:**
```
[WARN  websocat::readdebt] Incoming message too long (324990 > 65535)
```

**Cause:** DOM is larger than websocat's default 64KB buffer.

**Solution:**
```bash
# Increase buffer size to 1MB
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html

# For very large DOMs, use 2MB buffer
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 2097152 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html
```

**Alternative:** Extract only specific elements:
```bash
# Extract body only (smaller)
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.body.innerHTML","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Extract main content only
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.querySelector('\''main'\'').outerHTML","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Issue: WebSocket connection times out

**Symptoms:**
```
websocat: WebSocketError: IO error: Connection reset by peer
```

**Diagnosis:**
```bash
# Verify WebSocket URL is valid
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo "$WS_URL"

# Test connection
echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq
```

**Solution:**
```bash
# Re-fetch WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)

# Retry with increased timeout
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
  | timeout 10 websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Issue: WebSocket URL stale

**Symptoms:**
- WebSocket URL obtained at Chrome launch no longer works
- Page navigation occurred
- Commands time out or return "context not found" error

**Cause:** Page navigated, causing WebSocket URL to become invalid.

**Solution:**
```bash
# Always re-fetch WebSocket URL before extraction
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)

# Verify current page URL
curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .url'

# Then extract DOM
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'
```

---

## DOM Extraction Issues

### Issue: DOM extraction returns empty or truncated output

**Symptoms:**
- Empty file
- Partial HTML
- Truncated at specific size

**Diagnosis:**
```bash
# Check file size
ls -lh /tmp/live-dom.html

# Check for websocat buffer warning
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" 2>&1 | grep -i "warn"
```

**Solution:**
```bash
# Increase buffer size
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 2097152 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html

# Verify extraction
head -n 5 /tmp/live-dom.html
tail -n 5 /tmp/live-dom.html
```

### Issue: DOM extraction shows initial state, not after user interaction

**Symptoms:**
- Form fields show as empty when they should have values
- Error messages not visible
- DOM doesn't reflect user actions

**Cause:** Extracted DOM before user finished interacting, or used stale WebSocket URL.

**Solution:**
```bash
# Always re-fetch WebSocket URL after user interaction
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)

# Add delay for React/Vue hydration if needed
sleep 3

# Extract current state
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value' > /tmp/live-dom.html
```

### Issue: JavaScript frameworks not hydrated

**Symptoms:**
- Missing content that should be rendered by React/Vue/Angular
- Skeleton UI visible in DOM
- Dynamic content not present

**Solution:**
Wait for JavaScript frameworks to hydrate before extracting DOM:

```bash
# Launch Chrome
python3 -m scripts.cdp.cli.main orchestrate headed "http://localhost:3000" --include-console

# Wait for hydration (adjust timing as needed)
sleep 3

# Then extract DOM
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'
```

---

## Port Conflicts

### Issue: Port 9222 already in use

**Symptoms:**
```
ERROR: Port 9222 is already in use by PID 12345
```

**Diagnosis:**
```bash
# Check what's using the port
lsof -i :9222

# Check Chrome processes
ps aux | grep chrome | grep 9222
```

**Solution Option 1: Kill existing process**
```bash
# Kill existing Chrome processes
pkill -f "chrome.*9222"

# Wait for cleanup
sleep 2

# Verify port is free
lsof -i :9222

# Relaunch
python3 -m scripts.cdp.cli.main orchestrate headed "URL" --include-console
```

**Solution Option 2: Use alternate port**
```bash
# Launch on different port
chrome --headless=new --remote-debugging-port=9223 https://example.com &
sleep 2

# Get page ID with custom port
PAGE_ID=$(curl -s "http://localhost:9223/json" | jq -r '.[] | select(.type=="page") | .id' | head -1)

# Monitor with custom port
python3 -m scripts.cdp.cli.main console stream \
  --target "$PAGE_ID" \
  --chrome-port 9223 \
  --duration 30 \
  --output /tmp/console-9223.jsonl
```

### Issue: Cannot kill Chrome process

**Symptoms:**
```
pkill doesn't terminate Chrome
lsof still shows port in use
```

**Solution:**
```bash
# Get Chrome PID
CHROME_PID=$(lsof -ti :9222)

# Force kill
kill -9 $CHROME_PID

# Verify
lsof -i :9222

# If still running, kill all Chrome processes
pkill -9 chrome
```

---

## Chrome Version Compatibility

### Chrome 136+ Specific Issues

**Requirement:** Chrome 136+ (March 2025) requires `--user-data-dir` for headed mode CDP access.

**Issue: Headed mode silently hangs**

**Symptoms:**
- Chrome window opens
- CDP endpoint responds to HTTP
- WebSocket URL obtained successfully
- CDP commands never respond (infinite hang)
- No error messages anywhere

**Cause:** Chrome 136+ blocks CDP access to default profile for security.

**Solution:**
```bash
# Kill Chrome
pkill -f "chrome.*9222"

# ✅ Launch with isolated profile
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL
```

**Verification:**
```bash
# 1. Check Chrome version
chrome --version
# Should show 136.x or higher

# 2. Verify profile flag is present
ps aux | grep chrome | grep user-data-dir

# 3. Test CDP responds
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq

# Expected: Immediate response with Chrome version
```

**See also:** `docs/guides/chrome-136-incident.md`

### Issue: Tilde (~) not expanded in --user-data-dir

**Symptoms:**
Chrome creates a directory literally named `~` in the current directory.

**Cause:** Tilde expansion doesn't occur inside quoted strings or flag values.

**Solution:**
```bash
# ❌ WRONG - tilde inside quotes/flag value not expanded
chrome --user-data-dir=~/.chrome-debug-profile --remote-debugging-port=9222 URL

# ✅ CORRECT - use $HOME instead
chrome --user-data-dir="$HOME/.chrome-debug-profile" --remote-debugging-port=9222 URL

# ✅ CORRECT - expand tilde with variable
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL
```

---

## Diagnostic Procedures

### Full Diagnostic Workflow

```bash
#!/bin/bash
echo "=== Browser Debugger Diagnostics ==="
echo

echo "1. Checking prerequisites..."
python3 --version
python3 -c "import websockets; print('websockets: installed')" 2>/dev/null || echo "websockets: not found"
jq --version
chrome --version
command -v websocat &>/dev/null && echo "websocat: installed" || echo "websocat: not found"
echo

echo "2. Checking Chrome processes..."
ps aux | grep chrome | grep remote-debugging
echo

echo "3. Checking port 9222..."
lsof -i :9222
echo

echo "4. Testing CDP endpoint..."
curl -s http://localhost:9222/json | jq
echo

echo "5. Testing WebSocket connection..."
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl' 2>/dev/null)
if [ -n "$WS_URL" ]; then
    echo "WebSocket URL: $WS_URL"
    echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq
else
    echo "ERROR: Could not obtain WebSocket URL"
fi
echo

echo "=== Diagnostics complete ==="
```

### Manual Testing Procedure

Validate headed Chrome CDP functionality after Chrome updates:

```bash
# 1. Test headed Chrome launch
python3 -m scripts.cdp.cli.main orchestrate headed "https://example.com" --include-console

# 2. Verify Chrome responds to CDP commands
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"2+2","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq

# Expected: {"id":1,"result":{"result":{"type":"number","value":4}}}

# 3. Test DOM extraction
echo '{"id":2,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Expected: Page title

# 4. Cleanup
pkill -f "chrome.*9222"
```

### Smoke Test

Run automated smoke test for headed Chrome CDP functionality:

```bash
./tests/smoke-test-headed.sh
```

This validates:
- Chrome version detection
- `--user-data-dir` behavior
- Runtime.evaluate execution
- DOM access
- WebSocket connectivity

### Troubleshooting CDP Connection Issues Script

```bash
#!/bin/bash
echo "Troubleshooting CDP connection..."

# 1. Verify Chrome is running with debugging enabled
echo "1. Checking Chrome processes..."
if lsof -i :9222 &>/dev/null; then
    echo "✓ Port 9222 is in use"
    lsof -i :9222
else
    echo "✗ Port 9222 is not in use - Chrome not running with debugging"
    exit 1
fi

# 2. Check CDP endpoint is accessible
echo
echo "2. Testing CDP HTTP endpoint..."
if curl -s http://localhost:9222/json | jq &>/dev/null; then
    echo "✓ CDP HTTP endpoint accessible"
    curl -s http://localhost:9222/json | jq
else
    echo "✗ CDP HTTP endpoint not accessible"
    exit 1
fi

# 3. Verify WebSocket URL is valid
echo
echo "3. Extracting WebSocket URL..."
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
if [ -n "$WS_URL" ]; then
    echo "✓ WebSocket URL: $WS_URL"
else
    echo "✗ Could not extract WebSocket URL"
    exit 1
fi

# 4. Test basic CDP command
echo
echo "4. Testing basic CDP command..."
if echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq &>/dev/null; then
    echo "✓ CDP command successful"
    echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq
else
    echo "✗ CDP command failed"
    echo "This may indicate Chrome 136+ without --user-data-dir"
    echo "See: docs/guides/chrome-136-incident.md"
    exit 1
fi

echo
echo "✓ All checks passed"
```

---

## Script Execution Issues

### Issue: CLI commands not found

**Symptoms:**
```
cdp: command not found
python3: can't open file 'scripts/cdp/cli/main.py'
```

**Solution:**
```bash
# Ensure dependencies are installed
pip install -e .

# Use python module form if the cdp entrypoint is not on PATH
python3 -m scripts.cdp.cli.main --help

# Or call the installed entrypoint directly once available
cdp --help
```

---

## Edge Cases

### Multiple tabs open

**Issue:** Multiple tabs/pages exist, extraction returns wrong page.

**Solution:** Filter by URL:
```bash
WS_URL=$(curl -s http://localhost:9222/json \
  | jq -r '.[] | select(.type == "page" and (.url | contains("localhost:3000"))) | .webSocketDebuggerUrl' \
  | head -1)
```

### React/Vue hydration delay

**Issue:** DOM extracted before JavaScript framework finishes hydration.

**Solution:** Add delay before extraction:
```bash
sleep 3
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'
```

### Navigation during extraction

**Issue:** Page navigates while extracting DOM, causing "context not found" error.

**Solution:** Re-fetch WebSocket URL immediately before extraction:
```bash
# Always fetch WebSocket URL right before extraction
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'
```

---

## Quick Troubleshooting Checklist

1. ☐ Verify Chrome 136+ with `chrome --version`
2. ☐ Check prerequisites (Python websockets, jq, websocat)
3. ☐ Check Chrome is running: `lsof -i :9222`
4. ☐ Test CDP HTTP endpoint: `curl http://localhost:9222/json`
5. ☐ Verify WebSocket URL: `curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl'`
6. ☐ Test basic CDP command: `echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL"`
7. ☐ For Chrome 136+: Verify `--user-data-dir` flag present in Chrome process
8. ☐ Check for port conflicts: `lsof -i :9222`
9. ☐ Review Chrome launch command: `ps aux | grep chrome | grep remote-debugging`
10. ☐ Run smoke test: `./tests/smoke-test-headed.sh`

---

## Getting Help

If issues persist after following this guide:

1. **Run diagnostics:**
   ```bash
   # Full diagnostic check
   ./scripts/diagnostics/debug-cdp-connection.py
   ```

2. **Check documentation:**
   - Chrome 136+ Requirements: `docs/guides/chrome-136-incident.md`
   - Workflows: `docs/workflows.md`
   - CDP Commands: `docs/cdp-commands.md`

3. **Incident reports:**
   - Chrome 136 CDP incident: `docs/guides/chrome-136-incident.md`

4. **Test scripts:**
   - Smoke test: `tests/smoke-test-headed.sh`

---

## See Also

- **Chrome 136+ Requirements:** `docs/guides/chrome-136-incident.md`
- **Workflows:** `docs/workflows.md`
- **CDP Commands:** `docs/cdp-commands.md`
- **Chrome 136 Incident Report:** `docs/guides/chrome-136-incident.md`
- **WebSocket Internals:** `docs/websocat-analisys.md`
