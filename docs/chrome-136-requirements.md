# Chrome 136+ Requirements

## Overview

Chrome 136+ (released March 2025) introduced a security policy change that requires `--user-data-dir` for CDP (Chrome DevTools Protocol) access in headed mode. This document explains the requirement, why it exists, and how to comply.

## The Requirement

⚠️ **Chrome 136+ blocks CDP access to default profiles for security reasons.**

When launching Chrome with `--remote-debugging-port` in headed mode, you **must** also specify `--user-data-dir` with an isolated profile path.

## Correct Usage

### ✅ CORRECT - Chrome 136+ Compatible

```bash
# Using environment variable for clarity
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL

# Using explicit absolute path
chrome --user-data-dir="/Users/username/.chrome-debug-profile" --remote-debugging-port=9222 URL

# Using scripts/core/chrome-launcher.sh (automatic handling)
./scripts/core/chrome-launcher.sh --mode=headed --url="https://example.com" --port=9222

# Using scripts/core/debug-orchestrator.sh (automatic handling)
./scripts/core/debug-orchestrator.sh "https://example.com" --mode=headed --include-console
```

### ❌ INCORRECT - CDP Blocked

```bash
# Missing --user-data-dir (Chrome 136+ blocks CDP)
chrome --remote-debugging-port=9222 URL

# Tilde not expanded inside flag value
chrome --user-data-dir=~/.chrome-debug-profile --remote-debugging-port=9222 URL
```

## Security Rationale

**Why this change was made:**

Chrome 136+ blocks CDP access to your default user profile to prevent cookie and credential theft. This is a security measure to protect users from malicious tools that could steal:

- Saved passwords
- Session cookies
- Authentication tokens
- Browsing history
- Cached credentials

By requiring an isolated profile via `--user-data-dir`, Chrome ensures that CDP debugging tools cannot access sensitive data from your primary browser profile.

## Technical Details

**What happens without `--user-data-dir`:**

1. Chrome 136+ **silently ignores** `--remote-debugging-port` when using the default profile
2. The WebSocket connection succeeds (you get a WebSocket URL)
3. Chrome **never responds** to CDP commands (infinite hang with no error message)
4. No error is logged - the connection just times out

**Why the isolated profile works:**

Using `--user-data-dir` creates or uses a separate Chrome profile that:
- Contains no existing passwords or cookies
- Is isolated from your default profile
- Can safely enable CDP debugging
- Persists at the specified path for reuse

## Verification Commands

### Check Chrome Version

```bash
chrome --version
# Expected output: Google Chrome 136.x.xxxx.x or higher
```

### Verify CDP Is Accessible

```bash
# 1. Launch Chrome with isolated profile
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 https://example.com &

# 2. Wait for Chrome to start
sleep 2

# 3. Verify CDP endpoint responds
curl -s http://localhost:9222/json | jq

# Expected: JSON array with page information including webSocketDebuggerUrl
```

### Test WebSocket Connection

```bash
# 1. Get WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

# 2. Test basic CDP command
echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq

# Expected: {"id":1,"result":{"protocolVersion":"1.3","product":"Chrome/136.x.xxxx.x",...}}
```

### Test DOM Extraction

```bash
# Get WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

# Extract page title (quick test)
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Expected: The page title (e.g., "Example Domain")
```

## Automated Handling

All browser-debugger scripts handle Chrome 136+ requirements automatically:

### scripts/core/chrome-launcher.sh

```bash
./scripts/core/chrome-launcher.sh --mode=headed --url="https://example.com"
```

**What it does:**
- Detects Chrome version automatically
- Creates isolated profile at `$HOME/.chrome-debug-profile`
- Launches Chrome with correct flags
- Returns JSON with WebSocket URL and profile path

### scripts/core/debug-orchestrator.sh

```bash
./scripts/core/debug-orchestrator.sh "https://example.com" --mode=headed --include-console
```

**What it does:**
- Uses scripts/core/chrome-launcher.sh internally
- Handles profile creation and cleanup
- No manual flag management required
- Compatible with Chrome 136+ by default

## Troubleshooting

### Issue: Chrome hangs indefinitely, no response to CDP commands

**Symptoms:**
- `curl http://localhost:9222/json` returns valid JSON
- WebSocket URL is present
- CDP commands never respond (infinite hang)
- No error messages in Chrome output

**Diagnosis:**
```bash
# Check if you forgot --user-data-dir
ps aux | grep chrome | grep remote-debugging-port

# If you see ONLY --remote-debugging-port without --user-data-dir, that's the issue
```

**Solution:**
```bash
# Kill Chrome
pkill -f "chrome.*9222"

# Relaunch with isolated profile
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL
```

### Issue: "Profile in use" error

**Symptoms:**
```
The profile appears to be in use by another Google Chrome process
```

**Solution:**
```bash
# Kill all Chrome processes using that profile
pkill -f "chrome.*chrome-debug-profile"

# Or use a different profile path
chrome --user-data-dir="/tmp/chrome-debug-$(date +%s)" --remote-debugging-port=9222 URL
```

### Issue: Tilde (~) not expanded in --user-data-dir

**Symptoms:**
Chrome creates a directory literally named `~` in the current directory.

**Solution:**
```bash
# ❌ WRONG - tilde inside quotes/flag value not expanded
chrome --user-data-dir=~/.chrome-debug-profile --remote-debugging-port=9222 URL

# ✅ CORRECT - use $HOME instead
chrome --user-data-dir="$HOME/.chrome-debug-profile" --remote-debugging-port=9222 URL

# ✅ CORRECT - expand tilde with variable
PROFILE="$HOME/.chrome-debug-profile"
chrome --user-data-dir="$PROFILE" --remote-debugging-port=9222 URL
```

## Reference

- **Incident Report:** `docs/headed-mode/CHROME-136-CDP-INCIDENT.md`
- **Launcher Contract:** `docs/headed-mode/LAUNCHER_CONTRACT.md`
- **Smoke Test:** `tests/smoke-test-headed.sh`

## Version History

**Chrome 135 and earlier:** `--user-data-dir` was optional for CDP access

**Chrome 136+ (March 2025):** `--user-data-dir` with isolated profile is **required** for CDP access in headed mode

**Note:** Headless mode (`--headless=new`) is not affected by this change.
