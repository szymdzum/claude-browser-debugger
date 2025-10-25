# Agent CLI Guide: How to Debug Websites with CDP

**Audience**: AI agents using this skill to inspect websites
**Purpose**: Educational guide explaining DOM/console/network monitoring workflows
**Last Updated**: 2025-10-25

---

## Overview

This guide explains how AI agents interact with the CDP (Chrome DevTools Protocol) CLI to inspect websites. Think of it as **a phone line to Chrome's brain** that lets you see what's happening inside a webpage.

### What You Can Do

- 📄 **Extract DOM** - Get the HTML structure of any page
- 📝 **Monitor Console** - Capture JavaScript logs and errors
- 🌐 **Track Network** - See all API calls and resource loads
- 🎭 **Orchestrate All Three** - Full debugging session with one command

---

## The Three Core Commands

### 1. DOM Extraction 🏗️

**Purpose**: Get the HTML structure of a webpage

**Command**:
```bash
python -m scripts.cdp.cli.main dom dump --url "https://example.com" --output /tmp/page.html
```

**What Happens**:
1. CLI connects to Chrome via WebSocket
2. Sends CDP command: `Runtime.evaluate` with JavaScript: `document.documentElement.outerHTML`
3. Chrome executes the JavaScript and returns the HTML
4. CLI saves it to `/tmp/page.html`

**Output** (`/tmp/page.html`):
```html
<!DOCTYPE html>
<html>
<head>
  <title>Example Domain</title>
</head>
<body>
  <h1>Example Domain</h1>
  <p>This domain is for use in illustrative examples...</p>
</body>
</html>
```

**Use Case**: Understanding page structure, finding form fields, locating elements

**Think of it as**: Taking a snapshot of the website's skeleton

---

### 2. Console Monitoring 📝

**Purpose**: Capture JavaScript logs, warnings, and errors

**Command**:
```bash
python -m scripts.cdp.cli.main console stream --url "https://example.com" --duration 30 --output /tmp/console.jsonl
```

**What Happens**:
1. CLI connects to Chrome via WebSocket
2. Subscribes to `Console.messageAdded` events
3. Listens for 30 seconds (or until Ctrl+C)
4. Every time JavaScript does `console.log()` or throws an error, Chrome sends an event
5. CLI writes each message to `/tmp/console.jsonl` (one JSON object per line)

**Output** (`/tmp/console.jsonl`):
```json
{"source": "console-api", "level": "log", "text": "App initialized", "timestamp": 1698234567.123}
{"source": "console-api", "level": "log", "text": "User clicked login button", "timestamp": 1698234568.456}
{"source": "javascript", "level": "error", "text": "Uncaught TypeError: Cannot read property 'x' of undefined", "timestamp": 1698234569.789, "url": "https://example.com/app.js", "lineNumber": 42}
{"source": "network", "level": "warning", "text": "CORS policy blocked request to https://api.example.com", "timestamp": 1698234570.012}
```

**Use Case**: Debugging JavaScript errors, understanding user interactions, finding CORS issues

**Think of it as**: Recording everything printed to the browser's developer console

---

### 3. Network Monitoring 🌐

**Purpose**: Track all HTTP requests and responses

**Command**:
```bash
python -m scripts.cdp.cli.main network record --url "https://example.com" --duration 30 --output /tmp/network.jsonl
```

**What Happens**:
1. CLI connects to Chrome via WebSocket
2. Subscribes to `Network.requestWillBeSent` and `Network.responseReceived` events
3. Listens for 30 seconds (or until Ctrl+C)
4. Every time the website makes a fetch/AJAX call or loads an image, Chrome sends events
5. CLI writes each request/response to `/tmp/network.jsonl`

**Output** (`/tmp/network.jsonl`):
```json
{"event": "request", "requestId": "1234.1", "url": "https://api.example.com/user", "method": "GET", "timestamp": 1698234567.123}
{"event": "response", "requestId": "1234.1", "url": "https://api.example.com/user", "status": 200, "mimeType": "application/json", "timestamp": 1698234567.456}
{"event": "request", "requestId": "1234.2", "url": "https://cdn.example.com/logo.png", "method": "GET", "timestamp": 1698234568.123}
{"event": "response", "requestId": "1234.2", "url": "https://cdn.example.com/logo.png", "status": 200, "mimeType": "image/png", "timestamp": 1698234568.234}
```

