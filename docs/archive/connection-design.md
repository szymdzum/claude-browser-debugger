# connection.py Design Specification

## Overview

`connection.py` provides the foundational CDP session lifecycle management for the browser-debugger skill. It handles WebSocket connections, reconnection logic, command execution, and event streaming.

## Design Review Summary

**Key Decisions Made** (from design review feedback):

1. ✅ **Exception naming**: Renamed `ConnectionError` → `CDPConnectionError` (and all exceptions) to avoid masking Python built-ins
2. ✅ **Domain state replay**: Added `_enabled_domains` tracking; automatic re-enablement after reconnection via `_reconnect()` method
3. ✅ **Event callback safety**: Implemented error isolation with `_safe_async_callback()` wrapper; bad handlers can't crash `_receive_loop`
4. ✅ **Retry configuration exposure**: Added `retry_count` property and detailed logging; operators can tune via env vars/config/constructor
5. ✅ **Event ordering guarantees**: Per-event-type ordering for sync handlers; async handlers spawn as tasks (documented trade-offs)
6. ⏸️ **Document readiness hook**: Deferred to post-MVP (callers handle manually for now)
7. ⏸️ **Pluggable transport**: Deferred to post-MVP (YAGNI - use `websockets` directly, refactor if needed)

## Core Responsibilities

1. **Session Discovery**: Fetch available CDP targets from Chrome's `/json` endpoint
2. **Connection Management**: Establish and maintain WebSocket connections to CDP targets
3. **Command Execution**: Send CDP commands and await responses with timeout handling
4. **Event Streaming**: Subscribe to CDP events and deliver them to consumers
5. **Reconnection Logic**: Automatically recover from transient failures
6. **Resource Cleanup**: Ensure connections are properly closed

## Architecture

### Key Classes

```python
# Exception Hierarchy
class CDPError(Exception):
    """Base exception for all CDP-related errors"""
    pass

class CDPConnectionError(CDPError):
    """
    Failed to establish or maintain WebSocket connection.

    NOTE: Named CDPConnectionError to avoid masking Python's built-in ConnectionError,
    which would complicate exception handling and typing.
    """
    pass

class CDPCommandError(CDPError):
    """CDP command execution failed"""
    pass

class CDPTargetNotFoundError(CDPError):
    """Requested CDP target not available"""
    pass

class CDPContextDestroyedError(CDPError):
    """Execution context was destroyed (navigation, reload)"""
    pass

class CDPTimeoutError(CDPError):
    """Operation exceeded timeout threshold"""
    pass


# Core Connection Class
class CDPConnection:
    """
    Manages a single WebSocket connection to a CDP target.

    Lifecycle:
    1. Create instance with ws_url
    2. Call connect() or use as async context manager
    3. Send commands via execute()
    4. Subscribe to events via subscribe()
    5. Close via disconnect() or context manager exit
    """

    def __init__(
        self,
        ws_url: str,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        logger: Optional[logging.Logger] = None
    ):
        self.ws_url = ws_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logger or logging.getLogger(__name__)

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._command_id = 0
        self._pending_commands: Dict[int, asyncio.Future] = {}
        self._event_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._receive_task: Optional[asyncio.Task] = None
        self._connected = False

        # Domain state tracking for reconnection
        self._enabled_domains: Set[str] = set()  # e.g., {"Console", "Network", "Runtime"}
        self._retry_count = 0  # Current reconnection attempt count

    async def connect(self) -> None:
        """Establish WebSocket connection with retry logic"""

    async def disconnect(self) -> None:
        """Close WebSocket connection and cleanup resources"""

    async def execute(
        self,
        method: str,
        params: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute CDP command and return result.

        Automatically tracks domain enablement (Console.enable, Network.enable, etc.)
        for automatic re-enablement after reconnection.

        Raises:
            CDPCommandError: If CDP returns error response
            CDPTimeoutError: If command exceeds timeout
            CDPConnectionError: If connection is lost during execution
        """
        # Track domain enablement for reconnection
        if method.endswith(".enable"):
            domain = method.split(".")[0]
            self._enabled_domains.add(domain)
        elif method.endswith(".disable"):
            domain = method.split(".")[0]
            self._enabled_domains.discard(domain)

    def subscribe(self, event: str, handler: Callable[[Dict], None]) -> None:
        """Subscribe to CDP event (e.g., 'Console.messageAdded')"""

    def unsubscribe(self, event: str, handler: Callable[[Dict], None]) -> None:
        """Unsubscribe from CDP event"""

    async def _receive_loop(self) -> None:
        """Background task that receives messages and routes them"""

    async def __aenter__(self) -> 'CDPConnection':
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()


# Session Manager
class CDPSession:
    """
    High-level session manager for Chrome debugging.

    Responsibilities:
    - Discover available targets from Chrome /json endpoint
    - Create CDPConnection instances for specific targets
    - Manage connection pool for multiple targets
    - Provide convenience methods for common operations
    """

    def __init__(
        self,
        chrome_host: str = "localhost",
        chrome_port: int = 9222,
        *,
        logger: Optional[logging.Logger] = None
    ):
        self.chrome_host = chrome_host
        self.chrome_port = chrome_port
        self.logger = logger or logging.getLogger(__name__)
        self._connections: Dict[str, CDPConnection] = {}

    async def list_targets(self) -> List[Dict]:
        """Fetch available CDP targets from /json endpoint"""

    async def connect_to_page(
        self,
        page_id: Optional[str] = None,
        url_filter: Optional[str] = None
    ) -> CDPConnection:
        """
        Connect to a specific page target.

        Args:
            page_id: Explicit page ID to connect to
            url_filter: Regex pattern to match page URL (uses first match)

        Returns:
            CDPConnection instance for the target

        Raises:
            TargetNotFoundError: If no matching target found
        """

    async def close_all(self) -> None:
        """Close all managed connections"""
```

