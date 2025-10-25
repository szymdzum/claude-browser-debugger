# ⚡️ Claude Browser Debugger Skill

A lightweight Chrome DevTools Protocol (CDP) skill for Claude Code that provides browser inspection capabilities without the overhead of full MCP implementations. Built on CDP fundamentals with `websocat` and minimal dependencies, this skill launches Chrome on demand and streams DOM structure, console logs, and network activity directly to Claude.

Designed as a streamlined alternative to dev-tools-mcp, it focuses on quick telemetry capture for common debugging workflows while keeping dependencies minimal and startup fast.

Give Claude Code direct access to browser state—DOM snapshots, console output, and network traces—without manual screenshot exchanges or copy-pasted error logs.

---

## TL;DR
- **Minimal setup** – install, provide a URL, get browser telemetry in Claude
- **Headless or headed** – automated captures or interactive browser sessions for manual testing
- **Complete picture** – DOM snapshots, console output, network traces, structured summaries
- **Lightweight** – direct Chrome DevTools Protocol communication with minimal dependencies

---

### Sample CLI Run

Here's what the orchestrator produces when monitoring a page:

```bash
./scripts/core/debug-orchestrator.sh "https://example.com" 15 /tmp/output.log \
  --include-console --summary=both --idle=3
```
<details>
<summary>Sample output</summary>

```text
🔧 Debug Configuration:
   URL: https://example.com
   Mode: headless
   Duration: 15s
   Output: /tmp/output.log
   Summary format: both
   Console log: /tmp/output-console.log
   Idle timeout: 3s

✅ Chrome launched successfully
   PID: 73421
   Port: 9222
   Page ID: B3F1C93AF7B1138DBF22B723CCDB32C2

📡 Monitoring network traffic for 15s...
{"event": "request", "url": "https://example.com/", "method": "GET", "requestId": "76F4.1"}
{"event": "response", "url": "https://example.com/", "status": 200, "statusText": "OK", "mimeType": "text/html", "requestId": "76F4.1"}
{"type": "log", "timestamp": 1.0, "message": "Rendering home route", "source": "console-api"}

📊 Analysis Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Total Requests:  3
   Total Responses: 3
   Failed Requests: 0

📥 Top 10 Requests:
   GET https://example.com/
   GET https://example.com/static/app.css
   GET https://example.com/static/app.js

📤 Response Status Codes:
      3 200

🖥️ Console Summary:
   Entries: 2
   Levels:
      log: 1
      error: 1
   Sample Errors:
      Uncaught TypeError: Cannot read properties of undefined [https://example.com/static/app.js:42]

🧮 JSON Summary:
{
  "meta": {
    "log_path": "/tmp/output.log",
    "console_log": "/tmp/output-console.log",
    "generated_at": "2025-10-24T18:40:12.378512+00:00",
    "duration_seconds": 15.0,
    "filter": null,
    "total_events": 6,
    "unique_hosts": 1
  },
  "network": {
    "request_count": 3,
    "response_count": 3,
    "failure_count": 0,
    "methods": {
      "GET": 3
    },
    "status_codes": {
      "200": 3
    },
    "top_requests": [
      {
        "method": "GET",
        "url": "https://example.com/"
      },
      {
        "method": "GET",
        "url": "https://example.com/static/app.css"
      },
      {
        "method": "GET",
        "url": "https://example.com/static/app.js"
      }
    ],
    "failures": []
  },
  "console": {
    "entry_count": 2,
    "levels": {
      "log": 1,
      "error": 1
    },
    "sample_errors": [
      {
        "message": "Uncaught TypeError: Cannot read properties of undefined",
        "url": "https://example.com/static/app.js",
        "lineNumber": 42
      }
    ]
  }
}

💾 Full output saved to: /tmp/output.log
🧹 Cleaning up...
✅ Done!
```
</details>

---

## Usage Scenarios

### Scenario 1: Quick DOM Snapshot (Headless)
```
Use browser-debugger skill to capture the DOM of http://localhost:3000 in headless mode
with a 5 second idle timeout. Include console logs and provide a summary.
```
**Expected workflow:** Headless Chrome launches, waits for network idle, captures DOM and console logs, generates a summary, then terminates.

---

### Scenario 2: Interactive Registration Flow (Headed)
```
Use browser-debugger skill to launch http://localhost:3000/customer/register in headed mode.
Let me fill out the registration form manually, then extract the DOM and console logs after I'm done.
```
**Expected workflow:** Visible Chrome launches, user interacts with the page manually, Claude monitors in the background, DOM and logs are captured on request, browser remains available for additional testing.

---

### Scenario 3: Sign-In Flow with Network Monitoring
```
Launch http://localhost:3000/signin with browser-debugger in headed mode. Monitor network
requests and console logs while I test the login flow. After I submit the form, capture everything.
```
**Expected workflow:** Console and network monitoring begin, user tests the login flow, failed requests are highlighted, final DOM and logs are captured together.

---

### Scenario 4: Multi-Step User Journey
```
Use browser-debugger to help me debug the checkout flow on localhost:3000. Start at the homepage,
let me navigate to the product page, add to cart, and proceed to checkout. Capture the DOM at each
major step when I tell you.
```
**Expected workflow:** Persistent Chrome session, DOM captured at each checkpoint on request, complete history of the checkout flow available for analysis.

