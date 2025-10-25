"""
Main CLI entry point for browser-debugger CDP tool.

Provides unified command-line interface with subcommands for CDP operations.

Usage:
    python -m scripts.cdp.cli.main <subcommand> [options]

Subcommands:
    session     - List and inspect Chrome targets
    eval        - Execute JavaScript in a target
    dom         - Extract DOM from a page
    console     - Stream console logs
    network     - Record network activity
    orchestrate - Run automated debugging workflow
    query       - Execute arbitrary CDP commands
"""

import argparse
import sys
from typing import List, Optional
from scripts.cdp.config import Configuration
from scripts.cdp.logging_setup import setup_logging


def create_parent_parser() -> argparse.ArgumentParser:
    """
    Create parent parser with global options shared across all subcommands.

    Global options:
        --chrome-host: Chrome host (default: localhost)
        --chrome-port: Chrome debugging port (default: 9222)
        --timeout: Command timeout in seconds (default: 30.0)
        --format: Output format (json|text|table, default: json)
        --log-level: Log level (debug|info|warning|error, default: info)
        --quiet/--verbose: Mutual exclusion group for output control

    Returns:
        ArgumentParser with global options
    """
    parent = argparse.ArgumentParser(add_help=False)

    # Connection options
    parent.add_argument(
        "--chrome-host",
        default="localhost",
        help="Chrome host (default: localhost)",
    )
    parent.add_argument(
        "--chrome-port",
        type=int,
        default=9222,
        help="Chrome debugging port (default: 9222)",
    )
    parent.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Command timeout in seconds (default: 30.0)",
    )

    # Output format
    parent.add_argument(
        "--format",
        choices=["json", "text", "table"],
        default="json",
        help="Output format (default: json)",
    )

    # Logging options
    parent.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="Log level (default: info)",
    )

    # Mutual exclusion group for verbosity
    verbosity_group = parent.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-essential output (only show results)",
    )
    verbosity_group.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug output",
    )

    return parent


def create_main_parser(parent: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Create main parser with all subcommands.

    Args:
        parent: Parent parser with global options

    Returns:
        Main ArgumentParser with subcommands configured
    """
    parser = argparse.ArgumentParser(
        prog="browser-debugger",
        description="Chrome DevTools Protocol (CDP) debugging tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all page targets
  browser-debugger session list --type page

  # Execute JavaScript
  browser-debugger eval --url example.com "document.title"

  # Extract DOM
  browser-debugger dom dump --url example.com --output dom.html

  # Stream console logs for 60 seconds
  browser-debugger console stream --url example.com --duration 60

  # Record network activity
  browser-debugger network record --url example.com --duration 30 --include-bodies

  # Run automated debugging workflow
  browser-debugger orchestrate headless https://example.com --include-console

  # Execute arbitrary CDP command
  browser-debugger query --target <target-id> --method Runtime.evaluate --params '{"expression":"document.title"}'

For more information on subcommands, run: browser-debugger <subcommand> --help
        """,
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest="subcommand",
        title="subcommands",
        description="Available CDP operations",
        required=True,
    )

    # Import subcommand modules
    from . import (
        session_cmd,
        eval_cmd,
        dom_cmd,
        console_cmd,
        network_cmd,
        orchestrate_cmd,
        query_cmd,
    )

    # Wire up subcommands
    session_cmd.register_subcommand(subparsers, parent)
    eval_cmd.register_subcommand(subparsers, parent)
    dom_cmd.register_subcommand(subparsers, parent)
    console_cmd.register_subcommand(subparsers, parent)
    network_cmd.register_subcommand(subparsers, parent)
    orchestrate_cmd.register_subcommand(subparsers, parent)
    query_cmd.register_subcommand(subparsers, parent)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for CLI.

    Implements T093: Integrate Configuration and logging setup.
    Precedence: CLI flags > env vars > config file > defaults (R7 from research.md)

    Args:
        argv: Command-line arguments (default: sys.argv[1:])

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Create parsers
    parent = create_parent_parser()
    parser = create_main_parser(parent)

    # Parse arguments
    args = parser.parse_args(argv)

    # Load configuration with precedence: CLI > env > file > defaults
    config = Configuration()
    config.load_from_file("~/.cdprc")  # Load from config file if exists
    config.load_from_env()  # Override with environment variables

    # Merge CLI arguments (highest precedence)
    cli_overrides = {
        "chrome_port": args.chrome_port if hasattr(args, "chrome_port") else None,
        "timeout": args.timeout if hasattr(args, "timeout") else None,
        "log_level": args.log_level if hasattr(args, "log_level") else None,
        "log_format": args.format if hasattr(args, "format") else None,
    }
    config.merge(**{k: v for k, v in cli_overrides.items() if v is not None})

    # Handle verbosity flags (override log level)
    if hasattr(args, "quiet") and args.quiet:
        config.log_level = "ERROR"
    elif hasattr(args, "verbose") and args.verbose:
        config.log_level = "DEBUG"

    # Setup logging with final configuration
    setup_logging(
        format_type=config.log_format,
        level=config.log_level.upper() if isinstance(config.log_level, str) else "INFO",
        quiet=getattr(args, "quiet", False),
        verbose=getattr(args, "verbose", False),
    )

    # Attach config to args for subcommands to access
    args.config = config

    # Dispatch to subcommand handler (will be set via set_defaults(func=...) in subcommands)
    if hasattr(args, "func"):
        try:
            return args.func(args)
        except KeyboardInterrupt:
            print("\nInterrupted by user", file=sys.stderr)
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            if config.log_level.upper() == "DEBUG":
                raise  # Re-raise for full traceback in debug mode
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        # No subcommand provided (should not happen with required=True, but fallback)
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