## Session Lifecycle States

```
┌─────────────┐
│ UNCONNECTED │
└──────┬──────┘
       │ connect()
       ↓
┌─────────────┐     Network error / Navigation
│  CONNECTED  │────────────────────────────────┐
└──────┬──────┘                                │
       │                                       ↓
       │ execute(cmd)                  ┌──────────────┐
       ├──────────────────────────────→│  RECONNECTING │
       │                               └───────┬──────┘
       │                                       │
       │                                       │ Retry success
       │                                       ↓
       │                               ┌─────────────┐
       │                               │  CONNECTED  │
       │                               └─────────────┘
       │
       │ disconnect()                  Retry exhausted
       ↓                                       ↓
┌─────────────┐                        ┌─────────────┐
│   CLOSED    │                        │   FAILED    │
└─────────────┘                        └─────────────┘
```

## Reconnection Rules

### When to Reconnect

1. **WebSocket Connection Lost**
   - Network interruption
   - Chrome process crashed/restarted
   - **Action**: Retry with exponential backoff

2. **Execution Context Destroyed**
   - Page navigation
   - Page reload
   - **Action**: Re-establish connection, replay domain enablement commands

3. **Command Timeout**
   - No response received within timeout period
   - **Action**: Mark command as failed, maintain connection (do NOT reconnect)

### When NOT to Reconnect

1. **Invalid WebSocket URL**
   - Malformed URL format
   - **Action**: Raise `ConnectionError` immediately

2. **HTTP /json Endpoint Unreachable**
   - Chrome not running or wrong port
   - **Action**: Raise `ConnectionError` immediately

3. **Target Closed by User**
   - CDP returns `{"error": {"code": -32600, "message": "Target closed"}}`
   - **Action**: Raise `TargetNotFoundError`, do NOT retry

4. **Max Retries Exceeded**
   - After N failed reconnection attempts
   - **Action**: Raise `ConnectionError` with recovery hints

### Retry Strategy

```python
# Exponential backoff with jitter
def calculate_retry_delay(attempt: int, base_delay: float = 1.0) -> float:
    """
    Returns delay in seconds before retry attempt.

    attempt=1: 1.0s + jitter
    attempt=2: 2.0s + jitter
    attempt=3: 4.0s + jitter
    Max: 10.0s + jitter
    """
    delay = min(base_delay * (2 ** (attempt - 1)), 10.0)
    jitter = random.uniform(0, delay * 0.1)  # ±10% jitter
    return delay + jitter
```

