"""
DOM subcommand for extracting page DOM.

Implements 'dom dump' command to extract HTML via Runtime.evaluate.
"""

import argparse
import sys
from pathlib import Path

from ..session import CDPSession
from ..exceptions import CDPError, CDPTargetNotFoundError


async def dom_dump_handler_async(args: argparse.Namespace) -> int:
    """
    Handle 'dom dump' command (async implementation).

    Extracts DOM from target via Runtime.evaluate.

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
            # Use first page
            conn = await session.connect_to_first_page()
            async with conn:
                # Wait for selector if specified
                if args.wait_for:
                    wait_expr = f"""
                    new Promise((resolve, reject) => {{
                        const timeout = setTimeout(() => reject(new Error('Selector not found: {args.wait_for}')), {args.timeout * 1000});
                        const interval = setInterval(() => {{
                            if (document.querySelector('{args.wait_for}')) {{
                                clearInterval(interval);
                                clearTimeout(timeout);
                                resolve(true);
                            }}
                        }}, 100);
                    }})
                    """
                    await conn.execute_command(
                        "Runtime.evaluate",
                        {"expression": wait_expr, "awaitPromise": True},
                    )

                # Extract DOM
                result = await conn.execute_command(
                    "Runtime.evaluate",
                    {
                        "expression": "document.documentElement.outerHTML",
                        "returnByValue": True,
                    },
                )

                html = result["result"]["value"]

                # Write to file
                output_path = Path(args.output)
                output_path.write_text(html, encoding="utf-8")

                if not args.quiet:
                    print(f"DOM saved to: {output_path}", file=sys.stderr)

            return 0

        # Connect to target
        conn = await session.connect_to_target(target)
        async with conn:
            # Wait for selector if specified
            if args.wait_for:
                wait_expr = f"""
                new Promise((resolve, reject) => {{
                    const timeout = setTimeout(() => reject(new Error('Selector not found: {args.wait_for}')), {args.timeout * 1000});
                    const interval = setInterval(() => {{
                        if (document.querySelector('{args.wait_for}')) {{
                            clearInterval(interval);
                            clearTimeout(timeout);
                            resolve(true);
                        }}
                    }}, 100);
                }})
                """
                await conn.execute_command(
                    "Runtime.evaluate",
                    {"expression": wait_expr, "awaitPromise": True},
                )

            # Extract DOM
            result = await conn.execute_command(
                "Runtime.evaluate",
                {
                    "expression": "document.documentElement.outerHTML",
                    "returnByValue": True,
                },
            )

            html = result["result"]["value"]

            # Write to file
            output_path = Path(args.output)
            output_path.write_text(html, encoding="utf-8")

            if not args.quiet:
                print(f"DOM saved to: {output_path}", file=sys.stderr)

        return 0

    except CDPError as e:
        if args.log_level == "debug":
            raise
        print(f"Error: {e}", file=sys.stderr)
        if e.details.get("recovery"):
            print(f"Recovery hint: {e.details['recovery']}", file=sys.stderr)
        return 1


def dom_dump_handler(args: argparse.Namespace) -> int:
    """
    Synchronous wrapper for dom_dump_handler_async.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    import asyncio

    return asyncio.run(dom_dump_handler_async(args))


def register_subcommand(
    subparsers: argparse._SubParsersAction, parent: argparse.ArgumentParser
) -> None:
    """
    Register 'dom' subcommand.

    Args:
        subparsers: Subparsers from main parser
        parent: Parent parser with global options
    """
    dom_parser = subparsers.add_parser(
        "dom",
        parents=[parent],
        help="Extract DOM from a page",
        description="Extract page DOM via Runtime.evaluate",
        epilog="""
Examples:
  # Dump DOM from first page
  browser-debugger dom dump --output dom.html

  # Dump DOM from specific target
  browser-debugger dom dump --target <target-id> --output dom.html

  # Dump DOM from target matching URL
  browser-debugger dom dump --url example.com --output dom.html

  # Wait for element before dumping
  browser-debugger dom dump --url example.com --wait-for "#content" --output dom.html
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Action
    dom_parser.add_argument(
        "action",
        choices=["dump"],
        help="Action to perform (currently only 'dump' is supported)",
    )

    # Target selection (mutual exclusion)
    target_group = dom_parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--target", help="Target ID to extract DOM from"
    )
    target_group.add_argument(
        "--url",
        help="URL pattern to match target (uses first match)",
    )

    # Output file
    dom_parser.add_argument(
        "--output",
        required=True,
        help="Output file path for DOM HTML",
    )

    # Wait for selector
    dom_parser.add_argument(
        "--wait-for",
        help="CSS selector to wait for before extracting DOM",
    )

    # Set handler function
    dom_parser.set_defaults(func=dom_dump_handler)
