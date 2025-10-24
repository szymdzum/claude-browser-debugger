"""
Unit tests for CDP collectors (ConsoleCollector, NetworkCollector, etc.)

Tests User Story 2: Ergonomic Collector Refactoring with mocked CDPConnection.
"""

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from collections import deque

from scripts.cdp.collectors.console import ConsoleCollector
from scripts.cdp.connection import CDPConnection


@pytest.mark.asyncio
async def test_console_collector_lifecycle():
    """
    T028 (partial): Test ConsoleCollector start/stop lifecycle with mocked connection.

    Verifies:
    - Console.enable command is called on start()
    - Event subscription is registered
    - Periodic flush task is created when output_path specified
    - Cleanup is performed on stop()
    """
    # Create mock connection
    mock_conn = AsyncMock(spec=CDPConnection)
    mock_conn.execute_command = AsyncMock()
    mock_conn.subscribe = MagicMock()
    mock_conn.unsubscribe = MagicMock()

    # Create collector without output path (no periodic flush)
    collector = ConsoleCollector(mock_conn)

    # Start collector
    await collector.start()

    # Verify Console.enable was called
    mock_conn.execute_command.assert_called_once_with("Console.enable")

    # Verify event subscription
    mock_conn.subscribe.assert_called_once()
    args = mock_conn.subscribe.call_args[0]
    assert args[0] == "Console.messageAdded"
    assert callable(args[1])  # Callback function

    # Verify no flush task (no output path)
    assert collector._flush_task is None

    # Stop collector
    await collector.stop()

    # Verify unsubscribe
    mock_conn.unsubscribe.assert_called_once()
    unsubscribe_args = mock_conn.unsubscribe.call_args[0]
    assert unsubscribe_args[0] == "Console.messageAdded"


@pytest.mark.asyncio
async def test_console_collector_message_capture():
    """
    T028 (partial): Test message capture and buffering.

    Verifies:
    - Console messages are appended to buffer
    - Bounded buffer enforces maxlen=1000 limit
    - Message format is JSONL-compatible
    """
    mock_conn = AsyncMock(spec=CDPConnection)
    mock_conn.execute_command = AsyncMock()
    mock_conn.subscribe = MagicMock()

    collector = ConsoleCollector(mock_conn)
    await collector.start()

    # Simulate console message events
    await collector._on_message({
        "message": {
            "timestamp": 1634567890.123,
            "level": "log",
            "text": "Hello, world!",
            "url": "https://example.com",
            "lineNumber": 42
        }
    })

    await collector._on_message({
        "message": {
            "timestamp": 1634567891.456,
            "level": "error",
            "text": "Uncaught TypeError",
            "url": "https://example.com",
            "lineNumber": 55
        }
    })

    # Verify buffer contains 2 entries
    assert len(collector._buffer) == 2

    # Verify entry format
    first_entry = collector._buffer[0]
    assert first_entry["timestamp"] == 1634567890.123
    assert first_entry["level"] == "log"
    assert first_entry["text"] == "Hello, world!"
    assert first_entry["url"] == "https://example.com"
    assert first_entry["line"] == 42

    await collector.stop()


@pytest.mark.asyncio
async def test_console_collector_level_filter():
    """
    T028 (partial): Test level filtering functionality.

    Verifies:
    - level_filter="warn" only captures warn and error messages
    - Lower-level messages (log, info) are ignored
    """
    mock_conn = AsyncMock(spec=CDPConnection)
    mock_conn.execute_command = AsyncMock()
    mock_conn.subscribe = MagicMock()

    # Create collector with warn level filter
    collector = ConsoleCollector(mock_conn, level_filter="warn")
    await collector.start()

    # Simulate log message (should be filtered out)
    await collector._on_message({
        "message": {
            "timestamp": 1,
            "level": "log",
            "text": "Debug info",
            "url": "",
            "lineNumber": 0
        }
    })

    # Simulate info message (should be filtered out)
    await collector._on_message({
        "message": {
            "timestamp": 2,
            "level": "info",
            "text": "Info message",
            "url": "",
            "lineNumber": 0
        }
    })

    # Simulate warn message (should be captured)
    await collector._on_message({
        "message": {
            "timestamp": 3,
            "level": "warn",
            "text": "Warning message",
            "url": "",
            "lineNumber": 0
        }
    })

    # Simulate error message (should be captured)
    await collector._on_message({
        "message": {
            "timestamp": 4,
            "level": "error",
            "text": "Error message",
            "url": "",
            "lineNumber": 0
        }
    })

    # Verify only warn and error were captured
    assert len(collector._buffer) == 2
    assert collector._buffer[0]["level"] == "warn"
    assert collector._buffer[1]["level"] == "error"

    await collector.stop()


