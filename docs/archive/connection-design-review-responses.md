# connection.py Design Review - Response Summary

## Review Date
2025-10-24

## Review Feedback Addressed

### ✅ 1. Rename `ConnectionError` to Avoid Masking Python Built-in

**Issue**: `ConnectionError` collides with Python's built-in `ConnectionError`, complicating exception handling and typing.

**Resolution**:
- Renamed all exceptions with `CDP` prefix for namespace isolation:
  - `ConnectionError` → `CDPConnectionError`
  - `CommandError` → `CDPCommandError`
  - `TargetNotFoundError` → `CDPTargetNotFoundError`
  - `ContextDestroyedError` → `CDPContextDestroyedError`
  - `TimeoutError` → `CDPTimeoutError`

**Location**: `docs/development/connection-design.md:26-49`

**Rationale**: Clear namespace prevents accidental catches of Python built-in exceptions, improves IDE autocomplete, and makes exception hierarchy explicit.

---

### ✅ 2. Domain State Replay After Reconnection

**Issue**: Reconnection needs to remember which domains were enabled (Console, Network, etc.) and which event handlers were registered, then replay them automatically.

**Resolution**:
- Added `_enabled_domains: Set[str]` to `CDPConnection.__init__()` to track enabled domains
- Modified `execute()` to automatically track `*.enable` and `*.disable` commands
- Implemented `_reconnect()` method that:
  1. Closes stale WebSocket
  2. Re-establishes connection with exponential backoff
  3. **Replays all enabled domains** by calling `execute(f"{domain}.enable")`
  4. Event handlers remain attached (stored in `_event_subscribers`, no replay needed)

**Code Example**:
```python
# Automatic domain tracking
await conn.execute("Console.enable")  # Tracked in _enabled_domains
await conn.execute("Network.enable")  # Tracked in _enabled_domains

# On reconnection:
# 1. WebSocket reconnects
# 2. Automatically re-runs: Console.enable, Network.enable
# 3. Event handlers (already subscribed) continue receiving events
```

**Location**: `docs/development/connection-design.md:87-89, 279-344`

**Benefit**: Transparent reconnection for collectors (console, network). Collectors don't need to manually re-enable domains after connection loss.

---

### ✅ 3. Event Callback Error Handling

**Issue**:
- Async callbacks should be queued as separate tasks (non-blocking)
- Need ordering guarantees (per-event-type queue)
- Must guard against unhandled exceptions crashing `_receive_loop`

**Resolution**:

**Error Isolation**:
- Added `_safe_async_callback()` wrapper for async handlers
- Wrapped all handler calls in try/except blocks within `_receive_loop()`
- Callback exceptions logged with `exc_info=True` but do NOT crash receive loop

**Async Task Spawning**:
```python
if asyncio.iscoroutinefunction(handler):
    task = asyncio.create_task(self._safe_async_callback(handler, data))
else:
    handler(data)  # Sync handler called directly
```

**Ordering Guarantees**:
- **Per-event-type**: Sync handlers processed sequentially in subscription order
- **Cross-event-type**: Async handlers may execute concurrently (acceptable)
- **Recommendation**: Use sync handlers for order-sensitive logic (e.g., request/response matching)

**Location**: `docs/development/connection-design.md:395-479`

**Benefit**:
- Bad handlers can't break CDP communication
- Async handlers don't block message processing
- Clear ordering semantics for developers

---

### ✅ 4. Retry Configuration Exposure

**Issue**:
- Expose progressive backoff jitter to callers (config)
- Surface retry counts via logging for operator tuning

**Resolution**:

**Exposed State**:
```python
@property
def retry_count(self) -> int:
    """Current reconnection attempt count (0 if connected)"""
    return self._retry_count

@property
def is_reconnecting(self) -> bool:
    """True if currently attempting to reconnect"""
    return self._retry_count > 0
```

**Configuration Tuning**:
- Constructor arguments: `max_retries`, `retry_delay`, `timeout`
- Environment variables: `CDP_MAX_RETRIES`, `CDP_RETRY_DELAY`, `CDP_TIMEOUT`
- Config file: `~/.cdprc` with `[connection]` section

