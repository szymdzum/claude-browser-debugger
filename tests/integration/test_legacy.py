"""Integration tests for legacy Bash orchestrator deprecation (T111, User Story 8).

Tests verify that the deprecated debug-orchestrator.sh displays deprecation warnings
when executed, guiding users to migrate to the Python CDP CLI.
"""

import subprocess
import pytest


@pytest.mark.integration
class TestLegacyOrchestrator:
    """T111: Test deprecation warning for Bash orchestrator."""

    def test_deprecation_warning_displayed(self):
        """Verify Bash orchestrator shows deprecation warning on stderr."""
        # Run the legacy orchestrator with --help to trigger deprecation warning
        # without actually launching Chrome
        result = subprocess.run(
            ["./scripts/legacy/debug-orchestrator.sh", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Check that deprecation warning appears in stderr
        assert "DEPRECATION WARNING" in result.stderr or "deprecated" in result.stderr.lower(), \
            "Deprecation warning should appear in stderr"

        # Check that it mentions the Python CLI alternative
        stderr_combined = result.stderr.lower()
        assert "python" in stderr_combined, \
            "Deprecation warning should mention Python CLI alternative"
        assert "scripts.cdp.cli.main" in stderr_combined or "orchestrate" in stderr_combined, \
            "Deprecation warning should mention orchestrate command"

    def test_deprecation_notice_in_file_header(self):
        """Verify deprecation notice exists in script file header."""
        with open("./scripts/legacy/debug-orchestrator.sh", "r") as f:
            content = f.read()

        # Check for deprecation notice in file header
        assert "DEPRECATION" in content, \
            "Script should have DEPRECATION notice in header"
        assert "python3 -m scripts.cdp.cli.main" in content, \
            "Script should reference Python CLI in deprecation notice"
        assert "bash-to-python-migration.md" in content or "migration" in content.lower(), \
            "Script should reference migration guide"

    def test_migration_examples_provided(self):
        """Verify migration examples are provided in deprecation notice."""
        with open("./scripts/legacy/debug-orchestrator.sh", "r") as f:
            content = f.read()

        # Check that migration examples exist
        assert "Old:" in content and "New:" in content, \
            "Script should provide Old/New migration examples"
        assert "debug-orchestrator.sh" in content, \
            "Migration examples should show old Bash command"
        assert "orchestrate" in content, \
            "Migration examples should show new Python orchestrate command"
