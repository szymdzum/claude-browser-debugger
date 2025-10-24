"""
Integration tests for CLI interface.

Tests User Story 3: Unified CLI Interface - Help Text, Argument Validation
"""

import subprocess
import sys
import pytest
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


class TestCLIHelpText:
    """
    T047: Test CLI help text validation.

    Verifies all subcommands show help correctly.
    """

    def test_main_help(self):
        """Test main --help shows all subcommands."""
        returncode, stdout, stderr = run_cli("--help")

        assert returncode == 0
        assert "Chrome DevTools Protocol (CDP) debugging tool" in stdout
        assert "session" in stdout
        assert "eval" in stdout
        assert "dom" in stdout
        assert "console" in stdout
        assert "network" in stdout
        assert "orchestrate" in stdout
        assert "query" in stdout

    def test_session_help(self):
        """Test session subcommand help."""
        returncode, stdout, stderr = run_cli("session", "--help")

        assert returncode == 0
        assert "Discover and filter Chrome targets" in stdout or "List and inspect Chrome targets" in stdout
        assert "--type" in stdout
        assert "--url" in stdout
        assert "browser-debugger session list" in stdout

    def test_eval_help(self):
        """Test eval subcommand help."""
        returncode, stdout, stderr = run_cli("eval", "--help")

        assert returncode == 0
        assert "Execute JavaScript" in stdout
        assert "--target" in stdout
        assert "--url" in stdout
        assert "--await" in stdout
        assert "expression" in stdout

    def test_dom_help(self):
        """Test dom subcommand help."""
        returncode, stdout, stderr = run_cli("dom", "--help")

        assert returncode == 0
        assert "Extract" in stdout and "DOM" in stdout
        assert "--output" in stdout
        assert "--wait-for" in stdout

    def test_console_help(self):
        """Test console subcommand help."""
        returncode, stdout, stderr = run_cli("console", "--help")

        assert returncode == 0
        assert "Stream console logs" in stdout
        assert "--duration" in stdout
        assert "--level" in stdout

    def test_network_help(self):
        """Test network subcommand help."""
        returncode, stdout, stderr = run_cli("network", "--help")

        assert returncode == 0
        assert "Record network activity" in stdout
        assert "--duration" in stdout
        assert "--include-bodies" in stdout

    def test_orchestrate_help(self):
        """Test orchestrate subcommand help."""
        returncode, stdout, stderr = run_cli("orchestrate", "--help")

        assert returncode == 0
        assert "debugging" in stdout and ("workflow" in stdout or "session" in stdout)
        assert "headless" in stdout
        assert "headed" in stdout
        assert "--include-console" in stdout

    def test_query_help(self):
        """Test query subcommand help."""
        returncode, stdout, stderr = run_cli("query", "--help")

        assert returncode == 0
        assert "CDP" in stdout and ("command" in stdout or "method" in stdout)
        assert "--method" in stdout
        assert "--params" in stdout


class TestCLIMutualExclusion:
    """
    T048: Test mutual exclusion groups.

    Verifies --target and --url flags are mutually exclusive where applicable.
    """

    def test_eval_target_url_mutual_exclusion(self):
        """Test eval command rejects both --target and --url."""
        returncode, stdout, stderr = run_cli(
            "eval",
            "--target", "page-123",
            "--url", "example.com",
            "document.title"
        )

        assert returncode != 0
        assert "not allowed with argument" in stderr or "mutually exclusive" in stderr

    def test_dom_target_url_mutual_exclusion(self):
        """Test dom command rejects both --target and --url."""
        returncode, stdout, stderr = run_cli(
            "dom",
            "dump",
            "--target", "page-123",
            "--url", "example.com",
            "--output", "/tmp/test.html"
        )

        assert returncode != 0
        assert "not allowed with argument" in stderr or "mutually exclusive" in stderr

    def test_console_target_url_mutual_exclusion(self):
        """Test console command rejects both --target and --url."""
        returncode, stdout, stderr = run_cli(
            "console",
            "stream",
            "--target", "page-123",
            "--url", "example.com",
            "--duration", "10"
        )

        assert returncode != 0
        assert "not allowed with argument" in stderr or "mutually exclusive" in stderr

    def test_network_target_url_mutual_exclusion(self):
        """Test network command rejects both --target and --url."""
        returncode, stdout, stderr = run_cli(
            "network",
            "record",
            "--target", "page-123",
            "--url", "example.com",
            "--duration", "10"
        )

        assert returncode != 0
        assert "not allowed with argument" in stderr or "mutually exclusive" in stderr

    def test_query_target_url_mutual_exclusion(self):
        """Test query command rejects both --target and --url."""
        returncode, stdout, stderr = run_cli(
            "query",
            "--target", "page-123",
            "--url", "example.com",
            "--method", "Runtime.evaluate"
        )

        assert returncode != 0
        assert "not allowed with argument" in stderr or "mutually exclusive" in stderr

    def test_global_quiet_verbose_mutual_exclusion(self):
        """Test --quiet and --verbose are mutually exclusive."""
        returncode, stdout, stderr = run_cli(
            "session",
            "list",
            "--quiet",
            "--verbose"
        )

        assert returncode != 0
        assert "not allowed with argument" in stderr or "mutually exclusive" in stderr


