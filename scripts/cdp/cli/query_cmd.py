"""
Query subcommand for executing arbitrary CDP commands.

Implements 'query' command for direct CDP method invocation with custom params.
"""

import argparse
import asyncio
import json
import sys

from ..session import CDPSession
from ..exceptions import CDPError, CDPTargetNotFoundError


async def query_handler_async(args: argparse.Namespace) -> int:
    """
    Handle 'query' command (async implementation).

    Executes arbitrary CDP command with JSON params.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse params JSON
        params = {}
        if args.params:
            try:
                params = json.loads(args.params)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON params: {e}", file=sys.stderr)
                return 1

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
                # Execute command
                result = await conn.execute_command(args.method, params)

                # Output result
                if args.format == "json":
                    print(json.dumps(result, indent=2))
                else:
                    # Pretty-print for text format
                    print(json.dumps(result, indent=2))

            return 0

        # Connect to target
        conn = await session.connect_to_target(target)
        async with conn:
            # Execute command
            result = await conn.execute_command(args.method, params)

            # Output result
            if args.format == "json":
                print(json.dumps(result, indent=2))
            else:
                # Pretty-print for text format
                print(json.dumps(result, indent=2))

        return 0

    except CDPError as e:
        if hasattr(args, "config") and args.config.log_level.upper() == "DEBUG":
            raise
        print(f"Error: {e}", file=sys.stderr)
        if e.details.get("recovery"):
            print(f"Recovery hint: {e.details['recovery']}", file=sys.stderr)
        return 1


def query_handler(args: argparse.Namespace) -> int:
    """
    Synchronous wrapper for query_handler_async.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    return asyncio.run(query_handler_async(args))


def register_subcommand(
    subparsers: argparse._SubParsersAction, parent: argparse.ArgumentParser
) -> None:
    """
    Register 'query' subcommand.

    Args:
        subparsers: Subparsers from main parser
        parent: Parent parser with global options
    """
    query_parser = subparsers.add_parser(
        "query",
        parents=[parent],
        help="Execute arbitrary CDP command",
        description="Execute any CDP method with custom parameters",
        epilog="""
Examples:
  # Simple command
  browser-debugger query --method Runtime.evaluate --params '{"expression":"document.title","returnByValue":true}'

  # Command on specific target
  browser-debugger query --target <target-id> --method Page.navigate --params '{"url":"https://example.com"}'

  # Command on target matching URL
  browser-debugger query --url example.com --method Runtime.getHeapUsage

  # Enable domain
  browser-debugger query --method Console.enable

  # Complex params
  browser-debugger query --method Emulation.setDeviceMetricsOverride --params '{"width":375,"height":667,"deviceScaleFactor":2,"mobile":true}'
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Target selection (mutual exclusion)
    target_group = query_parser.add_mutually_exclusive_group()
    target_group.add_argument("--target", help="Target ID to execute command in")
    target_group.add_argument(
        "--url",
        help="URL pattern to match target (uses first match)",
    )

    # CDP method
    query_parser.add_argument(
        "--method",
        required=True,
        help="CDP method to execute (e.g., Runtime.evaluate, Page.navigate)",
    )

    # Parameters
    query_parser.add_argument(
        "--params",
        help="JSON-encoded parameters for the CDP method",
    )

    # Set handler function
    query_parser.set_defaults(func=query_handler)
