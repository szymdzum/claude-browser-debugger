"""
CDP Session management for target discovery.

Implements User Story 3: Unified CLI Interface - Target Discovery
"""

import json
import urllib.request
import urllib.error
from typing import List, Optional, Dict, Any

from .connection import CDPConnection
from .exceptions import CDPError, CDPTargetNotFoundError


class Target:
    """
    Represents a debuggable Chrome target (page, worker, service worker, iframe).

    Attributes:
        id: Unique target ID
        type: Target type ("page", "iframe", "worker", "service_worker", "browser")
        title: Page title or worker name
        url: Target URL
        webSocketDebuggerUrl: CDP WebSocket URL for this target
        description: Additional metadata (optional)
        devtoolsFrontendUrl: DevTools UI URL (optional)
        faviconUrl: Page favicon URL (optional)
    """

    def __init__(self, target_data: Dict[str, Any]):
        """
        Initialize Target from Chrome HTTP endpoint response.

        Args:
            target_data: Raw target dictionary from /json endpoint
        """
        self.id = target_data["id"]
        self.type = target_data["type"]
        self.title = target_data.get("title", "")
        self.url = target_data.get("url", "")
        self.webSocketDebuggerUrl = target_data["webSocketDebuggerUrl"]
        self.description = target_data.get("description", "")
        self.devtoolsFrontendUrl = target_data.get("devtoolsFrontendUrl", "")
        self.faviconUrl = target_data.get("faviconUrl", "")

    def to_dict(self) -> Dict[str, Any]:
        """Convert target to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "url": self.url,
            "webSocketDebuggerUrl": self.webSocketDebuggerUrl,
            "description": self.description,
            "devtoolsFrontendUrl": self.devtoolsFrontendUrl,
            "faviconUrl": self.faviconUrl,
        }

    def __repr__(self):
        return f"Target(id={self.id!r}, type={self.type!r}, url={self.url!r})"


class CDPSession:
    """
    Session manager for discovering Chrome targets and creating CDP connections.

    Provides higher-level target selection (by URL, type, ID) via Chrome HTTP endpoint.

    Usage:
        session = CDPSession("localhost", 9222)
        targets = session.list_targets(target_type="page")
        conn = await session.connect_to_target(targets[0])

    Attributes:
        chrome_host: Chrome host (default: "localhost")
        chrome_port: Chrome debugging port (default: 9222)
        timeout: HTTP request timeout for target discovery (default: 5s)
    """

    def __init__(
        self,
        chrome_host: str = "localhost",
        chrome_port: int = 9222,
        timeout: float = 5.0,
    ):
        """
        Initialize CDP session manager.

        Args:
            chrome_host: Chrome host
            chrome_port: Chrome debugging port (1-65535)
            timeout: HTTP request timeout in seconds

        Raises:
            ValueError: If chrome_port is out of range
        """
        if not 1 <= chrome_port <= 65535:
            raise ValueError(f"chrome_port must be 1-65535, got {chrome_port}")

        self.chrome_host = chrome_host
        self.chrome_port = chrome_port
        self.timeout = timeout

    def list_targets(
        self,
        target_type: Optional[str] = None,
        url_pattern: Optional[str] = None,
    ) -> List[Target]:
        """
        Fetch targets from Chrome HTTP endpoint with optional filtering.

        Args:
            target_type: Filter by target type ("page", "iframe", "worker", "service_worker", "browser")
            url_pattern: Filter by URL regex pattern (case-insensitive substring match)

        Returns:
            List of Target objects matching filters

        Raises:
            CDPError: If HTTP endpoint is unreachable or returns invalid data
        """
        endpoint_url = f"http://{self.chrome_host}:{self.chrome_port}/json"

        try:
            with urllib.request.urlopen(endpoint_url, timeout=self.timeout) as response:
                targets_data = json.loads(response.read())
        except urllib.error.URLError as e:
            raise CDPError(
                f"Failed to connect to Chrome at {endpoint_url}: {e}",
                details={
                    "chrome_host": self.chrome_host,
                    "chrome_port": self.chrome_port,
                    "recovery": "Ensure Chrome is running with --remote-debugging-port",
                },
            ) from e
        except json.JSONDecodeError as e:
            raise CDPError(
                f"Invalid JSON response from Chrome endpoint: {e}",
                details={"endpoint": endpoint_url},
            ) from e

        # Convert to Target objects
        targets = [Target(data) for data in targets_data]

        # Apply filters
        if target_type:
            targets = [t for t in targets if t.type == target_type]

        if url_pattern:
            # Case-insensitive substring match (simple pattern matching)
            url_pattern_lower = url_pattern.lower()
            targets = [t for t in targets if url_pattern_lower in t.url.lower()]

        return targets

    def get_target_by_id(self, target_id: str) -> Optional[Target]:
        """
        Find target by ID.

        Args:
            target_id: Target ID to search for

        Returns:
            Target object if found, None otherwise

        Raises:
            CDPError: If HTTP endpoint is unreachable
        """
        all_targets = self.list_targets()
        for target in all_targets:
            if target.id == target_id:
                return target
        return None

    async def connect_to_target(self, target: Target) -> CDPConnection:
        """
        Create CDPConnection for given target.

        Args:
            target: Target to connect to

        Returns:
            CDPConnection instance (not yet connected - call connect() or use as context manager)

        Raises:
            CDPError: If WebSocket URL is invalid
        """
        if not target.webSocketDebuggerUrl:
            raise CDPError(
                f"Target {target.id} has no WebSocket debugger URL",
                details={"target": target.to_dict()},
            )

        return CDPConnection(target.webSocketDebuggerUrl)

    async def connect_to_first_page(self) -> CDPConnection:
        """
        Convenience method to connect to first page target.

        Returns:
            CDPConnection instance connected to first page

        Raises:
            CDPTargetNotFoundError: If no page targets found
            CDPError: If connection fails
        """
        targets = self.list_targets(target_type="page")

        if not targets:
            raise CDPTargetNotFoundError(
                "No page targets found",
                details={
                    "chrome_host": self.chrome_host,
                    "chrome_port": self.chrome_port,
                    "recovery": "Navigate to a URL in Chrome or check --remote-debugging-port",
                },
            )

        return await self.connect_to_target(targets[0])