**Use Case**: Finding API endpoints, debugging AJAX failures, analyzing load performance

**Think of it as**: Wiretapping the website's phone calls to servers

---

## The Orchestrator (All-in-One) 🎭

**Purpose**: Capture DOM + console in a single automated session

**Command**:
```bash
python -m scripts.cdp.cli.main orchestrate headless "https://example.com" \
  --duration 30 \
  --include-console \
  --output-dir /tmp/debug-session/
```

**What Happens**:
1. CLI launches Chrome in headless mode with the URL
2. Starts console monitor in the background (if --include-console specified)
3. Waits for specified duration (or until you press Ctrl+C)
4. Extracts the final DOM state
5. Stops all monitors gracefully
6. Generates a summary report

**Output Files**:
```
/tmp/debug-session/
├── dom.html               # Final page structure
├── console.jsonl          # All console messages (if --include-console used)
└── summary.txt            # Human-readable summary
```

**Summary Example** (`/tmp/debug-session/summary.txt`):
```
=== Debugging Session Summary ===
URL: https://example.com
Duration: 30 seconds
Timestamp: 2025-10-25 18:30:45

Console Messages: 15 total
  - log: 12
  - warning: 2
  - error: 1

DOM: 1,234 elements extracted
```

**Note**: Network monitoring is available via the standalone `network record` command. To capture both console and network, run `orchestrate` with `--include-console` and `network record` in separate terminals.

**Use Case**: Automated website inspection, bug diagnosis, console error monitoring

**Think of it as**: An automated debugging session that captures state

---

## Interactive Mode (Headed) 🖥️

**Purpose**: Launch visible Chrome for manual interaction while monitoring

**Command**:
```bash
python -m scripts.cdp.cli.main orchestrate headed "http://localhost:3000/signin" \
  --include-console
```

**What Happens**:
1. CLI launches **visible Chrome window** (not headless)
2. Starts console monitor in background (if --include-console specified)
3. **You interact with the page manually** (click buttons, fill forms, navigate)
4. Monitor captures everything in the background
5. Press **Ctrl+C** when done
6. CLI extracts final DOM, stops monitor, generates summary

**Use Case**: Debugging login flows, testing interactive features, recording user sessions

**Cleanup on Ctrl+C**:
- Stops monitors with SIGTERM (graceful shutdown)
- Extracts final DOM automatically
- Generates summary report
- Displays all artifact locations
- Terminates Chrome cleanly

**Example Output**:
```
^C Signal received, stopping session...
✓ Console monitor stopped
✓ DOM extracted to /tmp/debug-session/dom.html
✓ Summary generated

Artifacts saved to:
  /tmp/debug-session/console.jsonl
  /tmp/debug-session/dom.html
  /tmp/debug-session/summary.txt
```

---

## How Type Annotations Help Agents

### Before Type Annotations ❌

**Agent workflow**:
1. Agent needs to know how to call `orchestrate`
2. Agent reads 200+ lines of Python implementation code 😓
3. Agent guesses argument types and defaults
4. Agent makes mistakes, has to retry

**Token cost**: High (reading implementation code)

### After Type Annotations ✅

**Agent workflow**:
1. Agent inspects function signature:
   ```python
   def orchestrate_handler(args: argparse.Namespace) -> int:
       """Run orchestrated debugging session."""
   ```
2. Agent sees: "Takes CLI arguments, returns exit code"
3. Agent checks CLI help:
   ```bash
   python -m scripts.cdp.cli.main orchestrate --help
   ```
4. Agent sees exact arguments and types
5. Agent constructs correct command immediately 🎉

**Token cost**: Low (reading type hints + help text)

**Token reduction**: ~30% (measured qualitatively in Feature 001)

---

## Type Hints in Action

### Example 1: Configuration File

**Agent wants to create a `.cdprc` config file**

