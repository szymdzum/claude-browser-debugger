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

### Monitor Console Logs (Python CLI)

Use when you need to debug JavaScript errors or see console output.

**Single Command:**
```bash
python3 -m scripts.cdp.cli.main console https://example.com \
  --duration 30 \
  --output /tmp/console.jsonl
```

**With filtering:**
```bash
# Only capture warnings and errors
python3 -m scripts.cdp.cli.main console https://example.com \
  --duration 30 \
  --level warn \
  --output /tmp/console.jsonl
```

Output format (JSONL):
```json
{"timestamp":1698765432.123,"level":"log","text":"Hello world","url":"https://example.com","line":42}
{"timestamp":1698765433.456,"level":"error","text":"Uncaught TypeError...","url":"https://example.com","line":55}
```

**Automatic Chrome Management:** The Python CLI launches Chrome automatically, monitors console logs, and cleans up when done.

### Monitor Network Activity

**Basic Network Monitoring:**
```bash
python3 -m scripts.cdp.cli.main network https://example.com \
  --duration 30 \
  --output /tmp/network.json
```

**With Response Bodies:**
```bash
# Capture response bodies (useful for API debugging)
python3 -m scripts.cdp.cli.main network https://example.com \
  --duration 30 \
  --include-bodies \
  --output /tmp/network.json
```

Output format (JSON):
```json
{
  "requests": [
    {"requestId":"...","url":"https://api.example.com/data","method":"GET","timestamp":1698765432.123}
  ],
  "responses": [
    {"requestId":"...","status":200,"statusText":"OK","mimeType":"application/json","timestamp":1698765433.456}
  ]
}
```

## Full Workflow Orchestration (Recommended)

The `orchestrate` command coordinates all debugging activities in one command: Chrome management, console monitoring, network capture, DOM extraction, and summary generation.

**Headless mode** (automated, no UI):
```bash
python3 -m scripts.cdp.cli.main orchestrate https://example.com/login \
  --duration 20 \
  --console \
  --network \
  --summary both \
  --output /tmp/example
```

**Headed mode** (visible browser for manual testing):
```bash
python3 -m scripts.cdp.cli.main orchestrate http://localhost:3000/checkout \
  --mode headed \
  --duration 20 \
  --console \
  --network \
  --summary both \
  --output /tmp/checkout
```

What you get:
- Network trace in JSON format
- Console logs in JSONL format
- DOM snapshot as HTML
- Text and JSON summaries
- Automatic Chrome lifecycle management

### Python CLI Options

**Available Subcommands:**
- `session` - List and manage CDP targets
- `eval` - Execute JavaScript expressions
- `dom` - Extract DOM snapshots
- `console` - Stream console logs
- `network` - Capture network traffic
- `orchestrate` - Full debugging workflow (recommended)
- `query` - Execute arbitrary CDP commands

**Common Orchestrate Options:**
- `--mode headed|headless` - Launch visible Chrome or run headless (default: headless)
- `--duration SECONDS` - Capture duration in seconds
- `--console` - Enable console log monitoring
- `--network` - Enable network traffic capture
- `--include-bodies` - Capture response bodies (use with `--network`)
- `--summary text|json|both` - Generate summary in specified format(s)
- `--output PATH` - Base path for output files

**Global Options:**
- `--chrome-port PORT` - Chrome debugging port (default: 9222)
- `--timeout SECONDS` - Command timeout (default: 30)
- `--format json|text|table` - Output format
- `--quiet` - Suppress non-essential output
- `--verbose` - Enable debug logging

### Handling Port Conflicts

If Chrome is already bound to port 9222:
```bash
pkill -f "chrome.*9222"
```

Or use a different port:
```bash
python3 -m scripts.cdp.cli.main --chrome-port 9223 orchestrate https://example.com
```

## Architecture

**Python CDP Package** (`scripts/cdp/`):
- `connection.py` - WebSocket CDP connection with automatic reconnection
- `session.py` - Target discovery and session management
- `collectors/` - Console, network, and DOM monitoring
- `cli/` - Unified command-line interface

**Chrome Launcher** (`scripts/core/chrome-launcher.sh`):
- Launches Chrome with CDP enabled (headless/headed)
- Manages isolated profiles for Chrome 136+ compatibility
- Returns JSON contract with WebSocket URL and process info


**For complete documentation, see [docs/guides/workflows.md](docs/guides/workflows.md)**

## Common Workflows

### Interactive DOM Inspection (Headed Mode)

Launch visible Chrome for manual testing, then extract DOM state after user interactions.

**Automated Workflow (Recommended):**
```bash
python3 -m scripts.cdp.cli.main orchestrate http://localhost:3000/signin \
  --mode headed \
  --duration 60 \
  --console \
  --network
```

This launches Chrome, monitors activity for 60 seconds (or until you press Ctrl+C), then automatically:
- Extracts final DOM state
- Saves console logs
- Captures network activity
- Generates summary report

**Manual DOM Extraction:**
If you need to extract DOM during interaction without stopping the session:
```bash
# Extract DOM at any point
python3 -m scripts.cdp.cli.main dom http://localhost:3000 \
  --output /tmp/dom-snapshot.html \
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

**Solution:** Use the Python CLI `orchestrate` command (handles this automatically):
```bash
python3 -m scripts.cdp.cli.main orchestrate URL --mode headed
```

If launching manually:
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
# Get DOM snapshot (simple)
chrome --headless=new --dump-dom $URL

# Get DOM snapshot (Python CLI)
python3 -m scripts.cdp.cli.main dom $URL --output /tmp/dom.html

# Monitor console logs
python3 -m scripts.cdp.cli.main console $URL --duration 30 --output /tmp/console.jsonl

# Monitor network traffic
python3 -m scripts.cdp.cli.main network $URL --duration 30 --include-bodies --output /tmp/network.json

# Full workflow orchestration (recommended)
python3 -m scripts.cdp.cli.main orchestrate $URL \
  --duration 30 \
  --console \
  --network \
  --summary both \
  --output /tmp/debug

# Headed mode (interactive debugging)
python3 -m scripts.cdp.cli.main orchestrate $URL \
  --mode headed \
  --console \
  --network

# Execute JavaScript
python3 -m scripts.cdp.cli.main eval $URL --expression "document.title" --format text

# List Chrome targets
python3 -m scripts.cdp.cli.main session list --format table

# Cleanup
pkill -f "chrome.*9222"
```

## Examples

### Example: Find all console errors on a page

```bash
python3 -m scripts.cdp.cli.main console https://example.com \
  --duration 10 \
  --level error \
  --output /tmp/errors.jsonl
```

### Example: Check if a page makes API calls to a specific domain

```bash
python3 -m scripts.cdp.cli.main network https://example.com \
  --duration 10 \
  --output /tmp/network.json

# Then filter the output
jq '.requests[] | select(.url | contains("api.example.com"))' /tmp/network.json
```

### Example: Get the page title via JavaScript evaluation

```bash
python3 -m scripts.cdp.cli.main eval https://example.com \
  --expression "document.title" \
  --format text
```

### Example: Full debugging session with all telemetry

```bash
python3 -m scripts.cdp.cli.main orchestrate https://example.com \
  --duration 30 \
  --console \
  --network \
  --include-bodies \
  --summary both \
  --output /tmp/full-debug
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