**Default Configuration**:
- `max_retries`: 3
- `base_delay`: 1.0s
- `timeout`: 30.0s per command

**Configurable per CDPConnection instance via constructor**

### Domain State Replay After Reconnection

When reconnection succeeds, `CDPConnection` automatically re-enables domains and re-attaches event handlers:

```python
async def _reconnect(self) -> None:
    """
    Internal reconnection handler.

    Steps:
    1. Close existing WebSocket (if any)
    2. Retry connection with exponential backoff
    3. Replay domain enablement commands from self._enabled_domains
    4. Event handlers remain attached (no replay needed)
    """
    self.logger.info(f"Reconnecting (attempt {self._retry_count + 1}/{self.max_retries})")

    # Step 1: Close stale WebSocket
    if self._ws:
        await self._ws.close()
        self._ws = None

    # Step 2: Retry connection with backoff
    for attempt in range(1, self.max_retries + 1):
        self._retry_count = attempt
        try:
            delay = calculate_retry_delay(attempt, self.retry_delay)
            self.logger.debug(f"Waiting {delay:.2f}s before reconnect attempt {attempt}")
            await asyncio.sleep(delay)

            # Re-establish WebSocket
            self._ws = await websockets.connect(self.ws_url, timeout=self.timeout)
            self._connected = True
            self.logger.info(f"Reconnection successful on attempt {attempt}")

            # Step 3: Replay domain enablement
            for domain in self._enabled_domains:
                self.logger.debug(f"Re-enabling domain: {domain}")
                await self.execute(f"{domain}.enable")

            # Step 4: Event handlers are already in self._event_subscribers, no replay needed
            self._retry_count = 0  # Reset retry count on success
            return

        except Exception as e:
            self.logger.warning(f"Reconnect attempt {attempt} failed: {e}")
            if attempt == self.max_retries:
                raise CDPConnectionError(
                    f"Failed to reconnect after {self.max_retries} attempts",
                    recovery_hint="Check if Chrome is still running and accessible"
                )

# Usage: Automatic reconnection on connection loss
try:
    result = await conn.execute("Runtime.evaluate", {"expression": "document.title"})
except CDPConnectionError as e:
    # Connection was lost and reconnection failed
    logger.error(f"Connection failed: {e.recovery_hint}")
```

**Logging During Reconnection**:
- `[INFO] Reconnecting (attempt 1/3)` - Reconnection initiated
- `[DEBUG] Waiting 1.05s before reconnect attempt 1` - Backoff delay
- `[INFO] Reconnection successful on attempt 1` - Success
- `[DEBUG] Re-enabling domain: Console` - Domain replay
- `[WARNING] Reconnect attempt 2 failed: ConnectionRefused` - Retry failure

## Async Strategy

### Core Principles

1. **Single Receive Loop**: One background task per connection that receives all messages
2. **Command Futures**: Pending commands use asyncio.Future for response delivery
3. **Event Callbacks**: Subscribers receive events via synchronous callbacks (must be fast)
4. **No Blocking**: All I/O operations are async (websockets, HTTP requests)

### Threading Model

```
Main Thread/Event Loop
├── CDPConnection._receive_loop() [background task]
│   ├── Receives WebSocket messages
│   ├── Routes responses to pending command futures
│   └── Dispatches events to subscribers
│
├── CDPConnection.execute() [coroutine]
│   ├── Creates Future for command
│   ├── Sends command via WebSocket
│   └── Awaits Future with timeout
│
└── User Code
    ├── await conn.execute("Runtime.evaluate", {...})
    └── conn.subscribe("Console.messageAdded", handler)
```

### Event Handling

**Synchronous Callbacks** (default):
```python
def on_console_message(event: Dict) -> None:
    """Must be fast - no async I/O"""
    print(event["params"]["text"])

conn.subscribe("Console.messageAdded", on_console_message)
```

**Async Callbacks** (advanced):
```python
async def on_network_response(event: Dict) -> None:
    """Can perform async I/O"""
    await save_to_database(event)

# Connection wraps async handlers in asyncio.create_task()
conn.subscribe("Network.responseReceived", on_network_response)
```

### Event Callback Error Handling