**Without type hints**:
```python
# Agent has to guess...
config.chrome_port = ???  # String? Int? What's valid?
config.timeout = ???      # Seconds? Milliseconds?
```

**With type hints**:
```python
# Agent inspects Configuration class:
@dataclass
class Configuration:
    chrome_port: int = 9222       # Ah! Integer, default 9222
    timeout: float = 30.0          # Float in seconds
    max_size: int = 2_097_152      # Int in bytes
    log_level: str = "INFO"        # String: DEBUG/INFO/WARNING/ERROR
    log_format: str = "text"       # String: text/json
```

**Agent now writes correct config** (`~/.cdprc`):
```json
{
  "chrome_port": 9222,
  "timeout": 45.0,
  "max_size": 4194304,
  "log_level": "DEBUG",
  "log_format": "json"
}
```

### Example 2: CDPConnection.execute_command()

**Agent wants to run a custom CDP command**

**Without type hints**:
```python
# Agent reads 100 lines of implementation...
result = await conn.execute_command(???, ???)
```

**With type hints**:
```python
# Agent inspects signature:
async def execute_command(
    self,
    method: str,
    params: Optional[dict] = None
) -> dict:
    """Execute CDP command and return result."""
```

**Agent immediately knows**:
- `method`: String (e.g., "Runtime.evaluate")
- `params`: Optional dict (can be None)
- Returns: dict (JSON response from Chrome)

**Agent writes correct code**:
```python
result = await conn.execute_command(
    "Runtime.evaluate",
    {"expression": "document.title", "returnByValue": True}
)
print(result["result"]["value"])  # Page title
```

---

## Common Workflows

### Workflow 1: Debug a Login Form

**Goal**: Understand why login fails

**Steps**:
1. **Run orchestrator in headed mode with console monitoring**:
   ```bash
   python -m scripts.cdp.cli.main orchestrate headed "http://localhost:3000/login" \
     --include-console \
     --output-dir /tmp/login-debug/
   ```

2. **In a separate terminal, start network monitoring**:
   ```bash
   python -m scripts.cdp.cli.main network record --url "http://localhost:3000/login" \
     --duration 60 --output /tmp/login-debug/network.jsonl
   ```

3. **Manually interact**: Fill username/password, click "Login"

4. **Press Ctrl+C** in orchestrator terminal when done

5. **Analyze console.jsonl**: Look for JavaScript errors
   ```bash
   cat /tmp/login-debug/console.jsonl | jq 'select(.level == "error")'
   ```

6. **Analyze network.jsonl**: Find failed API calls
   ```bash
   cat /tmp/login-debug/network.jsonl | jq 'select(.status >= 400)'
   ```

7. **Analyze DOM**: Check if error messages appeared
   ```bash
   grep "error-message" /tmp/login-debug/dom.html
   ```

### Workflow 2: Find API Endpoints

**Goal**: Discover all API endpoints a page uses

**Steps**:
1. **Run network monitor**:
   ```bash
   python -m scripts.cdp.cli.main network record --url "https://example.com" \
     --duration 30 --output /tmp/api-discovery.jsonl
   ```

2. **Extract unique URLs**:
   ```bash
   cat /tmp/api-discovery.jsonl | jq -r '.url' | sort -u
   ```

3. **Filter for API calls** (JSON responses):
   ```bash
   cat /tmp/api-discovery.jsonl | jq 'select(.mimeType == "application/json")'
   ```

### Workflow 3: Monitor Real-Time Changes

**Goal**: See how a page updates dynamically

**Steps**:
1. **Run console monitor in background**:
   ```bash
   python -m scripts.cdp.cli.main console stream --url "https://example.com/dashboard" \
     --duration 60 --output /tmp/live-updates.jsonl &
   ```

2. **Tail the output** to see live updates:
   ```bash
   tail -f /tmp/live-updates.jsonl | jq .
   ```

3. **Trigger actions** in the browser (manual or automated)

4. **Watch console messages appear in real-time**

---

## Advanced: Custom CDP Commands

If the CLI commands don't cover your use case, you can send custom CDP commands:

### Using `cdp-query.sh` (Legacy)

