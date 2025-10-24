"""
Integration tests for CLI interface.

Tests User Story 3: Unified CLI Interface - Help Text, Argument Validation
"""

import subprocess
import sys
import pytest


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
