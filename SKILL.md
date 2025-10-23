---
name: Browser Debugger
description: Inspect websites using Chrome headless and Chrome DevTools Protocol. Extract DOM structure, monitor JavaScript console logs, and track network requests. Use when debugging websites, checking for JavaScript errors, monitoring API calls, analyzing network activity, or inspecting page structure.
---

# Browser Debugger

This skill enables you to inspect and debug websites using Chrome's headless mode and the Chrome DevTools Protocol (CDP).

## What this skill does

- **Extract DOM**: Get the fully rendered HTML structure after JavaScript execution
- **Monitor Console**: Capture JavaScript console logs, errors, warnings, and exceptions
- **Track Network**: Monitor HTTP requests, responses, and failures in real-time

## Prerequisites

Required tools and packages:

- **Python 3.7+** (usually pre-installed)
- **websockets library**: `pip3 install websockets --break-system-packages`
- **Chrome or Chromium** browser
- **jq**: For JSON parsing (install with `brew install jq` on macOS or `apt-get install jq` on Linux)
- **curl**: Usually pre-installed

Verify installation:
```bash
python3 --version
python3 -c "import websockets; print('websockets installed')"
jq --version
```

## Instructions

### Get DOM Snapshot

Use when you need to see the page structure or inspect HTML elements.

```bash
chrome --headless=new --dump-dom https://example.com
```

This outputs the complete rendered HTML to stdout. You can save it to a file or pipe it to other commands:

```bash
# Save to file
chrome --headless=new --dump-dom https://example.com > page.html

# Search for specific content
chrome --headless=new --dump-dom https://example.com | grep "error"
```

### Monitor Console Logs

Use when you need to debug JavaScript errors or see console output.

**Step 1: Start Chrome with debugging port**
```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
```

**Step 2: Wait for Chrome to start**
```bash
sleep 2
```

**Step 3: Get the page ID (filter for actual pages, not extensions)**
```bash
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)
```

**Step 4: Monitor console**
```bash
python3 cdp-console.py $PAGE_ID
```

Output format:
```json
{"type":"log","timestamp":1698765432,"message":"Hello world","stackTrace":null}
{"type":"error","timestamp":1698765433,"message":"Uncaught TypeError...","stackTrace":{...}}
```

Navigate to a different URL after connecting:
```bash
python3 cdp-console.py $PAGE_ID https://different-url.com
```

Use a different debugging port (default is 9222):
```bash
python3 cdp-console.py $PAGE_ID https://example.com --port=9223
```

### Monitor Network Activity

Use when you need to see what API calls a page makes or track resource loading.

Follow the same setup as console monitoring (Steps 1-3), then:

```bash
python3 cdp-network.py $PAGE_ID
```

Output format:
```json
{"event":"request","url":"https://api.example.com/data","method":"GET","requestId":"..."}
{"event":"response","url":"https://api.example.com/data","status":200,"statusText":"OK","mimeType":"application/json","requestId":"..."}
{"event":"failed","errorText":"net::ERR_CONNECTION_REFUSED","requestId":"..."}
```

## Complete Workflows

### Workflow: Debug a website completely

```bash
URL="https://example.com"

# Step 1: Get DOM structure
echo "=== Fetching DOM ==="
chrome --headless=new --dump-dom $URL > /tmp/dom.html
echo "DOM saved ($(wc -l < /tmp/dom.html) lines)"

# Step 2: Start Chrome with debugging
echo "=== Starting Chrome ==="
chrome --headless=new --remote-debugging-port=9222 $URL &
CHROME_PID=$!
sleep 2

# Step 3: Get page ID
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
echo "Page ID: $PAGE_ID"

# Step 4: Monitor console and network
echo "=== Monitoring ==="
python3 cdp-console.py $PAGE_ID > /tmp/console.log &
CONSOLE_PID=$!
python3 cdp-network.py $PAGE_ID > /tmp/network.log &
NETWORK_PID=$!

# Wait for activity
sleep 10

# Step 5: Stop monitoring
kill $CONSOLE_PID $NETWORK_PID $CHROME_PID 2>/dev/null

# Step 6: Analyze results
echo "=== Analysis ==="
echo "Console errors:"
grep '"type":"error"' /tmp/console.log | jq -r '.message'

echo -e "\nNetwork failures:"
grep '"event":"failed"' /tmp/network.log | jq -r '.errorText'

echo -e "\nTotal elements: $(grep -o '<[a-zA-Z][^>]*>' /tmp/dom.html | wc -l)"
```

