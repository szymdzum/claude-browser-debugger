#!/bin/bash
set -euo pipefail

# cleanup-chrome.sh - Automated Chrome and CDP collector process cleanup
# Purpose: Terminate Chrome debug instances and release ports aggressively
# Usage: ./cleanup-chrome.sh [PORT]
# Default port: 9222

# ============================================================================
# Configuration
# ============================================================================

PORT="${1:-9222}"
# Use Python for reliable millisecond timing across platforms
START_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")

# ============================================================================
# Validation
# ============================================================================

# Validate port is numeric and in valid range
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    jq -nc \
        --arg status "error" \
        --arg code "INVALID_PORT" \
        --arg message "Port must be numeric, got: $PORT" \
        --arg recovery "Use a numeric port between 1024-65535" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

if [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
    jq -nc \
        --arg status "error" \
        --arg code "INVALID_PORT" \
        --arg message "Port out of valid range: $PORT (valid: 1024-65535)" \
        --arg recovery "Use a port between 1024-65535" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# Verify lsof is available
if ! command -v lsof >/dev/null 2>&1; then
    jq -nc \
        --arg status "error" \
        --arg code "LSOF_FAILED" \
        --arg message "lsof command not found - required for port verification" \
        --arg recovery "Install lsof: brew install lsof (macOS) or apt-get install lsof (Linux)" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# ============================================================================
# Cleanup Implementation
# ============================================================================

# Track killed PIDs to deduplicate
declare -a KILLED_PIDS=()

echo "Starting cleanup for port $PORT..." >&2

# Phase 1: Graceful SIGTERM to Chrome processes
echo "Phase 1: Sending SIGTERM to Chrome processes on port $PORT..." >&2
CHROME_PIDS=$(pgrep -f "chrome.*--remote-debugging-port=${PORT}" 2>/dev/null || true)

if [ -n "$CHROME_PIDS" ]; then
    for PID in $CHROME_PIDS; do
        echo "  Sending SIGTERM to PID $PID" >&2
        kill -TERM "$PID" 2>/dev/null || true
        KILLED_PIDS+=("$PID")
    done
    echo "  Waiting 2 seconds for graceful shutdown..." >&2
    sleep 2
else
    echo "  No Chrome processes found on port $PORT" >&2
fi

# Phase 2: Forceful SIGKILL to surviving processes
echo "Phase 2: Checking for surviving processes..." >&2
SURVIVORS=$(pgrep -f "chrome.*--remote-debugging-port=${PORT}" 2>/dev/null || true)

if [ -n "$SURVIVORS" ]; then
    echo "  Found surviving processes, sending SIGKILL..." >&2
    for PID in $SURVIVORS; do
        echo "  Sending SIGKILL to PID $PID" >&2
        kill -9 "$PID" 2>/dev/null || true
        # Add to KILLED_PIDS if not already present
        if [[ ! " ${KILLED_PIDS[@]} " =~ " ${PID} " ]]; then
            KILLED_PIDS+=("$PID")
        fi
    done
    sleep 1
else
    echo "  No surviving processes found" >&2
fi

# Phase 3: Port-based force kill (last resort)
echo "Phase 3: Verifying port is released..." >&2
sleep 1
PORT_PIDS=$(lsof -ti ":$PORT" 2>/dev/null || true)

if [ -n "$PORT_PIDS" ]; then
    echo "  Port $PORT still occupied by PIDs: $PORT_PIDS" >&2
    echo "  Forcing kill of processes on port..." >&2
    for PID in $PORT_PIDS; do
        echo "  Force killing PID $PID" >&2
        kill -9 "$PID" 2>/dev/null || true
        # Add to KILLED_PIDS if not already present
        if [[ ! " ${KILLED_PIDS[@]} " =~ " ${PID} " ]]; then
            KILLED_PIDS+=("$PID")
        fi
    done
    sleep 1
fi

# CDP Collector Cleanup
echo "Cleaning up CDP collectors..." >&2
CDP_CONSOLE_PIDS=$(pgrep -f "cdp-console.py" 2>/dev/null || true)
CDP_NETWORK_PIDS=$(pgrep -f "cdp-network.py" 2>/dev/null || true)
CDP_OTHER_PIDS=$(pgrep -f "cdp-.*\.py" 2>/dev/null || true)

for PID in $CDP_CONSOLE_PIDS $CDP_NETWORK_PIDS $CDP_OTHER_PIDS; do
    if [ -n "$PID" ]; then
        echo "  Killing CDP collector PID $PID" >&2
        kill -9 "$PID" 2>/dev/null || true
        # Add to KILLED_PIDS if not already present
        if [[ ! " ${KILLED_PIDS[@]} " =~ " ${PID} " ]]; then
            KILLED_PIDS+=("$PID")
        fi
    fi
done

# ============================================================================
# Final Verification
# ============================================================================

sleep 1
FINAL_CHECK=$(lsof -ti ":$PORT" 2>/dev/null || true)

if [ -n "$FINAL_CHECK" ]; then
    # Port still occupied - cleanup failed
    END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")
    CLEANUP_TIME=$((END_TIME - START_TIME))

    jq -nc \
        --arg status "error" \
        --arg code "PORT_STILL_BUSY" \
        --arg message "Port $PORT still occupied by PIDs: $FINAL_CHECK after cleanup" \
        --arg recovery "kill -9 $FINAL_CHECK, or check for non-Chrome processes: lsof -ti :$PORT" \
        '{status: $status, code: $code, message: $message, recovery: $recovery}' >&1
    exit 1
fi

# ============================================================================
# Success Response
# ============================================================================

# Calculate cleanup time
END_TIME=$(python3 -c "import time; print(int(time.time() * 1000))")
CLEANUP_TIME=$((END_TIME - START_TIME))

# Deduplicate and sort PIDs (handle empty array case)
if [ ${#KILLED_PIDS[@]} -eq 0 ]; then
    UNIQUE_PIDS=()
else
    UNIQUE_PIDS=($(printf '%s\n' "${KILLED_PIDS[@]}" | sort -u))
fi

# Build JSON array of killed PIDs
PIDS_JSON="["
for i in "${!UNIQUE_PIDS[@]}"; do
    PIDS_JSON+="${UNIQUE_PIDS[$i]}"
    if [ $i -lt $((${#UNIQUE_PIDS[@]} - 1)) ]; then
        PIDS_JSON+=","
    fi
done
PIDS_JSON+="]"

echo "Cleanup complete! Port $PORT released." >&2

jq -nc \
    --arg status "success" \
    --argjson port "$PORT" \
    --arg port_status "released" \
    --argjson processes_killed "$PIDS_JSON" \
    --argjson cleanup_time_ms "$CLEANUP_TIME" \
    '{status: $status, port: $port, port_status: $port_status, processes_killed: $processes_killed, cleanup_time_ms: $cleanup_time_ms}' >&1

exit 0
