# Browser Debugger - Quick Start Guide

## ✨ Simple Usage

Debug any page with network monitoring in one command:

```bash
.claude/skills/browser-debugger/debug-orchestrator.sh \
  "https://demo.example.com/customer/register?redirectTo=%2F" \
  --summary=both
```

That's it! The script will:
1. Start Chrome in headless mode
2. Enable network monitoring
3. Navigate to your URL
4. Capture all network requests/responses (and console logs if requested)
5. Show you a summary (add `--summary=json` or `--summary=both` for structured output)
6. Save detailed logs to `/tmp/page-debug.log`

## 📋 Examples

### Debug registration page (10 seconds)
```bash
.claude/skills/browser-debugger/debug-orchestrator.sh \
  "https://demo.example.com/customer/register?redirectTo=%2F" \
  10 \
  --summary=json
```

### Debug checkout with custom log file
```bash
.claude/skills/browser-debugger/debug-orchestrator.sh \
  "https://demo.example.com/checkout" \
  15 \
  /tmp/checkout-network.log
```

### Debug login with console + idle detection
```bash
.claude/skills/browser-debugger/debug-orchestrator.sh \
  "https://demo.example.com/login" \
  20 \
  /tmp/login-session.log \
  --include-console \
  --idle=3 \
  --summary=both
```

### Debug production site
```bash
.claude/skills/browser-debugger/debug-orchestrator.sh \
  "https://www.castorama.pl/customer/login" \
  20
```

### Capture specific API response bodies
```bash
.claude/skills/browser-debugger/debug-orchestrator.sh \
  "https://demo.example.com/customer/register?redirectTo=%2F" \
  15 \
  /tmp/marketing-data.log \
  --filter=marketingChannels
```

## 📊 What You Get

The script automatically analyzes and shows:
- **Total network requests** captured
- **HTTP status codes** (200, 404, 500, etc.)
- **Failed requests** with error messages
- **Top 10 requests** with URLs
- **Optional JSON summary** with counts, hosts, status breakdown
- **Console log breakdown** (entries, levels, sample errors) when `--include-console` is enabled

## 🔍 Manual Usage (Advanced)

If you need more control, use the CDP scripts directly:

```bash
# Step 1: Start Chrome
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new \
  --remote-debugging-port=9222 \
  about:blank &
sleep 3

# Step 2: Get Page ID
PAGE_ID=$(curl -s http://localhost:9222/json | \
  jq -r '.[] | select(.type == "page") | .id' | head -1)

# Step 3: Monitor network
timeout 10 python3 .claude/skills/browser-debugger/cdp-network.py \
  "$PAGE_ID" \
  "https://demo.example.com/customer/register?redirectTo=%2F" \
  > /tmp/network.log

# Step 4: Cleanup
pkill -f "chrome.*9222"
```

## 📝 Output Format

Network events are JSON formatted:

```json
{"event": "request", "url": "https://example.com/", "method": "GET", "requestId": "..."}
{"event": "response", "url": "https://example.com/", "status": 200, "statusText": "OK", "mimeType": "text/html", "requestId": "..."}
{"event": "failed", "errorText": "net::ERR_CONNECTION_REFUSED", "requestId": "..."}
```

## 🎯 Common Use Cases

### Finding API Calls
```bash
.claude/skills/browser-debugger/debug-orchestrator.sh "https://demo.example.com/mypage" 15
grep "api" /tmp/page-debug.log
```

### Checking for 404s
```bash
.claude/skills/browser-debugger/debug-orchestrator.sh "https://demo.example.com/mypage" 10
grep '"status":404' /tmp/page-debug.log
```

### Monitoring Failed Requests
```bash
.claude/skills/browser-debugger/debug-orchestrator.sh "https://demo.example.com/mypage" 10
grep 'event.*failed' /tmp/page-debug.log
```

## ⚙️ Parameters

```bash
debug-orchestrator.sh <URL> [duration] [output-file] \
  [--filter=pattern] [--summary=text|json|both] \
  [--include-console] [--console-log=path] [--idle=seconds]
```

- **URL** (required): The page to debug
- **duration** (optional): How long to monitor in seconds (default: 10)
- **output-file** (optional): Where to save logs (default: /tmp/page-debug.log)
- **--filter=pattern** (optional): Capture response bodies for URLs matching pattern
- **--summary=...** (optional): Choose `text` (default), `json`, or `both`
- **--include-console** (optional): Capture console output alongside network traffic
- **--console-log=path** (optional): Override the console log file path
- **--idle=seconds** (optional): Stop once the page has been idle for the specified time (duration still acts as a ceiling)

### Filter Mode

When you use `--filter`, the script:
- ✅ Only captures response bodies for URLs containing the filter string
- ✅ Shows the actual JSON/HTML content from matching responses
- ✅ Keeps output small by ignoring other requests
- ⚠️ Slightly slower due to extra API calls

**Example:**
```bash
# Capture marketingChannels API response body
debug-orchestrator.sh "https://demo.example.com/register" 15 /tmp/out.log --filter=marketingChannels
```

## 🚨 Troubleshooting

### Port 9222 in use
```bash
pkill -f "chrome.*9222"
# Wait a moment, then retry
```

### No network events captured
- Make sure your localhost server is running
- Try increasing the duration (some pages load slowly)
- Check if the page actually loads: `curl https://demo.example.com/your-page`

### "Failed to get page ID"
- Chrome might not have started fully - increase sleep time
- Check if Chrome is actually running: `lsof -i :9222`
