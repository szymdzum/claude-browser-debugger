# Chrome 136+ CDP Headed Mode Incident Report

**Date:** 2025-10-23
**Status:** ✅ RESOLVED
**Chrome Version:** 141.0.7390.109
**Impact:** Breaking change for headed Chrome CDP connections without `--user-data-dir`

---

## Executive Summary

Chrome 136 (March 2025) introduced a security policy that blocks Chrome DevTools Protocol (CDP) commands when `--remote-debugging-port` is used with the default user profile. This caused all headed Chrome CDP connections to hang indefinitely with no error message.

**Root Cause:** Chrome security change to prevent cookie/credential theft
**Solution:** Always use `--user-data-dir=<non-default-path>` with headed Chrome
**Status:** Resolved - `chrome-launcher.sh` already implements the fix

---

## The Chrome 136 Security Change

### What Changed

Starting with Chrome 136 (released March 2025), Google introduced a security policy:

1. **Blocks CDP on default profile**
   - `--remote-debugging-port` is silently ignored when using default user profile
   - WebSocket connection succeeds, but Chrome never responds to CDP commands
   - No error message - just infinite hang

2. **Security Rationale**
   - Prevents malicious tools from attaching to user's primary Chrome profile
   - Protects against cookie theft, credential harvesting, session hijacking
   - Forces debugging sessions onto isolated profiles with separate encryption keys

