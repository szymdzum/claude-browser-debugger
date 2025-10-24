# Browser Debugger Workflows

## Overview

This document provides complete workflow examples for using the browser-debugger skill in various debugging scenarios. All workflows support both headless (automated) and headed (interactive) modes.

## Table of Contents

- [Headless Capture Workflow](#headless-capture-workflow)
- [Headed Mode Workflow](#headed-mode-workflow)
- [Interactive DOM Inspection Workflow](#interactive-dom-inspection-workflow)
- [Manual CDP Control](#manual-cdp-control)
- [Session Management](#session-management)
- [Common Debugging Workflows](#common-debugging-workflows)

---

## Headless Capture Workflow

**Use case:** Automated testing, CI/CD pipelines, background monitoring

### One-Command Orchestrated Capture

The `debug-orchestrator.sh` script coordinates Chrome, CDP collectors, and post-run summaries.

```bash
./scripts/core/debug-orchestrator.sh "https://example.com/login" 20 /tmp/example.log \
  --include-console --summary=both --idle=3
```

**What you get:**
- Network stream written to `/tmp/example.log`
- Console stream written to `/tmp/example-console.log`
- Text and JSON summaries printed at the end
- Automatic Chrome startup/cleanup on port 9222

### Useful Flags

- `--idle=<seconds>`: Stop capture after the page goes quiet (applies to both console and network collectors)
- `--include-console`: Capture console events alongside network data
- `--console-log=PATH`: Direct console output to a custom file
- `--filter="<substring>"`: Switch to `cdp-network-with-body.py` collector and persist matching response bodies
- `--summary=text|json|both`: Control summarizer output format

### Example: Full Telemetry Capture

```bash
./scripts/core/debug-orchestrator.sh "https://api.example.com/dashboard" 30 /tmp/dashboard.log \
  --include-console \
  --idle=5 \
  --summary=both \
  --filter="api/v1"
```

**Output:**
- `/tmp/dashboard.log` - Network activity with response bodies for URLs containing "api/v1"
- `/tmp/dashboard-console.log` - All console logs
- Text summary with request counts, status codes, and error messages
- JSON summary for programmatic processing

---

## Headed Mode Workflow

**Use case:** Interactive debugging, manual testing, authentication flows

### Quick Start: Open Visible Browser

```bash
./scripts/core/debug-orchestrator.sh "http://localhost:3000/signin" \
  --mode=headed \
  --include-console
```

**What happens:**
- Opens a **visible Chrome window** showing the page
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

### Example: Checkout Flow Debugging

```bash
./scripts/core/debug-orchestrator.sh "http://localhost:3000/checkout" 20 /tmp/checkout.log \
  --mode=headed --include-console --summary=both
```

**Workflow:**
1. Chrome window opens at checkout page
2. Manually interact: add items, fill forms, click buttons
3. Console logs captured to `/tmp/checkout-console.log`
4. Network activity captured to `/tmp/checkout.log`
5. Close Chrome manually when done
6. Review summaries for errors or unexpected API calls

---

## Interactive DOM Inspection Workflow

**Use case:** Extract DOM state after user interaction for analysis

This workflow enables debugging scenarios where you need to:
- Inspect form state after user fills fields
- Analyze error messages after failed form submission
- Examine DOM changes after SPA navigation
- Debug issues that require manual authentication or interaction

### Phase 1: Launch Chrome with Debugging

```bash
./scripts/core/debug-orchestrator.sh "http://localhost:3000/signin" \
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

**Step 2a: Extract DOM** (websocat method - primary):
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html
```

**Flags:**
- `-n1`: Close after 1 message (request/response pattern)
- `-B 1048576`: 1MB buffer for large DOMs

**Step 2b: Extract DOM** (Python fallback if websocat unavailable):
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

**Step 3: Get Context** (current URL, title):
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

---

## Manual CDP Control

**Use case:** Custom workflows, pre-existing Chrome sessions, non-standard ports

When you cannot use the orchestrator, combine lower-level scripts to fit bespoke workflows.

### Launch Chrome on Custom Debugging Port

```bash
PORT=9230
chrome --headless=new --remote-debugging-port=${PORT} https://example.com &
sleep 2
PAGE_ID=$(curl -s "http://localhost:${PORT}/json" | jq -r '.[] | select(.type=="page") | .id' | head -1)
```

### Monitor Console Output

```bash
timeout 15 python3 scripts/collectors/cdp-console.py "$PAGE_ID" --port=${PORT} \
  | jq 'del(.stackTrace)'   # trim stack traces if you only need messages
```

### Monitor Network Traffic

```bash
timeout 15 python3 scripts/collectors/cdp-network.py "$PAGE_ID" --port=${PORT} > /tmp/network.log
```

Filter out noisy resources (e.g., blob URLs) during analysis:
```bash
jq 'select(.event == "request" and (.url | startswith("blob:") | not))' /tmp/network.log
```

### Capture Response Bodies

Capture response bodies for matching URLs:
```bash
timeout 20 python3 scripts/collectors/cdp-network-with-body.py "$PAGE_ID" --port=${PORT} \
  --filter=api/v1/orders > /tmp/network-with-bodies.log
```

### Get DOM Snapshot

```bash
chrome --headless=new --dump-dom https://example.com > /tmp/dom.html
```

### Full Manual Workflow Example

```bash
# Step 1: Start Chrome with debugging port
chrome --headless=new --remote-debugging-port=9222 https://example.com &

# Step 2: Wait for Chrome to start
sleep 2

# Step 3: Get page ID (filter for actual pages, not extensions)
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)

# Step 4: Monitor console in background
python3 scripts/collectors/cdp-console.py $PAGE_ID > /tmp/console.log &

# Step 5: Monitor network in background
python3 scripts/collectors/cdp-network.py $PAGE_ID > /tmp/network.log &

# Step 6: Wait for page activity (or use timeout)
sleep 15

# Step 7: Cleanup
pkill -f "chrome.*9222"
```

> **Tip:** Page IDs change after navigation, tab refreshes, or when new targets appear. Re-run the page ID command before each capture instead of reusing stale IDs.

---

## Session Management

### Save and Resume Sessions

**Pattern: Track Chrome PIDs and profiles for cleanup**

```bash
# Launch Chrome and save session info
./scripts/core/debug-orchestrator.sh "http://localhost:3000" --mode=headed --include-console > /tmp/chrome-session.json

# Extract session details
CHROME_PID=$(jq -r '.chrome_pid' /tmp/chrome-session.json)
WS_URL=$(jq -r '.ws_url' /tmp/chrome-session.json)
PROFILE=$(jq -r '.profile' /tmp/chrome-session.json)

# Later: Resume using saved WebSocket URL
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Cleanup using saved PID
kill $CHROME_PID
```

### Port Conflict Resolution

If Chrome is already bound to port 9222, the orchestrator aborts after showing the owning PID:

```bash
# Free the port
pkill -f "chrome.*9222"

# Or use alternate port
./scripts/core/debug-orchestrator.sh "URL" --mode=headed --port=9223
```

---

## Common Debugging Workflows

### Iterative Debugging (Multiple DOM Extractions)

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

### Form Submission Debugging

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

### Find All Console Errors

```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json \
  | jq -r '.[] | select(.type == "page") | .id' \
  | head -1)
timeout 10 python3 scripts/collectors/cdp-console.py $PAGE_ID | grep '"type":"error"'
pkill -f "chrome.*9222"
```

### Check API Calls to Specific Domain

```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json \
  | jq -r '.[] | select(.type == "page") | .id' \
  | head -1)
timeout 10 python3 scripts/collectors/cdp-network.py $PAGE_ID | grep 'api.example.com'
pkill -f "chrome.*9222"
```

### Extract Page Title from DOM

```bash
chrome --headless=new --dump-dom https://example.com | \
  grep -o '<title>.*</title>' | \
  sed 's/<title>\(.*\)<\/title>/\1/'
```

---

## Operational Tips

- **Trim console payloads**: Console entries include full stack traces by default; use `jq 'del(.stackTrace)'` or pipe to `sed`/`head` when reviewing long sessions to control file size.
- **Separate error channels early**: `jq 'select(.type=="error")' /tmp/example-console.log` gives a compact error-only view, sparing you from opening multi-hundred-kilobyte logs.
- **Keep Chrome tidy**: Always terminate headless Chrome when you are done to prevent port conflicts.
  ```bash
  pkill -f "chrome.*9222"
  ```
- **Prefer `timeout`**: Wrap long-running captures with `timeout <seconds> <command>` so unattended sessions shut down automatically.
- **Store artifacts predictably**: Write logs to `/tmp/<scenario>-network.log` and `/tmp/<scenario>-console.log` to make later comparisons with `diff` or `jq` painless.

---

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
python3 scripts/collectors/cdp-console.py $PAGE_ID

# Monitor network
python3 scripts/collectors/cdp-network.py $PAGE_ID

# Monitor both (background)
python3 scripts/collectors/cdp-console.py $PAGE_ID > /tmp/console.log &
python3 scripts/collectors/cdp-network.py $PAGE_ID > /tmp/network.log &

# Orchestrated capture with summaries & idle detection
./scripts/core/debug-orchestrator.sh "$URL" 15 /tmp/network.log --include-console --summary=both --idle=2

# Cleanup
pkill -f "chrome.*9222"
```

---

## Running Summaries After Capture

`cdp-summarize.py` consumes any network/console log pair and prints aggregate stats.

```bash
python3 scripts/collectors/cdp-summarize.py \
  --network /tmp/example.log \
  --console /tmp/example-console.log \
  --duration 20 \
  --format both \
  --include-console
```

Expect totals, status histograms, a host breakdown, and the top 10 distinct request URLs. Pair this with ad-hoc `jq` filters for deeper dives.

---

## See Also

- **Chrome 136+ Requirements:** `docs/chrome-136-requirements.md`
- **CDP Commands Reference:** `docs/reference/cdp-commands.md`
- **Troubleshooting Guide:** `docs/guides/troubleshooting.md`
- **Interactive Workflow Design:** `docs/guides/interactive-workflow-design.md`


## Test Section Added for Validation

This is a test section to verify that reference files can be updated without touching SKILL.md.

**Test completed successfully** ✅

