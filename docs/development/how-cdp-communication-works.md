# How Does Claude Talk to Chrome? CDP Communication Explained

A simple, educational breakdown of how this skill streams live browser telemetry (DOM, console logs, network requests) from Chrome to Claude using the Chrome DevTools Protocol.

---

## The Big Picture

Imagine you're watching a movie in a theater. You want to know:
- What's on screen right now? (DOM)
- What are the actors saying? (console logs)
- What props are being brought on stage? (network requests)

**The old way:** Take a photo with your phone, leave the theater, describe what you saw.
**The CDP way:** Sit in the director's booth with a live video feed, speakers, and a manifest of every prop coming in and out - **in real-time**.

That's what Chrome DevTools Protocol (CDP) does. It's a **live communication channel** into Chrome's brain while the browser is running.

---

## What is Chrome DevTools Protocol (CDP)?

**CDP is Chrome's remote control API.** It's the same technology that powers Chrome DevTools (the inspector you use with F12), but accessible via code.

**What it lets you do:**
- Execute JavaScript in a live page
- Monitor console logs in real-time
- Track every network request and response
- Inspect and modify the DOM
- Debug JavaScript execution
- Take screenshots, capture performance metrics
- Control browser navigation

**Think of it like:** Having a remote control for Chrome that speaks JSON instead of button clicks.

---

## The Two-Part Architecture: HTTP + WebSocket

Chrome's debugging interface has **two endpoints** that work together:

### Part 1: The HTTP Metadata Endpoint (The Directory)

```
http://localhost:9222/json
```

**What it does:** Returns a list of all open tabs and their WebSocket URLs

**Example request:**
```bash
curl -s http://localhost:9222/json
```

**Example response:**
```json
[
  {
    "id": "B3F1C93AF7B1138DBF22B723CCDB32C2",
    "type": "page",
    "title": "Example Domain",
    "url": "https://example.com",
    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/B3F1C93AF7B1138DBF22B723CCDB32C2"
  }
]
```

**Think of it like:** The building directory in a lobby - it tells you which room (WebSocket URL) to go to for the page you want.

**Why HTTP?**
- Simple, stateless
- Just returns a directory
- No need for persistent connection

---

### Part 2: The WebSocket Command Endpoint (The Live Connection)

```
ws://localhost:9222/devtools/page/{PAGE_ID}
```

**What it does:** Bidirectional communication channel for sending commands and receiving events

**Why WebSocket instead of HTTP?**

| Feature | HTTP | WebSocket |
|---------|------|-----------|
| Connection | Request → Response → Close | Open → Stay Connected |
| Direction | One-way (you ask, server responds) | Two-way (both can send anytime) |
| Use case | "Give me the page list" | "Tell me every time there's a console log" |
| Overhead | Full HTTP headers every time | Small frames after initial handshake |
| Events | Can't push events to client | Server pushes events as they happen |

**Example - Why WebSocket is essential:**

**Scenario:** Monitor console logs while you interact with a page

