# Headed Mode Workflow Guide

**Purpose**: Step-by-step guide for interactive testing workflow (launch → interact → extract → analyze)

**Estimated Time**: 5-10 minutes for experienced users, 15 minutes for first-time users

---

## 4-Phase Workflow Overview

1. **Launch** - Start Chrome in headed mode with monitoring
2. **Interact** - Perform manual testing in visible browser
3. **Extract** - Capture final application state
4. **Analyze** - Query extracted data for insights

---

## Phase 1: Launch Chrome in Headed Mode

**Command:**
```bash
./debug-orchestrator.sh "http://localhost:3000/customer/register" 3600 /tmp/my-test.log \
  --mode=headed --include-console
```

**Parameters:**
- `"http://localhost:3000/customer/register"` - URL to test
- `3600` - Session timeout in seconds (1 hour)
- `/tmp/my-test.log` - Network log output file
- `--mode=headed` - Visible Chrome window (vs headless)
- `--include-console` - Capture console logs

**Expected Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 CHROME WINDOW IS NOW OPEN AND READY!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 URL: http://localhost:3000/customer/register
⏱️  Session timeout: 60 minutes (3600s)
🔍 Monitoring: Network + Console logs
💾 Output: /tmp/my-test.log

🔧 Debug Info:
   Chrome PID: 12345
   Profile: /Users/you/.chrome-debug-profile

💬 You can now interact with the page.
   When you're done, let me know and I'll extract the final state.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Success Indicators:**
- ✅ Chrome window opens automatically
- ✅ Page loads at specified URL
- ✅ Notification appears within 3 seconds

**Duration:** 3-5 seconds

---

## Phase 2: Interact with the Page

**Actions:** Perform your manual testing:
- Fill out forms
- Click buttons and links
- Navigate between pages
- Trigger interactions you want to debug
- Observe errors or unexpected behavior

**Tips:**
- Chrome stays open until timeout or manual close
- Network and console capture runs in background
- You can minimize/restore the browser window
- No commands needed during this phase

**Duration:** As needed for your test scenario (up to timeout)

---

## Phase 3: Extract Final State

**Basic Extraction:**
```bash
./extract-state.sh
```

**Custom Port/Directory:**
```bash
./extract-state.sh 9222 /tmp/my-test-state
```

**Parameters:**
- `9222` - CDP port (default, usually unchanged)
- `/tmp/my-test-state` - Output directory (created if missing)

**Expected Output:**
```
🔍 Validating Chrome connection on port 9222...
✅ Connected to Chrome on port 9222

🔍 Extracting page state...

   DOM... ✅ (234.5 KiB)
   Redux state... ✅ (15.2 KiB)
   Form data... ✅ (23 fields)
   localStorage... ✅ (8 keys)
   Cookies... ✅ (12 cookies)

📂 State saved to: /tmp/state-extract-20251024-143215

✅ All extractions successful!
```

**Files Created:**
- `dom.html` - Full page HTML
- `redux-state.json` - Redux store snapshot (if exposed)
- `form-data.json` - All input/select/textarea values
- `localstorage.json` - localStorage key-value pairs
- `cookies.json` - All cookies for the domain
- `summary.json` - Extraction metadata and status

**Duration:** 5-10 seconds

---

## Phase 4: Analyze Extracted State

### Common Queries

**Check form field values:**
```bash
jq '.[] | select(.name == "email") | .value' /tmp/state-extract-*/form-data.json
```

**Find data in Redux state:**
```bash
jq '.customer.email' /tmp/state-extract-*/redux-state.json
```

**Search DOM for errors:**
```bash
grep -i 'error' /tmp/state-extract-*/dom.html
grep 'class="error"' /tmp/state-extract-*/dom.html
```

**List localStorage keys:**
```bash
jq 'keys' /tmp/state-extract-*/localstorage.json
```

**Check specific cookie:**
```bash
jq '.[] | select(.name == "sessionId")' /tmp/state-extract-*/cookies.json
```

**Inspect button state:**
```bash
grep -A 3 'id="submit-button"' /tmp/state-extract-*/dom.html
```

### Advanced Analysis

**Redux action history (from console logs):**
```bash
grep 'action' /tmp/my-test-console.log
```

**Network requests analysis:**
```bash
grep 'POST\|GET' /tmp/my-test.log | grep -i 'api'
```

**Form validation errors:**
```bash
jq '.[] | select(.value == "" and .required == true)' /tmp/state-extract-*/form-data.json
```

