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
