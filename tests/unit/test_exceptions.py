"""Unit tests for CDP exception hierarchy.

Tests exception types, inheritance, attributes, and string representations.
"""

import pytest
from scripts.cdp.exceptions import (
    CDPError,
    CDPConnectionError,
    ConnectionFailedError,
    ConnectionClosedError,
    CDPCommandError,
    CommandFailedError,
    InvalidCommandError,
    CDPTimeoutError,
    CDPTargetNotFoundError,
)


@pytest.mark.unit
class TestCDPError:
    """Test base CDPError exception."""

    def test_base_exception_message(self):
        """Test basic error message."""
        error = CDPError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_base_exception_with_details(self):
        """Test error with details dict."""
        error = CDPError("Test error", details={"key": "value", "count": 42})
        assert "Test error" in str(error)
        assert "key=value" in str(error)
        assert "count=42" in str(error)
        assert error.details == {"key": "value", "count": 42}


@pytest.mark.unit
class TestConnectionErrors:
    """Test connection-related exceptions."""

    def test_connection_error_inheritance(self):
        """Test CDPConnectionError inherits from CDPError."""
        error = CDPConnectionError("Connection failed")
        assert isinstance(error, CDPError)
        assert isinstance(error, CDPConnectionError)

    def test_connection_failed_error(self):
        """Test ConnectionFailedError for initial connection failures."""
        error = ConnectionFailedError(
            "Failed to connect",
            details={"url": "ws://localhost:9222", "reason": "timeout"},
        )
        assert isinstance(error, CDPConnectionError)
        assert "Failed to connect" in str(error)
        assert error.details["url"] == "ws://localhost:9222"

    def test_connection_closed_error(self):
        """Test ConnectionClosedError for unexpected disconnections."""
        error = ConnectionClosedError("Connection closed unexpectedly")
        assert isinstance(error, CDPConnectionError)
        assert "Connection closed unexpectedly" in str(error)


@pytest.mark.unit
class TestCommandErrors:
    """Test command execution exceptions."""

    def test_command_error_with_method(self):
        """Test CDPCommandError with method and error code."""
        error = CDPCommandError(
            "Invalid expression", method="Runtime.evaluate", error_code=-32000
        )
        assert isinstance(error, CDPError)
        assert error.method == "Runtime.evaluate"
        assert error.error_code == -32000

    def test_command_failed_error(self):
        """Test CommandFailedError for Chrome error responses."""
        error = CommandFailedError(
            "Cannot find context with specified id",
            method="Runtime.evaluate",
            error_code=-32000,
        )
        assert isinstance(error, CDPCommandError)
        assert "Cannot find context" in str(error)

    def test_invalid_command_error(self):
        """Test InvalidCommandError for malformed commands."""
        error = InvalidCommandError(
            "Missing required parameter",
            method="Page.navigate",
            details={"missing": "url"},
        )
        assert isinstance(error, CDPCommandError)
        assert "Missing required parameter" in str(error)


@pytest.mark.unit
class TestTimeoutError:
    """Test timeout exception."""

    def test_timeout_error_basic(self):
        """Test CDPTimeoutError basic message."""
        error = CDPTimeoutError("Command timed out")
        assert isinstance(error, CDPError)
        assert "Command timed out" in str(error)

    def test_timeout_error_with_details(self):
        """Test CDPTimeoutError with method and timeout duration."""
        error = CDPTimeoutError(
            "Timeout occurred", command_method="Runtime.evaluate", timeout=30.0
        )
        assert "Runtime.evaluate" in str(error)
        assert "30" in str(error)
        assert error.command_method == "Runtime.evaluate"
        assert error.timeout == 30.0


@pytest.mark.unit
class TestTargetNotFoundError:
    """Test target discovery exception."""

    def test_target_not_found_by_id(self):
        """Test CDPTargetNotFoundError with target ID."""
        error = CDPTargetNotFoundError("Target not found", target_id="ABC123")
        assert isinstance(error, CDPError)
        assert "ABC123" in str(error)
        assert error.target_id == "ABC123"

    def test_target_not_found_by_url(self):
        """Test CDPTargetNotFoundError with URL pattern."""
        error = CDPTargetNotFoundError(
            "No matching target", url_pattern="https://example.com"
        )
        assert "example.com" in str(error)
        assert error.url_pattern == "https://example.com"

    def test_target_not_found_generic(self):
        """Test CDPTargetNotFoundError without specific identifiers."""
        error = CDPTargetNotFoundError("No targets available")
        assert "No targets available" in str(error)
        assert error.target_id is None
        assert error.url_pattern is None
