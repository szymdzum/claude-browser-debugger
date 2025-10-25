# Browser Debugger Workflows

## Overview

This document provides complete workflow examples for using the browser-debugger skill in various debugging scenarios. All workflows support both headless (automated) and headed (interactive) modes.

## Table of Contents

- [Headless Capture Workflow](#headless-capture-workflow)
- [Headed Mode Workflow](#headed-mode-workflow)
- [Interactive DOM Inspection Workflow](#interactive-dom-inspection-workflow)
- [Graceful Session Cleanup](#graceful-session-cleanup)
- [Manual CDP Control](#manual-cdp-control)
- [Session Management](#session-management)
- [Common Debugging Workflows](#common-debugging-workflows)
- [Error Handling](#error-handling)

---

## Headless Capture Workflow

**Use case:** Automated testing, CI/CD pipelines, background monitoring

### One-Command Orchestrated Capture

The Python CDP CLI `orchestrate` subcommand coordinates Chrome, CDP collectors, and post-run summaries.

```bash
python3 -m scripts.cdp.cli.main orchestrate headless https://example.com/login \
  --duration 20 --include-console --summary both --output-dir /tmp
```

**What you get:**
- Network stream written to `/tmp/network-<timestamp>.jsonl`
- Console stream written to `/tmp/console-<timestamp>.jsonl` (if --include-console)
- Text and JSON summaries generated in `/tmp`
- Automatic Chrome startup/cleanup on port 9222
- Automatic reconnection on Chrome crash

### Useful Flags

- `--duration SECONDS`: Session duration (default: 15)
- `--include-console`: Capture console events alongside network data
- `--summary {text,json,both}`: Control summarizer output format (default: text)
- `--output-dir PATH`: Directory for output files (default: /tmp)
- `--chrome-port PORT`: Chrome debugging port (default: 9222)

### Example: Full Telemetry Capture

```bash
python3 -m scripts.cdp.cli.main orchestrate headless https://api.example.com/dashboard \
  --duration 30 \
  --include-console \
  --summary both \
  --output-dir /tmp/dashboard
```

**Output:**
- `/tmp/dashboard/network-<timestamp>.jsonl` - Network activity
- `/tmp/dashboard/console-<timestamp>.jsonl` - All console logs
- `/tmp/dashboard/summary-<timestamp>.txt` - Text summary with request counts, status codes, and error messages
- `/tmp/dashboard/summary-<timestamp>.json` - JSON summary for programmatic processing

**Note:** Response body filtering is now controlled via the `network` subcommand's `--include-bodies` flag when using manual workflows.

---

## Headed Mode Workflow

**Use case:** Interactive debugging, manual testing, authentication flows

### Quick Start: Open Visible Browser

```bash
python3 -m scripts.cdp.cli.main orchestrate headed http://localhost:3000/signin \
  --duration 600 \
  --include-console
```

**What happens:**
- Opens a **visible Chrome window** showing the page
- **Runs for specified duration** (600 seconds = 10 minutes in this example)
- You can **type, click, and interact** normally
- Console logs and network activity are captured in real-time
- Uses persistent profile at `$HOME/.chrome-debug-profile`
- Automatic reconnection if Chrome crashes

**Use cases:**
- Testing form interactions (login, signup, checkout)
- Debugging pages that require manual authentication
- Watching real-time form validation
- Testing workflows that need human interaction

**Note:** Set `--duration` to a value longer than your expected interaction time. The session will auto-close when the duration expires.

### Example: Checkout Flow Debugging

```bash
python3 -m scripts.cdp.cli.main orchestrate headed http://localhost:3000/checkout \
  --duration 600 --include-console --summary both --output-dir /tmp/checkout
```

**Workflow:**
1. Chrome window opens at checkout page
2. Manually interact: add items, fill forms, click buttons (within 10 minutes)
3. Console logs captured to `/tmp/checkout/console-<timestamp>.jsonl`
4. Network activity captured to `/tmp/checkout/network-<timestamp>.jsonl`
5. Session auto-closes after 600 seconds
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

**Option A: Using Python CLI (Recommended)**
```bash
python3 -m scripts.cdp.cli.main orchestrate headed http://localhost:3000/signin \
  --duration 600 \
  --include-console
```

**Option B: Using Chrome Launcher Directly (For Manual Control)**
```bash
./scripts/core/chrome-launcher.sh "http://localhost:3000/signin" --mode=headed
```

**Output (Chrome Launcher):**
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
- Browser stays open for interaction
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
2. ☐ Launch Chrome: `python3 -m scripts.cdp.cli.main orchestrate "URL" --mode=headed --include-console`
3. ☐ Extract WebSocket URL from JSON output or re-fetch: `curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl'`
4. ☐ Instruct user on what actions to perform
5. ☐ Wait for user signal ("ready")
6. ☐ Re-fetch WebSocket URL (if user navigated): `curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1`
7. ☐ Extract DOM: Use websocat or Python method
8. ☐ Get context (current URL, title)
9. ☐ Analyze DOM with grep/jq
10. ☐ Provide debugging insights to user

---

## Graceful Session Cleanup

**Use case:** Stop debugging sessions cleanly with automatic artifact preservation

The Python CDP CLI automatically handles cleanup when sessions end (either naturally or via Ctrl+C). This ensures all captured data is preserved and resources are released properly.

### How It Works

When a session ends (timeout or Ctrl+C):

1. **Monitors stopped gracefully** - Network and console collectors shut down cleanly
2. **Summary generated** - Text/JSON summary of captured data created
3. **Chrome terminated** - Browser process stopped cleanly (if managed by orchestrate)
4. **All artifacts preserved** - File locations displayed for review

### Example: Session Termination

```bash
# Start a session
python3 -m scripts.cdp.cli.main orchestrate headed http://localhost:3000/dashboard \
  --duration 600 --include-console --summary both --output-dir /tmp/session

# (Interact with the page...)
# Press Ctrl+C when ready to stop, or wait for 600s timeout

# Output:
Session ended. Cleaning up...
Stopping network monitor...
Stopping console monitor...
Generating summary report...

Session artifacts saved:
   Network log: /tmp/session/network-20251025-143522.jsonl
   Console log: /tmp/session/console-20251025-143522.jsonl
   Summary (text): /tmp/session/summary-20251025-143522.txt
   Summary (JSON): /tmp/session/summary-20251025-143522.json

Persistent profile kept at: /Users/user/.chrome-debug-profile
To clean: rm -rf /Users/user/.chrome-debug-profile

Session cleanup complete!
```

### Unique Session File Naming

All output files include timestamps to prevent conflicts when running concurrent sessions:

**File naming pattern:**
```
{type}-{YYYYMMDD-HHMMSS}.{ext}
```

**Examples:**
```bash
# Single session
python3 -m scripts.cdp.cli.main orchestrate headless http://localhost:3000 \
  --duration 30 --output-dir /tmp
# Creates: /tmp/network-20251025-143522.jsonl
#          /tmp/console-20251025-143522.jsonl (if --include-console)

# Concurrent sessions (no conflicts due to different timestamps)
python3 -m scripts.cdp.cli.main orchestrate headless http://example.com/login \
  --duration 30 --output-dir /tmp &
python3 -m scripts.cdp.cli.main orchestrate headless http://example.com/signup \
  --duration 30 --output-dir /tmp &
# Creates: /tmp/network-20251025-143522.jsonl
#          /tmp/network-20251025-143528.jsonl
```

### Benefits

- **No data loss** - Partial captures preserved even on early termination
- **Clean resource management** - No orphaned Chrome processes or monitors
- **Concurrent-safe** - Multiple sessions can run without file conflicts
- **Immediate feedback** - File locations displayed for quick review
- **Automatic reconnection** - Chrome crash recovery with domain replay

---

## Error Handling

The orchestrator implements robust error detection with clear recovery guidance.

### URL Validation Errors

#### 404 Hard-Stop (Remote URLs)

```bash
./scripts/corpython3 -m scripts.cdp.cli.main orchestrate "https://example.com/nonexistent"

# Output:
❌ URL validation failed - HARD STOP
   HTTP Status: 404 Not Found
   Error: The URL https://example.com/nonexistent does not exist on the server
   Recovery:
     1. Verify the URL is correct (check spelling, path)
     2. Verify the server is running and the resource exists
     3. Use --skip-validation ONLY if you need to generate a new page ID

   ⚠️  Chrome will NOT be launched. Fix the URL before proceeding.
```

**Key behaviors:**
- Remote URLs require 200-399 HTTP status (strict validation)
- 404 errors trigger immediate hard-stop with detailed guidance
- No Chrome launch occurs when validation fails
- Clear distinction between localhost (lenient) and remote (strict) validation

#### Localhost Lenient Validation

```bash
./scripts/corpython3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000/signin"

# Output (for any HTTP status 200-599):
🔍 Validating URL: http://localhost:3000/signin (localhost - lenient validation)
✅ URL validation passed (HTTP 404 - localhost lenient mode) in 125ms
```

**Key behaviors:**
- Localhost URLs (localhost, 127.0.0.1) accept any HTTP status 200-599
- No `--skip-validation` flag needed for local development
- Designed for dev servers that may return 404 for authenticated routes

### Collector Script Validation

```bash
# If collector scripts are missing/moved
./scripts/corpython3 -m scripts.cdp.cli.main orchestrate "http://example.com"

# Output:
{
  "status": "error",
  "code": "COLLECTOR_MISSING",
  "message": "Required collector script not found: /path/to/scripts/collectors/cdp-network.py",
  "recovery": "Verify repository structure: ls -la /path/to/scripts/collectors/"
}
```

**Key behaviors:**
- All collector scripts validated before Chrome launch
- Clear error message with missing script path
- Recovery guidance provided

### Port Conflict Detection

```bash
# If port 9222 is already in use
./scripts/corpython3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000"

# Output:
❌ Chrome launch failed
   Error: PORT_BUSY
   Message: Port 9222 is already in use by PID 12345

💡 Recovery:
   pkill -f 'chrome.*9222' && sleep 1
```

**Key behaviors:**
- Port conflicts detected during Chrome launch
- Displays owning PID for cleanup
- Suggests specific pkill command

### Monitor Startup Failures

```bash
# If Python websockets library is missing
./scripts/corpython3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000" --include-console

# Output:
❌ Console monitor failed to start
   Command: python3 /path/to/scripts/collectors/cdp-console.py 12345 --port=9222
   Check log: /tmp/page-debug-20251024-143522-12345-console.log

💡 Recovery:
   - Verify Python websockets installed: pip3 install websockets --break-system-packages
   - Check CDP port accessibility: curl -s http://localhost:9222/json
```

**Key behaviors:**
- Monitor PIDs verified after spawn (`kill -0 $PID`)
- Detailed error message with exact command attempted
- Recovery steps include dependency verification
- Partial cleanup performed (other monitors stopped)

### Skip Validation Flag

For intentionally unreachable URLs (e.g., testing CDP behavior on invalid pages):

```bash
./scripts/corpython3 -m scripts.cdp.cli.main orchestrate "https://invalid-domain-12345.com" \
  --skip-validation --summary=both
```

**Warning:** Only use `--skip-validation` when you specifically need to bypass URL checks. This is rarely needed and can lead to unexpected behavior.

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
./scripts/corpython3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000" --mode=headed --include-console > /tmp/chrome-session.json

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
./scripts/corpython3 -m scripts.cdp.cli.main orchestrate "URL" --mode=headed --port=9223
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
./scripts/corpython3 -m scripts.cdp.cli.main orchestrate "$URL" 15 /tmp/network.log --include-console --summary=both --idle=2

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

- **Chrome 136+ Requirements:** `docs/guides/chrome-136-incident.md`
- **CDP Commands Reference:** `docs/reference/cdp-commands.md`
- **Troubleshooting Guide:** `docs/guides/troubleshooting.md`
- **Interactive Workflow Design:** `docs/guides/interactive-workflow-design.md`


## Recent Updates

**2025-10-24**: Added graceful session cleanup (SIGINT trap), unique session file naming, and enhanced error handling sections. Updated to reflect 006-fix-orchestrator-paths feature improvements.

