---
name: Browser Debugger
description: Inspect websites using Chrome (headless or headed) and Chrome DevTools Protocol. Extract DOM structure, monitor JavaScript console logs, track network requests, and interact with live pages. Use when debugging websites, checking for JavaScript errors, monitoring API calls, analyzing network activity, inspecting page structure, or testing form interactions in real-time.
---

# Browser Debugger

This skill enables you to inspect and debug websites using Chrome with the Chrome DevTools Protocol (CDP). Supports both headless mode (automated testing) and headed mode (interactive debugging with visible browser).

## What this skill does

- **Extract DOM**: Get the fully rendered HTML structure after JavaScript execution
- **Monitor Console**: Capture JavaScript console logs, errors, warnings, and exceptions
- **Track Network**: Monitor HTTP requests, responses, and failures in real-time
- **Headed Mode (NEW)**: Launch visible Chrome window for interactive debugging
- **Real-time Form Monitoring**: Watch form field changes as users type

## Prerequisites

Required tools and packages:

- **Python 3.x** with **websockets library**: `pip3 install websockets --break-system-packages`
- **Chrome or Chromium** browser
- **jq**: For JSON parsing (install with `brew install jq` on macOS or `apt-get install jq` on Linux)
- **curl**: Usually pre-installed
- **websocat** *(optional but recommended for ad-hoc CDP commands)*: `brew install websocat`

### Chrome 136+ Requirement (IMPORTANT)

⚠️ **Chrome 136+ (March 2025) requires `--user-data-dir` for headed mode CDP.**

The orchestrator and launcher scripts handle this automatically. If you're launching Chrome manually:

```bash
# ❌ WRONG (Chrome 136+ blocks CDP on default profile)
chrome --remote-debugging-port=9222 URL

# ✅ CORRECT (Works with Chrome 136+)
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL

# ✅ Also valid: provide an explicit absolute path
chrome --user-data-dir="/Users/username/.chrome-debug-profile" --remote-debugging-port=9222 URL

# ❌ WRONG - tilde is not expanded inside the flag value
chrome --user-data-dir=~/.chrome-debug-profile --remote-debugging-port=9222 URL
```

**Why:** Chrome 136+ security policy blocks CDP access to your default user profile to prevent cookie/credential theft. This is a security measure to prevent malicious tools from stealing cookies and credentials from your primary profile.

Verify installation:
```bash
python3 --version
python3 -c "import websockets; print('websockets installed')"
jq --version
chrome --version  # Check if Chrome 136+
```

## Instructions

### Get DOM Snapshot

Use when you need to see the page structure or inspect HTML elements.

```bash
chrome --headless=new --dump-dom https://example.com
```

This outputs the complete rendered HTML to stdout. You can save it to a file or pipe it to other commands:

```bash
# Save to file
chrome --headless=new --dump-dom https://example.com > page.html

# Search for specific content
chrome --headless=new --dump-dom https://example.com | grep "error"
```

### Monitor Console Logs

Use when you need to debug JavaScript errors or see console output.

**Step 1: Start Chrome with debugging port**
```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
```

**Step 2: Wait for Chrome to start**
```bash
sleep 2
```

**Step 3: Get the page ID (filter for actual pages, not extensions)**
```bash
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
```

> **Tip:** Page IDs change after navigation, tab refreshes, or when new targets appear. Re-run this command (optionally filtering by `.url`) before each capture instead of reusing stale IDs.

**Step 4: Monitor console**
```bash
python3 cdp-console.py $PAGE_ID
```

Output format:
```json
{"type":"log","timestamp":1698765432,"message":"Hello world","stackTrace":null}
{"type":"error","timestamp":1698765433,"message":"Uncaught TypeError...","stackTrace":{...}}
```

Navigate to a different URL after connecting:
```bash
python3 cdp-console.py $PAGE_ID https://different-url.com
```

Use a different debugging port (default is 9222):
```bash
python3 cdp-console.py $PAGE_ID https://example.com --port=9223
```

### Monitor Network Activity

Use when you need to see what API calls a page makes or track resource loading.

