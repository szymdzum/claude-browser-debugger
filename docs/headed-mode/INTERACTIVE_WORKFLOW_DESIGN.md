# Interactive Browser Debugging Workflow Design

## Problem Statement

Currently, the headed mode launches Chrome and immediately starts monitoring. We need a **universal workflow** that:

1. Launches Chrome in headed mode and **pauses** (waits for user)
2. Allows user to **interact freely** (navigate, type, click, authenticate, etc.)
3. Provides a **signal mechanism** to indicate "I'm ready, start monitoring now"
4. Captures data **on-demand** based on user-specified selectors or targets

## Use Cases

### Use Case 1: Form Testing
- User opens signup page
- Fills in email, password, credit card (requires manual input)
- Signals "ready"
- System captures all form field values

### Use Case 2: Authenticated Pages
- User navigates to login page
- Manually logs in with 2FA
- Navigates to dashboard
- Signals "ready"
- System captures API calls made by authenticated session

### Use Case 3: Multi-Step Workflows
- User goes through checkout flow
- Adds items to cart manually
- Proceeds to payment page
- Signals "ready"
- System captures payment form state

### Use Case 4: Dynamic Content Testing
- User navigates to infinite scroll page
- Scrolls down to load more content
- Waits for specific content to appear
- Signals "ready"
- System captures DOM at that specific state

## Proposed Workflow Architecture

### Phase 1: Launch & Pause
```bash
./interactive-debug.sh "http://localhost:3000" --mode=launch-and-wait
```

**What happens:**
1. Chrome opens in headed mode with debugging enabled
2. Script prints connection info (port, page ID)
3. Script **enters wait state** listening for signals
4. User sees message: "Chrome is ready. Interact freely. Press ENTER when ready to capture."

### Phase 2: User Interaction
- Chrome window is visible and fully interactive
- User can:
  - Navigate to any page
  - Fill forms
  - Click buttons
  - Log in
  - Wait for AJAX requests
  - Scroll
  - Open modals
  - Anything a normal user would do

### Phase 3: Signal Mechanism

**Option A: Keyboard Signal (Simple)**
```
[Script waiting] Press ENTER to capture current state...
```
User presses ENTER → Script starts capturing

**Option B: CLI Command (Flexible)**
```bash
# Terminal 1: Launch and wait
./interactive-debug.sh "http://localhost:3000" --wait

# Terminal 2: User signals when ready
./interactive-signal.sh capture --selector="input[name='email']"
```

**Option C: File-Based Signal (Cross-Platform)**
```bash
# Script watches for signal file
watch -n 1 '[ -f /tmp/chrome-debug-signal ] && echo "READY"'

# User creates file when ready
touch /tmp/chrome-debug-signal
```

**Option D: HTTP Endpoint (Advanced)**
```bash
# Script starts mini HTTP server
http://localhost:8888/capture?selector=input[name='email']

# User clicks bookmark or uses curl
curl http://localhost:8888/capture
```

### Phase 4: Capture
Once signaled, script captures specified data:
- DOM snapshot
- Form field values
- Cookies
- LocalStorage/SessionStorage
- Network activity (from point of signal onward)
- Console logs

## Implementation Design

### File Structure
```
browser-debugger/
├── interactive-debug.sh          # Main workflow orchestrator
├── interactive-signal.sh         # Signal sender (Option B)
├── interactive-capture.py        # Capture logic
├── chrome-launcher.sh            # Existing launcher
└── cdp-dom-monitor.py           # Existing monitor
```

### interactive-debug.sh (Main Script)

