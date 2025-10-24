# Browser Debugger Skill for Claude Code

Give Claude Code instant access to live website telemetry:DOM snapshots, console errors, and network requests directly through Chrome DevTools Protocol. No MCP overhead, just fast, token-efficient debugging context when you need it.

## What This Does

Ask Claude to debug a website, and this skill automatically:

- **Captures the rendered DOM** - See exactly what the browser rendered, not just the source HTML
- **Monitors JavaScript console** - Catch errors, warnings, and log messages in real-time
- **Tracks network activity** - Inspect API calls, failed requests, and response data
- **Works both ways** - Automated headless capture or interactive headed mode for manual testing

## Usage Scenarios

### Scenario 1: Quick DOM Snapshot (Headless)
```
Use browser-debugger skill to capture the DOM of http://localhost:3000 in headless mode
with a 5 second idle timeout. Include console logs and provide a summary.
```

**Expected workflow:** Launch headless Chrome → Wait for page load → Capture DOM + console → Generate summary → Cleanup

---

### Scenario 2: Interactive Registration Flow (Headed)
```
Use browser-debugger skill to launch http://localhost:3000/customer/register in headed mode.
Let me fill out the registration form manually, then extract the DOM and console logs after I'm done.
```

**Expected workflow:** Launch visible Chrome → User fills form → Agent waits → Extract DOM on demand → Keep Chrome open for follow-up

---

### Scenario 3: Sign-In Flow with Network Monitoring
```
Launch http://localhost:3000/signin with browser-debugger in headed mode. Monitor network
requests and console logs while I test the login flow. After I submit the form, capture everything.
```

**Expected workflow:** Launch with console/network collectors → User interacts → Agent captures network traffic → Extract final state

---

### Scenario 4: Multi-Step User Journey
```
Use browser-debugger to help me debug the checkout flow on localhost:3000. Start at the homepage,
let me navigate to the product page, add to cart, and proceed to checkout. Capture the DOM at each
major step when I tell you.
```

**Expected workflow:** Persistent Chrome session → Multiple DOM extractions → Agent responds to "capture now" prompts

## Quick Start

### Install

```bash
# Recommended: Symlink mode (easy updates)
./install.sh --symlink

# Alternative: Copy mode (standalone)
./install.sh --copy
```

### Prerequisites

- Python 3.7+ with `websockets` library: `pip3 install websockets --break-system-packages`
- Chrome or Chromium browser
- `jq` for JSON parsing: `brew install jq` (macOS) or `apt-get install jq` (Linux)

### Use It