Follow the same setup as console monitoring (Steps 1-3), then:

```bash
python3 cdp-network.py $PAGE_ID
```

Output format:
```json
{"event":"request","url":"https://api.example.com/data","method":"GET","requestId":"..."}
{"event":"response","url":"https://api.example.com/data","status":200,"statusText":"OK","mimeType":"application/json","requestId":"..."}
{"event":"failed","errorText":"net::ERR_CONNECTION_REFUSED","requestId":"..."}
```

## Interactive DOM Inspection Workflow

**Use case:** Launch Chrome, allow user to interact with the page (click, type, navigate), then extract the dynamically modified DOM state for analysis.

This workflow enables debugging scenarios where you need to:
- Inspect form state after user fills fields
- Analyze error messages after failed form submission
- Examine DOM changes after SPA navigation
- Debug issues that require manual authentication or interaction

### Phase 1: Launch Chrome with Debugging

```bash
./debug-orchestrator.sh "http://localhost:3000/signin" \
  --mode=headed \
  --include-console
```

**Output:**
```json
{
  "chrome_version": "136.0.6786.0",
  "debug_port": 9222,
  "chrome_pid": 12345,
  "ws_url": "ws://localhost:9222/devtools/browser/6d5f8c3a-...",
  "mode": "headed",
  "profile": "/tmp/chrome-debug-12345"
}
```

**What happens:**
- Visible Chrome window opens at the specified URL
- CDP debugging enabled on port 9222
- Browser stays open indefinitely (no timeout)
- Returns WebSocket URL for later DOM extraction

### Phase 2: User Interaction

**Agent instructs user:**
```
Chrome window is now open at: http://localhost:3000/signin

Please perform these actions:
1. Click the "Username" field and type "testuser"
2. Click the "Password" field and type your password
3. Click the "Login" button
4. Wait for the page to load completely

When ready for me to analyze the current state, type "ready"
```

**User interacts with page:**
- Clicks, types, navigates as instructed
- DOM updates in real-time
- Chrome window remains open

### Phase 3: Extract Current DOM State

**Step 1: Re-fetch WebSocket URL** (page may have navigated):
```bash
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
```

**Step 2: Extract DOM** (websocat method):
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html
```

**Flags:**
- `-n1`: Close after 1 message (request/response pattern)
- `-B 1048576`: 1MB buffer for large DOMs

**Step 3: Extract DOM** (Python fallback if websocat unavailable):
```python
#!/usr/bin/env python3
import asyncio, websockets, json, sys

async def extract_dom(ws_url):
    async with websockets.connect(ws_url, max_size=2**20) as ws:
        cmd = {"id": 1, "method": "Runtime.evaluate",
               "params": {"expression": "document.documentElement.outerHTML", "returnByValue": True}}
        await ws.send(json.dumps(cmd))
        response = json.loads(await ws.recv())
        return response['result']['result']['value']

print(asyncio.run(extract_dom(sys.argv[1])))
```

Save as `/tmp/extract-dom.py`, then:
```bash
python3 /tmp/extract-dom.py "$WS_URL" > /tmp/live-dom.html
```

**Step 4: Get Context** (current URL, title):
```bash
# Current URL (verify navigation)
echo '{"id":2,"method":"Runtime.evaluate","params":{"expression":"window.location.href","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Page title
echo '{"id":3,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Phase 4: Analyze and Provide Guidance

**Search for specific elements:**
```bash
# Find forms
grep -o '<form[^>]*>' /tmp/live-dom.html

# Find input fields
grep -o '<input[^>]*>' /tmp/live-dom.html | head -10

# Find error messages
grep -i 'error\|invalid\|required' /tmp/live-dom.html

# Find buttons
grep -o '<button[^>]*>[^<]*</button>' /tmp/live-dom.html
```