```bash
#!/bin/bash
# Interactive debugging workflow

# Parse options
MODE="launch-and-wait"  # or "launch-and-monitor"
SIGNAL_METHOD="keyboard"  # or "file", "http", "cli"
CAPTURE_TARGET=""  # What to capture when signaled
WAIT_DURATION="infinite"  # How long to wait for signal

# Step 1: Launch Chrome in headed mode
echo "🚀 Launching Chrome in headed mode..."
LAUNCHER_OUTPUT=$(./chrome-launcher.sh --mode=headed --port=auto --url="$URL")

# Extract connection info
PORT=$(echo "$LAUNCHER_OUTPUT" | jq -r '.port')
PAGE_ID=$(echo "$LAUNCHER_OUTPUT" | jq -r '.page_id')
CHROME_PID=$(echo "$LAUNCHER_OUTPUT" | jq -r '.pid')

echo ""
echo "✅ Chrome is ready!"
echo ""
echo "📋 Connection Info:"
echo "   Port: $PORT"
echo "   Page ID: $PAGE_ID"
echo "   PID: $CHROME_PID"
echo ""

# Step 2: Enter wait state based on signal method
case "$SIGNAL_METHOD" in
    "keyboard")
        echo "👉 Interact with Chrome freely."
        echo "   When ready to capture, press ENTER here..."
        read -r
        ;;
    "file")
        SIGNAL_FILE="/tmp/chrome-debug-signal-$$"
        rm -f "$SIGNAL_FILE"
        echo "👉 Interact with Chrome freely."
        echo "   When ready, run: touch $SIGNAL_FILE"
        while [ ! -f "$SIGNAL_FILE" ]; do
            sleep 1
        done
        ;;
    "http")
        # Start HTTP listener in background
        python3 -m http.server 8888 &
        HTTP_PID=$!
        echo "👉 Interact with Chrome freely."
        echo "   When ready, visit: http://localhost:8888/capture"
        # Wait for HTTP signal
        ;;
    "cli")
        SIGNAL_FILE="/tmp/chrome-debug-command-$$"
        rm -f "$SIGNAL_FILE"
        echo "👉 Interact with Chrome freely."
        echo "   When ready, run: ./interactive-signal.sh capture --port=$PORT"
        while [ ! -f "$SIGNAL_FILE" ]; do
            sleep 1
        done
        # Read capture command from file
        CAPTURE_CMD=$(cat "$SIGNAL_FILE")
        ;;
esac

# Step 3: Capture on signal
echo ""
echo "📸 Signal received! Capturing state..."
./interactive-capture.py --port="$PORT" --page-id="$PAGE_ID" "$CAPTURE_TARGET"

# Step 4: Cleanup
echo ""
echo "🧹 Cleaning up..."
kill "$CHROME_PID" 2>/dev/null || true
```

### interactive-signal.sh (Signal Sender)

```bash
#!/bin/bash
# Send signal to waiting debug session

COMMAND="$1"
PORT=""
SELECTOR=""

# Parse arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --port=*)
            PORT="${1#--port=}"
            ;;
        --selector=*)
            SELECTOR="${1#--selector=}"
            ;;
    esac
    shift
done

case "$COMMAND" in
    "capture")
        # Find the waiting session
        SIGNAL_FILE=$(ls /tmp/chrome-debug-command-* 2>/dev/null | head -1)
        if [ -z "$SIGNAL_FILE" ]; then
            echo "❌ No waiting debug session found"
            exit 1
        fi

        # Write capture command
        echo "CAPTURE $SELECTOR" > "$SIGNAL_FILE"
        echo "✅ Signal sent"
        ;;
    "list")
        # List waiting sessions
        ls -la /tmp/chrome-debug-command-* 2>/dev/null || echo "No sessions"
        ;;
esac
```

### interactive-capture.py (Capture Logic)

```python
#!/usr/bin/env python3
"""
Capture browser state on demand
"""
import asyncio
import websockets
import json
import sys
import argparse

async def capture_state(port, page_id, selector=None):
    ws_url = f'ws://localhost:{port}/devtools/page/{page_id}'

    async with websockets.connect(ws_url) as ws:
        # Get current URL
        await ws.send(json.dumps({
            'id': 1,
            'method': 'Runtime.evaluate',
            'params': {
                'expression': 'window.location.href',
                'returnByValue': True
            }
        }))
        response = await ws.recv()
        result = json.loads(response)
        url = result['result']['result']['value']

        print(f"📍 Current URL: {url}")
        print()

        # Capture form fields
        if selector:
            capture_expr = f'''
                (function() {{
                    const el = document.querySelector("{selector}");
                    return el ? {{
                        tag: el.tagName.toLowerCase(),
                        type: el.type || null,
                        name: el.name || null,
                        id: el.id || null,
                        value: el.value || '',
                        checked: el.checked || null
                    }} : null;
                }})()
            '''
        else:
            # Capture all form fields
            capture_expr = '''
                (function() {
                    const fields = Array.from(document.querySelectorAll('input, textarea, select'));
                    return fields.map(el => ({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || null,
                        name: el.name || null,
                        id: el.id || null,
                        value: el.value || '',
                        checked: el.checked || null
                    }));
                })()
            '''

        await ws.send(json.dumps({
            'id': 2,
            'method': 'Runtime.evaluate',
            'params': {
                'expression': capture_expr,
                'returnByValue': True
            }
        }))

        response = await ws.recv()
        result = json.loads(response)

        if 'result' in result and 'result' in result['result']:
            data = result['result']['result']['value']

            if selector:
                print("📋 Captured Field:")
                print(json.dumps(data, indent=2))
            else:
                print(f"📋 Captured {len(data)} Fields:")
                for field in data:
                    print(f"  • {field['name'] or field['id']}: '{field['value']}'")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Capture browser state')
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--page-id', required=True)
    parser.add_argument('--selector', help='CSS selector for specific element')

    args = parser.parse_args()

    asyncio.run(capture_state(args.port, args.page_id, args.selector))
```

