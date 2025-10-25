# Python CDP Pivot - Implementation Plan

## Overview

Phased migration from Bash/Python hybrid to Python-first CDP architecture. Each phase builds on the previous, with validation gates to ensure stability before proceeding.

**Guiding Principles**:
1. **Validate early**: Real Chrome integration tests from Phase 1
2. **One collector at a time**: Prove API ergonomics before mass migration
3. **Parallel paths in CI**: Run old and new implementations side-by-side to catch drift
4. **No big-bang**: Incremental feature rollout with compatibility wrappers

---

## Phase 1: Foundation - Minimal Connection Layer

**Goal**: Working `CDPConnection` with core features, validated against real Chrome.

### Deliverables

**1.1 Core Connection Class** (`scripts/cdp/connection.py`)
- [ ] `CDPConnection.__init__()` with minimal config (ws_url, timeout, logger)
- [ ] `async connect()` - establish WebSocket connection
- [ ] `async disconnect()` - close connection and cleanup
- [ ] `async execute(method, params)` - send CDP command, await response
- [ ] `subscribe(event, handler)` - register event callback (sync handlers only)
- [ ] `_receive_loop()` - background task to route messages
- [ ] Context manager support (`__aenter__`, `__aexit__`)

**1.2 Exception Hierarchy** (`scripts/cdp/errors.py`)
- [ ] `CDPError` (base)
- [ ] `CDPConnectionError`
- [ ] `CDPCommandError`
- [ ] `CDPTimeoutError`

**1.3 Unit Tests** (`tests/unit/test_connection.py`)
- [ ] Test command execution with mocked WebSocket
- [ ] Test event subscription and dispatch
- [ ] Test timeout handling
- [ ] Test graceful shutdown
- [ ] Mock `websockets.connect()` using `pytest-asyncio` + `unittest.mock`

**1.4 Integration Tests** (`tests/integration/test_connection_chrome.py`)
- [ ] Spin up headless Chrome on random port
- [ ] Connect via `CDPConnection`
- [ ] Execute `Runtime.evaluate` to extract `document.title`
- [ ] Subscribe to `Console.messageAdded` events
- [ ] Verify events received
- [ ] Teardown Chrome process

**Validation Gate**:
- ✅ All unit tests pass
- ✅ Integration test passes with real Chrome
- ✅ No domain replay, no retry logic (defer to Phase 2)

**Skip for Now**:
- Domain tracking (`_enabled_domains`)
- Reconnection logic (`_reconnect()`)
- Async event handlers
- Retry/backoff

---

## Phase 2: Validate Ergonomics - Refactor One Collector

**Goal**: Prove `CDPConnection` API is usable by porting one existing collector.

### Deliverables

**2.1 Refactor Console Collector** (`scripts/collectors/cdp-console.py`)

**Before** (direct WebSocket):
```python
async def main():
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Console.enable"}))
        async for message in ws:
            # Manual message parsing
```

**After** (using `CDPConnection`):
```python
from scripts.cdp.connection import CDPConnection

async def main():
    async with CDPConnection(ws_url) as conn:
        await conn.execute("Console.enable")

        def on_message(event):
            print(f"[{event['params']['level']}] {event['params']['text']}")

        conn.subscribe("Console.messageAdded", on_message)
        await asyncio.sleep(duration)
```

**2.2 Smoke Test**
- [ ] Run refactored console collector against real Chrome
- [ ] Verify output matches old implementation
- [ ] Check for memory leaks (long-running test, monitor RSS)

**2.3 API Refinements**
- [ ] Document any ergonomic issues discovered
- [ ] Adjust `CDPConnection` API if needed (e.g., add convenience methods)
- [ ] Update unit tests to reflect changes

**Validation Gate**:
- ✅ Refactored console collector produces identical output to old version
- ✅ No memory leaks after 5-minute run
- ✅ API feels natural to use (no awkward boilerplate)

**Defer**:
- Porting other collectors (wait for Phase 4)

---

## Phase 3: CLI Skeleton - Lock Flag Semantics

**Goal**: Argparse scaffolding with all subcommands stubbed, help text validated.

### Deliverables

**3.1 CLI Entry Point** (`scripts/cdp/cli.py`)
- [ ] Main argparse parser with global options
- [ ] Subparsers for all commands: `session`, `eval`, `dom`, `console`, `network`, `orchestrate`, `query`
- [ ] Each subcommand has stub `run()` function that prints "Not implemented"
- [ ] Global options: `--chrome-host`, `--chrome-port`, `--timeout`, `--format`, `--json`, `--log-level`, `--quiet`, `--verbose`, `--config`

