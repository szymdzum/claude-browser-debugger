# Browser Debugger Scripts

This directory contains all executable scripts for the Browser Debugger skill, organized by function into three categories.

## Organization

Scripts are organized into three functional categories:

- **core/** - Orchestration and Chrome process management
- **collectors/** - CDP telemetry capture and monitoring
- **utilities/** - Helper tools and session management

## Core Scripts

High-level orchestration and Chrome process management.

| Script | Purpose | Usage |
|--------|---------|-------|
| **chrome-launcher.sh** | Launch Chrome with CDP debugging enabled | `./scripts/core/chrome-launcher.sh <URL> [--mode=headed\|headless] [--port=9222] [--profile=PATH] [--idle=SECONDS]` |
| **debug-orchestrator.sh** | Workflow coordinator for complete debugging sessions | `./scripts/core/debug-orchestrator.sh <URL> <duration> <output-file> [--mode=headed\|headless] [--include-console] [--summary=text\|json\|both]` |

### chrome-launcher.sh

Launches Chrome with CDP debugging and returns a JSON contract with WebSocket URL, PID, and profile path.

**Key Features:**
- Auto-detects Chrome 136+ and applies `--user-data-dir` requirement
- Supports both headed (visible browser) and headless modes
- Returns structured JSON with `ws_url`, `chrome_pid`, `profile_path`, `status`
- Handles port conflicts and profile lock issues

**Example:**
```bash
# Headed mode (visible browser)
./scripts/core/chrome-launcher.sh "https://example.com" --mode=headed

# Headless mode (automated testing)
./scripts/core/chrome-launcher.sh "https://example.com" --mode=headless
```

**Output:** JSON contract (see `docs/headed-mode/LAUNCHER_CONTRACT.md`)

### debug-orchestrator.sh

High-level workflow coordinator that manages Chrome launch, CDP collectors, and summary generation.

**Key Features:**
- Launches Chrome via chrome-launcher.sh
- Starts console and/or network collectors
- Monitors for idle timeout (no new events)
- Generates text and/or JSON summaries
- Handles cleanup on exit

**Example:**
```bash
# 30-second capture with console logging and text summary
./scripts/core/debug-orchestrator.sh "https://example.com" 30 /tmp/debug.log \
  --include-console --summary=text

# Headed mode for interactive debugging
./scripts/core/debug-orchestrator.sh "http://localhost:3000" 300 /tmp/app-debug.log \
  --mode=headed --include-console --idle=10
```

**Flags:**
- `--mode=headed|headless` - Browser visibility (default: headless)
- `--include-console` - Enable console log monitoring
- `--summary=text|json|both` - Summary format
- `--idle=SECONDS` - Auto-stop after N seconds of no events (default: 5)
- `--skip-validation` - Skip URL validation for local servers

---

## Collectors

CDP monitoring scripts that connect to Chrome's debugging WebSocket and capture telemetry.

| Script | Purpose | Usage |
|--------|---------|-------|
| **cdp-console.py** | Monitor JavaScript console logs and errors | `python3 scripts/collectors/cdp-console.py <page-id> [url] [--port=9222] [--idle-timeout=5]` |
| **cdp-network.py** | Track network requests and responses (headers only) | `python3 scripts/collectors/cdp-network.py <page-id> [--port=9222] [--idle-timeout=5]` |
| **cdp-network-with-body.py** | Track network with selective response body capture | `python3 scripts/collectors/cdp-network-with-body.py <page-id> [--port=9222] [--idle-timeout=5] [--max-body-size=10000]` |
| **cdp-dom-monitor.py** | Monitor real-time DOM changes and form field updates | `python3 scripts/collectors/cdp-dom-monitor.py <page-id> [--port=9222] [--idle-timeout=5]` |
| **cdp-summarize.py** | Generate human-readable summaries from collector logs | `python3 scripts/collectors/cdp-summarize.py <log-file> [--format=text\|json\|both]` |

### cdp-console.py

Captures JavaScript console messages including logs, errors, warnings, and exceptions.

**Key Features:**
- Captures all console.log(), console.error(), console.warn() output
- Records uncaught exceptions with stack traces
- Idle detection (stops after N seconds of no new messages)
- Outputs JSON events to stdout

**Example:**
```bash
# Get page ID first
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)

# Monitor console for 10 seconds or until 5s idle
python3 scripts/collectors/cdp-console.py "$PAGE_ID" --idle-timeout=5
```

**Output:** JSON events with `timestamp`, `level`, `message`, `source`, `line`, `url`

### cdp-network.py

Tracks HTTP requests and responses including method, URL, status code, and headers.

**Key Features:**
- Captures all network requests (XHR, fetch, resources)
- Records response status codes and timing
- Headers included (no response bodies)
- Idle detection

**Example:**
```bash
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
python3 scripts/collectors/cdp-network.py "$PAGE_ID" --idle-timeout=5
```

**Output:** JSON events with `requestId`, `method`, `url`, `status`, `headers`, `timing`

### cdp-network-with-body.py

Extended network monitoring with selective response body capture for debugging API responses.

**Key Features:**
- All features of cdp-network.py
- Captures response bodies for JSON/text responses
- Size limit protection (default 10KB per response)
- Filters out binary/image responses

**Example:**
```bash
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
python3 scripts/collectors/cdp-network-with-body.py "$PAGE_ID" --max-body-size=50000
```

**Use When:** Debugging API responses, checking JSON payloads, analyzing AJAX calls

### cdp-dom-monitor.py

Real-time monitoring of DOM mutations and form field changes.

**Key Features:**
- Tracks element additions/removals
- Monitors form input changes as users type
- Records mutation timestamps and selectors
- Idle detection for interactive sessions

**Example:**
```bash
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
python3 scripts/collectors/cdp-dom-monitor.py "$PAGE_ID" --idle-timeout=10
```

**Use When:** Debugging form submissions, tracking dynamic content, monitoring SPA route changes

### cdp-summarize.py

Post-capture summarizer that analyzes collector logs and generates human-readable reports.

**Key Features:**
- Parses JSON events from collector outputs
- Generates categorized summaries (errors, warnings, requests)
- Supports text and JSON output formats
- Highlights critical issues

**Example:**
```bash
# After running collectors, summarize the output
python3 scripts/collectors/cdp-summarize.py /tmp/debug.log --format=text
```

**Output Formats:**
- `text` - Human-readable markdown summary
- `json` - Structured JSON for parsing
- `both` - Both formats side-by-side

---

## Utilities

Helper scripts for session management, cleanup, and ad-hoc CDP queries.

| Script | Purpose | Usage |
|--------|---------|-------|
| **cdp-query.sh** | Execute ad-hoc CDP commands via WebSocket | `./scripts/utilities/cdp-query.sh <ws-url> <cdp-command> [args...]` |
| **cleanup-chrome.sh** | Kill Chrome processes on debugging port | `./scripts/utilities/cleanup-chrome.sh [--port=9222]` |
| **save-session.sh** | Save Chrome debugging session for later resume | `./scripts/utilities/save-session.sh <session-name> [--port=9222]` |
| **resume-session.sh** | Resume saved debugging session | `./scripts/utilities/resume-session.sh <session-name>` |

### cdp-query.sh

Execute one-off CDP commands without writing Python scripts. Useful for quick queries.

**Key Features:**
- Sends JSON-RPC commands to Chrome via WebSocket
- Auto-formats common commands (Runtime.evaluate, DOM.getDocument)
- Returns JSON response
- Requires WebSocket URL from chrome-launcher.sh or HTTP API

**Example:**
```bash
# Get WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

# Evaluate JavaScript
./scripts/utilities/cdp-query.sh "$WS_URL" "Runtime.evaluate" \
  --expression "document.title"

# Get page URL
./scripts/utilities/cdp-query.sh "$WS_URL" "Target.getTargetInfo"
```

**Common Commands:** Runtime.evaluate, DOM.getDocument, Page.navigate, Network.enable

### cleanup-chrome.sh

Forcefully terminate Chrome processes on the debugging port. Use when Chrome hangs or port is locked.

**Key Features:**
- Finds Chrome processes by debugging port
- Sends SIGTERM first (graceful), then SIGKILL if needed
- Cleans up lock files
- Safe to run when no Chrome is running

**Example:**
```bash
# Clean up default port 9222
./scripts/utilities/cleanup-chrome.sh

# Clean up custom port
./scripts/utilities/cleanup-chrome.sh --port=9223
```

**When to Use:** Port conflicts, hung Chrome processes, before starting new sessions

### save-session.sh

Save the current Chrome debugging session state including WebSocket URL, PID, and profile path.

**Key Features:**
- Captures session metadata to ~/.browser-debugger-sessions/
- Stores WebSocket URL for reconnection
- Records Chrome PID and port
- Enables resume after computer restart

**Example:**
```bash
# Start Chrome and save session
./scripts/utilities/save-session.sh "my-app-debug"

# Session saved to ~/.browser-debugger-sessions/my-app-debug.json
```

**Use When:** Long debugging sessions, need to pause and resume, sharing session with teammate

### resume-session.sh

Restore a previously saved debugging session by reconnecting to the WebSocket.

**Key Features:**
- Loads session from ~/.browser-debugger-sessions/
- Verifies Chrome process is still running
- Reconnects to saved WebSocket URL
- Fails gracefully if session expired

**Example:**
```bash
# Resume saved session
./scripts/utilities/resume-session.sh "my-app-debug"

# Reconnect and continue debugging
```

**Note:** Sessions expire when Chrome process terminates or computer restarts

---

## Quick Reference

### Typical Workflow

```bash
# 1. Launch Chrome with orchestrator
./scripts/core/debug-orchestrator.sh "https://example.com" 30 /tmp/debug.log \
  --include-console --summary=text

# 2. OR manually control collectors
./scripts/core/chrome-launcher.sh "https://example.com" --mode=headless
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
python3 scripts/collectors/cdp-console.py "$PAGE_ID" > /tmp/console.log
python3 scripts/collectors/cdp-network.py "$PAGE_ID" > /tmp/network.log

# 3. Summarize results
python3 scripts/collectors/cdp-summarize.py /tmp/console.log --format=text

# 4. Cleanup
./scripts/utilities/cleanup-chrome.sh
```

### Interactive Debugging (Headed Mode)

```bash
# Launch visible browser for manual interaction
./scripts/core/debug-orchestrator.sh "http://localhost:3000" 600 /tmp/interactive.log \
  --mode=headed --include-console --idle=20

# OR manually
./scripts/core/chrome-launcher.sh "http://localhost:3000" --mode=headed
# Interact with browser, fill forms, click buttons...
# Extract DOM after interaction:
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value' > /tmp/dom-after-interaction.html
```

### Port Conflicts

```bash
# Check if port is in use
lsof -i :9222

# Force cleanup
./scripts/utilities/cleanup-chrome.sh

# Use alternative port
./scripts/core/chrome-launcher.sh "https://example.com" --port=9223
```

---

## Script Locations

All scripts are now organized in functional subdirectories:

- **Orchestration:** `scripts/core/chrome-launcher.sh`, `scripts/core/debug-orchestrator.sh`
- **Monitoring:** `scripts/collectors/*.py`
- **Utilities:** `scripts/utilities/*.sh`

## Documentation

For detailed workflow examples, troubleshooting, and CDP command reference:

- **[SKILL.md](../SKILL.md)** - Main skill documentation
- **[docs/workflows.md](../docs/workflows.md)** - Detailed workflow patterns
- **[docs/troubleshooting.md](../docs/troubleshooting.md)** - Error handling and edge cases
- **[docs/cdp-commands.md](../docs/cdp-commands.md)** - CDP command reference
- **[docs/chrome-136-requirements.md](../docs/chrome-136-requirements.md)** - Chrome 136+ requirements

---

**Last Updated:** 2025-10-24 (Feature 004: Architecture Restructure)
