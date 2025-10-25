"""
Output comparison for migration safety testing (T069).

Compares outputs from Bash and Python implementations to detect behavioral differences.
Supports DOM HTML comparison, console log comparison, and network trace comparison.
"""

import hashlib
import difflib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .normalize_html import normalize_html


@dataclass
class ComparisonResult:
    """Base class for comparison results."""
    category: str
    passed: bool
    divergence_percent: float
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "INFO"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "category": self.category,
            "passed": self.passed,
            "divergence_percent": self.divergence_percent,
            "details": self.details,
            "severity": self.severity
        }


@dataclass
class DOMComparisonResult(ComparisonResult):
    """Result of DOM HTML comparison."""
    diff_details: List[str] = field(default_factory=list)
    category: str = field(default="dom", init=False)


@dataclass
class ConsoleComparisonResult(ComparisonResult):
    """Result of console log comparison."""
    missing_in_bash: List[Dict] = field(default_factory=list)
    missing_in_python: List[Dict] = field(default_factory=list)
    matched: bool = True
    category: str = field(default="console", init=False)

    def __post_init__(self):
        """Initialize passed status based on matched."""
        self.passed = self.matched


@dataclass
class NetworkComparisonResult(ComparisonResult):
    """Result of network trace comparison."""
    missing_requests: List[Dict] = field(default_factory=list)
    matched: bool = True
    timing_divergence_percent: float = 0.0
    category: str = field(default="network", init=False)

    def __post_init__(self):
        """Initialize passed status based on matched."""
        self.passed = self.matched


def compare_dom_html(
    html1: str,
    html2: str,
    threshold_percent: float = 5.0
) -> DOMComparisonResult:
    """
    Compare two DOM HTML outputs for semantic equivalence.

    Args:
        html1: First HTML string (Bash implementation output)
        html2: Second HTML string (Python implementation output)
        threshold_percent: Maximum allowed divergence percentage (default: 5%)

    Returns:
        DOMComparisonResult with divergence metrics and diff details
    """
    # Normalize both HTML strings
    normalized1 = normalize_html(html1)
    normalized2 = normalize_html(html2)

    # Calculate divergence using hash and diff
    if normalized1 == normalized2:
        return DOMComparisonResult(
            passed=True,
            divergence_percent=0.0,
            diff_details=[],
            severity="INFO"
        )

    # Calculate divergence percentage using character-level diff
    total_chars = max(len(normalized1), len(normalized2))
    if total_chars == 0:
        divergence = 0.0
    else:
        # Use difflib to calculate similarity
        matcher = difflib.SequenceMatcher(None, normalized1, normalized2)
        similarity_ratio = matcher.ratio()
        divergence = (1.0 - similarity_ratio) * 100.0

    # Generate diff details
    diff_lines = list(difflib.unified_diff(
        normalized1.splitlines(keepends=True),
        normalized2.splitlines(keepends=True),
        fromfile="bash",
        tofile="python",
        lineterm=""
    ))

    # Determine severity and pass/fail
    passed = divergence <= threshold_percent
    severity = "INFO" if passed else "HARD_FAIL"

    return DOMComparisonResult(
        passed=passed,
        divergence_percent=round(divergence, 2),
        diff_details=diff_lines[:50],  # Limit to first 50 lines
        details={"threshold": threshold_percent, "similarity_ratio": similarity_ratio},
        severity=severity
    )


