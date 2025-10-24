# CDP Commands Reference

## Overview

This document provides a comprehensive reference for Chrome DevTools Protocol (CDP) commands used with the browser-debugger skill. Includes WebSocket patterns, Runtime.evaluate examples, and advanced CDP operations.

## Table of Contents

- [WebSocket URL Discovery](#websocket-url-discovery)
- [Runtime.evaluate Commands](#runtimeevaluate-commands)
- [DOM Extraction](#dom-extraction)
- [Page Context Commands](#page-context-commands)
- [Network Monitoring](#network-monitoring)
- [Console Monitoring](#console-monitoring)
- [Advanced CDP Commands](#advanced-cdp-commands)
- [Response Formats](#response-formats)

---

## WebSocket URL Discovery

Before sending CDP commands, you must obtain the WebSocket debugger URL from Chrome's HTTP endpoint.

### Get All Pages

```bash
curl -s http://localhost:9222/json | jq
```

**Output format:**
```json
[
  {
    "description": "",
    "id": "6d5f8c3a-1b2e-4f9c-a8d7-3e4f5a6b7c8d",
    "title": "Login - MyApp",
    "type": "page",
    "url": "http://localhost:3000/signin",
    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/6d5f8c3a-..."
  }
]
```

### Extract WebSocket URL (First Page)

```bash
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
```

### Filter by Page Type

```bash
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
```

### Filter by URL Pattern

```bash
# Find page with specific URL substring
WS_URL=$(curl -s http://localhost:9222/json \
  | jq -r '.[] | select(.type == "page" and (.url | contains("localhost:3000"))) | .webSocketDebuggerUrl' \
  | head -1)
```

### Get Page ID for Python Scripts

```bash
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
```

> **Important:** WebSocket URLs and page IDs become stale after navigation. Always re-fetch before each extraction.

---

## Runtime.evaluate Commands

The `Runtime.evaluate` method executes JavaScript in the page context and returns the result.

### Basic Syntax

```json
{
  "id": 1,
  "method": "Runtime.evaluate",
  "params": {
    "expression": "JAVASCRIPT_CODE_HERE",
    "returnByValue": true
  }
}
```

### Execute via websocat

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"2+2","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq
```

**Response:**
```json
{
  "id": 1,
  "result": {
    "result": {
      "type": "number",
      "value": 4
    }
  }
}
```

### Execute via Python

```python
#!/usr/bin/env python3
import asyncio, websockets, json, sys

async def run_command(ws_url, expression):
    async with websockets.connect(ws_url, max_size=2**20) as ws:
        cmd = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": True
            }
        }
        await ws.send(json.dumps(cmd))
        response = json.loads(await ws.recv())
        return response['result']['result']['value']

result = asyncio.run(run_command(sys.argv[1], sys.argv[2]))
print(result)
```

Usage:
```bash
python3 run-cdp.py "$WS_URL" "document.title"
```

---

## DOM Extraction

### Full DOM (websocat)

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/dom.html
```

**Flags:**
- `-n1`: Close after 1 message
- `-B 1048576`: 1MB buffer (increase for large DOMs)

### Full DOM (Python)

```python
#!/usr/bin/env python3
import asyncio, websockets, json, sys

async def extract_dom(ws_url):
    async with websockets.connect(ws_url, max_size=2**20) as ws:
        cmd = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True
            }
        }
        await ws.send(json.dumps(cmd))
        response = json.loads(await ws.recv())
        return response['result']['result']['value']

print(asyncio.run(extract_dom(sys.argv[1])))
```

Usage:
```bash
python3 extract-dom.py "$WS_URL" > /tmp/dom.html
```

### Extract Specific Elements

```bash
# All forms
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"Array.from(document.querySelectorAll('\''form'\'')).map(f => f.outerHTML).join('\''\\n'\'')","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# All input fields
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"Array.from(document.querySelectorAll('\''input'\'')).map(i => i.outerHTML).join('\''\\n'\'')","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Main content only
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.querySelector('\''main'\'').outerHTML","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Large DOM Handling

For DOMs larger than 1MB, increase buffer size:

```bash
# 2MB buffer
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 2097152 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/dom.html
```

Or extract only specific elements to reduce size:
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.body.innerHTML","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

---

## Page Context Commands

### Current URL

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"window.location.href","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Page Title

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Scroll Position

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"JSON.stringify({x: window.scrollX, y: window.scrollY})","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Viewport Dimensions

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"JSON.stringify({width: window.innerWidth, height: window.innerHeight})","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Check if Element Exists

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"!!document.querySelector('\''#login-form'\'')","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Count Elements

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.querySelectorAll('\''button'\'').length","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

---

## Network Monitoring

### Setup Network Monitoring

```bash
# Step 1: Start Chrome
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2

# Step 2: Get page ID
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)

# Step 3: Monitor network
python3 scripts/collectors/cdp-network.py $PAGE_ID
```

### Network Event Formats

**Request event:**
```json
{
  "event": "request",
  "url": "https://api.example.com/data",
  "method": "GET",
  "requestId": "..."
}
```

**Response event:**
```json
{
  "event": "response",
  "url": "https://api.example.com/data",
  "status": 200,
  "statusText": "OK",
  "mimeType": "application/json",
  "requestId": "..."
}
```

**Failed request:**
```json
{
  "event": "failed",
  "errorText": "net::ERR_CONNECTION_REFUSED",
  "requestId": "..."
}
```

### Capture Response Bodies

```bash
# Filter and capture response bodies for specific URLs
timeout 20 python3 scripts/collectors/cdp-network-with-body.py "$PAGE_ID" --port=9222 \
  --filter="api/v1" > /tmp/network-with-bodies.log
```

### Filter Network Events

```bash
# Only requests (exclude responses)
jq 'select(.event == "request")' /tmp/network.log

# Only failed requests
jq 'select(.event == "failed")' /tmp/network.log

# Specific status code
jq 'select(.status == 404)' /tmp/network.log

# Exclude blob URLs
jq 'select(.event == "request" and (.url | startswith("blob:") | not))' /tmp/network.log
```

---

## Console Monitoring

### Setup Console Monitoring

```bash
# Step 1: Start Chrome
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2

# Step 2: Get page ID
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)

# Step 3: Monitor console
python3 scripts/collectors/cdp-console.py $PAGE_ID
```

### Console Event Formats

**Log entry:**
```json
{
  "type": "log",
  "timestamp": 1698765432,
  "message": "Hello world",
  "stackTrace": null
}
```

**Error entry:**
```json
{
  "type": "error",
  "timestamp": 1698765433,
  "message": "Uncaught TypeError: Cannot read property 'foo' of undefined",
  "stackTrace": {
    "callFrames": [...]
  }
}
```

### Navigate After Connecting

```bash
# Monitor console and navigate to different URL
python3 scripts/collectors/cdp-console.py $PAGE_ID https://different-url.com
```

### Use Custom Port

```bash
python3 scripts/collectors/cdp-console.py $PAGE_ID https://example.com --port=9223
```

### Filter Console Events

```bash
# Only errors
jq 'select(.type=="error")' /tmp/console.log

# Exclude stack traces
jq 'del(.stackTrace)' /tmp/console.log

# Only warnings
jq 'select(.type=="warning")' /tmp/console.log
```

---

## Advanced CDP Commands

### localStorage Access

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"JSON.stringify(localStorage)","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value' | jq .
```

### sessionStorage Access

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"JSON.stringify(sessionStorage)","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value' | jq .
```

### Cookies

```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.cookie","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Custom JavaScript Queries

**Get all form IDs:**
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"Array.from(document.querySelectorAll('\''form'\'')).map(f => f.id)","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

**Get all links:**
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"Array.from(document.querySelectorAll('\''a'\'')).map(a => ({text: a.textContent.trim(), href: a.href}))","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

**Get form field values:**
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"Array.from(document.querySelectorAll('\''input'\'')).map(i => ({name: i.name, type: i.type, value: i.value}))","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

### Browser Version

```bash
echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq
```

**Response:**
```json
{
  "id": 1,
  "result": {
    "protocolVersion": "1.3",
    "product": "Chrome/136.0.6786.0",
    "revision": "@12345",
    "userAgent": "Mozilla/5.0...",
    "jsVersion": "13.6.123.4"
  }
}
```

### Take Screenshot

```bash
echo '{"id":1,"method":"Page.captureScreenshot","params":{"format":"png"}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.data' | base64 -d > screenshot.png
```

### Get All Cookies (Network Domain)

```bash
echo '{"id":1,"method":"Network.getAllCookies"}' | websocat -n1 "$WS_URL" | jq
```

### Accessibility Tree

```bash
echo '{"id":1,"method":"Accessibility.getFullAXTree"}' | websocat -n1 -B 2097152 "$WS_URL" | jq
```

---

## Response Formats

### Successful Runtime.evaluate Response

```json
{
  "id": 1,
  "result": {
    "result": {
      "type": "string",
      "value": "<html>...</html>"
    }
  }
}
```

### CDP Error Response

```json
{
  "id": 1,
  "error": {
    "code": -32000,
    "message": "Cannot find context with specified id"
  }
}
```

**Common error codes:**
- `-32000`: Generic CDP error (stale context, invalid command)
- `-32601`: Method not found
- `-32602`: Invalid params

### debug-orchestrator.sh Output

```json
{
  "chrome_version": "136.0.6786.0",
  "debug_port": 9222,
  "chrome_pid": 12345,
  "ws_url": "ws://localhost:9222/devtools/browser/6d5f8c3a-1b2e-4f9c-a8d7-3e4f5a6b7c8d",
  "mode": "headed",
  "profile": "/tmp/chrome-debug-12345"
}
```

---

## Tool Detection Pattern

Automatically detect available tools and choose extraction method:

```bash
# Step 1: Check websocat (primary)
if command -v websocat &>/dev/null; then
    echo "Using websocat method (primary)"
    echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
      | websocat -n1 -B 1048576 "$WS_URL" \
      | jq -r '.result.result.value' > /tmp/live-dom.html
else
    # Step 2: Check Python websockets (fallback)
    if python3 -c "import websockets" 2>/dev/null; then
        echo "Using Python websockets method (fallback)"
        # Create extraction script
        cat > /tmp/extract-dom.py <<'EOF'
#!/usr/bin/env python3
import asyncio, websockets, json, sys
async def extract_dom(ws_url):
    async with websockets.connect(ws_url, max_size=2**20) as ws:
        cmd = {"id": 1, "method": "Runtime.evaluate",
               "params": {"expression": "document.documentElement.outerHTML", "returnByValue": True}}
        await ws.send(json.dumps(cmd))
        response = json.loads(await ws.recv())
        return response['result']['result']['value']
print(asyncio.run(extract_dom(sys.argv[1])))
EOF
        chmod +x /tmp/extract-dom.py
        python3 /tmp/extract-dom.py "$WS_URL" > /tmp/live-dom.html
    else
        # Step 3: No tools available
        echo "ERROR: Install websocat (brew install websocat) or Python websockets (pip3 install websockets)"
        exit 1
    fi
fi
```

---

## Edge Cases

### Navigation Detection

Always re-fetch WebSocket URL before extraction to handle navigation:

```bash
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl' | head -1)
```

### Multiple Tabs

Filter by URL if multiple tabs are open:

```bash
WS_URL=$(curl -s http://localhost:9222/json \
  | jq -r '.[] | select(.type == "page" and (.url | contains("localhost:3000"))) | .webSocketDebuggerUrl' \
  | head -1)
```

### React/Vue Hydration Delay

Wait for JavaScript frameworks to hydrate before extracting DOM:

```bash
sleep 3
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'
```

---

## WebSocket Buffer Management

When extracting large DOMs (>64KB), increase websocat's buffer size:

```bash
# Default buffer (64KB) - works for most pages
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Large buffer (1MB) - for moderate complexity
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'

# Extra large buffer (2MB) - for complex SPAs
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 2097152 "$WS_URL" | jq -r '.result.result.value'

# If buffer overflow persists, extract specific elements
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.querySelector('\''main'\'').outerHTML","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

---

## Quick Reference

```bash
# Get WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

# Extract full DOM
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" | jq -r '.result.result.value'

# Get page title
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Get current URL
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"window.location.href","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'

# Get browser version
echo '{"id":1,"method":"Browser.getVersion"}' | websocat -n1 "$WS_URL" | jq
```

---

## See Also

- **Workflows:** `docs/workflows.md` - Full workflow examples
- **Chrome 136+ Requirements:** `docs/guides/chrome-136-incident.md`
- **Troubleshooting:** `docs/guides/troubleshooting.md`
- **WebSocket Internals:** `docs/reference/websocat-analysis.md`
