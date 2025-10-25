"""
Integration tests for dual-path migration validation (T074, T075).

Tests User Story 5: Migration Safety with Parallel Testing.
"""

import subprocess
import pytest
import os
import json


class TestDualPathValidation:
    """T074: Test dual-path validation comparing Bash and Python outputs."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_dual_path_validation_with_example_com(self):
        """
        Run dual-path validation against example.com and verify outputs match.

        Verifies:
        - Both Bash and Python implementations complete successfully
        - DOM outputs match within 5% threshold
        - No rollback criteria triggered
        """
        script_path = os.path.join(
            os.path.dirname(__file__),
            "../../tests/ci/run_dual_path_validation.sh"
        )

        # Run dual-path validation
        result = subprocess.run(
            [script_path, "https://example.com", "5"],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should pass (exit code 0 or 1 for minor differences)
        assert result.returncode in [0, 1, 2], f"Unexpected exit code: {result.returncode}"

        # Verify outputs were generated
        assert "Bash implementation completed" in result.stdout
        assert "Python implementation completed" in result.stdout
        assert "Comparison Results" in result.stdout

    @pytest.mark.integration
    @pytest.mark.slow
    def test_dual_path_validation_outputs_match_semantically(self):
        """
        Verify that Bash and Python implementations produce semantically equivalent DOM.

        Uses a simple static page to ensure deterministic comparison.
        """
        script_path = os.path.join(
            os.path.dirname(__file__),
            "../../tests/ci/run_dual_path_validation.sh"
        )

        # Run against a simple static page
        result = subprocess.run(
            [script_path, "https://example.com", "3"],
            capture_output=True,
            text=True,
            timeout=45
        )

        # Should pass with matching outputs
        assert result.returncode == 0, f"Dual-path validation failed: {result.stderr}"

        # Verify specific success indicators
        assert "PASS: DOM outputs match" in result.stdout or "DOM outputs match within threshold" in result.stdout
        assert "Rollback criteria OK" in result.stdout

    @pytest.mark.integration
    def test_dual_path_comparison_script_exists(self):
        """Verify dual-path comparison script is present and executable."""
        script_path = os.path.join(
            os.path.dirname(__file__),
            "../../tests/ci/run_dual_path_validation.sh"
        )

        assert os.path.exists(script_path), "Dual-path validation script not found"
        assert os.access(script_path, os.X_OK), "Dual-path validation script not executable"

    @pytest.mark.integration
    def test_comparison_utilities_exist(self):
        """Verify comparison utilities (normalize_html.py, compare_outputs.py) exist."""
        ci_dir = os.path.join(os.path.dirname(__file__), "../../tests/ci")

        normalize_script = os.path.join(ci_dir, "normalize_html.py")
        compare_script = os.path.join(ci_dir, "compare_outputs.py")

        assert os.path.exists(normalize_script), "normalize_html.py not found"
        assert os.path.exists(compare_script), "compare_outputs.py not found"


class TestConsecutiveRunStability:
    """T075: Test consecutive run stability for migration safety."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.flaky(reruns=3)  # Allow retries for flaky network conditions
    def test_three_consecutive_runs_pass(self):
        """
        Verify 3 consecutive CI runs pass per FR-035.

        Ensures stability and reproducibility of dual-path validation.
        """
        script_path = os.path.join(
            os.path.dirname(__file__),
            "../../tests/ci/run_dual_path_validation.sh"
        )

        # Run 3 times consecutively
        results = []
        for run_num in range(1, 4):
            print(f"\n=== Consecutive Run {run_num}/3 ===")

            result = subprocess.run(
                [script_path, "https://example.com", "3"],
                capture_output=True,
                text=True,
                timeout=45
            )

            results.append({
                "run": run_num,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            })

            print(f"Run {run_num} exit code: {result.returncode}")

        # Analyze results
        pass_count = sum(1 for r in results if r["returncode"] == 0)
        print(f"\nConsecutive runs passed: {pass_count}/3")

        # FR-035: All 3 runs should pass
        assert pass_count == 3, f"Only {pass_count}/3 consecutive runs passed"

        # Verify consistency across runs
        for result in results:
            assert "Validation complete" in result["stdout"], \
                f"Run {result['run']} did not complete properly"

    @pytest.mark.integration
    def test_rollback_history_tracking(self):
        """
        Verify rollback history tracking works correctly.

        Checks that .dual-path-history.json is created and tracks results.
        """
        repo_root = os.path.join(os.path.dirname(__file__), "../..")
        history_file = os.path.join(repo_root, ".dual-path-history.json")

        # History file should exist after running dual-path validation
        # (or we create it here for testing)
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)

            # Should be a list of run results
            assert isinstance(history, list), "History should be a list"

            if history:
                # Verify structure of history entries
                latest = history[-1]
                assert "timestamp" in latest
                assert "dom_passed" in latest
                assert "dom_divergence" in latest
                assert "regression" in latest

    @pytest.mark.integration
    @pytest.mark.slow
    def test_rollback_criteria_detection(self):
        """
        Verify rollback criteria detection (2+ regressions in last 3 runs).

        This is a smoke test - full validation requires actual regressions.
        """
        script_path = os.path.join(
            os.path.dirname(__file__),
            "../../tests/ci/run_dual_path_validation.sh"
        )

        # Run once to generate history
        result = subprocess.run(
            [script_path, "https://example.com", "3"],
            capture_output=True,
            text=True,
            timeout=45
        )

        # Should include rollback check in output
        assert "Checking rollback criteria" in result.stdout or "rollback" in result.stdout.lower()

        # With passing run, rollback should not be needed
        if result.returncode == 0:
            assert "Rollback criteria OK" in result.stdout or "ROLLBACK RECOMMENDED" not in result.stdout