**Example agent response:**
```
I've extracted the current DOM state. Here's what I found:

Current URL: http://localhost:3000/dashboard
Page Title: Dashboard - MyApp
DOM Size: 245,873 bytes

Analysis:
1. Login successful - now on /dashboard
2. Found welcome message: <div class="welcome">Welcome, testuser!</div>
3. Detected 3 forms: searchForm, settingsForm, logoutForm

Debugging insights:
- Login flow correctly redirected /signin → /dashboard
- Username "testuser" appears in welcome div
- All expected dashboard widgets present
- No error messages detected

Reference: DOM saved at /tmp/live-dom.html
```

### Quick Start Checklist

**Sequential steps for agents to copy and track:**

1. ☐ Verify prerequisites (Chrome, Python, jq, websocat or Python websockets)
2. ☐ Launch Chrome: `./debug-orchestrator.sh "URL" --mode=headed --include-console`
3. ☐ Extract WebSocket URL from JSON output or re-fetch: `curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl'`
4. ☐ Instruct user on what actions to perform
5. ☐ Wait for user signal ("ready")
6. ☐ Re-fetch WebSocket URL (if user navigated): `curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1`
7. ☐ Extract DOM: Use websocat or Python method
8. ☐ Get context (current URL, title)
9. ☐ Analyze DOM with grep/jq
10. ☐ Provide debugging insights to user

### Prerequisites Check

**Commands to verify installation:**

```bash
# Check Chrome (required: Chrome 136+)
chrome --version

# Check Python (required: 3.7+)
python3 --version

# Check jq (required for JSON parsing)
jq --version

# Check websocat (primary method - optional)
command -v websocat &>/dev/null && echo "websocat: installed" || echo "websocat: not found"

# Check Python websockets (fallback method)
python3 -c "import websockets; print('websockets: installed')" 2>/dev/null || echo "websockets: not found"
```

**If dependencies missing:**

```bash
# Install websocat
brew install websocat              # macOS
cargo install websocat             # Linux with Rust

# Install Python websockets
pip3 install websockets --break-system-packages

# Install jq
brew install jq                    # macOS
apt-get install jq                 # Debian/Ubuntu
```

### Tool Detection Pattern

**Detect available tools and choose extraction method:**

```bash
# Step 1: Check websocat (primary)
if command -v websocat &>/dev/null; then
    echo "Using websocat method (primary)"
    # Extract DOM with websocat
    echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
      | websocat -n1 -B 1048576 "$WS_URL" \
      | jq -r '.result.result.value' > /tmp/live-dom.html
else
    # Step 2: Check Python websockets (fallback)
    if python3 -c "import websockets" 2>/dev/null; then
        echo "Using Python websockets method (fallback)"
        # Create extraction script
        cat > /tmp/extract-dom.py <<'EOF'
#!/usr/bin/env python3
import asyncio, websockets, json, sys
async def extract_dom(ws_url):
    async with websockets.connect(ws_url, max_size=2**20) as ws:
        cmd = {"id": 1, "method": "Runtime.evaluate",
               "params": {"expression": "document.documentElement.outerHTML", "returnByValue": True}}
        await ws.send(json.dumps(cmd))
        response = json.loads(await ws.recv())
        return response['result']['result']['value']
print(asyncio.run(extract_dom(sys.argv[1])))
EOF
        chmod +x /tmp/extract-dom.py
        # Extract DOM with Python
        python3 /tmp/extract-dom.py "$WS_URL" > /tmp/live-dom.html
    else
        # Step 3: No tools available
        echo "ERROR: Install websocat (brew install websocat) or Python websockets (pip3 install websockets)"
        exit 1
    fi
fi
```

### Common Workflows

#### Iterative Debugging (Multiple DOM Extractions)

**Use case:** Track DOM changes as user performs multiple actions

```bash
# Initial state
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value' > /tmp/dom-step1.html

# User action 1
echo "Please click 'Add Item', then type 'ready'"
read -r
echo '{"id":2,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value' > /tmp/dom-step2.html

# User action 2
echo "Please fill form fields, then type 'ready'"
read -r
echo '{"id":3,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value' > /tmp/dom-step3.html

# Compare states
diff /tmp/dom-step1.html /tmp/dom-step2.html | head -20
diff /tmp/dom-step2.html /tmp/dom-step3.html | head -20
```