**Detailed Logging**:
```
[INFO] Reconnecting (attempt 1/5)
[DEBUG] Waiting 2.15s before reconnect attempt 1  # Shows actual jitter
[WARNING] Reconnect attempt 1 failed: ConnectionRefused
```

**Location**: `docs/development/connection-design.md:534-567`

**Benefit**: Operators can tune reconnection behavior for different network conditions without code changes.

---

## Open Questions from Review

### ⏸️ 1. Document Readiness Hook in `connect_to_page()`

**Question**: Should `CDPSession.connect_to_page()` expose a hook for "ensure this JS expression succeeds before handing back the connection"?

**Example Use Case**: Wait for `document.readyState === 'complete'` before DOM extraction.

**Decision**: Deferred to post-MVP
- Callers can add readiness checks manually for now
- Add `ready_expression` parameter if commonly requested
- Simpler API for initial implementation

**Rationale**: YAGNI - avoid premature complexity. Current workaround is simple:
```python
conn = await session.connect_to_page(url_filter="example.com")
await conn.execute("Runtime.evaluate", {
    "expression": "new Promise(resolve => document.readyState === 'complete' ? resolve() : window.addEventListener('load', resolve))",
    "awaitPromise": True
})
```

**Location**: `docs/development/connection-design.md:680-705`

---

### ⏸️ 2. Pluggable Transport Abstraction

**Question**: Should we factor WebSocket transport behind an interface to support alternative clients (e.g., `websocket-client` vs `websockets`)?

**Decision**: Deferred to post-MVP
- Use `websockets` library directly
- Refactor to `CDPTransport` protocol if we need to swap implementations

**Rationale**:
- YAGNI - no concrete requirement for alternative transports
- `websockets` library is stable and widely supported
- Premature abstraction adds complexity without clear benefit

**Location**: `docs/development/connection-design.md:707-729`

---

## Implementation Checklist

### Phase 1: Core Connection
- [ ] Implement `CDPConnectionError` exception hierarchy
- [ ] Implement `CDPConnection` class with `_enabled_domains` tracking
- [ ] Implement `execute()` with domain tracking
- [ ] Implement `_reconnect()` with domain replay
- [ ] Add `retry_count` and `is_reconnecting` properties
- [ ] Unit tests with mocked WebSocket

### Phase 2: Event System
- [ ] Implement `_receive_loop()` with error handling
- [ ] Implement `_safe_async_callback()` wrapper
- [ ] Add per-event-type ordering tests
- [ ] Test callback exception isolation

### Phase 3: Configuration
- [ ] Environment variable loading (`CDP_MAX_RETRIES`, etc.)
- [ ] Config file support (`~/.cdprc`)
- [ ] Detailed logging during reconnection
- [ ] Integration tests with real Chrome

---

## Changes to Original Design

| Aspect | Original Design | Updated Design | Rationale |
|--------|-----------------|----------------|-----------|
| Exception Names | `ConnectionError`, `TimeoutError` | `CDPConnectionError`, `CDPTimeoutError` | Avoid masking Python built-ins |
| Domain Tracking | Not specified | `_enabled_domains` set, auto-replay on reconnect | Transparent reconnection |
| Event Callback Errors | Not specified | `_safe_async_callback()` wrapper, isolated exceptions | Prevent receive loop crashes |
| Retry Visibility | Default config only | Properties + detailed logging + tunable config | Operator observability |
| Async Handler Ordering | Option B (spawn tasks) | Option B + documented guarantees | Non-blocking with clear semantics |
| Document Readiness | Not considered | Deferred to post-MVP | Simpler initial API |
| Transport Abstraction | Not considered | Deferred to post-MVP | YAGNI, avoid premature complexity |

---

## Next Steps

1. **Review open questions** with stakeholders (document readiness, transport abstraction)
2. **Begin implementation** of Phase 1 (core connection)
3. **Write unit tests** for domain tracking and reconnection logic
4. **Validate reconnection** with integration tests (kill Chrome mid-session)

---

## Sign-off

**Reviewer**: (Your review feedback)
**Designer**: Claude Code Agent
**Status**: Design finalized, ready for implementation
**Date**: 2025-10-24
