"""
Orchestrate subcommand for automated debugging workflows.

Implements 'orchestrate' command to run full headless/headed debugging sessions.
"""

import argparse
import asyncio
import sys
import os
import subprocess
import json
import time
from pathlib import Path
from datetime import datetime

from ..session import CDPSession
from ..collectors.console import ConsoleCollector
from ..exceptions import CDPError, CDPTargetNotFoundError


async def orchestrate_handler_async(args: argparse.Namespace) -> int:
    """
    Handle 'orchestrate' command (async implementation).

    Runs full debugging workflow (launch Chrome, capture data, extract DOM, generate summary).

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    chrome_pid = None
    artifacts = {}

    try:
        # Setup output directory
        output_dir = Path(args.output_dir) if args.output_dir else Path("/tmp")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Timestamp for unique filenames
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        session_id = f"{timestamp}-{os.getpid()}"

        if not args.quiet:
            print(
                f"Orchestrating {args.mode} session for URL: {args.url}",
                file=sys.stderr,
            )

        # Launch Chrome via chrome-launcher.sh
        launcher_path = (
            Path(__file__).parent.parent.parent.parent
            / "scripts"
            / "core"
            / "chrome-launcher.sh"
        )

        if not launcher_path.exists():
            raise CDPError(
                f"chrome-launcher.sh not found at {launcher_path}",
                {"recovery": "Ensure chrome-launcher.sh exists in scripts/core/"},
            )

        launcher_result = subprocess.run(
            [
                str(launcher_path),
                f"--mode={args.mode}",
                "--port=9222",
                f"--url={args.url}",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if launcher_result.returncode != 0:
            # launcher writes debug to stderr, JSON to stdout
            # Parse JSON from stdout to get error details
            try:
                error_data = json.loads(launcher_result.stdout)
                raise CDPError(
                    error_data.get("message", "Chrome launcher failed"),
                    {
                        "recovery": error_data.get(
                            "recovery", "Check chrome-launcher.sh output"
                        )
                    },
                )
            except json.JSONDecodeError:
                raise CDPError(
                    f"Chrome launcher failed: {launcher_result.stderr}",
                    {"recovery": "Check chrome-launcher.sh output for details"},
                )

        # Parse JSON from stdout (last line contains the JSON)
        session_data = json.loads(launcher_result.stdout.strip().split("\n")[-1])
        if session_data.get("status") != "success":
            raise CDPError(
                f"Chrome launch failed: {session_data.get('message')}",
                {"recovery": session_data.get("recovery", "Unknown")},
            )

        chrome_pid = session_data["pid"]
        ws_url = session_data["ws_url"]

        if not args.quiet:
            print(f"Chrome launched (PID: {chrome_pid})", file=sys.stderr)

        # Connect to Chrome
        cdp_session = CDPSession(chrome_host="localhost", chrome_port=9222)
        conn = await cdp_session.connect_to_first_page()

        async with conn:
            # Start console collector if requested
            console_collector = None
            if args.include_console:
                console_path = output_dir / f"console-{session_id}.jsonl"
                console_collector = ConsoleCollector(
                    connection=conn, output_path=console_path
                )
                await console_collector.start()
                if not args.quiet:
                    print(f"Console monitoring started", file=sys.stderr)

            # Wait for duration
            if not args.quiet:
                print(f"Capturing for {args.duration} seconds...", file=sys.stderr)

            await asyncio.sleep(args.duration)

            # Stop console collector
            if console_collector:
                await console_collector.stop()
                if (
                    console_collector.output_path
                    and console_collector.output_path.exists()
                ):
                    artifacts["console"] = str(console_collector.output_path)

            # Extract DOM
            dom_path = output_dir / f"dom-{session_id}.html"
            dom_result = await conn.execute_command(
                "Runtime.evaluate",
                {
                    "expression": "document.documentElement.outerHTML",
                    "returnByValue": True,
                },
            )

            if dom_result.get("result", {}).get("value"):
                dom_path.write_text(dom_result["result"]["value"])
                artifacts["dom"] = str(dom_path)
                if not args.quiet:
                    print(f"DOM extracted to: {dom_path}", file=sys.stderr)

        # Generate summary
        summary_data = {
            "url": args.url,
            "mode": args.mode,
            "duration": args.duration,
            "timestamp": timestamp,
            "artifacts": artifacts,
        }

        if args.summary in ["json", "both"]:
            json_path = output_dir / f"summary-{session_id}.json"
            json_path.write_text(json.dumps(summary_data, indent=2))
            if not args.quiet:
                print(f"JSON summary: {json_path}", file=sys.stderr)

        if args.summary in ["text", "both"]:
            text_path = output_dir / f"summary-{session_id}.txt"
            text_lines = [
                f"Debugging Session Summary",
                f"=" * 50,
                f"URL: {args.url}",
                f"Mode: {args.mode}",
                f"Duration: {args.duration}s",
                f"Timestamp: {timestamp}",
                f"",
                f"Artifacts:",
            ]
            for artifact_type, artifact_path in artifacts.items():
                text_lines.append(f"  - {artifact_type}: {artifact_path}")

            text_path.write_text("\n".join(text_lines))
            if not args.quiet:
                print(f"Text summary: {text_path}", file=sys.stderr)

        return 0

    except CDPError as e:
        if hasattr(args, "config") and args.config.log_level.upper() == "DEBUG":
            raise
        print(f"Error: {e}", file=sys.stderr)
        if e.details.get("recovery"):
            print(f"Recovery hint: {e.details['recovery']}", file=sys.stderr)
        return 1

    except Exception as e:
        if hasattr(args, "config") and args.config.log_level.upper() == "DEBUG":
            raise
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1

    finally:
        # Cleanup: kill Chrome if we launched it
        if chrome_pid:
            try:
                subprocess.run(["kill", str(chrome_pid)], timeout=5)
            except Exception:
                pass  # Best effort cleanup


def orchestrate_handler(args: argparse.Namespace) -> int:
    """
    Synchronous wrapper for orchestrate_handler_async.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    return asyncio.run(orchestrate_handler_async(args))


