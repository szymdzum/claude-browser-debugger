"""Integration tests for CDPConnection with real Chrome.

These tests launch actual headless Chrome instances and perform real CDP operations.
Requires chrome-launcher.sh and Chrome/Chromium browser.
"""

import asyncio
import json
import subprocess
import pytest
from pathlib import Path

from scripts.cdp.connection import CDPConnection
from scripts.cdp.exceptions import CDPTimeoutError, CommandFailedError


@pytest.fixture
def chrome_session():
    """Launch headless Chrome for testing.

    Yields session info dict with chrome_pid and ws_url.
    Automatically kills Chrome after test completes.
    """
    # Path to chrome-launcher.sh (relative to repository root)
    launcher_path = Path(__file__).parent.parent.parent / "scripts" / "core" / "chrome-launcher.sh"

    if not launcher_path.exists():
        pytest.skip(f"chrome-launcher.sh not found at {launcher_path}")

    # Launch Chrome with about:blank
    try:
        output = subprocess.check_output(
            [
                str(launcher_path),
                "--mode=headless",
                "--port=9222",
                "--url=about:blank"
            ],
            stderr=subprocess.PIPE,
            timeout=10
        )
        session = json.loads(output)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        pytest.skip(f"Failed to launch Chrome: {e}")

    yield session

    # Cleanup: kill Chrome
    try:
        subprocess.run(["kill", str(session["pid"])], timeout=5)
    except subprocess.TimeoutExpired:
        subprocess.run(["kill", "-9", str(session["pid"])])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_connection_lifecycle(chrome_session):
    """FR-001: Test connection establishment and closure with real Chrome."""
    ws_url = chrome_session["ws_url"]

    # Test connection
    conn = CDPConnection(ws_url)
    assert not conn.is_connected

    await conn.connect()
    assert conn.is_connected

    await conn.disconnect()
    assert not conn.is_connected


@pytest.mark.integration
@pytest.mark.asyncio
async def test_connection_context_manager(chrome_session):
    """Test context manager with real Chrome."""
    ws_url = chrome_session["ws_url"]

    async with CDPConnection(ws_url) as conn:
        assert conn.is_connected

    assert not conn.is_connected


