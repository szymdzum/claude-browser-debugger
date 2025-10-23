# Browser Debugger Skill for Claude Code

Debug websites using Chrome headless and Chrome DevTools Protocol. Extract DOM, monitor console logs, and track network requests.

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

## What gets installed

```
~/.claude/skills/browser-debugger/
├── SKILL.md           # Skill instructions
├── cdp-console.py     # Console monitoring
└── cdp-network.py     # Network monitoring
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
python3 ~/.claude/skills/browser-debugger/cdp-console.py $PAGE_ID

# Cleanup
pkill -f "chrome.*9222"
```

## Capabilities

### Extract DOM
Get the fully rendered HTML structure after JavaScript execution.

### Monitor Console
Capture JavaScript logs, errors, warnings, and exceptions in real-time.

### Track Network
Monitor HTTP requests, responses, and failures.

## Files

- `SKILL.md` - Core skill documentation (Claude reads this)
- `cdp-console.py` - Console monitoring via WebSocket
- `cdp-network.py` - Network monitoring via WebSocket
- `install.sh` - Automated installer
- `README.md` - This file

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

## Uninstall

```bash
rm -rf ~/.claude/skills/browser-debugger
```

## Documentation

See `SKILL.md` for complete instructions and examples.