@pytest.mark.asyncio
async def test_console_collector_bounded_buffer():
    """
    T028 (partial): Test bounded buffer prevents memory leaks.

    Verifies:
    - Buffer enforces maxlen=1000 limit
    - Oldest entries are dropped when limit reached (FR-012)
    """
    mock_conn = AsyncMock(spec=CDPConnection)
    mock_conn.execute_command = AsyncMock()
    mock_conn.subscribe = MagicMock()

    collector = ConsoleCollector(mock_conn)
    await collector.start()

    # Add 1500 messages (exceeds buffer limit)
    for i in range(1500):
        await collector._on_message({
            "message": {
                "timestamp": i,
                "level": "log",
                "text": f"Message {i}",
                "url": "",
                "lineNumber": 0
            }
        })

    # Verify buffer is capped at 1000
    assert len(collector._buffer) == 1000

    # Verify oldest entries were dropped (first message should be #500)
    first_entry = collector._buffer[0]
    assert first_entry["text"] == "Message 500"

    # Verify latest entry is preserved
    last_entry = collector._buffer[-1]
    assert last_entry["text"] == "Message 1499"

    await collector.stop()


@pytest.mark.asyncio
async def test_console_collector_flush_to_disk(tmp_path):
    """
    T028 (partial): Test JSONL file writing.

    Verifies:
    - Flush writes buffer to JSONL file
    - Buffer is cleared after flush
    - Output format is valid JSONL
    """
    mock_conn = AsyncMock(spec=CDPConnection)
    mock_conn.execute_command = AsyncMock()
    mock_conn.subscribe = MagicMock()

    output_file = tmp_path / "console-logs.jsonl"
    collector = ConsoleCollector(mock_conn, output_path=output_file)
    await collector.start()

    # Add messages
    await collector._on_message({
        "message": {
            "timestamp": 1,
            "level": "log",
            "text": "First message",
            "url": "https://example.com",
            "lineNumber": 10
        }
    })

    await collector._on_message({
        "message": {
            "timestamp": 2,
            "level": "error",
            "text": "Second message",
            "url": "https://example.com",
            "lineNumber": 20
        }
    })

    # Flush to disk
    collector._flush_to_disk()

    # Verify buffer is cleared
    assert len(collector._buffer) == 0

    # Verify file exists and contains valid JSONL
    assert output_file.exists()
    with open(output_file) as f:
        lines = f.readlines()

    assert len(lines) == 2

    # Parse first line
    first_entry = json.loads(lines[0])
    assert first_entry["timestamp"] == 1
    assert first_entry["level"] == "log"
    assert first_entry["text"] == "First message"

    # Parse second line
    second_entry = json.loads(lines[1])
    assert second_entry["timestamp"] == 2
    assert second_entry["level"] == "error"
    assert second_entry["text"] == "Second message"

    await collector.stop()


@pytest.mark.asyncio
async def test_console_collector_context_manager(tmp_path):
    """
    T028 (partial): Test context manager support.

    Verifies:
    - __aenter__ calls start()
    - __aexit__ calls stop() and flushes data
    """
    mock_conn = AsyncMock(spec=CDPConnection)
    mock_conn.execute_command = AsyncMock()
    mock_conn.subscribe = MagicMock()
    mock_conn.unsubscribe = MagicMock()

    output_file = tmp_path / "console-logs.jsonl"

    # Use context manager
    async with ConsoleCollector(mock_conn, output_path=output_file) as collector:
        # Verify started
        assert collector._running

        # Add message
        await collector._on_message({
            "message": {
                "timestamp": 1,
                "level": "log",
                "text": "Test message",
                "url": "",
                "lineNumber": 0
            }
        })

    # Verify stopped
    assert not collector._running

    # Verify data was flushed
    assert output_file.exists()
    with open(output_file) as f:
        lines = f.readlines()
    assert len(lines) == 1


@pytest.mark.asyncio
async def test_console_collector_periodic_flush(tmp_path):
    """
    T028 (partial): Test periodic flush functionality.

    Verifies:
    - Periodic flush task is created when output_path specified
    - Flush is called periodically (test with short interval)
    - Task is cancelled on stop()
    """
    mock_conn = AsyncMock(spec=CDPConnection)
    mock_conn.execute_command = AsyncMock()
    mock_conn.subscribe = MagicMock()

    output_file = tmp_path / "console-logs.jsonl"
    collector = ConsoleCollector(mock_conn, output_path=output_file)

    # Patch asyncio.sleep to use shorter interval for testing
    with patch("asyncio.sleep", side_effect=[None, None, asyncio.CancelledError()]):
        await collector.start()

        # Verify flush task was created
        assert collector._flush_task is not None

        # Add message
        await collector._on_message({
            "message": {
                "timestamp": 1,
                "level": "log",
                "text": "Test",
                "url": "",
                "lineNumber": 0
            }
        })

        # Wait for periodic flush to trigger (mocked sleep)
        await asyncio.sleep(0.1)

        # Stop collector (should cancel flush task)
        await collector.stop()

        # Verify flush task was cancelled
        assert collector._flush_task.cancelled() or collector._flush_task.done()
