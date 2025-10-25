# Browser Debugger Scripts

This directory contains all executable scripts for the Browser Debugger skill, organized by function.

## Organization

Scripts are organized into functional categories:

- **cdp/** - Python CDP client library with CLI, connection management, and collectors
- **core/** - Chrome process management (chrome-launcher.sh)
- **utilities/** - Helper tools and session management

## Python CDP Package (`scripts/cdp/`)

The main interface for all CDP operations. Use via `python3 -m scripts.cdp.cli.main` or the `cdp` command after installation.

### CLI Commands

| Command | Purpose | Usage |
|---------|---------|-------|
| **session** | List and inspect Chrome targets | `cdp session list [--type page\|worker] [--url-filter PATTERN]` |
| **eval** | Execute JavaScript in a target | `cdp eval --url example.com "document.title"` |
| **dom** | Extract DOM from a page | `cdp dom dump --url example.com --output dom.html` |
| **console** | Stream console logs | `cdp console stream --url example.com --duration 30` |
| **network** | Record network activity | `cdp network record --url example.com --duration 30 --output network.jsonl` |
| **orchestrate** | Run automated debugging workflow | `cdp orchestrate headless https://example.com --console --network` |
| **query** | Execute arbitrary CDP command | `cdp query --url example.com --method Runtime.evaluate --params '{"expression":"2+2"}'` |

### Quick Examples

```bash
# List all page targets
python3 -m scripts.cdp.cli.main session list --type page

# Execute JavaScript
python3 -m scripts.cdp.cli.main eval --url https://example.com "document.title"

# Extract DOM
python3 -m scripts.cdp.cli.main dom dump --url https://example.com --output dom.html

# Stream console logs for 30 seconds
python3 -m scripts.cdp.cli.main console stream --url https://example.com --duration 30

# Record network activity
python3 -m scripts.cdp.cli.main network record --url https://example.com --duration 30 --output network.jsonl

# Full orchestrated workflow (headless)
python3 -m scripts.cdp.cli.main orchestrate headless https://example.com \
  --console --network --summary both

# Interactive debugging (headed mode)
python3 -m scripts.cdp.cli.main orchestrate headed http://localhost:3000 --console
```

### Installation

After running `./install.sh`, the CLI is available as `cdp`:

```bash
# Shorter command after installation
cdp session list --type page
cdp eval --url example.com "document.title"
cdp orchestrate headless https://example.com --console --network
```

---

## Chrome Launcher (`scripts/core/chrome-launcher.sh`)

Launches Chrome with CDP debugging and returns a JSON contract with WebSocket URL, PID, and profile path.

**Key Features:**
- Auto-detects Chrome 136+ and applies `--user-data-dir` requirement
- Supports both headed (visible browser) and headless modes
- Returns structured JSON with `ws_url`, `chrome_pid`, `profile_path`, `status`
- Handles port conflicts and profile lock issues

**Usage:**
```bash
# Headed mode (visible browser)
./scripts/core/chrome-launcher.sh "https://example.com" --mode=headed

# Headless mode (automated testing)
./scripts/core/chrome-launcher.sh "https://example.com" --mode=headless

# Custom port
./scripts/core/chrome-launcher.sh "https://example.com" --port=9223
```

**Output:** JSON contract with WebSocket URL and process info

---

## Utilities (`scripts/utilities/`)

Helper scripts for session management, cleanup, and state extraction.

| Script | Purpose | Usage |
|--------|---------|-------|
| **cdp-query.sh** | Execute ad-hoc CDP commands via WebSocket | `./scripts/utilities/cdp-query.sh <ws-url> <cdp-command> [args...]` |
| **cleanup-chrome.sh** | Kill Chrome processes on debugging port | `./scripts/utilities/cleanup-chrome.sh [--port=9222]` |
| **save-session.sh** | Save Chrome debugging session for later resume | `./scripts/utilities/save-session.sh <session-name> [--port=9222]` |
| **resume-session.sh** | Resume saved debugging session | `./scripts/utilities/resume-session.sh <session-name>` |
| **extract-state.sh** | Extract application state from Redux store | `./scripts/utilities/extract-state.sh <url> <output-dir> [--timeout=60]` |
| **inject-redux.js** | Inject Redux store exposure script into page | `cat scripts/utilities/inject-redux.js \| websocat -n1 "$WS_URL"` |
| **parse-redux-logs.py** | Parse Redux state timeline from console logs | `python3 scripts/utilities/parse-redux-logs.py <log-file> [-o output.json]` |

### cleanup-chrome.sh

Forcefully terminate Chrome processes on the debugging port. Use when Chrome hangs or port is locked.

```bash
# Clean up default port 9222
./scripts/utilities/cleanup-chrome.sh

# Clean up custom port
./scripts/utilities/cleanup-chrome.sh --port=9223
```

### cdp-query.sh

Execute one-off CDP commands without Python. Useful for quick queries.

```bash
# Get WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

# Evaluate JavaScript
./scripts/utilities/cdp-query.sh "$WS_URL" "Runtime.evaluate" \
  --expression "document.title"
```

### extract-state.sh

Extract application state from Redux stores in React applications.

```bash
./scripts/utilities/extract-state.sh "http://localhost:3000/app" /tmp/state-output --timeout=60
```

---

## Quick Reference

### Typical Workflow

```bash
# 1. Orchestrated workflow (recommended)
python3 -m scripts.cdp.cli.main orchestrate \
  --url https://example.com \
  --console \
  --network \
  --summary both \
  --output /tmp/debug

# 2. Manual step-by-step
# Launch Chrome
./scripts/core/chrome-launcher.sh "https://example.com" --mode=headless

# Stream console
python3 -m scripts.cdp.cli.main console stream --url https://example.com --duration 30

# Record network
python3 -m scripts.cdp.cli.main network record --url https://example.com --duration 30

# Extract DOM
python3 -m scripts.cdp.cli.main dom dump --url https://example.com --output dom.html

# Cleanup
./scripts/utilities/cleanup-chrome.sh
```

### Interactive Debugging (Headed Mode)

```bash
# Launch visible browser for manual interaction
python3 -m scripts.cdp.cli.main orchestrate headed http://localhost:3000 \
  --console \
  --duration 600

# After user interaction, extract DOM
python3 -m scripts.cdp.cli.main dom dump \
  --url http://localhost:3000 \
  --output /tmp/dom-after-interaction.html
```

### Port Conflicts

```bash
# Check if port is in use
lsof -i :9222

# Force cleanup
./scripts/utilities/cleanup-chrome.sh

# Use alternative port
python3 -m scripts.cdp.cli.main orchestrate --port 9223 --url https://example.com
```

---

## Documentation

For detailed workflow examples, troubleshooting, and CDP command reference:

- **[SKILL.md](../SKILL.md)** - Main skill documentation
- **[docs/guides/workflows.md](../docs/guides/workflows.md)** - Detailed workflow patterns
- **[docs/guides/troubleshooting.md](../docs/guides/troubleshooting.md)** - Error handling and edge cases
- **[docs/reference/cdp-commands.md](../docs/reference/cdp-commands.md)** - CDP command reference
- **[docs/guides/chrome-136-incident.md](../docs/guides/chrome-136-incident.md)** - Chrome 136+ requirements

---

**Last Updated:** 2025-10-25 (Post-migration cleanup: Python-first architecture)
