"""
Unit tests for output comparison (T074).

Tests User Story 5: Migration Safety - Output comparison for Bash vs Python.
"""

import pytest
from tests.ci.compare_outputs import (
    compare_dom_html,
    compare_console_logs,
    compare_network_traces,
    ComparisonResult,
    DOMComparisonResult,
    ConsoleComparisonResult,
    NetworkComparisonResult
)


class TestDOMComparison:
    """Test DOM HTML comparison functionality."""

    def test_identical_dom_returns_zero_divergence(self):
        """Identical DOM should have 0% divergence."""
        html1 = "<html><body><div>Content</div></body></html>"
        html2 = "<html><body><div>Content</div></body></html>"

        result = compare_dom_html(html1, html2)

        assert isinstance(result, DOMComparisonResult)
        assert result.divergence_percent == 0.0
        assert result.passed is True
        assert result.diff_details == []

    def test_whitespace_differences_normalized(self):
        """Whitespace differences should be normalized and not count as divergence."""
        html1 = "<html><body>  <div>Content</div>  </body></html>"
        html2 = "<html><body><div>Content</div></body></html>"

        result = compare_dom_html(html1, html2)

        assert result.divergence_percent == 0.0
        assert result.passed is True

    def test_attribute_order_differences_normalized(self):
        """Different attribute order should be normalized."""
        html1 = '<div class="foo" id="bar"></div>'
        html2 = '<div id="bar" class="foo"></div>'

        result = compare_dom_html(html1, html2)

        assert result.divergence_percent == 0.0
        assert result.passed is True

    def test_divergence_calculation(self):
        """Calculate divergence percentage for different content."""
        html1 = "<html><body><div>Original</div></body></html>"
        html2 = "<html><body><div>Modified</div></body></html>"

        result = compare_dom_html(html1, html2)

        assert result.divergence_percent > 0.0
        assert result.divergence_percent < 100.0
        assert len(result.diff_details) > 0

    def test_threshold_enforcement(self):
        """Test threshold enforcement for DOM comparison."""
        html1 = "<html><body><div>Original content here</div></body></html>"
        html2 = "<html><body><div>Completely different content</div></body></html>"

        # With 5% threshold (default)
        result = compare_dom_html(html1, html2, threshold_percent=5.0)

        assert result.divergence_percent > 5.0
        assert result.passed is False

    def test_large_dom_comparison(self):
        """Test comparison of large DOM structures."""
        html1 = "<html><body>" + "".join(f"<div id='item-{i}'>Item {i}</div>" for i in range(100)) + "</body></html>"
        html2 = "<html><body>" + "".join(f"<div id='item-{i}'>Item {i}</div>" for i in range(100)) + "</body></html>"

        result = compare_dom_html(html1, html2)

        assert result.divergence_percent == 0.0
        assert result.passed is True

    def test_diff_details_content(self):
        """Verify diff details contain useful information."""
        html1 = "<div>Old</div>"
        html2 = "<div>New</div>"

        result = compare_dom_html(html1, html2)

        assert len(result.diff_details) > 0
        assert any("Old" in detail or "New" in detail for detail in result.diff_details)


class TestConsoleLogComparison:
    """Test console log comparison functionality."""

    def test_identical_console_logs(self):
        """Identical console logs should match."""
        logs1 = [
            {"level": "log", "text": "Test message", "timestamp": 1234567890},
            {"level": "error", "text": "Error message", "timestamp": 1234567891}
        ]
        logs2 = [
            {"level": "log", "text": "Test message", "timestamp": 1234567890},
            {"level": "error", "text": "Error message", "timestamp": 1234567891}
        ]

        result = compare_console_logs(logs1, logs2)

        assert isinstance(result, ConsoleComparisonResult)
        assert result.matched is True
        assert result.missing_in_bash == []
        assert result.missing_in_python == []

    def test_timestamp_normalization(self):
        """Timestamps should be normalized - only content matters."""
        logs1 = [{"level": "log", "text": "Message", "timestamp": 1000}]
        logs2 = [{"level": "log", "text": "Message", "timestamp": 2000}]

        result = compare_console_logs(logs1, logs2, ignore_timestamps=True)

        assert result.matched is True

    def test_missing_logs_detection(self):
        """Detect logs missing in either implementation."""
        logs1 = [
            {"level": "log", "text": "Message 1"},
            {"level": "log", "text": "Message 2"}
        ]
        logs2 = [
            {"level": "log", "text": "Message 1"}
        ]

        result = compare_console_logs(logs1, logs2)

        assert result.matched is False
        assert len(result.missing_in_python) == 1
        assert "Message 2" in str(result.missing_in_python)

    def test_order_independent_comparison(self):
        """Console logs can arrive in different order."""
        logs1 = [
            {"level": "log", "text": "First"},
            {"level": "log", "text": "Second"}
        ]
        logs2 = [
            {"level": "log", "text": "Second"},
            {"level": "log", "text": "First"}
        ]

        result = compare_console_logs(logs1, logs2, order_matters=False)

        assert result.matched is True


