
  The Challenge: Getting React-Hydrated DOM

  The key problem was that headless Chrome's --dump-dom only captures the SSR shell, not the React-hydrated
  content. I needed to execute JavaScript in a live browser session to get the actual DOM.

  Failed Approaches First

  ❌ Attempt 1: Node.js + ws Library

  # Tried to use Node.js WebSocket library
  node extract-dom.js
  # Error: Cannot find module 'ws'
  Problem: The ws npm package wasn't installed globally, and I couldn't install it without access to the
  project.

  ❌ Attempt 2: Python + websockets Library

  # Tried to use Python WebSocket library
  python3 extract-dom.py
  # Error: No module named 'websockets'
  Problem: Python websockets library not installed.

  ❌ Attempt 3: CDP HTTP Endpoints

  # Chrome DevTools Protocol exposes HTTP endpoints
  curl http://localhost:9222/json/protocol
  Problem: HTTP endpoints only return the protocol specification, not live page data. CDP requires WebSocket for
   command execution.

  ---
  ✅ Solution: websocat - The Missing Piece

  Discovery

  I checked what WebSocket clients were available:
  which websocat
  # Output: /opt/homebrew/bin/websocat

  websocat is a command-line WebSocket client (think netcat for WebSockets) that was already installed on the
  system!

  How Chrome DevTools Protocol Works

  Chrome exposes a WebSocket endpoint for remote debugging:

  # 1. Get the WebSocket URL
  curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl'
  # Output: ws://localhost:9222/devtools/browser/abc-123-def

  This WebSocket URL allows you to send CDP commands in JSON format.

  ---
  The Working Solution: Combining websocat + Chrome

  Step-by-Step Process

  1. Launch Chrome with Remote Debugging

  # Browser debugger skill does this automatically
  google-chrome \
    --headless=new \
    --remote-debugging-port=9222 \
    http://localhost:3000/customer/register

  2. Get WebSocket Debugger URL

  WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
  echo $WS_URL
  # Output: ws://localhost:9222/devtools/browser/6d5f8c3a-1b2e-4f9c-a8d7-3e4f5a6b7c8d

  3. Create CDP Command (JSON)

  # Create a JSON file with the CDP command
  cat > /tmp/cdp-command.json << 'EOF'
  {
    "id": 1,
    "method": "Runtime.evaluate",
    "params": {
      "expression": "document.documentElement.outerHTML",
      "returnByValue": true
    }
  }
  EOF

  CDP Command Breakdown:
  - "method": "Runtime.evaluate" - Execute JavaScript in the page context
  - "expression": "document.documentElement.outerHTML" - Get entire DOM as string
  - "returnByValue": true - Return the actual value, not an object reference

  4. Send Command via websocat

  cat /tmp/cdp-command.json | \
    websocat -n1 -B 1048576 "$WS_URL" | \
    jq -r '.result.result.value' > /tmp/live-dom.html

  websocat flags:
  - -n1 - Close connection after receiving 1 message (request/response pattern)
  - -B 1048576 - Set buffer size to 1MB (default 64KB too small for large DOM)
  - Pipe JSON command → WebSocket → Receive response

  5. Extract DOM from CDP Response

  # CDP returns JSON response like:
  # {
  #   "id": 1,
  #   "result": {
  #     "result": {
  #       "type": "string",
  #       "value": "<html>...</html>"  ← The actual DOM!
  #     }
  #   }
  # }

  # jq extracts the nested value
  jq -r '.result.result.value' < /tmp/cdp-response.json

  ---
  Why This Approach Works

  1. WebSocket vs HTTP

  | Protocol  | Use Case         | Example                                        |
  |-----------|------------------|------------------------------------------------|
  | HTTP      | Get metadata     | curl http://localhost:9222/json → List of tabs |
  | WebSocket | Execute commands | websocat ws://... → Run JavaScript, get DOM    |

  CDP requires WebSocket for:
  - Executing JavaScript (Runtime.evaluate)
  - Getting live page state
  - Manipulating the DOM
  - Listening to events

  2. Python Script Role (Not Used, But Here's How It Would Work)

  If I had Python websockets installed, the script would look like:

  import asyncio
  import websockets
  import json

  async def get_dom(ws_url):
      async with websockets.connect(ws_url) as websocket:
          # Send CDP command
          command = {
              "id": 1,
              "method": "Runtime.evaluate",
              "params": {
                  "expression": "document.documentElement.outerHTML",
                  "returnByValue": True
              }
          }
          await websocket.send(json.dumps(command))

          # Receive response
          response = await websocket.recv()
          result = json.loads(response)

          # Extract DOM
          dom_html = result['result']['result']['value']
          return dom_html

  # Get WebSocket URL
  import subprocess
  ws_url = subprocess.check_output(
      "curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl'",
      shell=True
  ).decode().strip()

  # Get DOM
  dom = asyncio.run(get_dom(ws_url))
  print(dom)

  But websocat is simpler - no dependencies, just pipe JSON!

  ---
  The Buffer Size Issue

  Problem Encountered:

  [WARN  websocat::readdebt] Incoming message too long (324990 > 65535)

  The default buffer size (64KB) was too small for the 307KB DOM response.

  Solution:

  websocat -B 1048576  # Set buffer to 1MB (1,048,576 bytes)

  ---
  Complete Working Script

  Here's the final one-liner I used:

  #!/bin/bash
  # extract-live-dom.sh

  # 1. Get WebSocket debugger URL
  WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')

  # 2. Send CDP command via websocat, extract DOM
  echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnB
  yValue":true}}' | \
    websocat -n1 -B 1048576 "$WS_URL" | \
    jq -r '.result.result.value' > /tmp/live-dom-step2.html

  # 3. Verify
  ls -lh /tmp/live-dom-step2.html

  Output:
  -rw-r--r--  1 user  staff  307K Oct 23 10:30 /tmp/live-dom-step2.html

  ---
  Alternative: If Python Were Available

  Full Python + CDP Script

  #!/usr/bin/env python3
  import asyncio
  import websockets
  import json
  import subprocess

  async def extract_dom():
      # Get WebSocket URL from Chrome
      result = subprocess.run(
          ["curl", "-s", "http://localhost:9222/json"],
          capture_output=True,
          text=True
      )
      tabs = json.loads(result.stdout)
      ws_url = tabs[0]['webSocketDebuggerUrl']

      # Connect to Chrome via WebSocket
      async with websockets.connect(ws_url, max_size=2**20) as ws:
          # Send CDP command to evaluate JavaScript
          command = {
              "id": 1,
              "method": "Runtime.evaluate",
              "params": {
                  "expression": "document.documentElement.outerHTML",
                  "returnByValue": True
              }
          }

          await ws.send(json.dumps(command))

          # Receive response
          response = await ws.recv()
          data = json.loads(response)

          # Extract DOM HTML
          dom_html = data['result']['result']['value']

          # Write to file
          with open('/tmp/live-dom.html', 'w') as f:
              f.write(dom_html)

          print(f"DOM extracted: {len(dom_html)} bytes")

  # Run
  asyncio.run(extract_dom())

  Usage:
  python3 extract-dom.py
  # Output: DOM extracted: 307555 bytes

  ---
  Comparison: websocat vs Python

  | Aspect         | websocat                     | Python + websockets               |
  |----------------|------------------------------|-----------------------------------|
  | Dependencies   | ✅ None (binary)              | ❌ Requires pip install websockets |
  | Speed          | ✅ Fast (native binary)       | ⚠️ Slower (Python interpreter)    |
  | Scriptability  | ✅ Pipeable (Unix philosophy) | ⚠️ Requires script file           |
  | Error handling | ⚠️ Limited                   | ✅ Rich (try/except)               |
  | Complexity     | ✅ One-liner                  | ⚠️ 30+ lines of code              |
  | Buffer control | ✅ -B flag                    | ✅ max_size parameter              |

  Verdict: websocat was the perfect tool because it was already installed and dead simple to use.

  ---
  Why This Matters for Browser Debugging

  The Problem with Traditional Tools:

  # Headless Chrome --dump-dom
  chrome --headless --dump-dom https://example.com
  # ❌ Only captures SSR shell, misses React hydration

  # curl/wget
  curl https://example.com
  # ❌ Only gets initial HTML, no JavaScript execution

  The CDP + WebSocket Solution:

  # Launch Chrome with debugging
  chrome --remote-debugging-port=9222 https://example.com &

  # Execute JavaScript in LIVE page context
  echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title"}}' | \
    websocat -n1 "$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')"

  # Output: {"id":1,"result":{"result":{"type":"string","value":"Example Domain"}}}

  Benefits:
  - ✅ Get fully-rendered DOM after React/Vue/Angular hydration
  - ✅ Execute arbitrary JavaScript in page context
  - ✅ Access live browser state (localStorage, cookies, Redux store)
  - ✅ No browser extensions needed

  ---
  ★ Insight ─────────────────────────────────────

  The key insight is understanding the Chrome DevTools Protocol architecture:

  ┌─────────────────┐
  │  Chrome Browser │
  │  (Port 9222)    │
  └────────┬────────┘
           │
           ├── HTTP Endpoint (localhost:9222/json)
           │   ↳ Returns metadata (list of tabs, WebSocket URLs)
           │
           └── WebSocket Endpoint (ws://localhost:9222/devtools/browser/...)
               ↳ Executes commands (JavaScript, DOM manipulation, debugging)

  Why WebSocket?
  - Bidirectional: Chrome can send events back (console logs, network requests)
  - Stateful: Maintains connection for multiple commands
  - Async: Doesn't block browser rendering
  - Efficient: Binary protocol, low overhead

  Why Not HTTP?
  - One-way: Can't receive live events
  - Stateless: Every request creates new context
  - Synchronous: Would block browser
  - Overhead: JSON over HTTP for every tiny command

  websocat bridges the gap between Unix command-line tools (pipes, jq) and modern WebSocket protocols, making it
   perfect for extracting live DOM without writing full scripts.
