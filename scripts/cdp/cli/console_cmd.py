"""
Console subcommand for streaming console logs.

Implements 'console stream' command to monitor console messages.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from ..session import CDPSession
from ..collectors.console import ConsoleCollector
from ..exceptions import CDPError, CDPTargetNotFoundError


async def console_stream_handler_async(args: argparse.Namespace) -> int:
    """
    Handle 'console stream' command (async implementation).

    Streams console logs from target for specified duration.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Create CDP session
        session = CDPSession(
            chrome_host=args.chrome_host,
            chrome_port=args.chrome_port,
            timeout=args.timeout,
        )

        # Find target
        if args.target:
            target = session.get_target_by_id(args.target)
            if not target:
                raise CDPTargetNotFoundError(
                    f"Target not found: {args.target}",
                    target_id=args.target,
                )
        elif args.url:
            targets = session.list_targets(target_type="page", url_pattern=args.url)
            if not targets:
                raise CDPTargetNotFoundError(
                    f"No page target matching URL: {args.url}",
                    url_pattern=args.url,
                )
            target = targets[0]
        else:
            conn = await session.connect_to_first_page()
            async with conn:
                # Create console collector
                collector = ConsoleCollector(
                    connection=conn,
                    output_path=Path(args.output) if hasattr(args, "output") and args.output else None,
                    level_filter=args.level if hasattr(args, "level") else None,
                )

                async with collector:
                    await collector.start()

                    # Stream for specified duration
                    if not args.quiet:
                        print(
                            f"Streaming console logs for {args.duration} seconds...",
                            file=sys.stderr,
                        )

                    await asyncio.sleep(args.duration)

                    await collector.stop()

                if not args.quiet and collector.output_path:
                    print(
                        f"Console logs saved to: {collector.output_path}",
                        file=sys.stderr,
                    )

            return 0

        # Connect to target
        conn = await session.connect_to_target(target)
        async with conn:
            # Create console collector
            collector = ConsoleCollector(
                connection=conn,
                output_path=Path(args.output) if hasattr(args, "output") and args.output else None,
                level_filter=args.level if hasattr(args, "level") else None,
            )

            async with collector:
                await collector.start()

                # Stream for specified duration
                if not args.quiet:
                    print(
                        f"Streaming console logs for {args.duration} seconds...",
                        file=sys.stderr,
                    )

                await asyncio.sleep(args.duration)

                await collector.stop()

            if not args.quiet and collector.output_path:
                print(
                    f"Console logs saved to: {collector.output_path}", file=sys.stderr
                )

        return 0

    except CDPError as e:
        if args.log_level == "debug":
            raise
        print(f"Error: {e}", file=sys.stderr)
        if e.details.get("recovery"):
            print(f"Recovery hint: {e.details['recovery']}", file=sys.stderr)
        return 1


def console_stream_handler(args: argparse.Namespace) -> int:
    """
    Synchronous wrapper for console_stream_handler_async.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    return asyncio.run(console_stream_handler_async(args))


def register_subcommand(
    subparsers: argparse._SubParsersAction, parent: argparse.ArgumentParser
) -> None:
    """
    Register 'console' subcommand.

    Args:
        subparsers: Subparsers from main parser
        parent: Parent parser with global options
    """
    console_parser = subparsers.add_parser(
        "console",
        parents=[parent],
        help="Stream console logs",
        description="Monitor and record console messages from a target",
        epilog="""
Examples:
  # Stream console logs for 60 seconds
  browser-debugger console stream --duration 60

  # Stream from specific target
  browser-debugger console stream --target <target-id> --duration 30

  # Stream from target matching URL
  browser-debugger console stream --url example.com --duration 60

  # Filter by level
  browser-debugger console stream --duration 60 --level error

  # Save to custom file
  browser-debugger console stream --duration 60 --output console.jsonl
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Action
    console_parser.add_argument(
        "action",
        choices=["stream"],
        help="Action to perform (currently only 'stream' is supported)",
    )

    # Target selection (mutual exclusion)
    target_group = console_parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--target", help="Target ID to monitor console logs from"
    )
    target_group.add_argument(
        "--url",
        help="URL pattern to match target (uses first match)",
    )

    # Duration
    console_parser.add_argument(
        "--duration",
        type=int,
        required=True,
        help="Duration to stream logs in seconds",
    )

    # Level filter
    console_parser.add_argument(
        "--level",
        choices=["log", "info", "warning", "error", "debug"],
        help="Filter console messages by level",
    )

    # Output file
    console_parser.add_argument(
        "--output",
        help="Output file path for console logs (JSONL format)",
    )

    # Set handler function
    console_parser.set_defaults(func=console_stream_handler)