**Problem**: Unhandled exceptions in event callbacks can crash the `_receive_loop`, breaking all CDP communication.

**Solution**: Isolate callback exceptions and log them without disrupting message processing.

```python
async def _receive_loop(self) -> None:
    """
    Background task that receives messages and routes them.

    Error handling:
    - WebSocket errors: Trigger reconnection
    - Callback exceptions: Log and continue processing
    - JSON decode errors: Log and skip message
    """
    try:
        async for message in self._ws:
            try:
                data = json.loads(message)

                # Route response to pending command
                if "id" in data:
                    future = self._pending_commands.pop(data["id"], None)
                    if future and not future.done():
                        if "error" in data:
                            future.set_exception(CDPCommandError(data["error"]["message"]))
                        else:
                            future.set_result(data.get("result"))

                # Route event to subscribers
                elif "method" in data:
                    event_name = data["method"]
                    handlers = self._event_subscribers.get(event_name, [])

                    for handler in handlers:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                # Async handler: spawn as separate task with error handling
                                task = asyncio.create_task(self._safe_async_callback(handler, data))
                                # Optionally store task reference to prevent garbage collection
                            else:
                                # Sync handler: call directly with exception guard
                                handler(data)
                        except Exception as e:
                            # Callback exception: log but don't crash receive loop
                            self.logger.error(
                                f"Exception in event handler for {event_name}: {e}",
                                exc_info=True
                            )
                            # Continue processing other handlers

            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to decode CDP message: {e}")
                continue  # Skip malformed message

    except websockets.exceptions.ConnectionClosed:
        self.logger.warning("WebSocket connection closed, triggering reconnection")
        await self._reconnect()
    except Exception as e:
        self.logger.error(f"Fatal error in receive loop: {e}", exc_info=True)
        raise

async def _safe_async_callback(self, handler: Callable, event: Dict) -> None:
    """
    Wrapper for async event handlers to catch and log exceptions.

    Prevents unhandled task exceptions from appearing in logs.
    """
    try:
        await handler(event)
    except Exception as e:
        self.logger.error(
            f"Exception in async event handler {handler.__name__}: {e}",
            exc_info=True
        )
```

**Ordering Guarantees**:
- **Per-event-type ordering**: Handlers for the same event type (e.g., `Console.messageAdded`) are called in subscription order
- **Cross-event ordering**: Events for different types (e.g., `Console.messageAdded` vs `Network.responseReceived`) may be processed concurrently if using async handlers
- **Synchronous handlers**: Always processed in order within the receive loop
- **Async handlers**: Spawned as tasks, may complete out of order

**Recommendation**: Use sync handlers for order-sensitive logic (e.g., request/response matching), async handlers for I/O-bound work (e.g., database writes).

### Cancellation & Cleanup

**Context Manager Pattern** (recommended):
```python
async with CDPConnection(ws_url) as conn:
    result = await conn.execute("Runtime.evaluate", {"expression": "1+1"})
    # Automatic cleanup on exit
```

**Manual Management**:
```python
conn = CDPConnection(ws_url)
try:
    await conn.connect()
    result = await conn.execute("Runtime.evaluate", {"expression": "1+1"})
finally:
    await conn.disconnect()  # Ensures cleanup even on exception
```

**Graceful Shutdown**:
```python
async def shutdown(session: CDPSession):
    """Cleanup all connections"""
    await session.close_all()  # Closes all managed CDPConnection instances
```

## Error Handling & Recovery Hints

### Structured Error Messages

```python
class CDPConnectionError(CDPError):
    def __init__(self, message: str, recovery_hint: Optional[str] = None):
        super().__init__(message)
        self.recovery_hint = recovery_hint

# Usage
raise CDPConnectionError(
    "Failed to connect to ws://localhost:9222/devtools/page/ABC123",
    recovery_hint="Verify Chrome is running with --remote-debugging-port=9222"
)
```

### Common Error Scenarios