```bash
# Get WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

# Send custom CDP command
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"window.location.href","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" \
  | jq -r '.result.result.value'
```

### Using Python CDP Connection (Recommended)

```python
from scripts.cdp.connection import CDPConnection

async with CDPConnection("ws://localhost:9222/...") as conn:
    # Evaluate JavaScript
    result = await conn.execute_command(
        "Runtime.evaluate",
        {"expression": "document.querySelectorAll('a').length", "returnByValue": True}
    )
    link_count = result["result"]["value"]
    print(f"Page has {link_count} links")

    # Get page cookies
    cookies = await conn.execute_command("Network.getCookies")
    print(f"Cookies: {cookies['cookies']}")

    # Take screenshot
    screenshot = await conn.execute_command(
        "Page.captureScreenshot",
        {"format": "png"}
    )
    with open("screenshot.png", "wb") as f:
        f.write(base64.b64decode(screenshot["data"]))
```

---

## Troubleshooting

### Port 9222 Already in Use

```bash
# Kill existing Chrome debug sessions
pkill -f "chrome.*9222"
```

### WebSocket URL Stale (After Navigation)

```bash
# Re-fetch WebSocket URL before each extraction
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
```

### Buffer Overflow (Large DOMs)

```bash
# Increase websocat buffer to 2MB
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 2097152 "$WS_URL" | jq -r '.result.result.value'
```

### Chrome 136+ Headed Mode Hangs

**Issue**: Chrome 136+ (March 2025) blocks CDP access to default profiles

**Solution**: Always use `--user-data-dir` for headed mode (CLI handles this automatically)

```bash
# ✅ CORRECT (CLI does this automatically)
python -m scripts.cdp.cli.main orchestrate headed "https://example.com"

# ❌ WRONG (manual Chrome launch without --user-data-dir)
chrome --remote-debugging-port=9222 https://example.com
```

See `docs/guides/chrome-136-incident.md` for full incident details.

---

## File Format Reference

### console.jsonl Format

Each line is a JSON object representing one console message:

```typescript
{
  "source": "console-api" | "javascript" | "network" | "security" | ...,
  "level": "log" | "warning" | "error" | "info" | "debug",
  "text": string,              // Message text
  "timestamp": number,          // Seconds since epoch
  "url"?: string,              // Source file (for errors)
  "lineNumber"?: number,       // Line number (for errors)
  "stackTrace"?: object        // Stack trace (for errors)
}
```

### network.jsonl Format

Each line is a JSON object representing a request or response:

```typescript
{
  "event": "request" | "response",
  "requestId": string,         // Unique request ID (links request to response)
  "url": string,               // Full URL
  "method": "GET" | "POST" | ...,
  "timestamp": number,          // Seconds since epoch
  "status"?: number,           // HTTP status (response only)
  "mimeType"?: string,         // Content type (response only)
  "headers"?: object,          // Request/response headers
  "postData"?: string          // Request body (POST requests)
}
```

### DOM Format

Standard HTML5 document:

```html
<!DOCTYPE html>
<html>
<head>...</head>
<body>...</body>
</html>
```

---

## See Also

- **SKILL.md** - Agent-facing skill instructions
- **docs/reference/cdp-commands.md** - Full CDP command reference
- **docs/guides/workflow-guide.md** - Step-by-step headed mode workflow
- **docs/guides/chrome-136-incident.md** - Chrome 136 security policy change
- **scripts/cdp/cli/** - CLI implementation with type annotations

---

## Summary

**Key Takeaways**:

1. **Three core commands**: `dom`, `console`, `network`
2. **Orchestrator**: Runs all three together
3. **Headed mode**: Interactive debugging with visible Chrome
4. **Type hints**: 30% faster for agents to understand and use
5. **Output formats**: JSONL for machine parsing, HTML for structure, TXT for humans

**The Agent's Workflow**:
1. Read type hints to understand CLI arguments
2. Run orchestrate command to capture data
3. Analyze output files (DOM/console/network)
4. Understand website behavior
5. Report findings or suggest fixes

**Remember**: Type annotations mean you spend less time figuring out *how* to use the tool, and more time *using* it to solve problems! 🚀