**3.2 Mutual Exclusion Groups**
- [ ] All commands with target selection use `add_mutually_exclusive_group(required=True)`
- [ ] Test error messages for missing/conflicting args

**3.3 Command Stubs** (`scripts/cdp/commands/`)
- [ ] `session.py` - `setup_parser()` for `session list`, `session info`
- [ ] `eval_cmd.py` - `setup_parser()` for `eval`
- [ ] `dom.py` - `setup_parser()` for `dom dump`, `dom query`
- [ ] `console.py` - `setup_parser()` for `console stream`
- [ ] `network.py` - `setup_parser()` for `network record`
- [ ] `orchestrate.py` - `setup_parser()` for `orchestrate headless`, `orchestrate interactive`
- [ ] `query.py` - `setup_parser()` for `query`

**3.4 Help Text Integration Tests** (`tests/cli/test_help.py`)
- [ ] Test `--help` output for main command
- [ ] Test `--help` output for each subcommand
- [ ] Verify mutual exclusion error messages
- [ ] Regression test: flag changes break this test (intentional guard)

**3.5 Flag Validation Tests** (`tests/cli/test_flags.py`)
- [ ] Test `--format` vs `--output` separation
- [ ] Test `--json` alias works
- [ ] Test mutual exclusion for `--target` / `--url`
- [ ] Test required argument enforcement

**Validation Gate**:
- ✅ All `--help` invocations succeed
- ✅ Mutual exclusion enforced with clear error messages
- ✅ No ambiguous flag semantics

**Implementation Note**:
```python
# Example: dom dump with mutual exclusion
def setup_parser(subparsers):
    dump_parser = subparsers.add_parser("dump", help="Extract DOM as HTML")

    target_group = dump_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--target", help="Explicit target ID")
    target_group.add_argument("--url", help="Connect to first target matching URL pattern")

    dump_parser.add_argument("--output", help="Write to file (default: stdout)")
    dump_parser.add_argument("--wait-for", help="Wait for element to exist")
    dump_parser.add_argument("--pretty", action="store_true", help="Pretty-print HTML")
```

---

## Phase 4: Must-Have Commands - Incremental Implementation

**Goal**: Implement core commands in dependency order, validating each before proceeding.

### 4.1 `session list` (No CDP connection needed)

**Implementation**:
- [ ] Fetch targets from `http://localhost:9222/json` via `aiohttp`
- [ ] Filter by `--type`, `--url` regex
- [ ] Output JSON or table format
- [ ] No `CDPConnection` required (just HTTP)

**Tests**:
- [ ] Unit test with mocked HTTP response
- [ ] Integration test with real Chrome

**Validation**: `python -m scripts.cdp.cli session list --type page` returns valid JSON

---

### 4.2 `eval` (First CDP command)

**Implementation**:
- [ ] Use `CDPSession.connect_to_page(url_filter)` (new session manager)
- [ ] Implement `CDPSession` class (thin wrapper around `CDPConnection`)
- [ ] Execute `Runtime.evaluate` with expression
- [ ] Handle `--await` for promises
- [ ] Output result as JSON or text

**New Component**: `CDPSession` (`scripts/cdp/connection.py`)
```python
class CDPSession:
    def __init__(self, chrome_host="localhost", chrome_port=9222):
        self.chrome_host = chrome_host
        self.chrome_port = chrome_port

    async def list_targets(self) -> List[Dict]:
        """Fetch targets from /json endpoint"""

    async def connect_to_page(self, page_id=None, url_filter=None) -> CDPConnection:
        """Connect to specific page target"""
```

**Tests**:
- [ ] Unit test with mocked session
- [ ] Integration test: `eval "1+1"` returns `{"type": "number", "value": 2}`

**Validation**: `python -m scripts.cdp.cli eval "document.title" --url "example.com"` works

---

### 4.3 `dom dump` (First practical use case)

**Implementation**:
- [ ] Connect via `CDPSession`
- [ ] Execute `Runtime.evaluate` with `document.documentElement.outerHTML`
- [ ] Implement `--wait-for SELECTOR` polling logic
- [ ] Handle `--output FILE` vs stdout
- [ ] Optional `--pretty` formatting (requires `html5lib`)