#### Form Submission Debugging

**Use case:** Debug form submission issues with before/after extraction

```bash
# Extract before submission
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value' > /tmp/dom-before.html

# User submits form
echo "Please submit the form, then type 'ready'"
read -r

# Re-fetch WebSocket URL (page may have navigated)
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)

# Extract after submission
echo '{"id":2,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value' > /tmp/dom-after.html

# Check for error messages
grep -i 'error\|invalid\|failed' /tmp/dom-after.html

# Check if navigation occurred
echo '{"id":3,"method":"Runtime.evaluate","params":{"expression":"window.location.href","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Output Format Documentation

**debug-orchestrator.sh JSON output:**
```json
{
  "chrome_version": "136.0.6786.0",
  "debug_port": 9222,
  "chrome_pid": 12345,
  "ws_url": "ws://localhost:9222/devtools/browser/6d5f8c3a-1b2e-4f9c-a8d7-3e4f5a6b7c8d",
  "mode": "headed",
  "profile": "/tmp/chrome-debug-12345"
}
```

**CDP Runtime.evaluate response (DOM extraction):**
```json
{
  "id": 1,
  "result": {
    "result": {
      "type": "string",
      "value": "<html>...</html>"
    }
  }
}
```

**CDP error response:**
```json
{
  "id": 1,
  "error": {
    "code": -32000,
    "message": "Cannot find context with specified id"
  }
}
```

**HTTP /json endpoint (WebSocket URL discovery):**
```json
[
  {
    "description": "",
    "id": "6d5f8c3a-1b2e-4f9c-a8d7-3e4f5a6b7c8d",
    "title": "Login - MyApp",
    "type": "page",
    "url": "http://localhost:3000/signin",
    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/6d5f8c3a-..."
  }
]
```

### Error Handling

#### Error 1: websocat not found

**Symptom:**
```
bash: websocat: command not found
```

**Recovery:**
```bash
# Check Python websockets as fallback
python3 -c "import websockets" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "Using Python websockets method (see Tool Detection Pattern)"
    # Use Python extraction script
else
    echo "ERROR: Install websocat (brew install websocat) or Python websockets (pip3 install websockets)"
    exit 1
fi
```

#### Error 2: Buffer overflow

**Symptom:**
```
[WARN  websocat::readdebt] Incoming message too long (324990 > 65535)
```

**Recovery:**
```bash
# Increase buffer size to 2MB
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 2097152 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html
```

#### Error 3: WebSocket URL stale

**Symptom:**
```json
{
  "id": 1,
  "error": {
    "code": -32000,
    "message": "Cannot find context with specified id"
  }
}
```

**Recovery:**
```bash
# Re-fetch WebSocket URL (page navigated)
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
# Retry command
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'
```

#### Error 4: Chrome not responding

**Symptom:**
```
curl: (7) Failed to connect to localhost port 9222
```

**Recovery:**
```bash
# Check Chrome process
ps aux | grep chrome | grep remote-debugging

# If not running, relaunch
./debug-orchestrator.sh "URL" --mode=headed --include-console
```

#### Error 5: websockets library not found

**Symptom:**
```
ModuleNotFoundError: No module named 'websockets'
```

**Recovery:**
```bash
# Install Python websockets
pip3 install websockets --break-system-packages
# or
python3 -m pip install websockets --user
```

### Edge Cases

**Large DOMs (>1MB):**
```bash
# For DOMs larger than 1MB, increase buffer size
websocat -B 2097152 "$WS_URL"  # 2MB buffer

# Or extract specific elements instead of full DOM
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"Array.from(document.querySelectorAll('\''form'\'')).map(f => f.outerHTML).join('\''\\n'\'')","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

**Navigation detection:**
```bash
# Always re-fetch WebSocket URL before extraction
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
```

**Multiple tabs:**
```bash
# Filter by URL if multiple tabs open
WS_URL=$(curl -s http://localhost:9222/json \
  | jq -r '.[] | select(.type == "page" and (.url | contains("localhost:3000"))) | .webSocketDebuggerUrl' \
  | head -1)
```

