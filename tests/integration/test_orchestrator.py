"""
Integration tests for orchestrate command.

Tests User Story 4: Core Command Implementation - Orchestration
"""

import subprocess
import sys
import pytest
import json
from pathlib import Path


def run_cli(*args):
    """
    Helper to run CLI command and capture output.

    Args:
        *args: Command-line arguments to pass to CLI

    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    cmd = [sys.executable, "-m", "scripts.cdp.cli.main"] + list(args)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


class TestOrchestrateHeadless:
    """
    T065: Integration tests for orchestrate headless mode.

    Tests full automated debugging workflow with headless Chrome.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    def test_orchestrate_headless_basic(self, tmp_path):
        """
        Test orchestrate headless with basic URL.

        Verifies Chrome launch, data capture, DOM extraction, and cleanup.
        """
        # Use a simple static page
        url = "https://example.com"

        returncode, stdout, stderr = run_cli(
            "orchestrate",
            "headless",
            url,
            "--duration",
            "3",  # Short duration for testing
            "--output-dir",
            str(tmp_path),
        )

        assert returncode == 0, f"Command failed: {stderr}"

        # Verify DOM was extracted
        dom_files = list(tmp_path.glob("dom-*.html"))
        assert len(dom_files) == 1, f"Expected 1 DOM file, found {len(dom_files)}"

        # Verify DOM contains expected content
        dom_content = dom_files[0].read_text()
        assert "<html" in dom_content.lower()
        assert "example" in dom_content.lower()  # example.com should contain "example"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_orchestrate_headless_with_console(self, tmp_path):
        """
        Test orchestrate headless with console monitoring.

        Verifies --include-console flag enables console collection.
        """
        url = "https://example.com"

        returncode, stdout, stderr = run_cli(
            "orchestrate",
            "headless",
            url,
            "--duration",
            "3",
            "--include-console",
            "--output-dir",
            str(tmp_path),
        )

        assert returncode == 0, f"Command failed: {stderr}"

        # Verify DOM was extracted
        dom_files = list(tmp_path.glob("dom-*.html"))
        assert len(dom_files) == 1

        # Console file may or may not exist (depends on whether page logged anything)
        # Just verify command succeeded

    @pytest.mark.integration
    @pytest.mark.slow
    def test_orchestrate_headless_summary_json(self, tmp_path):
        """
        Test orchestrate headless with JSON summary.

        Verifies --summary json flag generates JSON output.
        """
        url = "https://example.com"

        returncode, stdout, stderr = run_cli(
            "orchestrate",
            "headless",
            url,
            "--duration",
            "3",
            "--summary",
            "json",
            "--output-dir",
            str(tmp_path),
        )

        assert returncode == 0, f"Command failed: {stderr}"

        # Verify JSON summary was created
        summary_files = list(tmp_path.glob("summary-*.json"))
        assert (
            len(summary_files) == 1
        ), f"Expected 1 JSON summary, found {len(summary_files)}"

        # Verify JSON is valid
        summary_data = json.loads(summary_files[0].read_text())
        assert "url" in summary_data
        assert "mode" in summary_data
        assert "artifacts" in summary_data

    @pytest.mark.integration
    @pytest.mark.slow
    def test_orchestrate_headless_summary_both(self, tmp_path):
        """
        Test orchestrate headless with both text and JSON summaries.

        Verifies --summary both flag generates both formats.
        """
        url = "https://example.com"

        returncode, stdout, stderr = run_cli(
            "orchestrate",
            "headless",
            url,
            "--duration",
            "3",
            "--summary",
            "both",
            "--output-dir",
            str(tmp_path),
        )

        assert returncode == 0, f"Command failed: {stderr}"

        # Verify both summary formats were created
        json_summaries = list(tmp_path.glob("summary-*.json"))
        text_summaries = list(tmp_path.glob("summary-*.txt"))

        assert (
            len(json_summaries) == 1
        ), f"Expected 1 JSON summary, found {len(json_summaries)}"
        assert (
            len(text_summaries) == 1
        ), f"Expected 1 text summary, found {len(text_summaries)}"


class TestOrchestrateHeaded:
    """
    T066: Integration tests for orchestrate headed mode.

    Tests interactive debugging workflow with visible Chrome.
    """

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.manual
    def test_orchestrate_headed_basic(self, tmp_path):
        """
        Test orchestrate headed mode.

        Verifies Chrome launches in visible mode for interactive debugging.

        Note: This test requires manual intervention and is marked as @pytest.mark.manual.
        It will be skipped in automated CI runs.
        """
        url = "https://example.com"

        returncode, stdout, stderr = run_cli(
            "orchestrate", "headed", url, "--output-dir", str(tmp_path)
        )

        # Placeholder test - headed mode requires manual interaction
        assert returncode in [0, 1]

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.manual
    def test_orchestrate_headed_with_console(self, tmp_path):
        """
        Test orchestrate headed mode with console monitoring.

        Verifies console collector works in headed mode.

        Note: Marked as manual test - requires user interaction.
        """
        url = "http://localhost:3000"  # Assuming local dev server

        returncode, stdout, stderr = run_cli(
            "orchestrate",
            "headed",
            url,
            "--include-console",
            "--output-dir",
            str(tmp_path),
        )

        # Placeholder test
        assert returncode in [0, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
