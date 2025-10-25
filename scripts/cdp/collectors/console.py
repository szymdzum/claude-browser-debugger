"""
Console collector for CDP - captures console messages from the page.

Implements User Story 2: Ergonomic Collector Refactoring
"""

import asyncio
import json
import sys
from pathlib import Path
from collections import deque
from typing import Optional, Callable, Awaitable, TextIO

from ..connection import CDPConnection
from ..exceptions import CDPError


class ConsoleCollector:
    """
    Captures console messages (log, warn, error, debug, info) from the page.

    Outputs JSONL format for token efficiency. Uses bounded buffer (deque maxlen=1000)
    to prevent memory leaks during long sessions. Implements periodic flush every 30s.

    Usage:
        # Write to file
        async with CDPConnection(ws_url) as conn:
            output_file = Path("/tmp/console-logs.jsonl")
            async with ConsoleCollector(conn, output_file, level_filter="warn") as collector:
                await asyncio.sleep(10)  # Monitor for 10 seconds
            # Collector automatically stopped, data flushed

        # Stream to stdout (default)
        async with CDPConnection(ws_url) as conn:
            async with ConsoleCollector(conn) as collector:
                await asyncio.sleep(10)  # Monitor for 10 seconds
            # Messages streamed to stdout in real-time

    Attributes:
        connection: Active CDP connection
        output_path: Output file path for captured data (None = stream to stdout)
        level_filter: Minimum log level to capture ("log", "info", "warn", "error")
        _buffer: Bounded in-memory buffer (max 1000 entries, only used for file output)
        _flush_task: Background task for periodic flush (file mode only)
        _running: Flag indicating if collector is active
    """

    # Log level hierarchy (ascending severity)
    LOG_LEVELS = {
        "verbose": 0,
        "debug": 0,    # Same as verbose
        "log": 1,
        "info": 2,
        "warn": 3,
        "warning": 3,  # Alias
        "error": 4,
    }

    def __init__(
        self,
        connection: CDPConnection,
        output_path: Optional[Path] = None,
        level_filter: Optional[str] = None,
    ):
        """
        Initialize console collector.

        Args:
            connection: Active CDPConnection instance
            output_path: Output file path for JSONL logs (None = stream to stdout)
            level_filter: Minimum log level to capture (None = capture all)
        """
        self.connection = connection
        self.output_path = Path(output_path) if output_path else None
        self.level_filter = level_filter

        self._buffer = deque(maxlen=1000)  # Bounded buffer (FR-012: memory leak prevention)
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """
        Enable console monitoring.

        Executes Console.enable CDP command and subscribes to Console.messageAdded events.
        Starts periodic flush task if output_path is specified.

        Raises:
            CDPError: If Console.enable command fails
        """
        # Enable Console domain (CRITICAL: must enable before subscribing)
        await self.connection.execute_command("Console.enable")

        # Subscribe to console events
        self.connection.subscribe("Console.messageAdded", self._on_message)

        self._running = True

        # Start periodic flush if output path specified
        if self.output_path:
            self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop(self):
        """
        Stop monitoring and flush data.

        Cancels periodic flush task, performs final flush, and unsubscribes from events.
        """
        self._running = False

        # Cancel periodic flush task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass  # Expected

        # Final flush to disk
        if self.output_path:
            self._flush_to_disk()

        # Unsubscribe from events
        self.connection.unsubscribe("Console.messageAdded", self._on_message)

    async def _on_message(self, params: dict):
        """
        Event handler for Console.messageAdded.

        Applies level filtering and either streams to stdout or appends to buffer.
        Non-blocking to avoid stalling CDP receive loop (see Principle 3: Token Efficiency).

        Args:
            params: CDP event parameters containing message object
        """
        message = params.get("message", {})

        # Apply level filter
        if self.level_filter and not self._should_capture(message.get("level", "log")):
            return

        entry = {
            "timestamp": message.get("timestamp", 0),
            "level": message.get("level", "log"),
            "text": message.get("text", ""),
            "url": message.get("url", ""),
            "line": message.get("lineNumber", 0),
        }

        # Stream to stdout if no output path specified, otherwise buffer for file
        if self.output_path is None:
            # Real-time stdout streaming
            print(json.dumps(entry), file=sys.stdout, flush=True)
        else:
            # Append to bounded buffer (oldest entries automatically dropped if full)
            self._buffer.append(entry)

    def _should_capture(self, level: str) -> bool:
        """
        Check if log level should be captured based on level_filter.

        Args:
            level: Log level from CDP message

        Returns:
            True if level >= level_filter, False otherwise
        """
        if not self.level_filter:
            return True  # Capture all if no filter

        # Get level indices (default to 0 if unknown)
        filter_idx = self.LOG_LEVELS.get(self.level_filter.lower(), 0)
        level_idx = self.LOG_LEVELS.get(level.lower(), 0)

        return level_idx >= filter_idx

    async def _periodic_flush(self):
        """
        Flush buffer to disk every 30 seconds.

        Runs in background task until cancelled. Prevents unbounded memory growth
        during long sessions (FR-012: memory leak prevention).
        """
        while self._running:
            await asyncio.sleep(30)
            self._flush_to_disk()

    def _flush_to_disk(self):
        """
        Write buffer to JSONL file.

        Appends entries to output_path in JSONL format (one JSON object per line).
        Clears buffer after writing to free memory.
        """
        if not self.output_path or not self._buffer:
            return

        # Ensure parent directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to JSONL file
        with open(self.output_path, "a") as f:
            for entry in self._buffer:
                f.write(json.dumps(entry) + "\n")

        # Clear buffer to free memory
        self._buffer.clear()

    async def __aenter__(self):
        """Context manager entry: start collector."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: stop collector."""
        await self.stop()
        return False  # Don't suppress exceptions
