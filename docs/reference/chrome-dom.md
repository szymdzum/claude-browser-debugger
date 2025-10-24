# Chrome DOM Testing Scenarios

Test prompts for validating the interactive workflow with the browser-debugger skill. These scenarios cover both automated and manual interaction workflows on localhost:3000.

## Test Prompts for localhost:3000

### Scenario 1: Quick DOM Snapshot (Headless)
```
Use browser-debugger skill to capture the DOM of http://localhost:3000 in headless mode with a 5 second idle timeout. Include console logs and provide a summary.
```

**Expected workflow:** Launch headless Chrome → Wait for page load → Capture DOM + console → Generate summary → Cleanup

---

### Scenario 2: Interactive Registration Flow (Headed)
```
Use browser-debugger skill to launch http://localhost:3000/customer/register in headed mode. Let me fill out the registration form manually, then extract the DOM and console logs after I'm done.
```

**Expected workflow:** Launch visible Chrome → User fills form → Agent waits → Extract DOM on demand → Keep Chrome open for follow-up

---

### Scenario 3: Sign-In Flow with Network Monitoring
```
Launch http://localhost:3000/signin with browser-debugger in headed mode. Monitor network requests and console logs while I test the login flow. After I submit the form, capture everything.
```

**Expected workflow:** Launch with console/network collectors → User interacts → Agent captures network traffic → Extract final state

---

### Scenario 4: Multi-Step User Journey
```
Use browser-debugger to help me debug the checkout flow on localhost:3000. Start at the homepage, let me navigate to the product page, add to cart, and proceed to checkout. Capture the DOM at each major step when I tell you.
```

**Expected workflow:** Persistent Chrome session → Multiple DOM extractions → Agent responds to "capture now" prompts

---

### Scenario 5: Form Validation Testing
```
Launch localhost:3000/contact-form in headed mode with browser-debugger. I want to test various validation states. Keep console logging active and extract the DOM after I trigger each validation error.
```

**Expected workflow:** Launch with console monitoring → User triggers errors → Multiple extractions showing different form states

---

### Scenario 6: Network Request Inspection
```
Use browser-debugger to monitor network activity on localhost:3000/dashboard. Launch in headless mode, wait 10 seconds for initial API calls to complete, then show me all network requests with response bodies.
```

**Expected workflow:** Launch with `cdp-network-with-body.py` → Capture API responses → Summarize endpoints and payloads

---

### Scenario 7: JavaScript Error Debugging
```
Launch localhost:3000/broken-page with browser-debugger in headed mode. Monitor the console for JavaScript errors while I interact with the page. After I reproduce the bug, show me the error stack traces.
```

**Expected workflow:** Launch with `cdp-console.py` → User reproduces bug → Agent extracts console errors with timestamps

---

### Scenario 8: Responsive Design Testing
```
Use browser-debugger to capture the mobile view of localhost:3000. Launch in headless mode with mobile viewport, wait 5 seconds, then extract the DOM and take a screenshot.
```

**Expected workflow:** Launch with `--window-size=375,667` → Capture mobile DOM → (Future: screenshot via CDP)

---

## Workflow Validation Checklist

After running these tests, validate:

- [ ] **Headed mode stays open** until user indicates completion
- [ ] **WebSocket URL refreshes** correctly after navigation
- [ ] **Console logs stream** in real-time during interaction
- [ ] **Network requests** capture timing + headers + bodies
- [ ] **Multiple extractions** work in same session
- [ ] **Error recovery** handles port conflicts, stale WebSocket URLs
- [ ] **Cleanup happens** only when user confirms done
- [ ] **Chrome 136+ profile isolation** works (`--user-data-dir`)

## Debugging Commands (If Things Break)

```bash
# Check Chrome process
ps aux | grep "chrome.*9222"

# Get current WebSocket URL
curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .webSocketDebuggerUrl'

# Manual DOM extraction
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')" \
  | jq -r '.result.result.value'

# Kill stuck Chrome
pkill -f "chrome.*9222"
```

## Success Criteria

**Optimal workflow achieved when:**
1. Headed mode requires minimal agent intervention (just launch + extract on demand)
2. Agent correctly interprets "I'm done interacting" signals
3. WebSocket URLs stay fresh across navigation
4. Console/network logs stream without blocking user interaction
5. Multiple extractions work without re-launching Chrome
