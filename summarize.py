#!/usr/bin/env python3
"""Aggregate network and console logs into text or JSON summaries."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def load_network_events(path: Path) -> Dict[str, Any]:
    events: List[Dict[str, Any]] = []
    requests: List[Dict[str, Any]] = []
    responses: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    request_by_id: Dict[str, Dict[str, Any]] = {}
    methods = Counter()
    status_codes = Counter()
    hosts = Counter()

    if not path.exists():
        return {
            "events": events,
            "requests": requests,
            "responses": responses,
            "failures": failures,
            "request_by_id": request_by_id,
            "methods": methods,
            "status_codes": status_codes,
            "hosts": hosts,
        }

    for raw_line in path.read_text().splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        events.append(data)
        event_type = data.get("event")

        if event_type == "request":
            requests.append(data)
            request_by_id[data.get("requestId")] = data
            method = data.get("method") or "UNKNOWN"
            methods[method] += 1
            url = data.get("url")
            if url:
                host = urlparse(url).netloc
                if host:
                    hosts[host] += 1

        elif event_type == "response":
            responses.append(data)
            status = str(data.get("status"))
            status_codes[status] += 1
            url = data.get("url")
            if url:
                host = urlparse(url).netloc
                if host:
                    hosts[host] += 1

        elif event_type == "failed":
            failures.append(data)

    return {
        "events": events,
        "requests": requests,
        "responses": responses,
        "failures": failures,
        "request_by_id": request_by_id,
        "methods": methods,
        "status_codes": status_codes,
        "hosts": hosts,
    }


def load_console_events(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"entry_count": 0, "levels": {}, "sample_errors": []}

    level_counts = Counter()
    sample_errors: List[Dict[str, Any]] = []

    for raw_line in path.read_text().splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError:
            continue

        level = (entry.get("type") or "").lower()
        if not level:
            continue

        level_counts[level] += 1

        if level in {"error", "exception"} and len(sample_errors) < 5:
            sample_errors.append(
                {
                    "message": entry.get("message"),
                    "url": entry.get("url"),
                    "lineNumber": entry.get("lineNumber"),
                }
            )

    return {
        "entry_count": sum(level_counts.values()),
        "levels": dict(level_counts),
        "sample_errors": sample_errors,
    }


def build_summary(
    network_path: Path,
    console_path: Optional[Path],
    duration: float,
    filter_value: Optional[str],
) -> Dict[str, Any]:
    network_data = load_network_events(network_path)
    console_report = (
        load_console_events(console_path)
        if console_path is not None
        else {"entry_count": 0, "levels": {}, "sample_errors": []}
    )

    report: Dict[str, Any] = {
        "meta": {
            "log_path": str(network_path),
            "console_log": str(console_path) if console_path else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration,
            "filter": filter_value or None,
            "total_events": len(network_data["events"]),
            "unique_hosts": len(network_data["hosts"]),
        },
        "network": {
            "request_count": len(network_data["requests"]),
            "response_count": len(network_data["responses"]),
            "failure_count": len(network_data["failures"]),
            "methods": dict(network_data["methods"]),
            "status_codes": dict(network_data["status_codes"]),
            "top_requests": [],
            "failures": [],
        },
    }

    seen_urls = set()
    for request in network_data["requests"]:
        url = request.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        report["network"]["top_requests"].append(
            {"method": request.get("method"), "url": url}
        )
        if len(report["network"]["top_requests"]) == 10:
            break

    for failure in network_data["failures"][:10]:
        request = network_data["request_by_id"].get(failure.get("requestId"), {})
        report["network"]["failures"].append(
            {
                "error": failure.get("errorText"),
                "url": request.get("url"),
                "method": request.get("method"),
                "requestId": failure.get("requestId"),
            }
        )

    report["console"] = console_report
    return report


def print_text(summary: Dict[str, Any], include_console: bool) -> None:
    network = summary["network"]
    print(f"   Total Requests:  {network['request_count']}")
    print(f"   Total Responses: {network['response_count']}")
    print(f"   Failed Requests: {network['failure_count']}")
    print("")

    if network["top_requests"]:
        print("📥 Top 10 Requests:")
        for item in network["top_requests"]:
            method = item.get("method", "UNKNOWN")
            url = item.get("url", "-")
            print(f"   {method} {url}")
        print("")

    if network["status_codes"]:
        print("📤 Response Status Codes:")
        for status, count in sorted(network["status_codes"].items()):
            print(f"      {count} {status}")
        print("")

    if network["failures"]:
        print("❌ Failed Requests:")
        for failure in network["failures"]:
            error = failure.get("error") or "Unknown error"
            url = failure.get("url")
            if url:
                print(f"   {error} [{url}]")
            else:
                print(f"   {error}")
        print("")

    if include_console:
        console = summary["console"]
        print("🖥️ Console Summary:")
        print(f"   Entries: {console['entry_count']}")
        if console["levels"]:
            print("   Levels:")
            for level, count in sorted(console["levels"].items()):
                print(f"      {level}: {count}")
        if console["sample_errors"]:
            print("   Sample Errors:")
            for error in console["sample_errors"]:
                message = error.get("message") or "(no message)"
                location = ""
                if error.get("url"):
                    location = f" [{error['url']}"
                    if error.get("lineNumber") is not None:
                        location += f":{error['lineNumber']}"
                    location += "]"
                print(f"      {message}{location}")
        print("")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", required=True, help="Path to network log file")
    parser.add_argument("--console", help="Optional console log path")
    parser.add_argument("--duration", type=float, required=True, help="Capture duration")
    parser.add_argument("--filter", help="Filter used during capture")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        required=True,
        help="Output format",
    )
    parser.add_argument(
        "--include-console",
        action="store_true",
        help="Include console metrics in the summary",
    )

    args = parser.parse_args()

    network_path = Path(args.network)
    console_path = Path(args.console) if args.console else None

    summary = build_summary(network_path, console_path, args.duration, args.filter)

    if args.format == "json":
        payload: Dict[str, Any] = {
            "meta": summary["meta"],
            "network": summary["network"],
        }
        if args.include_console:
            payload["console"] = summary["console"]
        print(json.dumps(payload, indent=2))
    else:
        print_text(summary, args.include_console)


if __name__ == "__main__":
    main()
