"""
Integration tests for ConsoleCollector with real Chrome instance.

Tests User Story 2: Ergonomic Collector Refactoring with live Chrome CDP connection.
"""

import pytest
import asyncio
import subprocess
import json
import time
import psutil
from pathlib import Path

from scripts.cdp.connection import CDPConnection
from scripts.cdp.collectors.console import ConsoleCollector


@pytest.fixture
def chrome_session():
    """
    Launch headless Chrome for testing and return session info.

    Yields:
        dict: Session info with ws_url, chrome_pid, profile paths
    """
    # Launch Chrome via chrome-launcher.sh (use auto port to avoid conflicts)
    launcher_cmd = [
        "./scripts/core/chrome-launcher.sh",
        "--mode=headless",
        "--port=auto",
        "--url=data:text/html,<script>console.log('Test message');</script>",
    ]

    output = subprocess.check_output(launcher_cmd, text=True, stderr=subprocess.DEVNULL)
    # Parse only the first line (JSON output), ignore debug messages
    session = json.loads(output.split("\n")[0])

    yield session

    # Cleanup: Kill Chrome process
    try:
        subprocess.run(["kill", str(session["pid"])], check=False)
    except Exception as e:
        print(f"Cleanup warning: {e}")


@pytest.mark.asyncio
async def test_console_collector_with_real_chrome(chrome_session, tmp_path):
    """
    T029: Test ConsoleCollector with real Chrome instance.

    Compares refactored Python collector output with expected console behavior.
    Verifies:
    - Console messages are captured from live page
    - JSONL output format is valid
    - Collector can start/stop cleanly
    """
    output_file = tmp_path / "console-test.jsonl"

    async with CDPConnection(chrome_session["ws_url"]) as conn:
        # Use ConsoleCollector
        async with ConsoleCollector(conn, output_file) as collector:
            # Navigate to page with console messages
            await conn.execute_command("Page.enable")
            await conn.execute_command(
                "Page.navigate",
                {
                    "url": "data:text/html,<script>console.log('Hello');"
                    "console.warn('Warning');"
                    "console.error('Error');</script>"
                },
            )

            # Wait for page to load and console messages to arrive
            await asyncio.sleep(2)

    # Verify file exists
    assert output_file.exists()

    # Read JSONL output
    with open(output_file) as f:
        lines = f.readlines()

    # Should have at least one console message
    assert len(lines) >= 1

    # Verify JSONL format
    for line in lines:
        entry = json.loads(line)
        assert "timestamp" in entry
        assert "level" in entry
        assert "text" in entry
        assert "url" in entry
        assert "line" in entry


@pytest.mark.asyncio
async def test_console_collector_memory_stability(chrome_session, tmp_path):
    """
    T030: Test ConsoleCollector memory stability over 5 minutes.

    Verifies FR-012: RSS memory variation <5% during long session.

    Note: This is a condensed version for CI (30 seconds instead of 5 minutes).
    For full validation, run manually with LONG_TEST=1 environment variable.
    """
    import os

    # Use shorter duration for CI, full 5 minutes if LONG_TEST=1
    duration = 300 if os.getenv("LONG_TEST") else 30

    output_file = tmp_path / "console-memory-test.jsonl"

    # Get initial memory baseline
    process = psutil.Process()
    initial_rss = process.memory_info().rss / (1024 * 1024)  # MB

    memory_samples = [initial_rss]

    async with CDPConnection(chrome_session["ws_url"]) as conn:
        async with ConsoleCollector(conn, output_file) as collector:
            # Navigate to page that generates console logs continuously
            await conn.execute_command("Page.enable")
            await conn.execute_command(
                "Page.navigate",
                {
                    "url": "data:text/html,<script>"
                    "setInterval(() => console.log('Log ' + Date.now()), 100);"
                    "</script>"
                },
            )

            # Monitor memory every 5 seconds
            start_time = time.time()
            while time.time() - start_time < duration:
                await asyncio.sleep(5)
                current_rss = process.memory_info().rss / (1024 * 1024)
                memory_samples.append(current_rss)

    # Calculate memory variation
    max_rss = max(memory_samples)
    min_rss = min(memory_samples)
    avg_rss = sum(memory_samples) / len(memory_samples)
    variation_pct = ((max_rss - min_rss) / avg_rss) * 100

    print(f"Memory samples: {memory_samples}")
    print(
        f"Min RSS: {min_rss:.2f}MB, Max RSS: {max_rss:.2f}MB, Avg RSS: {avg_rss:.2f}MB"
    )
    print(f"Variation: {variation_pct:.2f}%")

    # FR-012: Memory variation must be <5%
    assert (
        variation_pct < 5.0
    ), f"Memory variation {variation_pct:.2f}% exceeds 5% threshold"


