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
chrome --user-data-dir=~/.chrome-debug-profile --remote-debugging-port=9222 URL
```

**Why:** Chrome 136+ security policy blocks CDP access to your default user profile to prevent cookie/credential theft. See `docs/headed-mode/CHROME-136-CDP-INCIDENT.md` for details.

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
- Uses persistent profile at `~/.chrome-debug-profile`

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

`summarize.py` consumes any network/console log pair and prints aggregate stats.
```bash
python3 summarize.py \
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
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
timeout 10 python3 cdp-console.py $PAGE_ID | grep '"type":"error"'
pkill -f "chrome.*9222"
```

### Example: Check if a page makes API calls to a specific domain

```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
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
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
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

### Documentation Structure

Comprehensive documentation is available in `docs/`:

- **`docs/headed-mode/CHROME-136-CDP-INCIDENT.md`** - Chrome 136+ security change that requires `--user-data-dir` for headed mode. Includes investigation timeline, test results, and solution details.
- **`docs/headed-mode/INTERACTIVE_WORKFLOW_DESIGN.md`** - Headed mode workflow design and user interaction patterns.
- **`docs/headed-mode/LAUNCHER_CONTRACT.md`** - chrome-launcher.sh API specification, JSON output format, and error codes.

### Testing & Diagnostics

#### Smoke Test

Validate headed Chrome CDP functionality after Chrome updates:

```bash
./tests/smoke-test-headed.sh
```

**What it tests:**
- Chrome version detection (warns if Chrome 136+)
- Headed launch with proper `--user-data-dir`
- CDP endpoint availability
- Runtime.evaluate functionality
- DOM access
- Auto-cleanup

**Expected output:**
```
✓ All tests passed!

Summary:
  Chrome Version: Google Chrome 141.0.7390.109
  CDP Port: 9999
  Runtime.evaluate: ✓
  DOM Access: ✓
```

#### Diagnostic Script

For troubleshooting CDP connection issues:

```bash
# Get page ID first
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')

# Run diagnostic with full logging
PYTHONASYNCIODEBUG=1 python3 scripts/diagnostics/debug-cdp-connection.py $PAGE_ID 9222
```

**Shows:**
- Step-by-step WebSocket connection flow
- Exact point where Chrome stops responding (if any)
- Full async debug logs
- WebSocket handshake details

### Common Issues

**Issue: Headed mode hangs indefinitely**

**Cause:** Chrome 136+ requires `--user-data-dir` for CDP access.

**Solution:** Ensure you're using `chrome-launcher.sh` or `debug-orchestrator.sh`, which handle this automatically. If launching Chrome manually, always include `--user-data-dir`:

```bash
chrome --user-data-dir=~/.chrome-debug-profile --remote-debugging-port=9222 URL
```

**See:** `docs/headed-mode/CHROME-136-CDP-INCIDENT.md` for full details.