**With HTTP (doesn't work):**
```bash
# You'd have to poll constantly
while true; do
  curl http://localhost:9222/console-logs  # Doesn't exist!
  sleep 0.1
done
# Problems:
# - No such endpoint exists
# - Miss logs between polls
# - Massive overhead (full HTTP request every 100ms)
```

**With WebSocket (how it actually works):**
```bash
# Open connection once
websocat ws://localhost:9222/devtools/page/ABC123

# Chrome pushes events to you as they happen:
{"method":"Runtime.consoleAPICalled","params":{"type":"log","args":[...]}}
{"method":"Runtime.consoleAPICalled","params":{"type":"error","args":[...]}}
{"method":"Runtime.consoleAPICalled","params":{"type":"log","args":[...]}}
```

**Think of WebSocket like:** A phone call (stays connected, both can talk) vs HTTP like text messages (send, wait for reply, disconnect).

---

## How Messages Work: The JSON Request/Response Protocol

All CDP communication uses **JSON messages** over the WebSocket connection.

### Three Types of Messages

#### 1. Commands (You → Chrome)

**Format:**
```json
{
  "id": 1,
  "method": "Domain.methodName",
  "params": {
    "paramName": "value"
  }
}
```

**Example - Execute JavaScript:**
```json
{
  "id": 1,
  "method": "Runtime.evaluate",
  "params": {
    "expression": "document.title",
    "returnByValue": true
  }
}
```

**What this means:**
- `"id": 1` - Request ID so you can match responses (like a tracking number)
- `"method": "Runtime.evaluate"` - What to do (execute JavaScript)
- `"params"` - Command details (the JavaScript code to run)

---

#### 2. Command Responses (Chrome → You)

**Format:**
```json
{
  "id": 1,
  "result": {
    "result": {
      "type": "string",
      "value": "Example Domain"
    }
  }
}
```

**What this means:**
- `"id": 1` - Matches the request (this is the answer to command #1)
- `"result"` - The return value from your command
- Nested structure because CDP wraps everything for type safety

---

#### 3. Events (Chrome → You, unsolicited)

**Format:**
```json
{
  "method": "Network.requestWillBeSent",
  "params": {
    "requestId": "1234.5",
    "request": {
      "url": "https://example.com/api/data",
      "method": "GET"
    }
  }
}
```

**What this means:**
- **No `id` field** - This is an event, not a response
- `"method"` - What happened (a network request started)
- `"params"` - Event details (the request info)

**Key difference:** Events arrive whenever something happens, not in response to your commands.

---

## Real Example: Getting the Live DOM

Let's trace exactly what happens when Claude asks for the DOM.

### Step 1: Launch Chrome with Debugging Enabled

```bash
chrome \
  --headless=new \
  --remote-debugging-port=9222 \
  https://example.com &
```

**What this does:**
- Launches Chrome in headless mode (no GUI)
- Opens port 9222 for debugging
- Navigates to example.com
- Runs in background (`&`)

**Behind the scenes:** Chrome starts an HTTP server on port 9222 and a WebSocket server ready to accept connections.

---

### Step 2: Get the WebSocket URL

```bash
curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl'
```

**Output:**
```
ws://localhost:9222/devtools/page/B3F1C93AF7B1138DBF22B723CCDB32C2
```

**What's happening:**
1. `curl` makes HTTP GET request to the metadata endpoint
2. Chrome returns JSON list of open tabs
3. `jq` extracts the WebSocket URL from the first tab
4. We save this URL for the next step

---

### Step 3: Send CDP Command via WebSocket

**The command (JSON):**
```json
{
  "id": 1,
  "method": "Runtime.evaluate",
  "params": {
    "expression": "document.documentElement.outerHTML",
    "returnByValue": true
  }
}
```

**Sending it with websocat:**
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "ws://localhost:9222/devtools/page/B3F1C93AF7B1138DBF22B723CCDB32C2"
```

**What's happening here:**
- `echo` - Creates the JSON command
- `|` - Pipes it into websocat
- `websocat` - Opens WebSocket connection, sends message, receives response
  - `-n1` - Close after receiving 1 message (request/response pattern)
  - `-B 1048576` - Set buffer to 1MB (default 64KB too small for large DOM)
- The URL points to the specific page's WebSocket endpoint

---

### Step 4: Chrome Executes and Responds

**What Chrome does internally:**
1. Receives the JSON message over WebSocket
2. Parses it: "Ah, you want `Runtime.evaluate`"
3. Executes the JavaScript: `document.documentElement.outerHTML`
4. Gets the entire DOM as a string (could be 100KB-2MB)
5. Packages it into a CDP response
6. Sends back over the same WebSocket

**The response:**
```json
{
  "id": 1,
  "result": {
    "result": {
      "type": "string",
      "value": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <title>Example Domain</title>\n...</html>"
    }
  }
}
```

---

### Step 5: Extract the DOM

```bash
| jq -r '.result.result.value' > /tmp/live-dom.html
```

**What's happening:**
- `jq -r` - Parse JSON and extract nested value
  - `.result` - Outer result wrapper
  - `.result` - Inner result wrapper (CDP uses nested structure)
  - `.value` - The actual DOM string
  - `-r` - Raw output (no JSON quotes)
- `> /tmp/live-dom.html` - Save to file

**Result:** You now have the **fully-rendered DOM** including all JavaScript modifications, React hydration, etc.

---

## How the Collectors Work: Streaming Events

The DOM example above is **one-shot**: send command, get response, done.

But for **monitoring** (console logs, network requests), we need to **stream events**. Let's see how.

### Console Log Monitoring: Step by Step

**Script:** `scripts/collectors/cdp-console.py`

#### Step 1: Connect to WebSocket

```python
ws_url = f'ws://localhost:9222/devtools/page/{page_id}'
async with websockets.connect(ws_url) as ws:
    # Connection open, ready to send/receive
```

**What's happening:** Opens persistent WebSocket connection to Chrome.

---

#### Step 2: Enable Console Monitoring

```python
# Send command to enable Runtime domain
await ws.send(json.dumps({
    'id': 1,
    'method': 'Runtime.enable'
}))

# Send command to enable Log domain
await ws.send(json.dumps({
    'id': 2,
    'method': 'Log.enable'
}))

# Send command to enable Console domain
await ws.send(json.dumps({
    'id': 3,
    'method': 'Console.enable'
}))
```

**What this does:** Tells Chrome "start sending me console events"

**Chrome responds:**
```json
{"id": 1, "result": {}}
{"id": 2, "result": {}}
{"id": 3, "result": {}}
```

(Empty results mean "OK, enabled")

---

#### Step 3: Wait for Events (Infinite Loop)

```python
while True:
    message = await ws.recv()  # Wait for next message from Chrome
    msg = json.loads(message)  # Parse JSON

    # Check what kind of message it is
    if msg.get('method') == 'Runtime.consoleAPICalled':
        # This is a console log!
        # Extract and print it
```

**What's happening:**
- `ws.recv()` - **Blocks** until Chrome sends a message
- Could be a console log, or an exception, or any other event
- We check `msg.get('method')` to identify the event type
- Then extract relevant data and output it

---

#### Step 4: Handle Different Event Types

**When user does `console.log("Hello")` in browser:**

Chrome sends this event:
```json
{
  "method": "Runtime.consoleAPICalled",
  "params": {
    "type": "log",
    "timestamp": 1729782000.123,
    "args": [
      {
        "type": "string",
        "value": "Hello"
      }
    ]
  }
}
```

Our script sees this and outputs:
```json
{
  "type": "log",
  "timestamp": 1729782000.123,
  "message": "Hello"
}
```

---

**When user code throws an error:**

Chrome sends:
```json
{
  "method": "Runtime.exceptionThrown",
  "params": {
    "timestamp": 1729782001.456,
    "exceptionDetails": {
      "text": "Uncaught TypeError: Cannot read properties of undefined",
      "stackTrace": {
        "callFrames": [
          {
            "functionName": "onClick",
            "url": "https://example.com/app.js",
            "lineNumber": 42,
            "columnNumber": 15
          }
        ]
      }
    }
  }
}
```

Our script sees this and outputs:
```json
{
  "type": "exception",
  "timestamp": 1729782001.456,
  "message": "Uncaught TypeError: Cannot read properties of undefined",
  "stackTrace": {"callFrames": [...]}
}
```

---

### Network Monitoring: Same Pattern, Different Events

**Script:** `scripts/collectors/cdp-network.py`

**Step 1-2:** Same as console (connect + enable domain)

```python
await ws.send(json.dumps({'id': 1, 'method': 'Network.enable'}))
```

**Step 3-4:** Listen for network events

**When browser makes a request:**
```json
{
  "method": "Network.requestWillBeSent",
  "params": {
    "requestId": "1234.5",
    "request": {
      "url": "https://example.com/api/users",
      "method": "GET",
      "headers": {...}
    }
  }
}
```

**When response arrives:**
```json
{
  "method": "Network.responseReceived",
  "params": {
    "requestId": "1234.5",
    "response": {
      "url": "https://example.com/api/users",
      "status": 200,
      "statusText": "OK",
      "mimeType": "application/json"
    }
  }
}
```

**When request fails:**
```json
{
  "method": "Network.loadingFailed",
  "params": {
    "requestId": "1234.5",
    "errorText": "net::ERR_CONNECTION_REFUSED"
  }
}
```

Our script matches these up by `requestId` to show complete request/response pairs.

---

## The Complete Flow: From Claude's Question to Browser Telemetry

Let's trace a complete interaction when you ask Claude to debug a page.

### Your Request
```
Use browser-debugger skill to capture http://localhost:3000 in headless mode
with console logs and network monitoring
```

---

### What Happens Behind the Scenes

#### Phase 1: Chrome Launch (chrome-launcher.sh)

```bash
# 1. Script generates isolated profile path
PROFILE_DIR="$HOME/.chrome-debug-profile"

# 2. Launches Chrome with debugging
chrome \
  --headless=new \
  --remote-debugging-port=9222 \
  --user-data-dir="$PROFILE_DIR" \
  http://localhost:3000 &

CHROME_PID=$!

# 3. Waits for Chrome to be ready
sleep 2

# 4. Gets WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
PAGE_ID=$(echo "$WS_URL" | grep -oE '[^/]+$')

# 5. Returns JSON contract
echo '{"status":"success","chrome_pid":'$CHROME_PID',"ws_url":"'$WS_URL'","page_id":"'$PAGE_ID'"}'
```

**Output:**
```json
{
  "status": "success",
  "chrome_pid": 12345,
  "ws_url": "ws://localhost:9222/devtools/page/ABC123",
  "page_id": "ABC123"
}
```

---

#### Phase 2: Start Collectors (debug-orchestrator.sh)

```bash
# Launch console monitor in background
python3 scripts/collectors/cdp-console.py "$PAGE_ID" \
  --idle-timeout=5 \
  > /tmp/console.log 2>&1 &

CONSOLE_PID=$!

# Launch network monitor in background
python3 scripts/collectors/cdp-network.py "$PAGE_ID" \
  --idle-timeout=5 \
  > /tmp/network.log 2>&1 &

NETWORK_PID=$!
```

**What's happening:**
- Two Python scripts start in parallel
- Each opens its own WebSocket connection to the same page
- Console script listens for Runtime/Log/Console events
- Network script listens for Network events
- Both write JSON events to their respective log files
- Both run in background (`&`)

---

#### Phase 3: Live Monitoring (Parallel)

**Console collector:**
```
Connected to CDP (port 9222)
[Waits for events...]
{"type":"log","timestamp":1729782000.1,"message":"App initialized"}
{"type":"log","timestamp":1729782000.5,"message":"Fetching user data"}
{"type":"error","timestamp":1729782001.2,"message":"Failed to load resource"}
[Idle for 5 seconds... timeout reached]
```

**Network collector:**
```
Connected to CDP (port 9222)
[Waits for events...]
{"event":"request","url":"http://localhost:3000/","method":"GET","requestId":"1.1"}
{"event":"response","url":"http://localhost:3000/","status":200,"requestId":"1.1"}
{"event":"request","url":"http://localhost:3000/api/users","method":"GET","requestId":"1.2"}
{"event":"response","url":"http://localhost:3000/api/users","status":500,"requestId":"1.2"}
[Idle for 5 seconds... timeout reached]
```

**Behind the scenes:** Both scripts have open WebSocket connections, Chrome pushes events to both in real-time.

---

#### Phase 4: Extract Final DOM

```bash
# After monitoring completes, grab the DOM
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' \
  > /tmp/dom.html
```

---

#### Phase 5: Generate Summary

```bash
python3 scripts/collectors/cdp-summarize.py \
  /tmp/network.log \
  --console-log=/tmp/console.log \
  --format=both
```

**Output:**
```
📊 Analysis Results:
   Total Requests:  5
   Total Responses: 5
   Failed Requests: 1

📥 Top 10 Requests:
   GET http://localhost:3000/
   GET http://localhost:3000/api/users
   ...

🖥️ Console Summary:
   Entries: 8
   Levels:
      log: 6
      error: 2
   Sample Errors:
      Failed to load resource [http://localhost:3000/api/users]
```

---

#### Phase 6: Cleanup

```bash
# Kill Chrome
kill $CHROME_PID

# Collectors already exited (idle timeout)

echo "✅ Done!"
```

---

## Why This Architecture is Powerful

### 1. Real-Time Streaming

**Old way (--dump-dom):**
- Takes snapshot of initial HTML
- Misses everything that happens after page load
- No console logs, no network visibility

**CDP way:**
- Stream events as they happen
- See exact order of operations
- Catch timing-dependent bugs

---

### 2. Parallel Monitoring

**Multiple collectors simultaneously:**
- Console monitor sees logs
- Network monitor sees requests
- Both watching the same page at the same time
- Independent WebSocket connections
- No interference between them

---

### 3. Programmable Browser

**Not just reading data:**
- Execute arbitrary JavaScript
- Click buttons, fill forms
- Navigate pages
- Modify DOM
- Simulate mobile devices
- Capture screenshots

---

### 4. No Browser Extensions Required

**Everything via protocol:**
- No extension installation
- Works on any Chrome/Chromium
- Scriptable in any language
- No GUI needed (headless)

---

## Visual Summary: The Complete Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Your Command                            │
│  "Use browser-debugger to capture http://localhost:3000"        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   chrome-launcher.sh                            │
│  • Launches Chrome with --remote-debugging-port=9222            │
│  • Returns: {chrome_pid, ws_url, page_id}                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────┐
│                      Chrome Process                            │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  HTTP Metadata Server                                  │    │
│  │  http://localhost:9222/json                            │    │
│  │  Returns: List of tabs + WebSocket URLs                │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  WebSocket Command Server                              │    │
│  │  ws://localhost:9222/devtools/page/{PAGE_ID}           │    │
│  │                                                        │    │
│  │  Accepts:                                              │    │
│  │    • Commands (Runtime.evaluate, Network.enable)       │    │
│  │    • Events (console logs, network requests)           │    │
│  │  Sends:                                                │    │
│  │    • Command responses                                 │    │
│  │    • Events (console logs, network requests)           │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Page Rendering                                        │    │
│  │  http://localhost:3000                                 │    │
│  │  • Executes JavaScript                                 │    │
│  │  • Makes network requests                              │    │
│  │  • Generates console output                            │    │
│  └────────────────────────────────────────────────────────┘    │
└──────────┬──────────────────────────┬──────────────────────────┘
           │                          │
           │                          │
    ┌──────▼────────┐        ┌───────▼────────┐
    │               │        │                │
    │ cdp-console.py│        │ cdp-network.py │
    │               │        │                │
    │ WebSocket     │        │ WebSocket      │
    │ Connection    │        │ Connection     │
    │               │        │                │
    │ Sends:        │        │ Sends:         │
    │  Runtime.     │        │  Network.      │
    │  enable       │        │  enable        │
    │               │        │                │
    │ Receives:     │        │ Receives:      │
    │  Runtime.     │        │  Network.      │
    │  consoleAPI   │        │  requestWill   │
    │  Called       │        │  BeSent        │
    │               │        │  Network.      │
    │  Runtime.     │        │  response      │
    │  exception    │        │  Received      │
    │  Thrown       │        │                │
    │               │        │                │
    │ Outputs:      │        │ Outputs:       │
    │  JSON logs    │        │  JSON events   │
    │  to file      │        │  to file       │
    └───────────────┘        └────────────────┘
           │                          │
           │                          │
           ▼                          ▼
    /tmp/console.log          /tmp/network.log

           │                          │
           └──────────┬───────────────┘
                      │
                      ▼
          ┌─────────────────────┐
          │ cdp-summarize.py    │
          │ • Parse logs        │
          │ • Generate summary  │
          │ • Show failures     │
          └─────────────────────┘
                      │
                      ▼
              Summary Output
              (human + JSON)
```

---

## Key Takeaways

1. **CDP is Chrome's remote control API** - Same tech that powers DevTools
2. **Two-part architecture** - HTTP for metadata, WebSocket for commands/events
3. **WebSocket enables streaming** - Events pushed as they happen, not polled
4. **JSON-based protocol** - Simple, language-agnostic, easy to debug
5. **Multiple simultaneous connections** - Console + network monitors run in parallel
6. **Real-time telemetry** - See exactly what the browser sees, when it sees it
7. **No modifications needed** - Works with any Chrome/Chromium, no extensions

**Bottom line:** CDP turns Chrome into a programmable, observable system where every action, log, and network request is visible through a real-time JSON stream. This skill just wraps that protocol in simple scripts that Claude can invoke to debug pages without manual screenshot exchanges.

---

## Further Reading

- **Official CDP Documentation:** https://chromedevtools.github.io/devtools-protocol/
- **CDP Domains Reference:** `docs/reference/cdp-commands.md`
- **WebSocket Internals:** `docs/reference/websocat-analysis.md`
- **Collector Scripts:** `scripts/collectors/`