3. **What Still Works**
   - ✅ Headless Chrome (auto-creates isolated profile)
   - ✅ Headed Chrome with `--user-data-dir=<non-default-path>`
   - ✅ Plain Chromium builds (policy doesn't apply)

4. **What Breaks**
   - ❌ Headed Chrome without `--user-data-dir` flag
   - ❌ Any CDP tool pointing at default profile directory

### Official Sources

- **Chrome Developers Blog:** https://developer.chrome.com/blog/remote-debugging-port
- **Release Notes:** https://habr.com/ru/news/906164/
- **Affected Versions:** Chrome 136+ (not Chromium)

---

## Investigation Timeline

### Initial Symptoms

- All Python async/websockets scripts hung indefinitely with headed Chrome
- No error messages, no timeouts
- WebSocket connection established successfully
- Messages sent to Chrome, but Chrome never responded

### Hypothesis 1: Python Version Issue ❌

**Theory:** Python 3.14.0 incompatibility with websockets library

**Testing:**
```bash
# Installed Python 3.11.14 via Homebrew
brew install python@3.11

# Created use-python311.sh switcher script
# Installed websockets 15.0.1 for Python 3.11
# Ran tests with Python 3.11
```

**Result:** ❌ Still hung! Python version was NOT the problem.

### Hypothesis 2: WebSocket Library Issue ❌

**Theory:** websockets library bug

**Evidence Against:**
- Connection established successfully
- HTTP 101 upgrade succeeded
- WebSocket state = OPEN
- Messages sent successfully

**Result:** ❌ Library works correctly. Not the problem.

### Breakthrough: Debug Instrumentation ✅

Created `debug-cdp-connection.py` with PYTHONASYNCIODEBUG=1:

**Headed Chrome (default profile):**
```
2025-10-23 16:23:11,671 - websockets.client - DEBUG - = connection is OPEN
2025-10-23 16:23:11,671 - websockets.client - DEBUG - > TEXT '{"id": 1, "method": "Runtime.evaluate", ...
[HANGS FOREVER - NO RESPONSE FROM CHROME]
```

**Headless Chrome:**
```
2025-10-23 16:27:35,535 - websockets.client - DEBUG - = connection is OPEN
2025-10-23 16:27:35,535 - websockets.client - DEBUG - > TEXT '{"id": 1, "method": "Runtime.evaluate", ...
2025-10-23 16:27:35,536 - websockets.client - DEBUG - < TEXT '{"id":1,"result":{"result":{"type":"number","value":4}}}
✅ SUCCESS: Connection worked!
```

**Discovery:** Chrome (headed mode) doesn't respond, but headless works perfectly!

### Root Cause Identified ✅

**Chrome 136+ security policy blocks CDP on default profile.**

**Confirmation Test - Headed Chrome WITH `--user-data-dir`:**
```bash
chrome --user-data-dir=/tmp/chrome-headed-debug --remote-debugging-port=9228 URL
```

**Result:**
```
2025-10-23 16:36:12,402 - websockets.client - DEBUG - < TEXT '{"id":1,"result":{"result":{"type":"number","value":4}}}
✅ SUCCESS: Connection worked!
```

---

## Test Results

### Comparison Matrix

| Mode | Command | CDP Works? | Response Time |
|------|---------|------------|---------------|
| Headless | `--headless=new --remote-debugging-port=PORT` | ✅ Yes | < 1 second |
| Headed (default profile) | `--remote-debugging-port=PORT` | ❌ No | Hangs forever |
| Headed (with user-data-dir) | `--user-data-dir=PATH --remote-debugging-port=PORT` | ✅ Yes | < 1 second |

### Headless Mode (Port 9226) ✅

```bash
chrome --headless=new --remote-debugging-port=9226 URL
```

**Test 1: Simple CDP Command**
```json
{"id": 1, "result": {"result": {"type": "number", "value": 4}}}
```
✅ `2 + 2 = 4` evaluated correctly

**Test 2: Form State Inspection**
```json
{
  "inputs": [
    {"name": "email", "type": "email", "value": ""},
    {"name": "password", "type": "password", "value": ""}
  ]
}
```
✅ All form inputs extracted successfully

### Headed Mode WITHOUT `--user-data-dir` (Port 9225) ❌

```bash
chrome --remote-debugging-port=9225 URL
```

**Behavior:**
- ✅ Chrome launches
- ✅ HTTP endpoint responds (`curl http://localhost:9225/json`)
- ✅ WebSocket connection establishes
- ✅ Message sent to Chrome
- ❌ **Chrome never responds** (blocked by Chrome 136+ policy)
- ❌ Script hangs indefinitely

### Headed Mode WITH `--user-data-dir` (Port 9228) ✅

```bash
chrome --user-data-dir=/tmp/chrome-headed-debug --remote-debugging-port=9228 URL
```

**Test 1: Simple CDP Command**
```json
{"id": 1, "result": {"result": {"type": "number", "value": 4}}}
```
✅ Evaluated correctly, < 1 second

**Test 2: Form State Inspection**
```json
{
  "inputs": [
    {"name": "email", "type": "email", "value": "works@kek.com"},
    {"name": "password", "type": "password", "value": ""}
  ]
}
```
✅ **VISIBLE BROWSER + Real-time CDP access!**

User can type in the browser and CDP can read values immediately.

---

## The Solution

### Correct Chrome Launch Command

**❌ BROKEN (Chrome 136+):**
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  "http://localhost:3000"
```

**✅ CORRECT (Chrome 136+):**
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir=~/.chrome-debug-profile \
  --remote-debugging-port=9222 \
  "http://localhost:3000"
```

### Our Implementation

The `chrome-launcher.sh` already implements the fix correctly:

```bash
# Profile resolution (chrome-launcher.sh:126-139)
if [ -z "$PROFILE" ]; then
    if [ "$MODE" = "headless" ]; then
        RESOLVED_PROFILE="/tmp/chrome-headless-$$"
    else
        RESOLVED_PROFILE="$HOME/.chrome-debug-profile"  # ✅ Correct!
    fi
fi

# Chrome args (chrome-launcher.sh:167-172)
CHROME_ARGS=(
    --remote-debugging-port="$RESOLVED_PORT"
    --user-data-dir="$RESOLVED_PROFILE"  # ✅ Always set!
    --no-first-run
    --no-default-browser-check
)
```

**Result:** Our orchestrator already works correctly with Chrome 136+!

---

## Files Created During Investigation

### Diagnostic Scripts (Now in `scripts/diagnostics/`)

1. **`debug-cdp-connection.py`** - Instrumented CDP test with full logging
   - Usage: `python3 debug-cdp-connection.py <page_id> <port>`
   - Shows WebSocket flow step-by-step
   - Reveals where Chrome stops responding

2. **`check-form-state.py`** ❌ OBSOLETE - Removed
   - Replaced by orchestrator + collectors

3. **`get-dom.py`** ❌ OBSOLETE - Removed
   - Replaced by orchestrator + collectors

4. **`use-python311.sh`** ❌ OBSOLETE - Removed
   - Python version not the issue
   - Chrome 136 change makes this irrelevant

### Smoke Test (Now in `tests/`)

**`smoke-test-headed.sh`** - Validates headed Chrome CDP functionality

```bash
./tests/smoke-test-headed.sh
```

**What it tests:**
- Chrome version detection
- Headed launch with `--user-data-dir`
- CDP endpoint availability
- Runtime.evaluate functionality
- DOM access
- Auto-cleanup

**Use cases:**
- After Chrome updates
- CI/CD validation
- Debugging setup issues

### Documentation (Now in `docs/guides/`)

1. **`chrome-136-incident.md`** (this file)
   - Comprehensive incident report
   - Investigation timeline
   - Test results
   - Solution details

2. **`interactive-workflow-design.md`**
   - Headed mode workflow design
   - User interaction patterns

3. **`launcher-contract.md`**
   - chrome-launcher.sh API specification
   - JSON output format
   - Error codes

---

## Lessons Learned

### What We Got Right ✅

1. **Systematic debugging approach**
   - Started with Python version hypothesis
   - Tested with different Python versions
   - Used instrumentation to identify exact hang point
   - Compared headless vs headed behavior

2. **chrome-launcher.sh design**
   - Already set `--user-data-dir` for headed mode
   - Anticipated the need for profile isolation
   - Proper defaults for each mode

3. **Comprehensive testing**
   - Tested all three modes (headless, headed without flag, headed with flag)
   - Confirmed exact behavior differences
   - Validated fix with real-world use case

### What We Learned ❌

1. **Silent failures are the worst**
   - Chrome gives no error when blocking CDP
   - WebSocket connects successfully (misleading)
   - No timeout, no error message, just infinite wait

2. **Security changes can break tooling**
   - Chrome 136 change was undocumented in many places
   - Breaking change with no migration guide
   - Affects all CDP tools, not just ours

3. **Default assumptions are dangerous**
   - Assumed headed/headless CDP behavior was identical
   - Assumed Python version was the issue (Occam's Razor failed us)
   - Needed instrumentation to see the real problem

### Recommendations for Future

1. **Always use `--user-data-dir` for headed Chrome**
   - Even if Chrome version < 136
   - Provides isolation and security
   - Future-proofs against similar changes

2. **Add smoke tests for critical paths**
   - `smoke-test-headed.sh` catches this class of issue
   - Run after Chrome updates
   - Include in CI/CD if possible

3. **Monitor Chrome release notes**
   - Security changes often affect CDP
   - Subscribe to Chrome DevTools blog
   - Test beta/canary versions early

4. **Instrument failures early**
   - Don't guess - add logging
   - PYTHONASYNCIODEBUG=1 was critical
   - Step-by-step output reveals exact failure point

---

## Impact on Users

### Before Fix (Headed mode didn't work)

Users could not:
- ❌ Monitor DOM changes in visible browser
- ❌ Track network requests during manual interaction
- ❌ Debug forms while filling them out
- ❌ Test workflows requiring human input

**Workaround:** Use headless mode only (no visibility)

### After Fix (Headed mode works perfectly)

Users can now:
- ✅ Open visible Chrome window
- ✅ Type in forms manually
- ✅ CDP monitors changes in real-time
- ✅ See network requests as they happen
- ✅ Track console logs during interaction
- ✅ Test complete user workflows

**Example use case (now working):**
```bash
# Launch visible browser with CDP access
chrome --user-data-dir=~/.chrome-debug-profile \
       --remote-debugging-port=9222 \
       "http://localhost:3000/signin"

# Monitor in real-time while user interacts
python3 check-form-state.py <page_id> 9222

# Result: User types "test@example.com" in browser
# CDP sees: {"email": "test@example.com"} immediately
```

---

## References

### External Documentation

- **Chrome Developers Blog:** "Chrome 136: Remote debugging port security"
  https://developer.chrome.com/blog/remote-debugging-port

- **Community Reports:** Habr.com Chrome 136 release notes
  https://habr.com/ru/news/906164/

### Internal Documentation

- **Design:** `docs/guides/interactive-workflow-design.md`
- **API Spec:** `docs/guides/launcher-contract.md`
- **User Guide:** `SKILL.md`

### Related Scripts

- **Smoke Test:** `tests/smoke-test-headed.sh`
- **Diagnostics:** `scripts/diagnostics/debug-cdp-connection.py`
- **Launcher:** `chrome-launcher.sh`
- **Orchestrator:** Python CDP CLI (`cdp orchestrate`)

---

## Conclusion

The CDP headed mode hanging issue was caused by Chrome 136's security policy blocking CDP access to the default user profile. The fix is simple: always use `--user-data-dir` with a non-default path.

Our `chrome-launcher.sh` already implements this correctly (`$HOME/.chrome-debug-profile` for headed mode), so the orchestrator works out-of-the-box with Chrome 136+.

**Status:** ✅ **RESOLVED**

The browser-debugger skill now fully supports:
- ✅ Headless Chrome (automated testing)
- ✅ Headed Chrome (interactive debugging with visible browser)
- ✅ Real-time DOM/network/console monitoring
- ✅ Chrome 136+ compatibility

**Date Resolved:** 2025-10-23
**Validation:** Smoke test passes, real-world use case confirmed working