### Workflow: Check for JavaScript errors only

```bash
URL="https://example.com"

chrome --headless=new --remote-debugging-port=9222 $URL &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')

# Monitor for 10 seconds and filter errors
timeout 10 python3 cdp-console.py $PAGE_ID | \
  jq -r 'select(.type == "error") | .message'

# Cleanup
pkill -f "chrome.*9222"
```

### Workflow: List all API calls

```bash
URL="https://example.com"

chrome --headless=new --remote-debugging-port=9222 $URL &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')

# Monitor for 10 seconds and show all requests
timeout 10 python3 cdp-network.py $PAGE_ID | \
  jq -r 'select(.event == "request") | .method + " " + .url'

# Cleanup
pkill -f "chrome.*9222"
```

## Best Practices

1. **Always clean up Chrome processes**:
   ```bash
   pkill -f "chrome.*9222"
   ```

2. **Use timeouts to prevent hanging**:
   ```bash
   timeout 10 python3 cdp-console.py $PAGE_ID
   ```

3. **Save outputs for analysis**:
   ```bash
   python3 cdp-console.py $PAGE_ID > /tmp/console.log
   ```

4. **Wait for Chrome to start** (the `sleep 2` is critical):
   ```bash
   chrome --headless=new --remote-debugging-port=9222 $URL &
   sleep 2  # Don't skip this
   ```

5. **Verify page ID before monitoring**:
   ```bash
   PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
   if [ -z "$PAGE_ID" ] || [ "$PAGE_ID" = "null" ]; then
       echo "Error: Could not get page ID"
       exit 1
   fi
   ```

## Platform-Specific Notes

### Finding Chrome on different systems

```bash
# Auto-detect Chrome
if [[ "$OSTYPE" == "darwin"* ]]; then
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif command -v google-chrome &> /dev/null; then
    CHROME="google-chrome"
elif command -v chromium-browser &> /dev/null; then
    CHROME="chromium-browser"
else
    echo "Error: Chrome not found"
    exit 1
fi
```

## Troubleshooting

### "No module named 'websockets'"
```bash
pip3 install websockets --break-system-packages
# or
python3 -m pip install websockets --user
```

### "Connection refused" when connecting to CDP
```bash
# Check if Chrome is running
lsof -i :9222

# Verify debugging endpoint
curl http://localhost:9222/json
```

### Port 9222 already in use
```bash
# Kill existing Chrome processes
pkill -f "chrome.*9222"

# Or use a different port
chrome --headless=new --remote-debugging-port=9223 $URL &
```

### Scripts don't execute
```bash
chmod +x cdp-console.py
chmod +x cdp-network.py
```

## Examples

### Example: Find all console errors on a page

```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
timeout 10 python3 cdp-console.py $PAGE_ID | grep '"type":"error"'
pkill -f "chrome.*9222"
```

### Example: Check if a page makes API calls to a specific domain

```bash
chrome --headless=new --remote-debugging-port=9222 https://example.com &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
timeout 10 python3 cdp-network.py $PAGE_ID | grep 'api.example.com'
pkill -f "chrome.*9222"
```

### Example: Get the page title from DOM

```bash
chrome --headless=new --dump-dom https://example.com | \
  grep -o '<title>.*</title>' | \
  sed 's/<title>\(.*\)<\/title>/\1/'
```

## Quick Reference

```bash
# Get DOM
chrome --headless=new --dump-dom $URL

# Monitor console
chrome --headless=new --remote-debugging-port=9222 $URL &
sleep 2
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[0].id')
python3 cdp-console.py $PAGE_ID

# Monitor network
python3 cdp-network.py $PAGE_ID

# Monitor both (background)
python3 cdp-console.py $PAGE_ID > /tmp/console.log &
python3 cdp-network.py $PAGE_ID > /tmp/network.log &

# Cleanup
pkill -f "chrome.*9222"
```