**React/Vue hydration delay:**
```bash
# Wait for JavaScript frameworks to hydrate
sleep 3
# Then extract DOM
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'
```

## Quick Start: Headed Mode (Interactive Debugging)

**NEW**: Launch a visible Chrome window that stays open for manual interaction:

```bash
./debug-orchestrator.sh "http://localhost:3000/signin" \
  --mode=headed \
  --include-console
```

This will:
- Open a **visible Chrome window** showing the page
- **Stays open indefinitely** - no automatic timeout (close manually when done)
- You can **type, click, and interact** normally
- Console logs and network activity are captured in real-time
- Uses persistent profile at `$HOME/.chrome-debug-profile`

**Use cases:**
- Testing form interactions (login, signup, checkout)
- Debugging pages that require manual authentication
- Watching real-time form validation
- Testing workflows that need human interaction

**Note:** For headed mode, do NOT use `--idle` timeout unless you specifically want auto-close behavior. The browser should stay open for interactive debugging.

## Recommended Workflow (One-Command Orchestrator)

`debug-orchestrator.sh` coordinates Chrome, the CDP collectors, and post-run summaries. Use it whenever you need full telemetry in one go.

**Headless mode** (automated, no UI):
```bash
./debug-orchestrator.sh "https://example.com/login" 20 /tmp/example.log \
  --include-console --summary=both --idle=3
```

**Headed mode** (visible browser):
```bash
./debug-orchestrator.sh "http://localhost:3000/checkout" 20 /tmp/checkout.log \
  --mode=headed --include-console --summary=both
```

What you get:
- Network stream written to `/tmp/example.log`
- Console stream written to `/tmp/example-console.log`
- Text and JSON summaries printed at the end
- Automatic Chrome startup/cleanup on port 9222

### Useful flags
- `--idle=<seconds>`: stop capture after the page goes quiet (applies to both console and network collectors).
- `--include-console`: capture console events alongside network data.
- `--console-log=PATH`: direct console output to a custom file.
- `--filter="<substring>"`: switch to the `cdp-network-with-body.py` collector and persist matching response bodies; use cautiously because bodies can become large.
- `--summary=text|json|both`: control summarizer output.

### Handling port conflicts
If Chrome is already bound to port 9222 the orchestrator aborts after showing the owning PID. Free the port and rerun:
```bash
pkill -f "chrome.*9222"   # safe when you launched Chrome headlessly
# or rerun in manual mode with an alternate port (see below)
```

## Manual Control (When You Cannot Use the Orchestrator)

The lower-level scripts are still available and mirror the orchestrator’s behaviour. Combine them to fit bespoke workflows or to run against a pre-existing Chrome session.

### Launch Chrome on a custom debugging port
```bash
PORT=9230
chrome --headless=new --remote-debugging-port=${PORT} https://example.com &
sleep 2
PAGE_ID=$(curl -s "http://localhost:${PORT}/json" | jq -r '.[] | select(.type=="page") | .id' | head -1)
```

### Monitor console output
```bash
timeout 15 python3 cdp-console.py "$PAGE_ID" --port=${PORT} \
  | jq 'del(.stackTrace)'   # trim stack traces if you only need messages
```

### Monitor network traffic
```bash
timeout 15 python3 cdp-network.py "$PAGE_ID" --port=${PORT} > /tmp/network.log
```

Filter out noisy resources (e.g., blob URLs) during analysis:
```bash
jq 'select(.event == "request" and (.url | startswith("blob:") | not))' /tmp/network.log
```

Capture response bodies for matching URLs:
```bash
timeout 20 python3 cdp-network-with-body.py "$PAGE_ID" --port=${PORT} \
  --filter=api/v1/orders > /tmp/network-with-bodies.log
```

### Grab a DOM snapshot
```bash
chrome --headless=new --dump-dom https://example.com > /tmp/dom.html
```

## Running Summaries After the Fact

`cdp-summarize.py` consumes any network/console log pair and prints aggregate stats.
```bash
python3 cdp-summarize.py \
  --network /tmp/example.log \
  --console /tmp/example-console.log \
  --duration 20 \
  --format both \
  --include-console
```

