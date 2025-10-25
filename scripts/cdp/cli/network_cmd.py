"""
Network subcommand for recording network activity.

Implements 'network record' command to capture network requests and responses.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from ..session import CDPSession
from ..collectors.network import NetworkCollector
from ..exceptions import CDPError, CDPTargetNotFoundError


async def network_record_handler_async(args: argparse.Namespace) -> int:
    """
    Handle 'network record' command (async implementation).

    Records network activity from target for specified duration.

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
                # Create network collector
                collector = NetworkCollector(
                    connection=conn,
                    output_path=(
                        Path(args.output)
                        if hasattr(args, "output") and args.output
                        else None
                    ),
                    include_bodies=(
                        args.include_bodies
                        if hasattr(args, "include_bodies")
                        else False
                    ),
                )

                async with collector:
                    if not args.quiet:
                        print(
                            f"Recording network activity for {args.duration} seconds...",
                            file=sys.stderr,
                        )

                    await asyncio.sleep(args.duration)

                if not args.quiet and collector.output_path:
                    print(
                        f"Network logs saved to: {collector.output_path}",
                        file=sys.stderr,
                    )

            return 0

        # Connect to target
        conn = await session.connect_to_target(target)
        async with conn:
            # Create network collector
            collector = NetworkCollector(
                connection=conn,
                output_path=(
                    Path(args.output)
                    if hasattr(args, "output") and args.output
                    else None
                ),
                include_bodies=(
                    args.include_bodies if hasattr(args, "include_bodies") else False
                ),
            )

            async with collector:
                if not args.quiet:
                    print(
                        f"Recording network activity for {args.duration} seconds...",
                        file=sys.stderr,
                    )

                await asyncio.sleep(args.duration)

            if not args.quiet and collector.output_path:
                print(
                    f"Network logs saved to: {collector.output_path}",
                    file=sys.stderr,
                )

        return 0

    except CDPError as e:
        if hasattr(args, "config") and args.config.log_level.upper() == "DEBUG":
            raise
        print(f"Error: {e}", file=sys.stderr)
        if e.details.get("recovery"):
            print(f"Recovery hint: {e.details['recovery']}", file=sys.stderr)
        return 1


def network_record_handler(args: argparse.Namespace) -> int:
    """
    Synchronous wrapper for network_record_handler_async.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    return asyncio.run(network_record_handler_async(args))


def register_subcommand(
    subparsers: argparse._SubParsersAction, parent: argparse.ArgumentParser
) -> None:
    """
    Register 'network' subcommand.

    Args:
        subparsers: Subparsers from main parser
        parent: Parent parser with global options
    """
    network_parser = subparsers.add_parser(
        "network",
        parents=[parent],
        help="Record network activity",
        description="Monitor and record network requests and responses from a target",
        epilog="""
Examples:
  # Record network activity for 60 seconds
  browser-debugger network record --duration 60

  # Record from specific target
  browser-debugger network record --target <target-id> --duration 30

  # Record from target matching URL
  browser-debugger network record --url example.com --duration 60

  # Include response bodies
  browser-debugger network record --duration 60 --include-bodies

  # Save to custom file
  browser-debugger network record --duration 60 --output network.jsonl
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Action
    network_parser.add_argument(
        "action",
        choices=["record"],
        help="Action to perform (currently only 'record' is supported)",
    )

    # Target selection (mutual exclusion)
    target_group = network_parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--target", help="Target ID to monitor network activity from"
    )
    target_group.add_argument(
        "--url",
        help="URL pattern to match target (uses first match)",
    )

    # Duration
    network_parser.add_argument(
        "--duration",
        type=int,
        required=True,
        help="Duration to record network activity in seconds",
    )

    # Include bodies
    network_parser.add_argument(
        "--include-bodies",
        action="store_true",
        help="Capture response bodies (increases memory usage)",
    )

    # Output file
    network_parser.add_argument(
        "--output",
        help="Output file path for network logs (JSONL format)",
    )

    # Set handler function
    network_parser.set_defaults(func=network_record_handler)
