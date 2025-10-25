# Chrome Launcher Contract

This document defines the interface contract between `chrome-launcher.sh` and the Python orchestrator.

## Purpose

`chrome-launcher.sh` is responsible for starting Chrome with debugging enabled and returning connection information. It fails fast with actionable errors rather than implementing retry logic.

## Command Line Interface

```bash
./chrome-launcher.sh --mode=<MODE> --port=<PORT> --profile=<PROFILE> --url=<URL>
```

### Required Arguments

- `--mode=<headless|headed>`
  - `headless`: Chrome runs without UI (existing behavior)
  - `headed`: Chrome runs with visible window (new feature)

### Optional Arguments

- `--port=<number|auto>` (default: `9222`)
  - Specific port number (e.g., `9222`)
  - `auto`: Find first free port in range 9222-9299

- `--profile=<path|none>` (default: mode-dependent)
  - Custom path to Chrome profile directory
  - `none`: Use ephemeral temp directory
  - Default for `headless`: `/tmp/chrome-headless-$PID`
  - Default for `headed`: `~/.chrome-debug-profile`

- `--url=<url>` (default: `about:blank`)
  - Initial page to load

## Output Format

All output goes to **stdout** as a **single line of JSON**.

### Success Response

```json
{
  "status": "success",
  "port": 9222,
  "pid": 12345,
  "page_id": "E4F5D6C7-8A9B-4C3D-2E1F-0A1B2C3D4E5F",
  "profile": "/Users/username/.chrome-debug-profile",
  "ws_url": "ws://localhost:9222/devtools/page/E4F5D6C7-8A9B-4C3D-2E1F-0A1B2C3D4E5F"
}
```

### Error Response

```json
{
  "status": "error",
  "code": "PORT_BUSY",
  "message": "Port 9222 is already in use by PID 54321",
  "recovery": "pkill -f 'chrome.*9222' && sleep 1"
}
```

## Error Codes

| Code | Exit Status | Trigger | Recovery Command |
|------|-------------|---------|------------------|
| `CHROME_NOT_FOUND` | 1 | Chrome binary not found | `brew install google-chrome` (macOS) |
| `PORT_BUSY` | 2 | Debugging port already bound | `pkill -f "chrome.*9222"` or use `--port=auto` |
| `PORT_RANGE_EXHAUSTED` | 2 | All ports 9222-9299 busy | `pkill -f "chrome.*922[0-9]"` |
| `PROFILE_LOCKED` | 3 | Profile directory locked | `rm -rf ~/.chrome-debug-profile/SingletonLock` |
| `PROFILE_PERMISSION` | 3 | Can't create profile directory | `mkdir -p ~/.chrome-debug-profile && chmod 755 ~/.chrome-debug-profile` |
| `WEBSOCKET_FAILED` | 4 | CDP endpoint unreachable | Check if Chrome crashed: `ps aux \| grep $PID` |
| `PAGE_NOT_FOUND` | 4 | No page available after startup | Retry launch or check Chrome logs |
| `STARTUP_TIMEOUT` | 5 | Chrome didn't start within 10s | Check system resources: `top` |

## Implementation Requirements

### Chrome Binary Detection

```bash
# macOS
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome

# Linux (try in order)
google-chrome
google-chrome-stable
chromium-browser
chromium
```

### Port Detection Strategy

1. If `--port=<number>`:
   - Check if port is free using `lsof -i :<port>`
   - If busy: return `PORT_BUSY` error with PID
   - If free: use that port

2. If `--port=auto`:
   - Iterate ports 9222-9299
   - Find first free port
   - If all busy: return `PORT_RANGE_EXHAUSTED`

### Profile Handling

| Mode | Profile Argument | Actual Path |
|------|------------------|-------------|
| `headless` | (default) | `/tmp/chrome-headless-$$` |
| `headless` | `--profile=none` | `/tmp/chrome-headless-$$` |
| `headed` | (default) | `~/.chrome-debug-profile` |
| `headed` | `--profile=/custom/path` | `/custom/path` |
| Any | `--profile=none` | `/tmp/chrome-headless-$$` |

### Startup Sequence

1. Detect Chrome binary path
2. Resolve port (check availability or auto-detect)
3. Resolve profile path
4. Start Chrome with flags:
   ```bash
   "$CHROME" \
     $([ "$MODE" = "headless" ] && echo "--headless=new") \
     --remote-debugging-port=$PORT \
     --user-data-dir="$PROFILE" \
     --no-first-run \
     --no-default-browser-check \
     "$URL" &
   ```
5. Wait up to 10 seconds for debugging endpoint
6. Poll `http://localhost:$PORT/json` until available
7. Extract first page ID where `type == "page"`
8. Output success JSON
9. Exit with code 0

### Cleanup

The launcher does **not** clean up Chrome processes. That is the orchestrator's responsibility. The launcher only:
- Starts Chrome
- Verifies it's running
- Returns connection info

## Example Usage

### Orchestrator calling launcher

```bash
# Call launcher
LAUNCHER_OUTPUT=$(./chrome-launcher.sh \
  --mode=headed \
  --port=auto \
  --url="http://localhost:3000/signin")

# Parse output
STATUS=$(echo "$LAUNCHER_OUTPUT" | jq -r '.status')

if [ "$STATUS" = "error" ]; then
  CODE=$(echo "$LAUNCHER_OUTPUT" | jq -r '.code')
  MESSAGE=$(echo "$LAUNCHER_OUTPUT" | jq -r '.message')
  RECOVERY=$(echo "$LAUNCHER_OUTPUT" | jq -r '.recovery')

  echo "Error: $CODE - $MESSAGE"
  echo "Recovery: $RECOVERY"
  exit 1
fi

# Extract connection info
PORT=$(echo "$LAUNCHER_OUTPUT" | jq -r '.port')
PAGE_ID=$(echo "$LAUNCHER_OUTPUT" | jq -r '.page_id')
CHROME_PID=$(echo "$LAUNCHER_OUTPUT" | jq -r '.pid')

# Pass to CLI collectors
python3 -m scripts.cdp.cli.main console stream --target "$PAGE_ID" --chrome-port "$PORT" --duration 30
```

## Testing Error Conditions

```bash
# Test PORT_BUSY
nc -l 9222 &  # Occupy port
./chrome-launcher.sh --mode=headless --port=9222
# Expected: {"status":"error","code":"PORT_BUSY",...}

# Test PORT_RANGE_EXHAUSTED
for port in {9222..9299}; do nc -l $port & done
./chrome-launcher.sh --mode=headless --port=auto
# Expected: {"status":"error","code":"PORT_RANGE_EXHAUSTED",...}

# Test CHROME_NOT_FOUND
PATH=/usr/bin ./chrome-launcher.sh --mode=headless
# Expected: {"status":"error","code":"CHROME_NOT_FOUND",...}

# Test PROFILE_LOCKED
mkdir -p ~/.chrome-debug-profile
touch ~/.chrome-debug-profile/SingletonLock
chmod 000 ~/.chrome-debug-profile/SingletonLock
./chrome-launcher.sh --mode=headed
# Expected: {"status":"error","code":"PROFILE_LOCKED",...}
```

## Logging

- All **diagnostic messages** go to **stderr**
- Only **JSON output** goes to **stdout**
- This allows orchestrator to parse stdout while showing stderr to user

Example:
```bash
echo "Detecting Chrome binary..." >&2
echo "Starting Chrome on port 9222..." >&2
echo '{"status":"success",...}' >&1
```