**Wait-For Logic**:
```python
async def wait_for_selector(conn: CDPConnection, selector: str, timeout: float = 30.0):
    """Poll until selector exists"""
    start = time.time()
    while time.time() - start < timeout:
        result = await conn.execute("Runtime.evaluate", {
            "expression": f"!!document.querySelector({json.dumps(selector)})",
            "returnByValue": True
        })
        if result["result"]["value"]:
            return
        await asyncio.sleep(0.1)
    raise CDPTimeoutError(f"Timeout waiting for selector '{selector}'")
```

**Tests**:
- [ ] Unit test wait-for logic with mocked connection
- [ ] Integration test: dump DOM from example.com
- [ ] Integration test: `--wait-for` with dynamic content

**Validation**: `python -m scripts.cdp.cli dom dump --url "example.com" > page.html` produces valid HTML

---

### 4.4 `console stream` (Reuse refactored collector)

**Implementation**:
- [ ] Use refactored `cdp-console.py` logic
- [ ] Connect via `CDPSession`
- [ ] Enable `Console` domain
- [ ] Subscribe to `Console.messageAdded`
- [ ] Stream events for `--duration` seconds
- [ ] Output JSONL or text format

**Tests**:
- [ ] Integration test: capture console.log() messages
- [ ] Test `--level` filtering

**Validation**: Console messages appear in output during test

---

### 4.5 `network record` (Reuse refactored collector)

**Implementation**:
- [ ] Refactor `cdp-network.py` to use `CDPConnection`
- [ ] Enable `Network` domain
- [ ] Subscribe to `Network.requestWillBeSent`, `Network.responseReceived`
- [ ] Implement `--include-bodies` with `--max-body-size` limit
- [ ] Output JSON or HAR format

**Body Capture Safety**:
```python
async def get_response_body(conn: CDPConnection, request_id: str, max_size: int = 1048576):
    """Fetch response body with size limit"""
    try:
        result = await conn.execute("Network.getResponseBody", {"requestId": request_id})
        body = result["body"]
        if len(body) > max_size:
            logger.warning(f"Response body truncated (size: {len(body)} > {max_size})")
            return body[:max_size] + "\n[TRUNCATED]"
        return body
    except CDPCommandError:
        return None  # Body not available
```

**Tests**:
- [ ] Integration test: capture network requests
- [ ] Test body capture with size limit
- [ ] Test `--filter-url` regex

**Validation**: Network trace includes expected requests

---

### 4.6 `orchestrate` (Compose previous commands)

**Implementation**:
- [ ] Launch Chrome via `chrome-launcher.sh` (reuse existing script)
- [ ] Parse JSON output from launcher to get WebSocket URL
- [ ] Spawn console/network monitors as background tasks
- [ ] Extract DOM at end of duration
- [ ] Generate summary from artifacts
- [ ] Handle partial failure (preserve artifacts, return status)

**Failure Handling**:
```python
async def orchestrate_headless(url: str, duration: int, output_dir: str, **opts):
    artifacts = {}
    status = "completed"
    error = None

    try:
        # Launch Chrome
        chrome = await launch_chrome(url)
        artifacts["chrome_pid"] = chrome.pid

        # Start monitors
        console_task = asyncio.create_task(monitor_console(...))
        network_task = asyncio.create_task(monitor_network(...))

        # Wait for duration
        await asyncio.sleep(duration)

        # Extract DOM
        dom_path = await extract_dom(...)
        artifacts["dom"] = dom_path

    except ChromeLaunchError as e:
        status = "failed"
        error = str(e)
    except Exception as e:
        status = "partial"
        error = str(e)
    finally:
        # Save partial artifacts
        if console_task:
            artifacts["console"] = await console_task
        if network_task:
            artifacts["network"] = await network_task

    return {"status": status, "error": error, "artifacts": artifacts}
```

**Tests**:
- [ ] Integration test: full headless workflow
- [ ] Test Chrome launch failure (port in use)
- [ ] Test partial failure (kill Chrome mid-run)

**Validation**: End-to-end orchestrate produces all expected artifacts

---

## Phase 5: Migration Guardrails - Parallel Paths in CI

**Goal**: Run old and new implementations side-by-side to catch behavioral drift.

### Deliverables

**5.1 Compatibility Wrapper** (`scripts/core/debug-orchestrator.sh`)

**Before** (Bash orchestrator):
```bash
#!/usr/bin/env bash
# Full Bash implementation
chrome_launcher.sh "$URL"
cdp-console.py "$PAGE_ID" &
cdp-network.py "$PAGE_ID" &
# ... (existing logic)
```

**After** (thin wrapper to Python CLI):
```bash
#!/usr/bin/env bash
# Wrapper that calls Python CLI
exec python -m scripts.cdp.cli orchestrate headless "$@"
```