## Recommended Approach

**For simplicity and universal compatibility, I recommend starting with Option A + B:**

### Option A: Keyboard Signal (Default)
- **Pros:** Simple, works everywhere, no dependencies
- **Cons:** Single terminal only, user must stay in terminal
- **Best for:** Quick testing, simple workflows

### Option B: CLI Command (Advanced)
- **Pros:** Multi-terminal, flexible, can specify what to capture
- **Cons:** Requires second terminal window
- **Best for:** Complex workflows, multiple capture points

## Example Workflows

### Workflow 1: Simple Form Capture
```bash
# Launch and wait
./interactive-debug.sh "http://localhost:3000/signin" --signal=keyboard

# [User fills form in browser]
# [User presses ENTER in terminal]

# Output:
# 📋 Captured 2 Fields:
#   • email: 'user@example.com'
#   • password: '********'
```

### Workflow 2: Multi-Step with CLI Signals
```bash
# Terminal 1: Launch and wait
./interactive-debug.sh "http://localhost:3000" --signal=cli

# [User navigates to page 1]

# Terminal 2: Capture state at step 1
./interactive-signal.sh capture --selector="input[name='search']"

# [User proceeds to page 2]

# Terminal 2: Capture state at step 2
./interactive-signal.sh capture --selector="input[name='email']"

# Terminal 1: Stop monitoring
# Ctrl+C
```

### Workflow 3: Authenticated Session Testing
```bash
# Launch and wait
./interactive-debug.sh "http://localhost:3000/login" --signal=keyboard --capture=all

# User manually:
# 1. Logs in with 2FA
# 2. Navigates to dashboard
# 3. Presses ENTER

# Output:
# 📍 Current URL: http://localhost:3000/dashboard
# 🍪 Cookies: auth_token=xyz123...
# 📋 LocalStorage: {user_id: "12345", theme: "dark"}
# 📋 Form Fields: [...]
```

## Implementation Phases

### Phase 1: MVP (Minimal Viable Product)
- ✅ Chrome launcher with headed mode (DONE)
- ✅ CDP connection (DONE)
- ⬜ Keyboard signal implementation
- ⬜ Basic capture (form fields only)

### Phase 2: Enhanced Features
- ⬜ CLI signal implementation
- ⬜ Multiple capture points in single session
- ⬜ Capture cookies and storage

### Phase 3: Advanced Features
- ⬜ HTTP signal endpoint
- ⬜ Real-time monitoring between signals
- ⬜ Diff between capture points
- ⬜ Network activity capture
- ⬜ Screenshot on capture

## Configuration Options

```bash
./interactive-debug.sh <URL> [OPTIONS]

Options:
  --signal=<keyboard|file|cli|http>    How to signal ready state (default: keyboard)
  --capture=<fields|cookies|storage|network|all>  What to capture (default: fields)
  --selector=<CSS>                     Specific element to capture (optional)
  --wait=<seconds>                     Max wait time (default: infinite)
  --output=<file>                      Save capture to file (default: stdout)
  --continue                           Keep Chrome open after capture
```

## Benefits of This Approach

1. **Universal:** Works with any page, any interaction
2. **Non-intrusive:** User interacts normally, no special setup
3. **Flexible:** Multiple signal methods for different scenarios
4. **Reusable:** Same workflow for forms, APIs, auth, etc.
5. **Testable:** Can script the workflow for automated testing later

## Questions to Address

1. **Multiple pages:** What if user navigates away from initial URL?
   - Solution: Always capture from currently active page

2. **Multiple tabs:** What if user opens new tabs?
   - Solution: Let user specify which tab (page ID) or capture all

3. **Cleanup:** What if user forgets to signal?
   - Solution: Add timeout option, auto-cleanup after X minutes

4. **Persistence:** Should we keep Chrome profile between runs?
   - Solution: Option to use persistent vs ephemeral profile

5. **Error handling:** What if capture fails?
   - Solution: Retry mechanism, fallback to full DOM dump

## Next Steps

To implement this:

1. Create `interactive-debug.sh` with keyboard signal support (simplest)
2. Test with your signin form use case
3. Add CLI signal support for advanced workflows
4. Document common patterns and examples
5. Consider adding to SKILL.md as primary workflow