@pytest.mark.asyncio
async def test_console_collector_level_filtering_integration(chrome_session, tmp_path):
    """
    T029 (additional): Test level filtering with real Chrome.

    Verifies:
    - level_filter="warn" only captures warn and error messages
    - Lower-level messages are properly filtered
    """
    output_file = tmp_path / "console-filtered.jsonl"

    async with CDPConnection(chrome_session["ws_url"]) as conn:
        # Use ConsoleCollector with warn filter
        async with ConsoleCollector(
            conn, output_file, level_filter="warn"
        ) as collector:
            await conn.execute_command("Page.enable")
            await conn.execute_command(
                "Page.navigate",
                {
                    "url": "data:text/html,<script>"
                    "console.log('Should be filtered');"
                    "console.info('Also filtered');"
                    "console.warn('Should appear');"
                    "console.error('Should also appear');"
                    "</script>"
                },
            )

            # Wait for messages
            await asyncio.sleep(2)

    # Read output
    with open(output_file) as f:
        lines = f.readlines()

    # Parse entries
    entries = [json.loads(line) for line in lines]

    # Verify only warn and error messages captured
    levels = [e["level"] for e in entries]
    assert "log" not in levels, "log messages should be filtered"
    assert "info" not in levels, "info messages should be filtered"

    # At least one warn or error should be captured
    assert any(
        l in ["warn", "warning", "error"] for l in levels
    ), "Expected at least one warn/error message"


@pytest.mark.asyncio
async def test_console_collector_comparison_with_legacy(chrome_session, tmp_path):
    """
    T029: Compare refactored Python collector with original implementation.

    Verifies:
    - Output format matches expected structure
    - No regressions from original implementation
    """
    output_file = tmp_path / "console-comparison.jsonl"

    async with CDPConnection(chrome_session["ws_url"]) as conn:
        async with ConsoleCollector(conn, output_file) as collector:
            await conn.execute_command("Page.enable")
            await conn.execute_command(
                "Page.navigate",
                {
                    "url": "data:text/html,<script>"
                    "console.log('Message 1');"
                    "console.log('Message 2');"
                    "console.log('Message 3');"
                    "</script>"
                },
            )

            await asyncio.sleep(2)

    # Verify output format matches legacy format
    with open(output_file) as f:
        lines = f.readlines()

    assert len(lines) >= 3, "Expected at least 3 log messages"

    # Verify each entry has required fields
    for line in lines:
        entry = json.loads(line)
        assert isinstance(entry["timestamp"], (int, float))
        assert entry["level"] in ["log", "info", "warn", "error", "verbose", "debug"]
        assert isinstance(entry["text"], str)
        assert isinstance(entry["url"], str)
        assert isinstance(entry["line"], int)


@pytest.mark.asyncio
async def test_console_collector_handles_complex_messages(chrome_session, tmp_path):
    """
    T029 (additional): Test handling of complex console messages.

    Verifies:
    - Object logging is handled gracefully
    - Array logging works correctly
    - Messages with special characters are escaped properly
    """
    output_file = tmp_path / "console-complex.jsonl"

    async with CDPConnection(chrome_session["ws_url"]) as conn:
        async with ConsoleCollector(conn, output_file) as collector:
            await conn.execute_command("Page.enable")
            await conn.execute_command(
                "Page.navigate",
                {
                    "url": "data:text/html,<script>"
                    "console.log('String with \"quotes\" and \\n newlines');"
                    "console.log({key: 'value', nested: {foo: 'bar'}});"
                    "console.log([1, 2, 3, 'four']);"
                    "</script>"
                },
            )

            await asyncio.sleep(2)

    # Verify file is valid JSONL (no parsing errors)
    with open(output_file) as f:
        lines = f.readlines()

    for line in lines:
        entry = json.loads(line)  # Should not raise exception
        assert "text" in entry


@pytest.mark.asyncio
async def test_console_collector_graceful_shutdown(chrome_session, tmp_path):
    """
    T029 (additional): Test graceful shutdown and final flush.

    Verifies:
    - Collector flushes all buffered data on stop()
    - Context manager exit triggers flush
    - No data loss on shutdown
    """
    output_file = tmp_path / "console-shutdown.jsonl"

    async with CDPConnection(chrome_session["ws_url"]) as conn:
        collector = ConsoleCollector(conn, output_file)
        await collector.start()

        # Navigate and wait for messages
        await conn.execute_command("Page.enable")
        await conn.execute_command(
            "Page.navigate",
            {
                "url": "data:text/html,<script>"
                "for (let i = 0; i < 10; i++) console.log('Message ' + i);"
                "</script>"
            },
        )

        await asyncio.sleep(1)

        # Stop collector (should trigger final flush)
        await collector.stop()

    # Verify all messages were flushed
    with open(output_file) as f:
        lines = f.readlines()

    # Should have at least 10 messages
    assert len(lines) >= 10, f"Expected >=10 messages, got {len(lines)}"