---

## Advanced: Redux Store Injection (Optional)

**When to use:** Need direct Redux state access during interaction (before extraction)

**Steps:**

1. Get WebSocket URL:
```bash
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
```

2. Inject Redux accessor:
```bash
cat inject-redux.js | websocat -n1 "$WS_URL"
```

3. Verify in Chrome DevTools Console:
```javascript
window.__EXPOSED_REDUX_STORE__.getState()
```

4. Extract via CDP (optional):
```bash
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"JSON.stringify(window.__EXPOSED_REDUX_STORE__.getState())","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" | jq -r '.result.result.value'
```

---

## Troubleshooting

### Port 9222 Already in Use

**Symptom:** `Error: Port 9222 already in use`

**Solution:**
```bash
pkill -f "chrome.*9222"
# Wait 2 seconds
./debug-orchestrator.sh ...  # Retry
```

---

### WebSocket URL Stale

**Symptom:** State extraction returns empty or errors after page navigation

**Solution:**
```bash
# Re-fetch WebSocket URL
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
# Use fresh URL in extraction commands
```

**Cause:** Page reloads or navigation invalidate the WebSocket connection

---

### Redux Store Not Found

**Symptom:** `redux-state.json` shows `"not_available"` in summary

**Solutions:**

**Option A:** Inject store accessor before extraction
```bash
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
cat inject-redux.js | websocat -n1 "$WS_URL"
./extract-state.sh  # Retry extraction
```

**Option B:** Use console log parser (see Phase 8 docs)

---

### Chrome Closes Prematurely

**Symptom:** Browser closes during interaction before you're done

**Solution:** Increase timeout duration
```bash
./debug-orchestrator.sh "URL" 7200 /tmp/test.log --mode=headed  # 2 hours instead of 1
```

---

### Extraction Fails - Chrome Not Running

**Symptom:** `❌ Chrome not running on port 9222`

**Solution:**
- Ensure headed mode session is still active
- Check Chrome PID from ready notification
- Restart debug-orchestrator.sh if needed

---

## Complete Example: Registration Form Testing

**Scenario:** Debug registration form, capture submitted data and validation errors

```bash
# 1. Launch headed mode
./debug-orchestrator.sh "http://localhost:3000/register" 1800 /tmp/register-test.log \
  --mode=headed --include-console

# Expected: Chrome opens with registration form
# Wait for ready notification

# 2. Interact (manual steps)
# - Fill email: test@example.com
# - Fill password: ********
# - Click "Create Account" button
# - Observe validation errors or success

# 3. Extract state
./extract-state.sh 9222 /tmp/register-state

# Expected output: 5 files created in /tmp/register-state/

# 4. Analyze
# Check if submit button was disabled
jq '.[] | select(.id == "submit-button") | .disabled' /tmp/register-state/form-data.json

# Find email in Redux
jq '.customer.email' /tmp/register-state/redux-state.json

# Check for error messages in DOM
grep -i 'error\|invalid' /tmp/register-state/dom.html

# View form field states
jq '.[] | {name, value, type}' /tmp/register-state/form-data.json
```

**Result:** Complete capture of registration flow for debugging validation issues

---

## Quick Reference

| Command | Purpose | Duration |
|---------|---------|----------|
| `./debug-orchestrator.sh URL 3600 LOG --mode=headed --include-console` | Launch Chrome | 3-5s |
| `./extract-state.sh [PORT] [DIR]` | Extract state | 5-10s |
| `cat inject-redux.js \| websocat -n1 $WS_URL` | Inject Redux | 1s |
| `jq '.field' OUTPUT/file.json` | Query JSON | <1s |
| `grep 'pattern' OUTPUT/dom.html` | Search DOM | <1s |

---

## Next Steps

- **Filter flag usage**: See [FILTER_FLAG_GUIDE.md](./FILTER_FLAG_GUIDE.md) for selective network body capture
- **Automation**: Create bash functions for common testing sequences
- **CI integration**: Use headless mode for automated regression tests
- **Advanced debugging**: Combine state snapshots with network logs and console output

---

## Related Documentation

- [Filter Flag Guide](./FILTER_FLAG_GUIDE.md) - Network body capture patterns
- [Chrome Launcher Contract](./LAUNCHER_CONTRACT.md) - chrome-launcher.sh API
- [Stage Test Results](../002-stage-test-result.md) - Original UX findings
- [Feature Quickstart](../../specs/001-interactive-dom-access/quickstart.md) - Original workflow
