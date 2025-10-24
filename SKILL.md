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
- **Headed Mode**: Launch visible Chrome window for interactive debugging
- **Real-time Form Monitoring**: Watch form field changes as users type

## Prerequisites

Required tools and packages:

- **Python 3.x** with **websockets library**: `pip3 install websockets --break-system-packages`
- **Chrome or Chromium** browser
- **jq**: For JSON parsing (install with `brew install jq` on macOS or `apt-get install jq` on Linux)
- **curl**: Usually pre-installed
- **websocat** *(optional but recommended for ad-hoc CDP commands)*: `brew install websocat`

Verify installation:
```bash
python3 --version
python3 -c "import websockets; print('websockets installed')"
jq --version
chrome --version  # Check if Chrome 136+
```

## Chrome 136+ Important Note

⚠️ **Chrome 136+ (March 2025) requires `--user-data-dir` for headed mode CDP.**

The orchestrator and launcher scripts handle this automatically. If launching Chrome manually:

```bash
# ❌ WRONG (Chrome 136+ blocks CDP on default profile)
chrome --remote-debugging-port=9222 URL

# ✅ CORRECT (Works with Chrome 136+)
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL
```

**Why:** Chrome 136+ security policy blocks CDP access to your default user profile to prevent cookie/credential theft.

**For detailed Chrome 136 requirements, troubleshooting, and technical background, see [docs/guides/chrome-136-incident.md](docs/guides/chrome-136-incident.md)**

## Quick Start

### Get DOM Snapshot

The simplest way to extract rendered HTML:

```bash
chrome --headless=new --dump-dom https://example.com
```

Save to file or pipe to other commands:

```bash
# Save to file
chrome --headless=new --dump-dom https://example.com > page.html

# Search for specific content
chrome --headless=new --dump-dom https://example.com | grep "error"
```

### Monitor Console Logs (Basic Workflow)

Use when you need to debug JavaScript errors or see console output.

**Step 1: Start Chrome with debugging port**
```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
```

**Step 2: Wait for Chrome to start**
```bash
sleep 2
```

**Step 3: Get the page ID**
```bash
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
```

> **Tip:** Page IDs change after navigation. Re-run this command before each capture instead of reusing stale IDs.

**Step 4: Monitor console**
```bash
python3 scripts/collectors/cdp-console.py $PAGE_ID
```

Output format:
```json
{"type":"log","timestamp":1698765432,"message":"Hello world","stackTrace":null}
{"type":"error","timestamp":1698765433,"message":"Uncaught TypeError...","stackTrace":{...}}
```

**Step 5: Cleanup when done**
```bash
pkill -f "chrome.*9222"
```

### Monitor Network Activity

Follow the same setup as console monitoring (Steps 1-3), then:

```bash
python3 scripts/collectors/cdp-network.py $PAGE_ID
```

Output format:
```json
{"event":"request","url":"https://api.example.com/data","method":"GET","requestId":"..."}
{"event":"response","url":"https://api.example.com/data","status":200,"statusText":"OK","mimeType":"application/json","requestId":"..."}
{"event":"failed","errorText":"net::ERR_CONNECTION_REFUSED","requestId":"..."}
```

## Using the Orchestrator Script

`scripts/core/debug-orchestrator.sh` coordinates Chrome, CDP collectors, and post-run summaries. Use it for full telemetry in one command.

**Headless mode** (automated, no UI):
```bash
./scripts/core/debug-orchestrator.sh "https://example.com/login" 20 /tmp/example.log \
  --include-console --summary=both --idle=3
```

**Headed mode** (visible browser):
```bash
./scripts/core/debug-orchestrator.sh "http://localhost:3000/checkout" 20 /tmp/checkout.log \
  --mode=headed --include-console --summary=both
```

What you get:
- Network stream written to `/tmp/example.log`
- Console stream written to `/tmp/example-console.log`
- Text and JSON summaries printed at the end
- Automatic Chrome startup/cleanup on port 9222

### Useful Orchestrator Flags

