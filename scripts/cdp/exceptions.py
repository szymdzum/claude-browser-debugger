"""Exception hierarchy for CDP operations.

All CDP-related exceptions inherit from CDPError base class.
Provides structured error types for connection, command, and timeout failures.
"""

from typing import Optional


class CDPError(Exception):
    """Base exception for all CDP-related errors.

    Attributes:
        message: Human-readable error message
        details: Optional dictionary with additional error context
    """

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class CDPConnectionError(CDPError):
    """WebSocket connection failures.

    Raised when establishing or maintaining CDP WebSocket connection fails.
    """

    pass


class ConnectionFailedError(CDPConnectionError):
    """Initial connection failed.

    Raised when WebSocket connection cannot be established.
    Common causes: wrong port, Chrome not running, network issues.
    """

    pass


class ConnectionClosedError(CDPConnectionError):
    """Connection closed unexpectedly.

    Raised when WebSocket connection is closed unexpectedly.
    Common causes: Chrome crash, network interruption, manual closure.
    """

    pass


class CDPCommandError(CDPError):
    """Command execution failures.

    Raised when CDP command returns an error response.
    """

    def __init__(
        self,
        message: str,
        method: Optional[str] = None,
        error_code: Optional[int] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.method = method
        self.error_code = error_code


class CommandFailedError(CDPCommandError):
    """Command returned error response.

    Raised when Chrome returns error response for executed command.
    Example: invalid JavaScript expression in Runtime.evaluate
    """

    pass


class InvalidCommandError(CDPCommandError):
    """Malformed command.

    Raised when command is invalid before sending to Chrome.
    Example: missing required parameters, invalid method name.
    """

    pass


class CDPTimeoutError(CDPError):
    """Command timed out.

    Raised when CDP command does not receive response within timeout period.
    """

    def __init__(
        self,
        message: str,
        command_method: Optional[str] = None,
        timeout: Optional[float] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.command_method = command_method
        self.timeout = timeout

    def __str__(self):
        if self.command_method and self.timeout:
            return f"Command '{self.command_method}' timed out after {self.timeout}s"
        return self.message


class CDPTargetNotFoundError(CDPError):
    """Target discovery failures.

    Raised when requested Chrome target cannot be found.
    Example: no page target matching URL filter, invalid target ID.
    """

    def __init__(
        self,
        message: str,
        target_id: Optional[str] = None,
        url_pattern: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.target_id = target_id
        self.url_pattern = url_pattern

    def __str__(self):
        if self.target_id:
            return f"Target not found: {self.target_id}"
        if self.url_pattern:
            return f"No target matching URL pattern: {self.url_pattern}"
        return self.message