For command-line testing:
```bash
./scripts/core/debug-orchestrator.sh "https://example.com" 15 /tmp/output.log \
  --include-console --summary=both --idle=3
```
This produces network timelines, console output, and both JSON and human-readable summaries.

---

## Who This Helps

- **Front-end engineers** debugging complex UI state issues that require multiple interactions to reproduce
- **QA teams** who need quick browser telemetry capture during manual testing workflows
- **Backend developers** validating client-side API requests and response handling
- **Full-stack developers** working on localhost who need efficient browser debugging integrated with Claude

---

## Installation

### Python CLI (Recommended)

The unified Python CLI provides a modern interface with better error handling and structured output:

```bash
# Install in development mode (from repository root)
pip install -e .

# Or production install (once published to PyPI)
pip install browser-debugger
```

**Quick Start**:
```bash
# List Chrome targets
cdp session list

# Execute JavaScript
cdp eval --url example.com "document.title"

# Extract DOM
cdp dom dump --url example.com --output dom.html

# Full workflow automation
cdp orchestrate headless https://example.com --include-console
```

See `docs/examples/` for comprehensive usage examples.

### Claude Code Skill (Legacy Bash Interface)

```bash
# Recommended: symlink install (updates follow git pulls automatically)
./install.sh --symlink

# Alternative: standalone copy
./install.sh --copy
```

**Prerequisites**
- Python 3.10+ with `websockets`: `pip install websockets`
- Chrome or Chromium (headless or headed mode)
- `jq` for JSON parsing: `brew install jq` (macOS) or `apt-get install jq` (Linux)

Once installed, Claude Code can invoke the skill at `~/.claude/skills/browser-debugger` when you request browser debugging.

---

## Common Use Cases

- **Inspect API calls** – capture all network requests and responses (headless or headed)
- **Validate form submissions** – monitor POST payloads and server responses in real-time
- **Debug SPA routing** – capture DOM state after client-side navigation completes
- **Responsive testing** – capture DOM at different viewport sizes on request

See `SKILL.md` for additional workflow examples and detailed usage instructions.

---

## Troubleshooting

```bash
# Missing websockets?
pip3 install websockets --break-system-packages

# Need jq?
brew install jq            # macOS
sudo apt-get install jq    # Linux

# Port 9222 already in use?
pkill -f "chrome.*9222"
```

This skill handles Chrome 136+ profile isolation requirements automatically. For additional troubleshooting, see `docs/guides/troubleshooting.md`.

---

## Advanced Usage

```bash
# Idle detection (stops after 3s of network inactivity)
./scripts/core/debug-orchestrator.sh "https://example.com" --idle=3

# Fixed timeout (30 seconds)
./scripts/core/debug-orchestrator.sh "https://example.com" 30 /tmp/out.log

# Capture response bodies for failed requests
./scripts/core/debug-orchestrator.sh "https://example.com" \
  --include-console \
  --network-script=cdp-network-with-body.py \
  --filter-status=error

# Session persistence
./scripts/utilities/save-session.sh /tmp/debug-session
./scripts/utilities/resume-session.sh /tmp/debug-session
```

**Uninstall**
```bash
rm -rf ~/.claude/skills/browser-debugger
```

---

## Architecture

<details>
<summary>Technical details and documentation</summary>

### Core Components

- **`scripts/core/chrome-launcher.sh`** – Launches Chrome (headless/headed), manages isolated profiles for Chrome 136+, returns CDP WebSocket URL
- **`scripts/core/debug-orchestrator.sh`** – Coordinates collectors, manages lifecycle, generates structured summaries
- **`scripts/collectors/`** – Console logging, network monitoring (with optional response bodies), DOM change detection, summary generation
- **`scripts/utilities/`** – Session save/resume, Chrome cleanup, ad-hoc CDP command execution

### Manual Testing

```bash
# Quick DOM dump
chrome --headless=new --dump-dom https://example.com

# Console monitoring example
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
python3 ~/.claude/skills/browser-debugger/scripts/collectors/cdp-console.py "$PAGE_ID"
pkill -f "chrome.*9222"
```

### Documentation

- **`SKILL.md`** – Agent-facing workflow instructions
- **`docs/guides/`** – User workflows and troubleshooting
- **`docs/reference/`** – CDP command reference and DOM APIs
- **`docs/development/`** – Contributor guidelines

</details>

---

## Why This Over chrome-dev-mcp?

This skill is designed as a **lightweight alternative** to chrome-dev-mcp for common browser debugging workflows:

- **Faster startup** – Direct CDP with minimal dependencies vs. full MCP server initialization
- **Simpler deployment** – Single skill installation vs. MCP server + client configuration
- **Focused scope** – Optimized for quick telemetry capture (DOM, console, network) rather than comprehensive browser automation
- **Token efficient** – Structured output designed for AI consumption without MCP protocol overhead

Choose chrome-dev-mcp when you need comprehensive browser automation capabilities. Choose this skill when you need quick, focused browser inspection integrated with Claude Code.

---

Ready to integrate browser debugging with Claude? Install the skill and start capturing DOM, console, and network data directly in your conversations.