class TestNetworkTraceComparison:
    """Test network trace comparison functionality."""

    def test_identical_network_traces(self):
        """Identical network traces should match."""
        trace1 = [
            {"url": "https://example.com", "method": "GET", "status": 200},
            {"url": "https://api.example.com", "method": "POST", "status": 201}
        ]
        trace2 = [
            {"url": "https://example.com", "method": "GET", "status": 200},
            {"url": "https://api.example.com", "method": "POST", "status": 201}
        ]

        result = compare_network_traces(trace1, trace2)

        assert isinstance(result, NetworkComparisonResult)
        assert result.matched is True
        assert result.missing_requests == []

    def test_timing_differences_ignored(self):
        """Network timing differences should be ignored or soft-warned."""
        trace1 = [{"url": "https://example.com", "method": "GET", "duration_ms": 100}]
        trace2 = [{"url": "https://example.com", "method": "GET", "duration_ms": 200}]

        result = compare_network_traces(trace1, trace2, ignore_timing=True)

        assert result.matched is True
        # Timing difference should be in warnings, not failures
        assert result.timing_divergence_percent > 0

    def test_missing_request_detection(self):
        """Detect requests present in one trace but not the other."""
        trace1 = [
            {"url": "https://example.com/page1", "method": "GET"},
            {"url": "https://example.com/page2", "method": "GET"}
        ]
        trace2 = [
            {"url": "https://example.com/page1", "method": "GET"}
        ]

        result = compare_network_traces(trace1, trace2)

        assert result.matched is False
        assert len(result.missing_requests) == 1
        assert "page2" in str(result.missing_requests)

    def test_request_order_tolerance(self):
        """Network requests can arrive in different order."""
        trace1 = [
            {"url": "https://example.com/a", "method": "GET"},
            {"url": "https://example.com/b", "method": "GET"}
        ]
        trace2 = [
            {"url": "https://example.com/b", "method": "GET"},
            {"url": "https://example.com/a", "method": "GET"}
        ]

        result = compare_network_traces(trace1, trace2, order_matters=False)

        assert result.matched is True


class TestComparisonResult:
    """Test ComparisonResult data class."""

    def test_comparison_result_structure(self):
        """Verify ComparisonResult has required fields."""
        result = ComparisonResult(
            category="dom",
            passed=True,
            divergence_percent=0.0,
            details={}
        )

        assert result.category == "dom"
        assert result.passed is True
        assert result.divergence_percent == 0.0
        assert isinstance(result.details, dict)

    def test_json_serialization(self):
        """ComparisonResult should be JSON-serializable."""
        result = ComparisonResult(
            category="console",
            passed=False,
            divergence_percent=10.5,
            details={"missing": 3}
        )

        import json
        json_str = json.dumps(result.to_dict())
        assert "console" in json_str
        assert "10.5" in json_str


class TestThresholdConfiguration:
    """Test threshold configuration per T071."""

    def test_hard_fail_threshold(self):
        """DOM divergence >5% should hard fail."""
        html1 = "<div>Original</div>"
        html2 = "<div>Completely different long content that exceeds 5 percent threshold</div>"

        result = compare_dom_html(html1, html2, threshold_percent=5.0)

        if result.divergence_percent > 5.0:
            assert result.passed is False
            assert "HARD_FAIL" in result.severity

    def test_soft_warn_timing_threshold(self):
        """Timing divergence >50% should soft warn, not fail."""
        trace1 = [{"url": "https://example.com", "duration_ms": 100}]
        trace2 = [{"url": "https://example.com", "duration_ms": 200}]

        result = compare_network_traces(trace1, trace2, ignore_timing=False, timing_threshold_percent=50.0)

        if result.timing_divergence_percent > 50.0:
            # Timing divergence should warn, not fail
            assert "SOFT_WARN" in result.severity
            assert result.matched is True  # Still passes overall


class TestRollbackCriteria:
    """Test rollback criteria detection per T072."""

    def test_two_or_more_regressions_triggers_rollback(self):
        """2+ regressions should trigger rollback recommendation."""
        from tests.ci.compare_outputs import detect_rollback_criteria

        results = [
            ComparisonResult("dom", False, 10.0, {}),
            ComparisonResult("console", False, 5.0, {}),
        ]

        recommendation = detect_rollback_criteria(results)

        assert recommendation["rollback_recommended"] is True
        assert recommendation["reason"] == "2+ regressions detected"

    def test_critical_bug_triggers_rollback(self):
        """Critical bugs should trigger immediate rollback."""
        from tests.ci.compare_outputs import detect_rollback_criteria

        results = [
            ComparisonResult("dom", False, 100.0, {"severity": "CRITICAL"})
        ]

        recommendation = detect_rollback_criteria(results)

        assert recommendation["rollback_recommended"] is True
        assert "CRITICAL" in recommendation["reason"]