def compare_console_logs(
    logs1: List[Dict[str, Any]],
    logs2: List[Dict[str, Any]],
    ignore_timestamps: bool = True,
    order_matters: bool = False
) -> ConsoleComparisonResult:
    """
    Compare console log outputs.

    Args:
        logs1: Console logs from first implementation
        logs2: Console logs from second implementation
        ignore_timestamps: Whether to ignore timestamp differences
        order_matters: Whether log order must match

    Returns:
        ConsoleComparisonResult with matched status and missing logs
    """
    # Normalize logs for comparison
    def normalize_log(log: Dict[str, Any]) -> str:
        """Normalize a single log entry for comparison."""
        key_parts = [
            log.get("level", ""),
            log.get("text", "")
        ]
        if not ignore_timestamps:
            key_parts.append(str(log.get("timestamp", "")))
        return "|".join(key_parts)

    # Create sets for comparison
    logs1_normalized = [normalize_log(log) for log in logs1]
    logs2_normalized = [normalize_log(log) for log in logs2]

    if order_matters:
        # Exact sequence match
        matched = logs1_normalized == logs2_normalized
        missing_in_python = []
        missing_in_bash = []

        # Find differences
        if not matched:
            for i, (log1, log2) in enumerate(zip(logs1_normalized, logs2_normalized)):
                if log1 != log2:
                    if i < len(logs1):
                        missing_in_python.append(logs1[i])
                    if i < len(logs2):
                        missing_in_bash.append(logs2[i])
    else:
        # Set-based comparison (order independent)
        set1 = set(logs1_normalized)
        set2 = set(logs2_normalized)

        missing_in_python_set = set1 - set2
        missing_in_bash_set = set2 - set1

        matched = len(missing_in_python_set) == 0 and len(missing_in_bash_set) == 0

        # Convert back to original log format
        missing_in_python = [logs1[i] for i, norm in enumerate(logs1_normalized) if norm in missing_in_python_set]
        missing_in_bash = [logs2[i] for i, norm in enumerate(logs2_normalized) if norm in missing_in_bash_set]

    divergence_percent = 0.0
    if not matched and max(len(logs1), len(logs2)) > 0:
        total = max(len(logs1), len(logs2))
        different = len(missing_in_python) + len(missing_in_bash)
        divergence_percent = (different / total) * 100.0

    return ConsoleComparisonResult(
        matched=matched,
        passed=matched,
        divergence_percent=round(divergence_percent, 2),
        missing_in_bash=missing_in_bash,
        missing_in_python=missing_in_python,
        details={
            "total_logs_bash": len(logs1),
            "total_logs_python": len(logs2),
            "order_matters": order_matters
        }
    )


def compare_network_traces(
    trace1: List[Dict[str, Any]],
    trace2: List[Dict[str, Any]],
    ignore_timing: bool = True,
    order_matters: bool = False,
    timing_threshold_percent: float = 50.0
) -> NetworkComparisonResult:
    """
    Compare network trace outputs.

    Args:
        trace1: Network trace from first implementation
        trace2: Network trace from second implementation
        ignore_timing: Whether to ignore timing differences
        order_matters: Whether request order must match
        timing_threshold_percent: Threshold for timing divergence warnings

    Returns:
        NetworkComparisonResult with matched status and missing requests
    """
    # Normalize requests for comparison
    def normalize_request(req: Dict[str, Any]) -> str:
        """Normalize a single network request for comparison."""
        key_parts = [
            req.get("url", ""),
            req.get("method", "GET"),
            str(req.get("status", ""))
        ]
        return "|".join(key_parts)

    # Create normalized lists
    trace1_normalized = [normalize_request(req) for req in trace1]
    trace2_normalized = [normalize_request(req) for req in trace2]

    if order_matters:
        # Exact sequence match
        matched = trace1_normalized == trace2_normalized
        missing_requests = []

        if not matched:
            # Find requests in trace1 but not in trace2 at the same position
            for req1, req2, orig_req in zip(trace1_normalized, trace2_normalized, trace1):
                if req1 != req2:
                    missing_requests.append(orig_req)
    else:
        # Set-based comparison
        set1 = set(trace1_normalized)
        set2 = set(trace2_normalized)

        missing_set = set1.symmetric_difference(set2)
        matched = len(missing_set) == 0

        # Convert back to original format
        missing_requests = [
            trace1[i] for i, norm in enumerate(trace1_normalized) if norm in missing_set
        ] + [
            trace2[i] for i, norm in enumerate(trace2_normalized) if norm in missing_set
        ]

    # Calculate timing divergence (always calculate, but only warn/fail based on ignore_timing)
    timing_divergence_percent = 0.0
    severity = "INFO"

    if len(trace1) > 0 and len(trace2) > 0:
        # Compare timing for matched requests
        timings1 = [req.get("duration_ms", 0) for req in trace1]
        timings2 = [req.get("duration_ms", 0) for req in trace2]

        if timings1 and timings2:
            avg_timing1 = sum(timings1) / len(timings1)
            avg_timing2 = sum(timings2) / len(timings2)

            if avg_timing1 > 0:
                timing_divergence_percent = abs(avg_timing2 - avg_timing1) / avg_timing1 * 100.0

        # Timing divergence is a soft warning, not a hard fail (only if not ignoring)
        if not ignore_timing and timing_divergence_percent > timing_threshold_percent:
            severity = "SOFT_WARN"

    divergence_percent = 0.0
    if not matched and max(len(trace1), len(trace2)) > 0:
        total = max(len(trace1), len(trace2))
        divergence_percent = (len(missing_requests) / total) * 100.0

    return NetworkComparisonResult(
        matched=matched,
        passed=matched,
        divergence_percent=round(divergence_percent, 2),
        missing_requests=missing_requests,
        timing_divergence_percent=round(timing_divergence_percent, 2),
        details={
            "total_requests_bash": len(trace1),
            "total_requests_python": len(trace2),
            "timing_threshold": timing_threshold_percent
        },
        severity=severity
    )