- `--mode=headed|headless`: Launch visible Chrome or run headless (default: headless)
- `--idle=<seconds>`: Stop capture after the page goes quiet (applies to both console and network)
- `--include-console`: Capture console events alongside network data
- `--console-log=PATH`: Direct console output to a custom file
- `--summary=text|json|both`: Control summarizer output format
- `--filter="<substring>"`: Capture response bodies for matching URLs (use cautiously, bodies can be large)

### Handling Port Conflicts

If Chrome is already bound to port 9222, free the port and rerun:
```bash
pkill -f "chrome.*9222"
```

## Script Organization

This skill's scripts are organized by function:

- **scripts/core/**: Main workflow scripts
  - `chrome-launcher.sh` - Launch Chrome with CDP enabled
  - `debug-orchestrator.sh` - High-level workflow coordinator

- **scripts/collectors/**: CDP monitoring scripts
  - `cdp-console.py` - Console log monitoring
  - `cdp-network.py` - Network request/response tracking
  - `cdp-network-with-body.py` - Network with response body capture
  - `cdp-dom-monitor.py` - Real-time DOM/form field change monitoring

- **scripts/utilities/**: Helper scripts
  - `summarize.py` - Post-capture summary generation
  - `cleanup-chrome.sh` - Kill Chrome processes and release ports

**For complete script documentation and advanced usage, see [scripts/README.md](scripts/README.md)**

## Common Workflows

### Interactive DOM Inspection (Headed Mode)

Launch Chrome, allow user to interact, then extract DOM state for analysis.

**Step 1: Launch Chrome**
```bash
./scripts/core/debug-orchestrator.sh "http://localhost:3000/signin" \
  --mode=headed \
  --include-console
```

**Step 2: User Interacts**
Browser stays open. User clicks, types, navigates as needed.

**Step 3: Extract Current DOM**
```bash
# Re-fetch WebSocket URL (page may have navigated)
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)

# Extract DOM with websocat
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html
```

**Step 4: Analyze DOM**
```bash
# Find forms
grep -o '<form[^>]*>' /tmp/live-dom.html

# Find error messages
grep -i 'error\|invalid\|required' /tmp/live-dom.html

# Get current URL
echo '{"id":2,"method":"Runtime.evaluate","params":{"expression":"window.location.href","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Form Submission Debugging

Debug form submission issues with before/after DOM extraction.

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
```

**For complete workflow documentation, advanced patterns, and examples, see [docs/guides/workflows.md](docs/guides/workflows.md)**

## Ad-hoc CDP Commands with websocat

Execute custom CDP commands directly via WebSocket:

```bash
# 1. Get WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

# 2. Extract DOM
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html

# 3. Get page title
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# 4. Access localStorage
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"JSON.stringify(localStorage)","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value' | jq .

# 5. Get cookies
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.cookie","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

**Tips:**
- `-B 1048576` sets 1MB buffer for large responses (increase to 2097152 for 2MB if needed)
- Use `-n1` to close after 1 message (request/response pattern)
- Other useful CDP methods: `Page.captureScreenshot`, `Network.getAllCookies`, `Accessibility.getFullAXTree`

**For complete CDP command reference, see [docs/reference/cdp-commands.md](docs/reference/cdp-commands.md)**

## Quick Troubleshooting

### "No module named 'websockets'"
```bash
pip3 install websockets --break-system-packages
# or
python3 -m pip install websockets --user
```

### Port 9222 already in use
```bash
# Kill existing Chrome processes
pkill -f "chrome.*9222"

# Or use a different port
chrome --headless=new --remote-debugging-port=9223 $URL &
```

### Buffer overflow (websocat)
```bash
# Increase buffer size to 2MB
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 2097152 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html
```

### WebSocket URL stale (after navigation)
```bash
# Re-fetch WebSocket URL before each extraction
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
```

### Headed mode hangs indefinitely

**Cause:** Chrome 136+ requires `--user-data-dir` for CDP access.

**Solution:** Use `scripts/core/chrome-launcher.sh` or `scripts/core/debug-orchestrator.sh` (automatic). If launching manually:
```bash
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL
```

**For comprehensive troubleshooting, error handling, and edge cases, see [docs/guides/troubleshooting.md](docs/guides/troubleshooting.md)**

## Documentation

Complete reference documentation:

### Core Documentation
- **[README.md](README.md)** - Installation, capabilities, and maintainer guide
- **[scripts/README.md](scripts/README.md)** - Script usage, parameters, and examples


### Technical References
- **[docs/guides/chrome-136-incident.md](docs/guides/chrome-136-incident.md)** - Chrome 136 security policy change, investigation, solution
- **[docs/guides/launcher-contract.md](docs/guides/launcher-contract.md)** - chrome-launcher.sh API specification
- **[docs/guides/interactive-workflow-design.md](docs/guides/interactive-workflow-design.md)** - Headed mode design rationale
- **[docs/reference/websocat-analysis.md](docs/reference/websocat-analysis.md)** - WebSocket/CDP internals and buffer tuning
- **[docs/reference/cdp-commands.md](docs/reference/cdp-commands.md)** - Complete CDP command reference

### Workflow Documentation
- **[docs/guides/workflows.md](docs/guides/workflows.md)** - Detailed workflow patterns and examples
- **[docs/guides/troubleshooting.md](docs/guides/troubleshooting.md)** - Error handling, recovery patterns, and edge cases

### Spec-Kit Integration
- **[docs/skills.md](docs/skills.md)** - Skill development guide
- **[docs/skills-best-practices.md](docs/skills-best-practices.md)** - Best practices for skill authors

## Quick Reference

```bash
# Get DOM snapshot
chrome --headless=new --dump-dom $URL

# Monitor console (4-step pattern)
chrome --headless=new --remote-debugging-port=9222 $URL &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
python3 scripts/collectors/cdp-console.py $PAGE_ID

# Monitor network
python3 scripts/collectors/cdp-network.py $PAGE_ID

# Orchestrated capture with summaries
./scripts/core/debug-orchestrator.sh "$URL" 15 /tmp/network.log --include-console --summary=both --idle=2

# Headed mode (interactive debugging)
./scripts/core/debug-orchestrator.sh "$URL" --mode=headed --include-console

# Extract live DOM (after user interaction)
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value' > /tmp/live-dom.html

# Cleanup
pkill -f "chrome.*9222"
```

## Examples

### Example: Find all console errors on a page

```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
timeout 10 python3 scripts/collectors/cdp-console.py $PAGE_ID | grep '"type":"error"'
pkill -f "chrome.*9222"
```

### Example: Check if a page makes API calls to a specific domain

```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
timeout 10 python3 scripts/collectors/cdp-network.py $PAGE_ID | grep 'api.example.com'
pkill -f "chrome.*9222"
```

### Example: Get the page title from DOM

```bash
chrome --headless=new --dump-dom https://example.com | \
  grep -o '<title>.*</title>' | \
  sed 's/<title>\(.*\)<\/title>/\1/'
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

### v2.2.0 (2025-10-24)

**Improvement:** Progressive Disclosure Documentation Structure

**Changes:**
- Condensed SKILL.md from 1114 to ~480 lines (57% reduction)
- Applied progressive disclosure pattern: overview → details via links
- Reorganized scripts into scripts/core/, scripts/collectors/, scripts/utilities/
- Moved detailed workflows to docs/guides/workflows.md
- Moved comprehensive troubleshooting to docs/guides/troubleshooting.md
- Added Documentation section with complete reference index
- Improved Quick Start section with minimal but complete examples
- Maintained all essential content (prerequisites, Chrome 136 note, basic workflows)
- Enhanced navigation with clear links to detailed documentation

### v2.1.0 (2025-10-24)

**Feature:** Interactive DOM Access for AI Agents

**Enhancements:**
- Added comprehensive Interactive DOM Inspection Workflow with 4-phase structure
- Documented primary (websocat) and fallback (Python websockets) DOM extraction methods
- Added Quick Start Checklist, Prerequisites Check, Tool Detection Pattern
- Added Common Workflows for iterative debugging and form submission debugging
- Added Output Format Documentation and Error Handling sections
- Chrome 136+ compatibility ensured with automatic `--user-data-dir` handling