**5.2 CI Dual-Path Tests** (`.github/workflows/cdp-migration.yml`)
- [ ] Run smoke tests with old Bash orchestrator
- [ ] Run smoke tests with new Python CLI
- [ ] Diff outputs (DOM, console logs, network traces)
- [ ] Fail if outputs diverge beyond threshold (e.g., different request counts)

**5.3 Output Diff Validation**
```bash
# Example CI step
old_dom=$(mktemp)
new_dom=$(mktemp)

# Run old path
./scripts/core/debug-orchestrator.sh https://example.com 10 "$old_dom"

# Run new path (via wrapper)
python -m scripts.cdp.cli orchestrate headless https://example.com --duration 10 --output-dir /tmp

# Compare
diff -u "$old_dom" /tmp/dom-*.html || echo "WARNING: DOM outputs differ"
```

**Validation Gate**:
- ✅ Both paths produce artifacts
- ✅ Artifacts are semantically equivalent (allow minor formatting differences)
- ✅ No functional regressions

**Acceptance Criteria**:
- Run dual-path CI for **3 iterations** (3 releases/PRs)
- If outputs are stable, deprecate Bash orchestrator in docs
- If divergence found, fix before proceeding

---

## Phase 6: Advanced Features - Retry & Domain Replay

**Goal**: Add reconnection logic and domain state replay (deferred from Phase 1).

### Deliverables

**6.1 Reconnection Logic** (`scripts/cdp/connection.py`)
- [ ] Add `_retry_count`, `_enabled_domains` to `__init__()`
- [ ] Track domain enablement in `execute()` (`.enable` / `.disable` commands)
- [ ] Implement `_reconnect()` method with exponential backoff
- [ ] Replay enabled domains after successful reconnection
- [ ] Add `retry_count` and `is_reconnecting` properties

**6.2 Async Event Handlers**
- [ ] Detect `asyncio.iscoroutinefunction()` in `subscribe()`
- [ ] Spawn async handlers as tasks via `_safe_async_callback()`
- [ ] Wrap handlers in try/except to prevent receive loop crashes

**6.3 Tests**
- [ ] Unit test: domain tracking (enable Console, verify in `_enabled_domains`)
- [ ] Unit test: reconnection with domain replay
- [ ] Integration test: kill Chrome mid-session, verify auto-reconnect
- [ ] Integration test: async event handler with exception (verify receive loop continues)

**Validation Gate**:
- ✅ Reconnection survives Chrome restart
- ✅ Domains re-enabled automatically
- ✅ Event handlers persist across reconnection
- ✅ Bad event handlers don't crash receive loop

---

## Phase 7: Polish - Config, Logging, Docs

**Goal**: Production-ready CLI with observability and documentation.

### Deliverables

**7.1 Configuration Loading** (`scripts/cdp/config.py`)
- [ ] Environment variable support (`CDP_CHROME_PORT`, `CDP_TIMEOUT`, etc.)
- [ ] Config file support (`~/.cdprc` INI format)
- [ ] Precedence: CLI flags > env vars > config file > defaults

**7.2 Structured Logging** (`scripts/cdp/util/logging.py`)
- [ ] JSON log format for `--format json`
- [ ] Human-readable format for `--format text`
- [ ] Respect `--quiet` and `--verbose` flags
- [ ] Log reconnection attempts with backoff details

**7.3 Output Helpers** (`scripts/cdp/output.py`)
- [ ] Format JSON with indentation
- [ ] Format tables (for `session list --format table`)
- [ ] Handle stdout vs file output

**7.4 Documentation**
- [ ] Update `README.md` with Python CLI examples
- [ ] Add `docs/guides/python-cli-guide.md` with command reference
- [ ] Migrate Bash examples to Python in `docs/guides/workflows.md`
- [ ] Update `CLAUDE.md` with CLI-first instructions

**7.5 End-to-End Test Suite** (`tests/e2e/test_workflows.py`)
- [ ] Spin up headless Chrome
- [ ] Run full orchestrate workflow
- [ ] Verify all artifacts created
- [ ] Check artifact contents (DOM has `<html>`, console has expected messages)
- [ ] Teardown Chrome

**Validation Gate**:
- ✅ All commands have examples in docs
- ✅ E2E tests pass on clean checkout
- ✅ Config loading works from all sources

---

## Phase 8: Deprecation - Remove Bash Orchestrator

**Goal**: Official cutover to Python CLI, remove Bash implementation.

### Deliverables