| Error | Condition | Recovery Hint |
|-------|-----------|---------------|
| `CDPConnectionError` | /json endpoint unreachable | "Start Chrome with --remote-debugging-port=9222" |
| `CDPTargetNotFoundError` | No page matching filter | "Check page URL or navigate Chrome to the target site" |
| `CDPContextDestroyedError` | Page navigated during command | "Retry command after navigation completes" |
| `CDPTimeoutError` | Command exceeded 30s | "Increase timeout or check if Chrome is responsive" |
| `CDPCommandError` | CDP returned error response | Include CDP error message verbatim |

### Retry Configuration Exposure

Expose retry count and backoff parameters via logging and connection state for operator tuning:

```python
# Expose retry state for monitoring
@property
def retry_count(self) -> int:
    """Current reconnection attempt count (0 if connected)"""
    return self._retry_count

@property
def is_reconnecting(self) -> bool:
    """True if currently attempting to reconnect"""
    return self._retry_count > 0

# Example: Custom retry configuration
conn = CDPConnection(
    ws_url,
    max_retries=5,          # Increase for flaky networks
    retry_delay=2.0,        # Start with longer backoff
    timeout=60.0            # Allow more time per command
)

# Logging surfaces retry details automatically:
# [INFO] Reconnecting (attempt 1/5)
# [DEBUG] Waiting 2.15s before reconnect attempt 1  # Shows actual backoff with jitter
# [WARNING] Reconnect attempt 1 failed: ConnectionRefused
```

**Operators can tune defaults via**:
- Environment variables: `CDP_MAX_RETRIES`, `CDP_RETRY_DELAY`
- Config file: `~/.cdprc` with `[connection]` section
- Constructor arguments (highest precedence)

## Integration with Existing Collectors

### Current Pattern (cdp-console.py)

```python
# Current: Direct websocket connection in script
async def main():
    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Console.enable"}))
        # ... message loop
```

### New Pattern

```python
# New: Use CDPConnection
from scripts.cdp.connection import CDPSession

async def stream_console(chrome_port: int = 9222):
    session = CDPSession(chrome_port=chrome_port)
    async with await session.connect_to_page() as conn:

        # Enable console domain
        await conn.execute("Console.enable")

        # Subscribe to console messages
        def on_message(event: Dict):
            print(f"[{event['params']['level']}] {event['params']['text']}")

        conn.subscribe("Console.messageAdded", on_message)

        # Keep connection alive
        await asyncio.sleep(300)  # 5 minutes
```

## Testing Strategy

### Unit Tests (Mocked WebSocket)

```python
@pytest.mark.asyncio
async def test_execute_command_success():
    """Verify command execution with mocked response"""
    conn = CDPConnection("ws://mock")
    # Mock websocket send/receive
    # Assert command sent correctly, result returned

@pytest.mark.asyncio
async def test_reconnect_on_connection_lost():
    """Verify retry logic on connection failure"""
    conn = CDPConnection("ws://mock", max_retries=3)
    # Simulate connection loss on first attempt
    # Assert reconnection attempted with backoff
```

### Integration Tests (Real Chrome)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_dom_extraction_real_chrome(chrome_instance):
    """End-to-end DOM extraction with real Chrome"""
    session = CDPSession(chrome_port=chrome_instance.port)
    async with await session.connect_to_page() as conn:
        await conn.execute("Runtime.enable")
        result = await conn.execute("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True
        })
        assert "<html" in result["result"]["value"]
```

## Configuration

### Environment Variables

```bash
CDP_CHROME_HOST=localhost
CDP_CHROME_PORT=9222
CDP_TIMEOUT=30.0
CDP_MAX_RETRIES=3
CDP_RETRY_DELAY=1.0
CDP_LOG_LEVEL=INFO
```

### Config File Support (Future)

```python
# config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class CDPConfig:
    chrome_host: str = "localhost"
    chrome_port: int = 9222
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0

    @classmethod
    def from_env(cls) -> 'CDPConfig':
        """Load from environment variables"""

    @classmethod
    def from_file(cls, path: str) -> 'CDPConfig':
        """Load from .env or .cdprc file"""
