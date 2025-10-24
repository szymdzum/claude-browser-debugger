# Browser Debugger Skill for Claude Code

Provide quick website telemetry directly to Claude Code CLI using native Chrome DevTools Protocol via WebSocket—no MCP overhead. Capture token-efficient DOM snapshots, console logs, and network requests for instant context during debugging workflows. Launch headless Chrome for automated capture or headed mode to interact with the page manually, then extract console, network, or DOM state to validate.

## Why This Exists

- Provides a lightweight alternative to Chrome Dev MCP for gathering quick page context without burning large MCP token budgets.
- Avoids heavier stacks like Selenium; depends only on a local headless Chrome session and the CDP websocket.
- Focuses on the essentials agents usually need: rendered DOM, console output, and network traffic.
- Intended as a complementary tool—keep Chrome Dev MCP for deep, interactive debugging, but reach for this when you just need fast telemetry to answer a question.

## Quick Install

```bash
# Recommended: Symlink mode (easy updates)
./install.sh --symlink

# Alternative: Copy mode (standalone)
./install.sh --copy
```

This installs the skill to `~/.claude/skills/browser-debugger/`

## Installation Modes

| Mode | Command | Best For | Updates |
|------|---------|----------|---------|
| **Symlink** | `./install.sh --symlink` | Developers who maintain the skill | `git pull` |
| **Copy** | `./install.sh --copy` | Stable installations | Re-run installer |

### Symlink Mode (Recommended)
- Links `~/.claude/skills/browser-debugger` → this directory
- Changes sync immediately
- Perfect for version-controlled installations
- Use when you maintain the skill

### Copy Mode
- Copies files to `~/.claude/skills/browser-debugger`
- Standalone installation
- Use when you want a stable, immutable version

## Prerequisites

- Python 3.7+
- `websockets` library: `pip3 install websockets --break-system-packages`
- Chrome or Chromium
- `jq`: `brew install jq` (macOS) or `apt-get install jq` (Linux)
- `websocat` (optional CLI for ad-hoc CDP commands): `brew install websocat`

## Usage

Start Claude Code and ask questions like:

```
Debug https://example.com
```

```
Check https://example.com for JavaScript errors
```

```
What API calls does https://example.com make?
```

Claude will automatically use this skill when appropriate.

### Orchestrator options at a glance

- `--summary=json|both` adds structured output; `json` emits machine-readable data only, `both` keeps the human summary too.
- `--include-console` launches the console monitor alongside network capture, merging error counts into the summary (log file defaults to `<output>-console.log`, override with `--console-log=...`).
- `--idle=<seconds>` stops as soon as Chrome has been quiet for the given period, so you can capture long pages without guessing a timeout.

## What gets installed

```
~/.claude/skills/browser-debugger/
├── SKILL.md                     # Agent-facing instructions (updated for headed mode + Chrome 136 policy)
├── README.md                    # Maintainer guide
├── scripts/
│   ├── core/
│   │   ├── chrome-launcher.sh          # Smart launcher (headed/headless, profile isolation, JSON contract)
│   │   └── debug-orchestrator.sh       # Top-level workflow with summaries and mode selection
│   ├── collectors/
│   │   ├── cdp-console.py              # Console monitor (configurable port, idle timeout)
│   │   ├── cdp-network.py              # Network monitor
│   │   ├── cdp-network-with-body.py    # Network monitor with selective response bodies
│   │   ├── cdp-dom-monitor.py          # DOM/form-field change monitor
│   │   └── cdp-summarize.py            # Shared post-run summariser
│   └── utilities/
│       ├── cdp-query.sh                # Ad-hoc CDP command execution
│       ├── cleanup-chrome.sh           # Clean Chrome debug sessions
│       ├── save-session.sh             # Save debugging session state
│       └── resume-session.sh           # Resume saved session
└── install.sh                   # Installer script
```

## Manual testing

Test the skill without Claude:

```bash
# Get DOM
chrome --headless=new --dump-dom https://example.com

# Monitor console
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
python3 ~/.claude/skills/browser-debugger/scripts/collectors/cdp-console.py $PAGE_ID

# Cleanup
pkill -f "chrome.*9222"
```

### Ad-hoc CDP commands with websocat