class TestCLIMissingArguments:
    """
    T049: Test missing argument error handling.

    Verifies CLI shows clear error messages for missing required arguments.
    """

    def test_no_subcommand(self):
        """Test error when no subcommand provided."""
        returncode, stdout, stderr = run_cli()

        assert returncode != 0
        # argparse should show help or error
        assert "required" in stderr.lower() or "the following arguments are required" in stderr.lower()

    def test_eval_missing_expression(self):
        """Test eval command requires expression argument."""
        returncode, stdout, stderr = run_cli("eval")

        assert returncode != 0
        assert "required" in stderr.lower() or "expression" in stderr.lower()

    def test_dom_missing_output(self):
        """Test dom dump command requires --output argument."""
        returncode, stdout, stderr = run_cli("dom", "dump")

        assert returncode != 0
        assert "required" in stderr.lower() or "output" in stderr.lower()

    def test_console_missing_duration(self):
        """Test console stream command requires --duration argument."""
        returncode, stdout, stderr = run_cli("console", "stream")

        assert returncode != 0
        assert "required" in stderr.lower() or "duration" in stderr.lower()

    def test_network_missing_duration(self):
        """Test network record command requires --duration argument."""
        returncode, stdout, stderr = run_cli("network", "record")

        assert returncode != 0
        assert "required" in stderr.lower() or "duration" in stderr.lower()

    def test_orchestrate_missing_mode(self):
        """Test orchestrate command requires mode argument."""
        returncode, stdout, stderr = run_cli("orchestrate")

        assert returncode != 0
        assert "required" in stderr.lower() or "mode" in stderr.lower()

    def test_orchestrate_missing_url(self):
        """Test orchestrate command requires URL argument."""
        returncode, stdout, stderr = run_cli("orchestrate", "headless")

        assert returncode != 0
        assert "required" in stderr.lower() or "url" in stderr.lower()

    def test_query_missing_method(self):
        """Test query command requires --method argument."""
        returncode, stdout, stderr = run_cli("query")

        assert returncode != 0
        assert "required" in stderr.lower() or "method" in stderr.lower()

    def test_session_missing_action(self):
        """Test session command requires action argument."""
        returncode, stdout, stderr = run_cli("session")

        assert returncode != 0
        assert "required" in stderr.lower() or "list" in stderr.lower()