See the [Usage Scenarios](#usage-scenarios) section above for detailed examples. In general, just ask Claude naturally:

- "Debug https://example.com"
- "Check localhost:3000 for JavaScript errors"
- "Launch localhost:3000/signin in headed mode and let me test the login flow"

Claude automatically invokes the skill when appropriate.

## Why Use This?

**Lightweight telemetry** - Skip the heavyweight MCP stacks when you just need quick page context. Native Chrome DevTools Protocol over WebSocket keeps overhead minimal.

**Fast answers** - Get rendered DOM, console logs, and network traffic in seconds without complex setup or large token budgets.

**Flexible workflows** - Headless mode for automated capture or headed mode to interact with the page manually before extraction.

**Chrome 136+ compatible** - Automatically handles modern Chrome security requirements (profile isolation for CDP access).

## Usage Examples

### Automated Debugging (Headless)

Claude runs this automatically, but you can test manually:

```bash
# Full diagnostic capture with console monitoring
./scripts/core/debug-orchestrator.sh "https://example.com" 15 /tmp/output.log \
  --include-console --summary=both --idle=3
```

This captures:
- Network requests (method, URL, status, timing)
- Console logs (errors, warnings, info)
- Structured summary (JSON + human-readable)
- Automatic idle detection (stops when page settles)

### Interactive Debugging (Headed)

Launch visible Chrome for manual interaction:

```bash
# Start Chrome with debugging enabled
./scripts/core/debug-orchestrator.sh "http://localhost:3000/signin" \
  --mode=headed --include-console
```

Now you can:
1. Click through the page manually
2. Fill out forms
3. Trigger JavaScript interactions
4. Extract the final DOM state when ready

Perfect for debugging authentication flows, dynamic content, or complex SPAs.

### Quick DOM Snapshot

```bash
chrome --headless=new --dump-dom https://example.com > page.html
```

Simple, fast, no ceremony.

## What You Get

After installation, the skill is available at `~/.claude/skills/browser-debugger/`:

**Core Scripts:**
- Smart Chrome launcher (headless/headed with automatic profile isolation)
- Workflow orchestrator (manages collectors, generates summaries)
- CDP collectors for console, network, and DOM monitoring
- Session utilities for cleanup and state management

**Documentation:**
- `SKILL.md` - Comprehensive agent-facing instructions with examples
- Troubleshooting guides for common Chrome and CDP issues

## Installation Modes

| Mode | Best For | How Updates Work |
|------|----------|------------------|
| **Symlink** | Active development | `git pull` syncs immediately |
| **Copy** | Stable installations | Re-run installer to update |

**Symlink mode** (recommended for most users):
- Links `~/.claude/skills/browser-debugger` to this repository
- Changes sync automatically when you update the repo
- Perfect for version-controlled skill development

**Copy mode**:
- Creates standalone installation in `~/.claude/skills/browser-debugger`
- No external dependencies after installation
- Use when you want a frozen, stable version

## Common Use Cases

**Debugging JavaScript errors** - See exactly what console errors fire and when

**Inspecting API calls** - Track all network requests with timing and status codes

**Validating form submissions** - Monitor network traffic when forms POST data

**Checking authentication flows** - Use headed mode to log in manually, then extract DOM

**Analyzing SPA routing** - Capture DOM state after JavaScript renders the page

**Testing responsive layouts** - Extract DOM at different viewport sizes

## Troubleshooting

**Missing `websockets` library:**
```bash
pip3 install websockets --break-system-packages
```

**Missing `jq`:**
```bash
brew install jq  # macOS
sudo apt-get install jq  # Linux
```

**Port 9222 already in use:**
```bash
pkill -f "chrome.*9222"
```

**Chrome version issues:**
This skill automatically handles Chrome 136+ security requirements. If you encounter CDP access issues, check `docs/guides/troubleshooting.md` for detailed guidance.

## Advanced Usage

### Custom Timeouts and Idle Detection

```bash
# Stop after 3 seconds of inactivity (smart detection)
./scripts/core/debug-orchestrator.sh "https://example.com" --idle=3

# Fixed 30-second timeout
./scripts/core/debug-orchestrator.sh "https://example.com" 30 /tmp/out.log
```

### Capture Response Bodies

```bash
# Include response bodies for failed requests
./scripts/core/debug-orchestrator.sh "https://example.com" \
  --include-console \
  --network-script=cdp-network-with-body.py \
  --filter-status=error
```

### Session Management

```bash
# Save debugging session for later
./scripts/utilities/save-session.sh /tmp/debug-session

# Resume saved session
./scripts/utilities/resume-session.sh /tmp/debug-session
```

## Uninstall

```bash
rm -rf ~/.claude/skills/browser-debugger
```

---

## Technical Details

<details>
<summary>For maintainers and contributors (click to expand)</summary>

### Architecture

**Chrome Launcher** (`scripts/core/chrome-launcher.sh`):
- Launches Chrome in headless or headed mode
- Returns JSON contract with WebSocket URL, PID, and profile path
- Automatically enforces `--user-data-dir` for Chrome 136+ compatibility

**Debug Orchestrator** (`scripts/core/debug-orchestrator.sh`):
- High-level workflow coordinator
- Manages CDP collectors (console, network, DOM)
- Generates structured summaries
- Handles cleanup and error recovery

**CDP Collectors** (`scripts/collectors/`):
- `cdp-console.py` - Console log monitoring with idle detection
- `cdp-network.py` - Network request/response tracking
- `cdp-network-with-body.py` - Network capture with selective response bodies
- `cdp-dom-monitor.py` - Real-time DOM and form field change monitoring
- `cdp-summarize.py` - Post-capture summary generation

**Utilities** (`scripts/utilities/`):
- Session save/resume for complex debugging workflows
- Chrome cleanup for stuck debug sessions
- Ad-hoc CDP command execution via `cdp-query.sh`

### Manual Testing

Test the skill without Claude:

```bash
# Test headless DOM capture
chrome --headless=new --dump-dom https://example.com

# Test console monitoring
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
python3 ~/.claude/skills/browser-debugger/scripts/collectors/cdp-console.py $PAGE_ID
pkill -f "chrome.*9222"
```

### Chrome 136+ Compatibility

Chrome 136 (March 2025) introduced a security policy that blocks CDP access to default user profiles. This skill automatically handles this by using isolated profiles (`--user-data-dir`) for all headed mode sessions.

See `docs/guides/chrome-136-incident.md` for the full investigation and solution.

### Documentation

- `SKILL.md` - Agent-facing workflow guide
- `docs/guides/` - User-facing workflow and troubleshooting guides
- `docs/reference/` - Technical references (CDP commands, Chrome DOM API)
- `docs/development/` - Skill development best practices

</details>