def register_subcommand(
    subparsers: argparse._SubParsersAction, parent: argparse.ArgumentParser
) -> None:
    """
    Register 'orchestrate' subcommand.

    Args:
        subparsers: Subparsers from main parser
        parent: Parent parser with global options
    """
    orchestrate_parser = subparsers.add_parser(
        "orchestrate",
        parents=[parent],
        help="Run automated debugging workflow",
        description="Launch Chrome and run full debugging session with collectors",
        epilog="""
Examples:
  # Headless session
  browser-debugger orchestrate headless https://example.com

  # Headed session (interactive)
  browser-debugger orchestrate headed https://example.com

  # Include console monitoring
  browser-debugger orchestrate headless https://example.com --include-console

  # Custom duration
  browser-debugger orchestrate headless https://example.com --duration 60

  # Text summary
  browser-debugger orchestrate headless https://example.com --summary text

  # JSON + text summaries
  browser-debugger orchestrate headless https://example.com --summary both
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Mode
    orchestrate_parser.add_argument(
        "mode",
        choices=["headless", "headed"],
        help="Chrome mode (headless for automation, headed for interactive debugging)",
    )

    # URL
    orchestrate_parser.add_argument(
        "url",
        help="URL to load in Chrome",
    )

    # Duration
    orchestrate_parser.add_argument(
        "--duration",
        type=int,
        default=15,
        help="Session duration in seconds (default: 15)",
    )

    # Include console
    orchestrate_parser.add_argument(
        "--include-console",
        action="store_true",
        help="Enable console log monitoring",
    )

    # Summary format
    orchestrate_parser.add_argument(
        "--summary",
        choices=["text", "json", "both"],
        default="text",
        help="Summary format (default: text)",
    )

    # Output directory
    orchestrate_parser.add_argument(
        "--output-dir",
        help="Output directory for artifacts (default: /tmp)",
    )

    # Set handler function
    orchestrate_parser.set_defaults(func=orchestrate_handler)