Expect totals, status histograms, a host breakdown, and the top 10 distinct request URLs. Pair this with ad-hoc `jq` filters for deeper dives.

## Operational Tips

- **Trim console payloads**: console entries include full stack traces by default; use `jq 'del(.stackTrace)'` or pipe to `sed`/`head` when reviewing long sessions to control file size.
- **Separate error channels early**: `jq 'select(.type=="error")' /tmp/example-console.log` gives a compact error-only view, sparing you from opening multi-hundred-kilobyte logs.
- **Keep Chrome tidy**: always terminate headless Chrome when you are done to prevent port conflicts.
  ```bash
  pkill -f "chrome.*9222"
  ```
- **Prefer `timeout`**: wrap long-running captures with `timeout <seconds> <command>` so unattended sessions shut down automatically.
- **Store artefacts predictably**: write logs to `/tmp/<scenario>-network.log` and `/tmp/<scenario>-console.log` to make later comparisons with `diff` or `jq` painless.

## Platform-Specific Notes

### Finding Chrome on different systems

```bash
# Auto-detect Chrome
if [[ "$OSTYPE" == "darwin"* ]]; then
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif command -v google-chrome &> /dev/null; then
    CHROME="google-chrome"
elif command -v chromium-browser &> /dev/null; then
    CHROME="chromium-browser"
else
    echo "Error: Chrome not found"
    exit 1
fi
```

## Troubleshooting

### "No module named 'websockets'"
```bash
pip3 install websockets --break-system-packages
# or
python3 -m pip install websockets --user
```

### "Connection refused" when connecting to CDP
```bash
# Check if Chrome is running
lsof -i :9222

# Verify debugging endpoint
curl http://localhost:9222/json
```

### Port 9222 already in use
```bash
# Kill existing Chrome processes
pkill -f "chrome.*9222"

# Or use a different port
chrome --headless=new --remote-debugging-port=9223 $URL &
```

### Scripts don't execute
```bash
chmod +x cdp-console.py
chmod +x cdp-network.py
```

## Examples

### Example: Find all console errors on a page

```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json \
  | jq -r '.[] | select(.type == "page") | .id' \
  | head -1)
timeout 10 python3 cdp-console.py $PAGE_ID | grep '"type":"error"'
pkill -f "chrome.*9222"
```

### Example: Check if a page makes API calls to a specific domain

```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json \
  | jq -r '.[] | select(.type == "page") | .id' \
  | head -1)
timeout 10 python3 cdp-network.py $PAGE_ID | grep 'api.example.com'
pkill -f "chrome.*9222"
```

### Example: Get the page title from DOM

```bash
chrome --headless=new --dump-dom https://example.com | \
  grep -o '<title>.*</title>' | \
  sed 's/<title>\(.*\)<\/title>/\1/'
```

## Quick Reference

```bash
# Get DOM
chrome --headless=new --dump-dom $URL

# Monitor console
chrome --headless=new --remote-debugging-port=9222 $URL &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json \
  | jq -r '.[] | select(.type == "page") | .id' \
  | head -1)
# Optional: narrow to a specific URL if multiple tabs are open
# PAGE_ID=$(curl -s http://localhost:9222/json \
#   | jq -r '.[] | select(.type == "page" and (.url | contains("localhost:3000"))) | .id' \
#   | head -1)
python3 cdp-console.py $PAGE_ID

# Monitor network
python3 cdp-network.py $PAGE_ID

# Monitor both (background)
python3 cdp-console.py $PAGE_ID > /tmp/console.log &
python3 cdp-network.py $PAGE_ID > /tmp/network.log &

# Orchestrated capture with summaries & idle detection
debug-orchestrator.sh "$URL" 15 /tmp/network.log --include-console --summary=both --idle=2

# Cleanup
pkill -f "chrome.*9222"
```

## Ad-hoc CDP Commands with websocat

Need the fully hydrated DOM or a custom Chrome DevTools command? Use the built-in `websocat` CLI.

