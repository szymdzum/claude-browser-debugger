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
OUTPUT_FILE="/tmp/debug-output.log"
SUMMARY_FORMAT="none"
INCLUDE_CONSOLE="false"
CONSOLE_LOG=""
IDLE_SECONDS="5"
MODE="headless"
PORT="9222"
PROFILE=""

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
    OUTPUT_FILE="$1"
    shift
fi

# Parse named flags
while [ $# -gt 0 ]; then
    case "$1" in
        --summary=*)
            SUMMARY_FORMAT="${1#--summary=}"
            ;;
        --include-console)
            INCLUDE_CONSOLE="true"
            ;;
        --console-log=*)
            CONSOLE_LOG="${1#--console-log=}"
            ;;
        --idle=*)
            IDLE_SECONDS="${1#--idle=}"
            ;;
        --mode=*)
            MODE="${1#--mode=}"
            ;;
        --port=*)
            PORT="${1#--port=}"
            ;;
        --profile=*)
            PROFILE="${1#--profile=}"
            ;;
        --filter=*)
            # Filter flag not yet implemented in Python CLI (ignore for now)
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
    --output "$OUTPUT_FILE"
    --idle "$IDLE_SECONDS"
    --chrome-port "$PORT"
)

# Add optional flags
if [ "$INCLUDE_CONSOLE" = "true" ]; then
    PYTHON_CMD+=(--include-console)
fi

if [ -n "$CONSOLE_LOG" ]; then
    PYTHON_CMD+=(--console-log "$CONSOLE_LOG")
fi

if [ "$SUMMARY_FORMAT" != "none" ]; then
    PYTHON_CMD+=(--summary "$SUMMARY_FORMAT")
fi

if [ -n "$PROFILE" ] && [ "$PROFILE" != "none" ]; then
    PYTHON_CMD+=(--profile "$PROFILE")
fi

# Execute Python CLI from repository root
cd "$REPO_ROOT"
exec "${PYTHON_CMD[@]}"
