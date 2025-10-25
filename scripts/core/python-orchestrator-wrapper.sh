#!/bin/bash
# python-orchestrator-wrapper.sh - Compatibility wrapper mapping Bash orchestrator flags to Python CLI
#
# Purpose: Enables dual-path CI validation by translating debug-orchestrator.sh calls to Python CLI equivalents
#
# Usage: ./python-orchestrator-wrapper.sh <URL> [duration] [output-file] [--flags...]
#
# Mapping Strategy:
#   Bash debug-orchestrator.sh → Python: python3 -m scripts.cdp.cli.main orchestrate
#
# Task: T067 [US5] - Migration Safety with Parallel Testing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default values (match debug-orchestrator.sh defaults)
URL=""
DURATION="15"
OUTPUT_DIR=""
SUMMARY_FORMAT="text"
INCLUDE_CONSOLE="false"
MODE="headless"
PORT="9222"

# Parse positional arguments
if [ $# -ge 1 ]; then
    URL="$1"
    shift
fi

if [ $# -ge 1 ] && [[ ! "$1" =~ ^-- ]]; then
    DURATION="$1"
    shift
fi

if [ $# -ge 1 ] && [[ ! "$1" =~ ^-- ]]; then
    # Legacy positional arg for output file - reject with clear error
    echo "Error: Python CLI does not support positional output file argument" >&2
    echo "Legacy: ./script.sh URL DURATION /path/to/output.log" >&2
    echo "Python:  Use --output-dir /path/to/dir instead" >&2
    echo "Note: Python CLI generates timestamped files (YYYYMMDD-HHMMSS-PID-*)" >&2
    exit 1
fi

# Parse named flags
while [ $# -gt 0 ]; do
    case "$1" in
        --summary=*)
            SUMMARY_FORMAT="${1#--summary=}"
            ;;
        --include-console)
            INCLUDE_CONSOLE="true"
            ;;
        --mode=*)
            MODE="${1#--mode=}"
            ;;
        --port=*)
            PORT="${1#--port=}"
            ;;
        --output-dir=*)
            OUTPUT_DIR="${1#--output-dir=}"
            ;;
        # Legacy/unsupported flags (ignore with warning)
        --console-log=*|--idle=*|--profile=*|--filter=*)
            echo "Warning: Flag $1 not supported in Python CLI (ignoring)" >&2
            ;;
        *)
            echo "Warning: Unknown flag $1 (ignoring)" >&2
            ;;
    esac
    shift
done

# Validation
if [ -z "$URL" ]; then
    echo "Error: URL is required" >&2
    echo "Usage: $0 <URL> [duration] [output-file] [--flags...]" >&2
    exit 1
fi

# Build Python CLI command
# Python CLI: python3 -m scripts.cdp.cli.main orchestrate <mode> <url> [options]
PYTHON_CMD=(
    python3 -m scripts.cdp.cli.main orchestrate
    "$MODE"
    "$URL"
    --duration "$DURATION"
    --chrome-port "$PORT"
)

# Add summary flag only if not "none" (legacy compatibility)
if [ "$SUMMARY_FORMAT" != "none" ]; then
    PYTHON_CMD+=(--summary "$SUMMARY_FORMAT")
fi

# Add optional flags
if [ "$INCLUDE_CONSOLE" = "true" ]; then
    PYTHON_CMD+=(--include-console)
fi

if [ -n "$OUTPUT_DIR" ]; then
    PYTHON_CMD+=(--output-dir "$OUTPUT_DIR")
fi

# Execute Python CLI from repository root
cd "$REPO_ROOT"
exec "${PYTHON_CMD[@]}"