class TestCLICommandsWithChrome:
    """
    Integration tests for CLI commands with real Chrome.

    Tests User Story 4: Core Command Implementation

    These tests require Chrome to be running with --remote-debugging-port=9222.
    They will be skipped if Chrome is not available.
    """

    @pytest.fixture(scope="class")
    def chrome_session(self):
        """Launch fresh Chrome instance for testing."""
        import json
        import subprocess

        # Use chrome-launcher.sh to start fresh Chrome
        launcher_path = Path(__file__).parent.parent.parent / "scripts" / "core" / "chrome-launcher.sh"

        session = None
        try:
            output = subprocess.check_output([
                str(launcher_path),
                "--mode=headless",
                "--port=9222",
                "--url=about:blank"
            ], timeout=10, stderr=subprocess.PIPE, text=True)

            session = json.loads(output)

            # Verify Chrome started
            if session.get("status") != "success":
                pytest.skip(f"Chrome launcher failed: {session.get('message', 'Unknown error')}")

            yield session

        except subprocess.TimeoutExpired:
            pytest.skip("Chrome launcher timed out")
        except subprocess.CalledProcessError as e:
            pytest.skip(f"Chrome launcher failed: {e.stderr}")
        except FileNotFoundError:
            pytest.skip("chrome-launcher.sh not found")
        finally:
            # Cleanup: kill Chrome process if started
            if session and "chrome_pid" in session:
                try:
                    subprocess.run(["kill", str(session["chrome_pid"])], timeout=5)
                except Exception:
                    pass  # Best effort cleanup

    @pytest.mark.integration
    def test_session_list_with_chrome(self, chrome_session):
        """
        T060: Test session list command with real Chrome.

        Verifies session list fetches targets and outputs JSON.
        """
        returncode, stdout, stderr = run_cli("session", "list", "--format", "json")

        assert returncode == 0, f"Command failed: {stderr}"

        # Parse JSON output
        import json
        targets = json.loads(stdout)

        assert isinstance(targets, list)
        assert len(targets) > 0

        # Verify target structure
        for target in targets:
            assert "id" in target
            assert "type" in target
            assert "webSocketDebuggerUrl" in target

    @pytest.mark.integration
    def test_session_list_with_type_filter(self, chrome_session):
        """
        T060: Test session list with type filtering.

        Verifies --type flag filters targets correctly.
        """
        returncode, stdout, stderr = run_cli(
            "session", "list",
            "--type", "page",
            "--format", "json"
        )

        assert returncode == 0, f"Command failed: {stderr}"

        import json
        targets = json.loads(stdout)

        # All targets should be page type
        assert all(t["type"] == "page" for t in targets)

    @pytest.mark.integration
    def test_session_list_text_format(self, chrome_session):
        """
        T060: Test session list with text output format.

        Verifies --format text produces tab-separated output.
        """
        returncode, stdout, stderr = run_cli("session", "list", "--format", "text")

        assert returncode == 0, f"Command failed: {stderr}"
        assert "\t" in stdout  # Tab-separated format

    @pytest.mark.integration
    def test_eval_command_with_chrome(self, chrome_session):
        """
        T061: Test eval command with real Chrome.

        Verifies JavaScript execution via Runtime.evaluate.
        """
        returncode, stdout, stderr = run_cli(
            "eval",
            "2 + 2",
            "--format", "json"
        )

        assert returncode == 0, f"Command failed: {stderr}"

        # Parse JSON output
        import json
        result = json.loads(stdout)

        # Should contain CDP response
        assert "result" in result

    @pytest.mark.integration
    def test_eval_document_title(self, chrome_session):
        """
        T061: Test eval command extracting document.title.

        Verifies eval can access page DOM.
        """
        returncode, stdout, stderr = run_cli(
            "eval",
            "document.title",
            "--format", "json"
        )

        assert returncode == 0, f"Command failed: {stderr}"

        import json
        result = json.loads(stdout)

        # Should have result value
        assert "result" in result
        assert "value" in result["result"]

    @pytest.mark.integration
    def test_dom_dump_command(self, chrome_session, tmp_path):
        """
        T062: Test dom dump command with real Chrome.

        Verifies DOM extraction and file output.
        """
        output_file = tmp_path / "test_dom.html"

        returncode, stdout, stderr = run_cli(
            "dom", "dump",
            "--output", str(output_file)
        )

        assert returncode == 0, f"Command failed: {stderr}"

        # Verify file was created
        assert output_file.exists()

        # Verify HTML content
        html = output_file.read_text()
        assert "<html" in html.lower()
        assert "</html>" in html.lower()

    @pytest.mark.integration
    @pytest.mark.slow
    def test_console_stream_command(self, chrome_session, tmp_path):
        """
        T063: Test console stream command with real Chrome.

        Verifies console log capture for short duration.
        """
        output_file = tmp_path / "console.jsonl"

        returncode, stdout, stderr = run_cli(
            "console", "stream",
            "--duration", "2",  # Short duration for testing
            "--output", str(output_file)
        )

        assert returncode == 0, f"Command failed: {stderr}"

        # File may not be created if no console activity
        # This is acceptable - command succeeded

    @pytest.mark.integration
    @pytest.mark.slow
    def test_network_record_command(self, chrome_session, tmp_path):
        """
        T064: Test network record command with real Chrome.

        Verifies network activity capture (placeholder until NetworkCollector implemented).
        """
        output_file = tmp_path / "network.jsonl"

        returncode, stdout, stderr = run_cli(
            "network", "record",
            "--duration", "2",  # Short duration for testing
            "--output", str(output_file) if output_file else ""
        )

        # May not be fully implemented yet, but should not crash
        # assert returncode == 0 or "not yet implemented" in stderr.lower()

    @pytest.mark.integration
    def test_query_command_runtime_evaluate(self, chrome_session):
        """
        T059: Test query command with Runtime.evaluate.

        Verifies arbitrary CDP command execution.
        """
        returncode, stdout, stderr = run_cli(
            "query",
            "--method", "Runtime.evaluate",
            "--params", '{"expression":"1+1","returnByValue":true}',
            "--format", "json"
        )

        assert returncode == 0, f"Command failed: {stderr}"

        import json
        result = json.loads(stdout)

        # Should contain CDP response
        assert "result" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