@pytest.mark.integration
@pytest.mark.asyncio
async def test_runtime_evaluate_command(chrome_session):
    """FR-002: Test Runtime.evaluate command execution."""
    ws_url = chrome_session["ws_url"]

    async with CDPConnection(ws_url) as conn:
        # Simple expression
        result = await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "1 + 1", "returnByValue": True}
        )
        assert result["result"]["value"] == 2

        # Document title (should be empty for about:blank)
        result = await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "document.title", "returnByValue": True}
        )
        assert result["result"]["value"] == ""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_console_event_subscription(chrome_session):
    """FR-003: Test Console.messageAdded event subscription."""
    ws_url = chrome_session["ws_url"]

    received_messages = []

    async def on_console_message(params: dict):
        """Event handler that collects console messages."""
        received_messages.append(params)

    async with CDPConnection(ws_url) as conn:
        # Enable Console domain
        await conn.execute_command("Console.enable")

        # Subscribe to events
        conn.subscribe("Console.messageAdded", on_console_message)

        # Trigger console.log via JavaScript
        await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "console.log('Test message')"}
        )

        # Wait for event to be received
        await asyncio.sleep(0.5)

        # Verify event was received
        assert len(received_messages) > 0
        message = received_messages[0]["message"]
        assert message["level"] == "log"
        assert "Test message" in message["text"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_commands_sequential(chrome_session):
    """Test executing multiple commands sequentially."""
    ws_url = chrome_session["ws_url"]

    async with CDPConnection(ws_url) as conn:
        # Execute multiple commands
        result1 = await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "1 + 1", "returnByValue": True}
        )
        result2 = await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "2 * 3", "returnByValue": True}
        )
        result3 = await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "10 - 5", "returnByValue": True}
        )

        assert result1["result"]["value"] == 2
        assert result2["result"]["value"] == 6
        assert result3["result"]["value"] == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_command_timeout_with_real_chrome(chrome_session):
    """Test that command timeout works with real Chrome."""
    ws_url = chrome_session["ws_url"]

    async with CDPConnection(ws_url, timeout=0.1) as conn:
        # This should timeout because we're using a very short timeout
        # and sending invalid method that Chrome won't respond to properly
        with pytest.raises((CDPTimeoutError, CommandFailedError)):
            await conn.execute_command(
                "NonExistent.invalidMethod",
                {},
                timeout=0.1
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_domain_tracking_with_real_chrome(chrome_session):
    """Test that enabling domains tracks them correctly."""
    ws_url = chrome_session["ws_url"]

    async with CDPConnection(ws_url) as conn:
        # Enable multiple domains
        await conn.execute_command("Console.enable")
        await conn.execute_command("Network.enable")
        await conn.execute_command("Page.enable")

        # Verify domains are tracked
        assert "Console" in conn._enabled_domains
        assert "Network" in conn._enabled_domains
        assert "Page" in conn._enabled_domains


@pytest.mark.integration
@pytest.mark.asyncio
async def test_large_dom_extraction(chrome_session):
    """Test extracting large DOM (tests max_size buffer)."""
    ws_url = chrome_session["ws_url"]

    async with CDPConnection(ws_url) as conn:
        # Navigate to a page with content
        await conn.execute_command(
            "Runtime.evaluate",
            {
                "expression": """
                    document.body.innerHTML = '<div>' + 'x'.repeat(10000) + '</div>';
                """
            }
        )

        # Extract DOM
        result = await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "document.documentElement.outerHTML", "returnByValue": True}
        )

        dom = result["result"]["value"]
        assert len(dom) > 10000
        assert "<div>" in dom


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chrome_crash_recovery_with_reconnect(chrome_session):
    """T084: Test Chrome crash recovery via reconnect_with_backoff.

    Simulates Chrome crash by killing the process, then verifies
    reconnect_with_backoff can successfully reconnect when Chrome restarts.
    """
    ws_url = chrome_session["ws_url"]
    chrome_pid = chrome_session["pid"]

    conn = CDPConnection(ws_url, timeout=5.0)
    await conn.connect()

    # Verify connection works
    result = await conn.execute_command(
        "Runtime.evaluate",
        {"expression": "1 + 1", "returnByValue": True}
    )
    assert result["result"]["value"] == 2

    # Simulate Chrome crash (kill Chrome)
    subprocess.run(["kill", "-9", str(chrome_pid)])
    await asyncio.sleep(0.5)

    # Connection should fail now
    assert not conn.is_connected

    # Relaunch Chrome on same port
    launcher_path = Path(__file__).parent.parent.parent / "scripts" / "core" / "chrome-launcher.sh"
    try:
        output = subprocess.check_output(
            [str(launcher_path), "--mode=headless", "--port=9222", "--url=about:blank"],
            stderr=subprocess.PIPE,
            timeout=10
        )
        new_session = json.loads(output)
    except Exception as e:
        pytest.skip(f"Failed to relaunch Chrome: {e}")

    # Update connection URL to new session
    conn.ws_url = new_session["ws_url"]

    # Reconnect with backoff (should succeed immediately since Chrome is running)
    try:
        await conn.reconnect_with_backoff(max_attempts=3)
        assert conn.is_connected

        # Verify reconnected session works
        result = await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "2 + 2", "returnByValue": True}
        )
        assert result["result"]["value"] == 4
    finally:
        await conn.disconnect()
        # Cleanup new Chrome instance
        subprocess.run(["kill", str(new_session["pid"])])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_domain_replay_after_reconnect(chrome_session):
    """T085: Test domain replay after reconnection.

    Enables multiple CDP domains, disconnects, reconnects, and verifies
    all domains are automatically re-enabled via _replay_domains.
    """
    ws_url = chrome_session["ws_url"]

    conn = CDPConnection(ws_url)
    await conn.connect()

    # Enable multiple domains
    await conn.execute_command("Console.enable")
    await conn.execute_command("Network.enable")
    await conn.execute_command("Page.enable")

    # Verify domains tracked
    assert "Console" in conn._enabled_domains
    assert "Network" in conn._enabled_domains
    assert "Page" in conn._enabled_domains

    # Disconnect and reconnect
    await conn.disconnect()
    await conn.reconnect_with_backoff(max_attempts=3)

    # Verify domains were replayed (events should work)
    received_events = []

    async def on_console_message(params: dict):
        received_events.append(params)

    conn.subscribe("Console.messageAdded", on_console_message)

    # Trigger console event (should work because Console domain was replayed)
    await conn.execute_command(
        "Runtime.evaluate",
        {"expression": "console.log('Replay test')"}
    )

    await asyncio.sleep(0.5)

    # Event should be received (proving domain was re-enabled)
    assert len(received_events) > 0
    assert "Replay test" in received_events[0]["message"]["text"]

    await conn.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_handler_exception_isolation(chrome_session):
    """T086: Test event handler exception isolation.

    Verifies that exceptions in event handlers don't crash the connection
    or prevent other handlers from running.
    """
    ws_url = chrome_session["ws_url"]

    received_by_good_handler = []
    error_handler_called = False

    async def failing_handler(params: dict):
        """Handler that always throws exception."""
        nonlocal error_handler_called
        error_handler_called = True
        raise RuntimeError("Intentional test error")

    async def good_handler(params: dict):
        """Handler that works correctly."""
        received_by_good_handler.append(params)

    async with CDPConnection(ws_url) as conn:
        await conn.execute_command("Console.enable")

        # Subscribe both handlers to same event
        conn.subscribe("Console.messageAdded", failing_handler)
        conn.subscribe("Console.messageAdded", good_handler)

        # Trigger console event
        await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "console.log('Exception isolation test')"}
        )

        await asyncio.sleep(0.5)

        # Verify both handlers were called
        assert error_handler_called, "Failing handler should have been called"
        assert len(received_by_good_handler) > 0, "Good handler should have received event"

        # Verify connection still works after handler exception
        result = await conn.execute_command(
            "Runtime.evaluate",
            {"expression": "1 + 1", "returnByValue": True}
        )
        assert result["result"]["value"] == 2