def detect_rollback_criteria(results: List[ComparisonResult]) -> Dict[str, Any]:
    """
    Detect if rollback criteria are met based on comparison results.

    Criteria (per T072):
    - 2+ regressions (failed comparisons)
    - 1+ critical bugs

    Args:
        results: List of comparison results

    Returns:
        Dictionary with rollback recommendation and reason
    """
    failed_count = sum(1 for r in results if not r.passed)
    critical_count = sum(1 for r in results if r.details.get("severity") == "CRITICAL" or r.severity == "CRITICAL")

    rollback_recommended = False
    reason = ""

    if critical_count >= 1:
        rollback_recommended = True
        reason = f"CRITICAL bug detected ({critical_count} critical issue(s))"
    elif failed_count >= 2:
        rollback_recommended = True
        reason = "2+ regressions detected"

    return {
        "rollback_recommended": rollback_recommended,
        "reason": reason,
        "failed_count": failed_count,
        "critical_count": critical_count,
        "total_comparisons": len(results)
    }


if __name__ == "__main__":
    # CLI interface for testing
    import sys
    import json

    if len(sys.argv) < 4:
        print("Usage: python3 compare_outputs.py <type> <file1> <file2>")
        print("Types: dom, console, network")
        sys.exit(1)

    comparison_type = sys.argv[1]
    file1 = sys.argv[2]
    file2 = sys.argv[3]

    with open(file1, 'r') as f:
        content1 = f.read()

    with open(file2, 'r') as f:
        content2 = f.read()

    if comparison_type == "dom":
        result = compare_dom_html(content1, content2)
    elif comparison_type == "console":
        logs1 = json.loads(content1) if content1.strip().startswith('[') else []
        logs2 = json.loads(content2) if content2.strip().startswith('[') else []
        result = compare_console_logs(logs1, logs2)
    elif comparison_type == "network":
        trace1 = json.loads(content1) if content1.strip().startswith('[') else []
        trace2 = json.loads(content2) if content2.strip().startswith('[') else []
        result = compare_network_traces(trace1, trace2)
    else:
        print(f"Unknown comparison type: {comparison_type}")
        sys.exit(1)

    print(json.dumps(result.to_dict(), indent=2))
    sys.exit(0 if result.passed else 1)
