"""
Network collector for CDP - captures network requests and responses.

Implements User Story 4: Core Command Implementation - Network Monitoring
"""

import asyncio
import json
import sys
from pathlib import Path
from collections import deque
from typing import Optional, Dict, Any

from ..connection import CDPConnection
from ..exceptions import CDPError


class NetworkCollector:
    """
    Captures network requests and responses from the page.

    Outputs JSONL format for token efficiency. Uses bounded buffer (deque maxlen=1000)
    to prevent memory leaks during long sessions. Implements periodic flush every 30s.

    Usage:
        # Write to file
        async with CDPConnection(ws_url) as conn:
            output_file = Path("/tmp/network-logs.jsonl")
            async with NetworkCollector(conn, output_file) as collector:
                await asyncio.sleep(60)  # Monitor for 60 seconds
            # Collector automatically stopped, data flushed

        # Stream to stdout (default)
        async with CDPConnection(ws_url) as conn:
            async with NetworkCollector(conn) as collector:
                await asyncio.sleep(60)  # Monitor for 60 seconds
            # Network events streamed to stdout in real-time

    Attributes:
        connection: Active CDP connection
        output_path: Output file path for captured data (None = stream to stdout)
        include_bodies: Whether to capture response bodies
        _buffer: Bounded in-memory buffer (max 1000 entries, only used for file output)
        _flush_task: Background task for periodic flush (file mode only)
        _running: Flag indicating if collector is active
        _requests: Dict mapping requestId to request data
    """

    def __init__(
        self,
        connection: CDPConnection,
        output_path: Optional[Path] = None,
        include_bodies: bool = False,
        max_body_size: int = 1048576,  # 1MB default limit
    ):
        """
        Initialize network collector.

        Args:
            connection: Active CDPConnection instance
            output_path: Output file path for JSONL logs (None = stream to stdout)
            include_bodies: Whether to capture response bodies
            max_body_size: Maximum response body size to capture (bytes)
        """
        self.connection = connection
        self.output_path = Path(output_path) if output_path else None
        self.include_bodies = include_bodies
        self.max_body_size = max_body_size

        self._buffer = deque(maxlen=1000)  # Bounded buffer for memory leak prevention
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._requests: Dict[str, Dict[str, Any]] = {}  # Track requests for matching

    async def start(self):
        """
        Enable network monitoring.

        Executes Network.enable CDP command and subscribes to network events.
        Starts periodic flush task if output_path is specified.

        Raises:
            CDPError: If Network.enable command fails
        """
        # Enable Network domain
        await self.connection.execute_command("Network.enable")

        # Subscribe to network events
        self.connection.subscribe("Network.requestWillBeSent", self._on_request)
        self.connection.subscribe("Network.responseReceived", self._on_response)
        self.connection.subscribe("Network.loadingFinished", self._on_loading_finished)
        self.connection.subscribe("Network.loadingFailed", self._on_loading_failed)

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
        self.connection.unsubscribe("Network.requestWillBeSent", self._on_request)
        self.connection.unsubscribe("Network.responseReceived", self._on_response)
        self.connection.unsubscribe(
            "Network.loadingFinished", self._on_loading_finished
        )
        self.connection.unsubscribe("Network.loadingFailed", self._on_loading_failed)

    async def _on_request(self, params: dict):
        """
        Event handler for Network.requestWillBeSent.

        Stores request data for later matching with response.

        Args:
            params: CDP event parameters containing request object
        """
        request_id = params.get("requestId")
        request = params.get("request", {})

        # Store request for matching (only if we have a valid request_id)
        if request_id is not None:
            self._requests[request_id] = {
                "requestId": request_id,
                "url": request.get("url", ""),
                "method": request.get("method", ""),
                "timestamp": params.get("timestamp", 0),
                "type": params.get("type", ""),
            }

    async def _on_response(self, params: dict):
        """
        Event handler for Network.responseReceived.

        Matches response with request and optionally fetches body.

        Args:
            params: CDP event parameters containing response object
        """
        request_id = params.get("requestId")
        response = params.get("response", {})

        # Get matching request
        request_data = (
            self._requests.get(request_id, {}) if request_id is not None else {}
        )

        # Build entry
        entry = {
            "requestId": request_id,
            "url": response.get("url", request_data.get("url", "")),
            "method": request_data.get("method", "GET"),
            "status": response.get("status", 0),
            "statusText": response.get("statusText", ""),
            "mimeType": response.get("mimeType", ""),
            "timestamp": response.get("timing", {}).get("receiveHeadersEnd", 0),
            "type": params.get("type", request_data.get("type", "")),
        }

        # Capture response body if requested
        if self.include_bodies and self._should_capture_body(response):
            try:
                # Fetch response body via CDP
                body_result = await self.connection.execute_command(
                    "Network.getResponseBody", {"requestId": request_id}
                )
                if body_result.get("body"):
                    body = body_result["body"]
                    # Limit body size
                    if len(body) <= self.max_body_size:
                        entry["body"] = body
                        entry["base64Encoded"] = body_result.get("base64Encoded", False)
            except Exception:
                # Body not available (e.g., redirect, cached, etc.)
                pass

        # Stream to stdout if no output path specified, otherwise buffer for file
        if self.output_path is None:
            # Real-time stdout streaming
            print(json.dumps(entry), file=sys.stdout, flush=True)
        else:
            # Append to buffer
            self._buffer.append(entry)

    async def _on_loading_finished(self, params: dict):
        """
        Event handler for Network.loadingFinished.

        Cleanup completed requests.

        Args:
            params: CDP event parameters
        """
        request_id = params.get("requestId")
        # Remove from tracking dict to free memory
        if request_id is not None:
            self._requests.pop(request_id, None)

    async def _on_loading_failed(self, params: dict):
        """
        Event handler for Network.loadingFailed.

        Log failed requests.

        Args:
            params: CDP event parameters
        """
        request_id = params.get("requestId")
        request_data = (
            self._requests.get(request_id, {}) if request_id is not None else {}
        )

        # Log failure
        entry = {
            "requestId": request_id,
            "url": request_data.get("url", ""),
            "method": request_data.get("method", "GET"),
            "status": 0,
            "statusText": "FAILED",
            "errorText": params.get("errorText", ""),
            "timestamp": params.get("timestamp", 0),
        }

        # Stream to stdout if no output path specified, otherwise buffer for file
        if self.output_path is None:
            # Real-time stdout streaming
            print(json.dumps(entry), file=sys.stdout, flush=True)
        else:
            self._buffer.append(entry)

        # Cleanup
        if request_id is not None:
            self._requests.pop(request_id, None)

    def _should_capture_body(self, response: dict) -> bool:
        """
        Determine if response body should be captured.

        Args:
            response: Response object from CDP

        Returns:
            True if body should be captured
        """
        # Skip large files
        headers = response.get("headers", {})
        content_length = headers.get("Content-Length", headers.get("content-length"))
        if content_length and int(content_length) > self.max_body_size:
            return False

        # Skip binary types by default
        mime_type = response.get("mimeType", "").lower()
        if mime_type.startswith(("image/", "video/", "audio/", "font/")):
            return False

        return True

    async def _periodic_flush(self):
        """
        Flush buffer to disk every 30 seconds.

        Runs in background task until cancelled. Prevents unbounded memory growth
        during long sessions.
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