**8.1 Documentation Updates**
- [ ] Mark `scripts/core/debug-orchestrator.sh` as deprecated in README
- [ ] Add deprecation notice at top of Bash script
- [ ] Update all examples to use Python CLI
- [ ] Move Bash scripts to `scripts/legacy/` directory

**8.2 Bash Wrapper Simplified**
```bash
#!/usr/bin/env bash
# scripts/core/debug-orchestrator.sh (deprecated wrapper)
echo "WARNING: This script is deprecated. Use Python CLI instead:" >&2
echo "  python -m scripts.cdp.cli orchestrate headless \"\$@\"" >&2
exec python -m scripts.cdp.cli orchestrate headless "$@"
```

**8.3 Final CI Cleanup**
- [ ] Remove dual-path tests (old vs new)
- [ ] Keep only Python CLI tests
- [ ] Archive old Bash test scripts

**Validation Gate**:
- ✅ No active usage of Bash orchestrator in CI
- ✅ All documentation uses Python CLI
- ✅ Wrapper script still works (backward compat)

**Timeline**: 2-4 weeks after Phase 7 completion, monitor for user feedback

---

## Rollback Plan

If critical issues discovered at any phase:

1. **Phase 1-3**: No user impact (internal changes only), safe to iterate
2. **Phase 4**: Revert wrapper to Bash implementation, iterate on Python CLI
3. **Phase 5-6**: Keep dual-path CI, extend validation period
4. **Phase 7-8**: Wrapper ensures Bash path still works, low rollback risk

**Escape Hatch**: Bash orchestrator remains functional throughout migration via wrapper

---

## Success Metrics

**Phase Completion**:
- [ ] Phase 1: Connection layer passes integration tests
- [ ] Phase 2: One collector refactored and validated
- [ ] Phase 3: All CLI help text documented and tested
- [ ] Phase 4: Core commands (`session`, `eval`, `dom`, `console`, `network`, `orchestrate`) implemented
- [ ] Phase 5: Dual-path CI passes for 3 iterations
- [ ] Phase 6: Reconnection logic validated with real Chrome
- [ ] Phase 7: E2E tests pass, docs updated
- [ ] Phase 8: Bash orchestrator deprecated, Python CLI is primary

**Quality Gates**:
- Test coverage: ≥80% for `scripts/cdp/` modules
- No memory leaks in long-running tests (5+ minutes)
- Integration tests pass with real Chrome (headless and headed)
- Dual-path CI outputs are semantically equivalent

---

## Dependencies

**External**:
- `websockets` library (install: `pip3 install websockets`)
- `aiohttp` for HTTP JSON endpoint
- `pytest`, `pytest-asyncio` for testing
- Chrome/Chromium with CDP enabled

**Internal**:
- `chrome-launcher.sh` (reuse existing, no changes needed)
- Existing collectors (refactor in Phase 2+)

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Foundation | 3-5 days | None |
| Phase 2: Validate Ergonomics | 2-3 days | Phase 1 ✅ |
| Phase 3: CLI Skeleton | 2-3 days | None (parallel with Phase 2) |
| Phase 4: Must-Have Commands | 5-7 days | Phases 1-3 ✅ |
| Phase 5: Migration Guardrails | 2-3 days | Phase 4 ✅ |
| Phase 6: Advanced Features | 3-4 days | Phases 1-5 ✅ |
| Phase 7: Polish | 3-4 days | Phase 6 ✅ |
| Phase 8: Deprecation | 1-2 days | Phase 7 ✅ + 2-4 week soak |

**Total**: 3-4 weeks of implementation + 2-4 weeks validation before deprecation

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| API ergonomics issues | Phase 2 validates with real collector before mass migration |
| Behavioral drift from Bash | Phase 5 dual-path CI catches divergence early |
| Reconnection instability | Phase 6 defers retry logic until foundation is stable |
| User disruption | Wrapper ensures Bash path works throughout migration |
| Test coverage gaps | Integration tests with real Chrome from Phase 1 |

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Begin Phase 1**: Implement minimal `CDPConnection` class
3. **Set up test infrastructure**: pytest-asyncio, Chrome fixture
4. **First milestone**: Green integration test with real Chrome

**Ready to start Phase 1?**

Create ticket/branch:
```bash
git checkout -b 007-python-cdp-foundation
```

Implement:
- `scripts/cdp/__init__.py`
- `scripts/cdp/connection.py` (minimal)
- `scripts/cdp/errors.py`
- `tests/unit/test_connection.py`
- `tests/integration/test_connection_chrome.py`

**Acceptance**: Integration test passes with real Chrome extracting `document.title`