For live DOM extraction or one-off commands, talk directly to Chrome’s WebSocket endpoint:

```bash
# Launch Chrome (or use debug-orchestrator.sh)

# Discover the WebSocket debugger URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

# Grab the fully hydrated DOM
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/live-dom.html

# Other expressions work too—document title, cookies, screenshots, etc.
```

Notes:
- `-B 1048576` bumps the buffer to 1 MB so large pages don’t truncate.
- Swap the expression to run anything in the page context:
  ```bash
  echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
    | websocat -n1 "$WS_URL"
  ```
- For screenshots, use `Page.captureScreenshot` and base64‑decode the result.
- Headed sessions launched via `scripts/core/chrome-launcher.sh` already set `--user-data-dir`, which Chrome 136+ requires for CDP.

## Capabilities

- **Headless & headed Chrome support** (headed mode uses an isolated profile so Chrome 136+ keeps answering CDP calls).
- **DOM snapshots & live form monitoring** via `scripts/collectors/cdp-dom-monitor.py`.
- **Console + network capture** with idle detection and optional response bodies.
- **Smart orchestration**: `scripts/core/debug-orchestrator.sh` launches Chrome, hands off to collectors, aggregates results, and emits recovery hints when launch fails.
- **Chrome 136+ compatible**: Automatically handles `--user-data-dir` requirement for headed mode.

## Files

- `scripts/core/chrome-launcher.sh` – launches Chrome in headless/headed modes, returns JSON contract, enforces `--user-data-dir`.
- `scripts/core/debug-orchestrator.sh` – wraps the launcher, starts collectors, summarises output.
- `scripts/collectors/cdp-console.py`, `scripts/collectors/cdp-network.py`, `scripts/collectors/cdp-network-with-body.py` – CDP collectors (shared with orchestrator).
- `scripts/collectors/cdp-dom-monitor.py` – live DOM/form-field watcher.
- `scripts/collectors/cdp-summarize.py` – shared summary formatter.
- `scripts/utilities/` – helper scripts for session management and cleanup.
- `SKILL.md` – agent-facing skill guide with comprehensive workflow documentation.
- `README.md`, `install.sh` – maintainer info and installer.

## Troubleshooting

### websockets not found
```bash
pip3 install websockets --break-system-packages
```

### jq not found
```bash
brew install jq  # macOS
sudo apt-get install jq  # Linux
```

### Port 9222 in use
```bash
pkill -f "chrome.*9222"
```

## Spec-Kit Integration

This project uses [GitHub Spec-Kit](https://github.com/github/spec-kit) for spec-driven development. Spec-Kit provides structured workflows for creating specifications, plans, and tasks before implementation.

### Available Spec-Kit Commands

Use these slash commands in Claude Code:

**Core Workflow:**
- `/speckit.constitution` - Establish project principles and development guidelines
- `/speckit.specify` - Create functional specifications
- `/speckit.plan` - Create technical architecture aligned with your stack
- `/speckit.tasks` - Generate actionable task breakdowns
- `/speckit.implement` - Execute implementation systematically

**Optional Enhancements:**
- `/speckit.clarify` - Resolve ambiguous requirements before planning
- `/speckit.analyze` - Validate cross-artifact consistency
- `/speckit.checklist` - Generate quality validation checklists

### Spec-Kit Files

- `.claude/commands/speckit.*.md` - Slash command definitions
- `.specify/templates/` - Document templates for specs, plans, and tasks
- `.specify/scripts/bash/` - Helper scripts for spec-driven workflows
- `.specify/memory/` - Generated specifications and project artifacts (gitignored)

## Uninstall

```bash
rm -rf ~/.claude/skills/browser-debugger
```

## Testing

Test the skill manually after updating Chrome:

```bash
# Test headed Chrome launch
./scripts/core/debug-orchestrator.sh "https://example.com" --mode=headed --include-console

# Verify Chrome responds to CDP commands
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"2+2","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq

# Expected: {"id":1,"result":{"result":{"type":"number","value":4}}}

# Cleanup
pkill -f "chrome.*9222"
```

This verifies Chrome version detection, `--user-data-dir` behaviour, Runtime.evaluate functionality, and DOM access.
