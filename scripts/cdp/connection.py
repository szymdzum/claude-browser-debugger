"""CDP WebSocket connection management.

Provides CDPConnection class for low-level CDP command execution and event subscription.
Handles WebSocket lifecycle, message routing, and error recovery.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Awaitable, Dict, List, Optional, Set

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    from websockets.exceptions import ConnectionClosed
except ImportError:
    raise ImportError(
        "websockets library not found. Install with: pip3 install websockets"
    )

from .exceptions import (
    CDPConnectionError,
    ConnectionFailedError,
    ConnectionClosedError,
    CDPCommandError,
    CommandFailedError,
    CDPTimeoutError,
)

logger = logging.getLogger(__name__)


class CDPConnection:
    """Manages WebSocket connection to Chrome DevTools Protocol endpoint.

    Handles:
    - Connection lifecycle (connect, disconnect, context manager)
    - Command execution with timeout handling
    - Event subscription and dispatching
    - Message routing between commands and events
    - Automatic domain tracking for reconnection replay

    Usage:
        async with CDPConnection(ws_url) as conn:
            result = await conn.execute_command("Runtime.evaluate", {"expression": "1+1"})
            conn.subscribe("Console.messageAdded", my_callback)

    Attributes:
        ws_url: WebSocket debugger URL
        timeout: Default command timeout in seconds
        max_size: Maximum WebSocket message size in bytes (for large DOMs)
    """

    def __init__(
        self,
        ws_url: str,
        *,
        timeout: float = 30.0,
        max_size: int = 2_097_152  # 2MB default buffer
    ):
        """Initialize CDP connection.

        Args:
            ws_url: WebSocket debugger URL (e.g., ws://localhost:9222/devtools/page/ABC123)
            timeout: Default command timeout in seconds
            max_size: Maximum WebSocket message size in bytes
        """
        if not ws_url.startswith(("ws://", "wss://")):
            raise ValueError(f"Invalid WebSocket URL: {ws_url}")

        self.ws_url = ws_url
        self.timeout = timeout
        self.max_size = max_size

        # Connection state
        self._ws: Optional[WebSocketClientProtocol] = None
        self._next_command_id: int = 1
        self._pending_commands: Dict[int, asyncio.Future] = {}
        self._event_handlers: Dict[str, List[Callable[[dict], Awaitable[None]]]] = {}
        self._receive_task: Optional[asyncio.Task] = None
        self._enabled_domains: Set[str] = set()  # For domain replay after reconnection
        self._is_connected: bool = False

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket connection is active."""
        if not self._is_connected or self._ws is None:
            return False
        # Check if WebSocket is still open (works with websockets 12+ and 15+)
        try:
            return self._ws.state.name == "OPEN"
        except AttributeError:
            # Fallback for older versions
            return not getattr(self._ws, "closed", True)

    async def connect(self) -> None:
        """Establish WebSocket connection and start receive loop.

        Raises:
            ConnectionFailedError: If WebSocket connection fails
        """
        try:
            logger.info(f"Connecting to {self.ws_url}")
            self._ws = await websockets.connect(
                self.ws_url,
                max_size=self.max_size
            )
            self._is_connected = True
            self._receive_task = asyncio.create_task(self._receive_loop())
            logger.info("CDP connection established")
        except Exception as e:
            raise ConnectionFailedError(
                f"Failed to connect to {self.ws_url}: {e}",
                details={"url": self.ws_url, "error": str(e)}
            )

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        logger.info("Disconnecting CDP connection")
        self._is_connected = False

        # Cancel receive loop
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self._ws:
            try:
                # Check if already closed using state (websockets 15+)
                if hasattr(self._ws, 'state') and self._ws.state.name != "CLOSED":
                    await self._ws.close()
                elif not hasattr(self._ws, 'state'):
                    # Fallback: just try to close
                    await self._ws.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")

        # Clear pending commands with ConnectionClosedError
        for future in self._pending_commands.values():
            if not future.done():
                future.set_exception(
                    ConnectionClosedError("Connection closed during command execution")
                )
        self._pending_commands.clear()

        logger.info("CDP connection closed")

    async def __aenter__(self) -> "CDPConnection":
        """Context manager entry: connect automatically."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: disconnect automatically."""
        await self.disconnect()

    async def execute_command(
        self,
        method: str,
        params: Optional[dict] = None,
        *,
        timeout: Optional[float] = None
    ) -> dict:
        """Execute CDP command and wait for response.

        Args:
            method: CDP method name (e.g., "Runtime.evaluate", "Console.enable")
            params: Method parameters (default: empty dict)
            timeout: Command timeout in seconds (default: self.timeout)

        Returns:
            Command result dict (contents of "result" field in response)

        Raises:
            ConnectionClosedError: If connection is not active
            CDPTimeoutError: If command times out
            CommandFailedError: If Chrome returns error response
        """
        if not self.is_connected:
            raise ConnectionClosedError("Cannot execute command: connection not active")

        # Generate unique command ID
        cmd_id = self._next_command_id
        self._next_command_id += 1

        # Create future for response
        future: asyncio.Future = asyncio.Future()
        self._pending_commands[cmd_id] = future

        # Track enabled domains for reconnection replay
        if method.endswith(".enable"):
            domain = method.split(".")[0]
            self._enabled_domains.add(domain)

        # Send command
        message = json.dumps({
            "id": cmd_id,
            "method": method,
            "params": params or {}
        })

        try:
            await self._ws.send(message)
            logger.debug(f"Sent command {cmd_id}: {method}")

            # Wait for response with timeout
            cmd_timeout = timeout if timeout is not None else self.timeout
            response = await asyncio.wait_for(future, timeout=cmd_timeout)
            return response

        except asyncio.TimeoutError:
            raise CDPTimeoutError(
                f"Command timed out",
                command_method=method,
                timeout=cmd_timeout
            )
        finally:
            # Clean up pending command
            self._pending_commands.pop(cmd_id, None)

    def subscribe(
        self,
        event_name: str,
        callback: Callable[[dict], Awaitable[None]]
    ) -> None:
        """Register async callback for CDP event.

        Args:
            event_name: CDP event name (e.g., "Console.messageAdded")
            callback: Async function with signature: async def callback(params: dict)

        Note:
            Remember to enable the corresponding CDP domain first.
            Example: await conn.execute_command("Console.enable")
        """
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(callback)
        logger.debug(f"Subscribed to event: {event_name}")

    def unsubscribe(
        self,
        event_name: str,
        callback: Callable[[dict], Awaitable[None]]
    ) -> None:
        """Remove event callback.

        Args:
            event_name: CDP event name
            callback: Previously registered callback function
        """
        if event_name in self._event_handlers:
            try:
                self._event_handlers[event_name].remove(callback)
                logger.debug(f"Unsubscribed from event: {event_name}")
            except ValueError:
                logger.warning(f"Callback not found for event: {event_name}")

    async def _receive_loop(self) -> None:
        """Background task to receive and route WebSocket messages.

        Routes messages to either:
        - Command responses (matched by ID to pending futures)
        - Event notifications (dispatched to registered callbacks)

        Handles malformed messages and connection errors gracefully.
        """
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)

                    # Command response (has "id" field)
                    if "id" in data:
                        cmd_id = data["id"]
                        if cmd_id in self._pending_commands:
                            future = self._pending_commands[cmd_id]

                            # Error response
                            if "error" in data:
                                error = data["error"]
                                future.set_exception(
                                    CommandFailedError(
                                        error.get("message", "Unknown CDP error"),
                                        error_code=error.get("code"),
                                        details={"error": error}
                                    )
                                )
                            # Success response
                            else:
                                result = data.get("result", {})
                                future.set_result(result)

                    # Event notification (has "method" field, no "id")
                    elif "method" in data:
                        event_name = data["method"]
                        params = data.get("params", {})
                        logger.debug(f"Received event: {event_name}")

                        # Dispatch to registered handlers
                        handlers = self._event_handlers.get(event_name, [])
                        for handler in handlers:
                            try:
                                # Run handler as background task (non-blocking)
                                asyncio.create_task(handler(params))
                            except Exception as e:
                                # Isolate handler errors (Principle 6: Diagnostic Transparency)
                                logger.error(
                                    f"Event handler error for {event_name}: {e}",
                                    exc_info=True
                                )

                except json.JSONDecodeError as e:
                    logger.error(f"Malformed CDP message: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)

        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            self._is_connected = False
            # Fail all pending commands
            for future in self._pending_commands.values():
                if not future.done():
                    future.set_exception(
                        ConnectionClosedError(f"Connection closed: {e}")
                    )
        except Exception as e:
            logger.error(f"Receive loop error: {e}", exc_info=True)
            self._is_connected = False
