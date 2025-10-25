"""
Session subcommand for target discovery and listing.

Implements 'session list' command to discover and filter Chrome targets.
"""

import argparse
import json
import sys
from typing import List

from ..session import CDPSession
from ..exceptions import CDPError


def session_list_handler(args: argparse.Namespace) -> int:
    """
    Handle 'session list' command.

    Lists Chrome targets with optional filtering by type and URL pattern.

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

        # List targets with filters
        targets = session.list_targets(
            target_type=args.type if hasattr(args, "type") else None,
            url_pattern=args.url if hasattr(args, "url") else None,
        )

        # Output results
        if args.format == "json":
            output = [target.to_dict() for target in targets]
            print(json.dumps(output, indent=2))
        elif args.format == "text":
            for target in targets:
                print(f"{target.id}\t{target.type}\t{target.url}\t{target.title}")
        elif args.format == "table":
            # Simple table format
            print(f"{'ID':<40} {'TYPE':<15} {'URL':<50} {'TITLE':<30}")
            print("-" * 135)
            for target in targets:
                print(
                    f"{target.id:<40} {target.type:<15} {target.url[:50]:<50} {target.title[:30]:<30}"
                )

        return 0

    except CDPError as e:
        if hasattr(args, "config") and args.config.log_level.upper() == "DEBUG":
            raise
        print(f"Error: {e}", file=sys.stderr)
        if e.details.get("recovery"):
            print(f"Recovery hint: {e.details['recovery']}", file=sys.stderr)
        return 1


def register_subcommand(
    subparsers: argparse._SubParsersAction, parent: argparse.ArgumentParser
) -> None:
    """
    Register 'session' subcommand.

    Args:
        subparsers: Subparsers from main parser
        parent: Parent parser with global options
    """
    # Create session parser
    session_parser = subparsers.add_parser(
        "session",
        parents=[parent],
        help="List and inspect Chrome targets",
        description="Discover and filter Chrome targets via CDP HTTP endpoint",
        epilog="""
Examples:
  # List all targets
  browser-debugger session list

  # List only page targets
  browser-debugger session list --type page

  # Find targets matching URL pattern
  browser-debugger session list --url example.com

  # Combine filters
  browser-debugger session list --type page --url localhost

  # Output as table
  browser-debugger session list --format table
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add session-specific arguments
    session_parser.add_argument(
        "action",
        choices=["list"],
        help="Action to perform (currently only 'list' is supported)",
    )

    session_parser.add_argument(
        "--type",
        choices=["page", "iframe", "worker", "service_worker", "browser"],
        help="Filter targets by type",
    )

    session_parser.add_argument(
        "--url",
        help="Filter targets by URL pattern (case-insensitive substring match)",
    )

    # Set handler function
    session_parser.set_defaults(func=session_list_handler)