```bash
# 1. Launch Chrome with --remote-debugging-port (or run debug-orchestrator.sh)

# 2. Discover the WebSocket debugger URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

# 3. Run a CDP command (this example grabs the full DOM)
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html

head -n 20 /tmp/live-dom.html   # inspect the output
```

Tips:
- `-B 1048576` raises the buffer to 1 MB so large pages don’t truncate.
- Swap the expression to collect other data:
  ```bash
  echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
    | websocat -n1 "$WS_URL"
  ```
- Other handy methods: `Page.captureScreenshot`, `Network.getAllCookies`, `Accessibility.getFullAXTree`.
- Headed sessions launched via `chrome-launcher.sh` already set `--user-data-dir`, which Chrome 136+ requires. Include it if you launch manually.

## Documentation & Testing

### Testing & Diagnostics

#### Manual Testing

Validate headed Chrome CDP functionality after Chrome updates:

```bash
# Test headed Chrome launch
./debug-orchestrator.sh "https://example.com" --mode=headed --include-console

# Verify Chrome responds to CDP commands
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"2+2","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq

# Expected: {"id":1,"result":{"result":{"type":"number","value":4}}}

# Cleanup
pkill -f "chrome.*9222"
```

#### Troubleshooting CDP Connection Issues

If Chrome doesn't respond to CDP commands:

```bash
# 1. Verify Chrome is running with debugging enabled
lsof -i :9222

# 2. Check CDP endpoint is accessible
curl -s http://localhost:9222/json | jq

# 3. Verify WebSocket URL is valid
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo "$WS_URL"

# 4. Test basic CDP command
echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq
```

### Common Issues

**Issue: Headed mode hangs indefinitely**

**Cause:** Chrome 136+ (March 2025) requires `--user-data-dir` for CDP access. This is a security policy to prevent CDP from accessing your default profile where all your passwords and cookies are stored.

**Solution:** Ensure you're using `chrome-launcher.sh` or `debug-orchestrator.sh`, which handle this automatically. If launching Chrome manually, always include `--user-data-dir`:

```bash
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL
```

**Technical details:** Chrome 136+ silently ignores `--remote-debugging-port` when using the default profile. The WebSocket connection succeeds, but Chrome never responds to CDP commands (infinite hang with no error). Using an isolated profile via `--user-data-dir` is now required for all headed Chrome CDP sessions.

## Advanced Usage

### Additional CDP Commands

Beyond DOM extraction, you can execute other CDP commands via WebSocket:

**localStorage access:**
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"JSON.stringify(localStorage)","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value' | jq .
```

**Cookies:**
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.cookie","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

**Custom JavaScript:**
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"Array.from(document.querySelectorAll('\''form'\'')).map(f => f.id)","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### chrome-launcher.sh Usage

The `chrome-launcher.sh` script provides a reliable way to launch Chrome with CDP enabled:

```bash
# Launch headed Chrome
./chrome-launcher.sh --mode=headed --url="https://example.com" --port=9222

# Launch headless Chrome
./chrome-launcher.sh --mode=headless --url="https://example.com" --port=9222

# Custom profile location
./chrome-launcher.sh --mode=headed --url="https://example.com" --profile="/tmp/my-profile"
```

**Output:** Returns JSON with Chrome PID, WebSocket URL, and profile path for automation.

### WebSocket Buffer Management

When extracting large DOMs (>64KB), increase websocat's buffer size:

```bash
# Default buffer (64KB) - works for most pages
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Large buffer (2MB) - for complex SPAs
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 2097152 "$WS_URL" | jq -r '.result.result.value'

# If buffer overflow persists, extract specific elements
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.querySelector('\''main'\'').outerHTML","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Background Process Tracking

When managing multiple debug sessions, track background monitors to prevent redundant processes and ensure clean cleanup.

**Pattern: Track monitors by URL using associative arrays**