```

## Open Questions & Decisions

### 1. Document Readiness Hook in `connect_to_page()`

**Question**: Should `CDPSession.connect_to_page()` expose a hook for "ensure this JS expression succeeds before handing back the connection"?

**Use Case**: Wait for `document.readyState === 'complete'` before starting DOM extraction.

**Option A**: Add `ready_expression` parameter
```python
conn = await session.connect_to_page(
    url_filter="example.com",
    ready_expression="document.readyState === 'complete'"
)
# Connection only returned when expression evaluates to truthy value
```

**Option B**: Callers add readiness check themselves (current proposal)
```python
conn = await session.connect_to_page(url_filter="example.com")
# Caller waits manually
await conn.execute("Runtime.evaluate", {
    "expression": "new Promise(resolve => document.readyState === 'complete' ? resolve() : window.addEventListener('load', resolve))",
    "awaitPromise": True
})
```

**Recommendation**: Option B for MVP (simpler API), add Option A if commonly requested.

### 2. Pluggable Transport Abstraction

**Question**: Should we factor WebSocket transport behind an interface to support alternative clients (e.g., `websocket-client` vs `websockets`)?

**Option A**: Abstract transport now
```python
class CDPTransport(Protocol):
    async def connect(self, url: str) -> None: ...
    async def send(self, message: str) -> None: ...
    async def receive(self) -> str: ...
    async def close(self) -> None: ...

class WebSocketsTransport(CDPTransport):
    # Implementation using `websockets` library
```

**Option B**: Defer abstraction until we need to swap implementations (current proposal)
- Directly use `websockets` library
- Refactor later if alternative transports needed

**Recommendation**: Option B for MVP (YAGNI principle), refactor when we have concrete alternative transport requirements.

**Rationale**: Premature abstraction adds complexity without clear benefit. Current `websockets` library is stable and widely supported.

### 3. Event Callback Threading (RESOLVED)

**Decision**: Spawn async handlers as separate tasks (non-blocking)

**Implementation**:
- Synchronous handlers: Called directly in `_receive_loop` with exception guard
- Async handlers: Wrapped in `asyncio.create_task()` via `_safe_async_callback()`
- Per-event-type ordering guaranteed for sync handlers
- Async handlers may complete out of order (acceptable trade-off)

### 4. Connection Pool Management (RESOLVED)

**Decision**: Create connections on-demand initially

**Rationale**: Simpler lifecycle, easier to reason about. Profile later and optimize to pooling if needed.

### 5. Reconnection During Command Execution (RESOLVED)

**Decision**: Raise error, let caller retry

**Rationale**: Avoids idempotency concerns (some CDP commands have side effects like navigation). Provide retry decorator for convenience:

```python
from scripts.cdp.util.retry import retry_on_disconnect

@retry_on_disconnect(max_attempts=3)
async def get_page_title(conn: CDPConnection) -> str:
    result = await conn.execute("Runtime.evaluate", {
        "expression": "document.title",
        "returnByValue": True
    })
    return result["value"]
```

## Performance Considerations

### Message Buffering

- WebSocket messages are processed sequentially in `_receive_loop`
- Large messages (e.g., DOM dumps) may block event processing
- **Mitigation**: Use separate connections for long-running operations vs event streaming

### Memory Management

- `_pending_commands` dict grows with concurrent commands
- **Mitigation**: Implement command timeout to clean up stale futures
- **Monitoring**: Log warning if dict exceeds threshold (e.g., 100 pending commands)

### Connection Limits

- Chrome CDP has no hard limit on WebSocket connections
- Practical limit: ~10 concurrent connections before performance degrades
- **Recommendation**: Document recommended usage patterns (1 connection per workflow)

## Implementation Phases

### Phase 1: Core Connection (Milestone 1)
- [ ] Implement `CDPConnection` class
- [ ] Command execution with timeout
- [ ] Basic reconnection logic
- [ ] Unit tests with mocked WebSocket

### Phase 2: Session Management (Milestone 2)
- [ ] Implement `CDPSession` class
- [ ] Target discovery from /json endpoint
- [ ] Connection pooling (optional)
- [ ] Integration tests with real Chrome

### Phase 3: Event System (Milestone 3)
- [ ] Event subscription/unsubscription
- [ ] Async callback support
- [ ] Event ordering guarantees
- [ ] Performance benchmarks

### Phase 4: Productionization (Milestone 4)
- [ ] Configuration file support
- [ ] Structured logging
- [ ] Metrics/observability hooks
- [ ] Documentation and examples
