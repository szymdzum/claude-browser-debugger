"""
Eval subcommand for executing JavaScript in Chrome targets.

Implements 'eval' command to execute JavaScript expressions via Runtime.evaluate.
"""

import argparse
import json
import sys

from ..session import CDPSession
from ..exceptions import CDPError, CDPTargetNotFoundError


async def eval_handler_async(args: argparse.Namespace) -> int:
    """
    Handle 'eval' command (async implementation).

    Executes JavaScript in specified target using Runtime.evaluate.

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
            # Connect by target ID
            target = session.get_target_by_id(args.target)
            if not target:
                raise CDPTargetNotFoundError(
                    f"Target not found: {args.target}",
                    target_id=args.target,
                )
        elif args.url:
            # Find target by URL pattern
            targets = session.list_targets(target_type="page", url_pattern=args.url)
            if not targets:
                raise CDPTargetNotFoundError(
                    f"No page target matching URL: {args.url}",
                    url_pattern=args.url,
                )
            target = targets[0]  # Use first match
        else:
            # Use first page target
            conn = await session.connect_to_first_page()
            async with conn:
                result = await conn.execute_command(
                    "Runtime.evaluate",
                    {
                        "expression": args.expression,
                        "returnByValue": True,
                        "awaitPromise": args.await_promise,
                    },
                )

                # Output result
                if args.format == "json":
                    print(json.dumps(result, indent=2))
                else:
                    if "result" in result and "value" in result["result"]:
                        print(result["result"]["value"])
                    elif "exceptionDetails" in result:
                        print(
                            f"Error: {result['exceptionDetails']['text']}",
                            file=sys.stderr,
                        )
                        return 1

            return 0

        # Connect to target
        conn = await session.connect_to_target(target)
        async with conn:
            result = await conn.execute_command(
                "Runtime.evaluate",
                {
                    "expression": args.expression,
                    "returnByValue": True,
                    "awaitPromise": args.await_promise,
                },
            )

            # Output result
            if args.format == "json":
                print(json.dumps(result, indent=2))
            else:
                if "result" in result and "value" in result["result"]:
                    print(result["result"]["value"])
                elif "exceptionDetails" in result:
                    print(
                        f"Error: {result['exceptionDetails']['text']}", file=sys.stderr
                    )
                    return 1

        return 0

    except CDPError as e:
        if hasattr(args, 'config') and args.config.log_level.upper() == "DEBUG":
            raise
        print(f"Error: {e}", file=sys.stderr)
        if e.details.get("recovery"):
            print(f"Recovery hint: {e.details['recovery']}", file=sys.stderr)
        return 1


def eval_handler(args: argparse.Namespace) -> int:
    """
    Synchronous wrapper for eval_handler_async.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    import asyncio

    return asyncio.run(eval_handler_async(args))


def register_subcommand(
    subparsers: argparse._SubParsersAction, parent: argparse.ArgumentParser
) -> None:
    """
    Register 'eval' subcommand.

    Args:
        subparsers: Subparsers from main parser
        parent: Parent parser with global options
    """
    eval_parser = subparsers.add_parser(
        "eval",
        parents=[parent],
        help="Execute JavaScript in a target",
        description="Execute JavaScript expression via Runtime.evaluate",
        epilog="""
Examples:
  # Evaluate in first page
  browser-debugger eval "document.title"

  # Evaluate in specific target
  browser-debugger eval --target <target-id> "window.location.href"

  # Evaluate in target matching URL
  browser-debugger eval --url example.com "document.querySelector('h1').textContent"

  # Wait for promise resolution
  browser-debugger eval --await "fetch('/api/data').then(r => r.json())"

  # JSON output
  browser-debugger eval --format json "document.querySelector('h1').textContent"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Target selection (mutual exclusion)
    target_group = eval_parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--target", help="Target ID to execute JavaScript in"
    )
    target_group.add_argument(
        "--url",
        help="URL pattern to match target (uses first match)",
    )

    # JavaScript expression
    eval_parser.add_argument(
        "expression",
        help="JavaScript expression to evaluate",
    )

    # Await promise
    eval_parser.add_argument(
        "--await",
        dest="await_promise",
        action="store_true",
        help="Wait for promise resolution (awaitPromise: true)",
    )

    # Set handler function
    eval_parser.set_defaults(func=eval_handler)