```bash
#!/bin/bash
declare -A ACTIVE_MONITORS

# Launch monitor for a URL (kills previous monitor for same URL)
launch_monitor() {
    local url=$1

    # Kill previous monitor for this URL if exists
    if [ -n "${ACTIVE_MONITORS[$url]:-}" ]; then
        echo "Killing previous monitor PID ${ACTIVE_MONITORS[$url]} for $url" >&2
        kill "${ACTIVE_MONITORS[$url]}" 2>/dev/null || true
        unset ACTIVE_MONITORS[$url]
    fi

    # Launch new monitor in background
    ./debug-orchestrator.sh "$url" --mode=headed --include-console &
    ACTIVE_MONITORS[$url]=$!

    echo "Monitor launched for $url with PID ${ACTIVE_MONITORS[$url]}" >&2
}

# Cleanup all tracked monitors
cleanup_all_monitors() {
    echo "Cleaning up all monitors..." >&2
    for url in "${!ACTIVE_MONITORS[@]}"; do
        echo "  Killing monitor for $url (PID ${ACTIVE_MONITORS[$url]})" >&2
        kill "${ACTIVE_MONITORS[$url]}" 2>/dev/null || true
        unset ACTIVE_MONITORS[$url]
    done
    echo "All monitors cleaned up" >&2
}

# Usage examples
launch_monitor "http://localhost:3000"
# ... later, relaunch for same URL - kills previous first
launch_monitor "http://localhost:3000"

# Launch monitor for different URL
launch_monitor "http://localhost:4000"

# Cleanup all
cleanup_all_monitors
```

**Why this pattern:**
- **No duplicate processes**: Relaunching for same URL kills previous monitor automatically
- **Clean shutdown**: Single function cleans up all tracked monitors
- **URL-based organization**: Easy to see which URLs have active monitors
- **Background-friendly**: Compatible with long-running debug sessions

**Real-world scenario:**

```bash
# Start monitoring user signup flow
launch_monitor "http://localhost:3000/signup"

# User reports bug, need to switch to login flow
launch_monitor "http://localhost:3000/login"

# Retest signup flow - previous login monitor continues
launch_monitor "http://localhost:3000/signup"

# Done debugging - cleanup all monitors and Chrome instances
cleanup_all_monitors
./scripts/cleanup-chrome.sh 9222
```

**Integration with cleanup script:**

```bash
# Enhanced cleanup: monitors + Chrome processes
cleanup_session() {
    local port=${1:-9222}

    echo "Starting full session cleanup..." >&2

    # Kill all tracked monitors
    cleanup_all_monitors

    # Kill Chrome and release port
    ./scripts/cleanup-chrome.sh "$port"

    echo "Session cleanup complete" >&2
}
```

## Summary

This skill provides a lightweight way to inspect websites using Chrome DevTools Protocol (CDP). Key features:

- **Headless & Headed Mode** - Automated testing or interactive debugging
- **DOM Extraction** - Get fully rendered HTML after JavaScript execution
- **Console Monitoring** - Capture JavaScript errors and logs
- **Network Tracking** - Monitor HTTP requests and responses
- **Chrome 136+ Compatible** - Handles security policy requiring `--user-data-dir`

The skill is designed for quick telemetry capture with minimal dependencies (Python, jq, Chrome), making it ideal for AI agents that need website context without heavy MCP infrastructure.

## Version History

### v2.1.0 (2025-10-24)

**Feature:** Interactive DOM Access for AI Agents

**Enhancements:**
- Added comprehensive **Interactive DOM Inspection Workflow** with 4-phase structure (Launch → User Interact → Extract → Analyze)
- Documented primary (websocat) and fallback (Python websockets) DOM extraction methods
- Added **Quick Start Checklist** for sequential workflow execution
- Added **Prerequisites Check** section with dependency verification commands
- Added **Tool Detection Pattern** with automatic fallback logic
- Added **Common Workflows** for iterative debugging and form submission debugging
- Added **Output Format Documentation** for all JSON structures (orchestrator, CDP responses, /json endpoint)
- Added **Error Handling** section with 5 common errors and recovery patterns
- Added **Edge Cases** documentation (large DOMs, navigation detection, multiple tabs, React/Vue hydration)
- Chrome 136+ compatibility ensured with automatic `--user-data-dir` handling
