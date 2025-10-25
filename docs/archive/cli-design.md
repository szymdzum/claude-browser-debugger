# CLI Interface Design Specification

## Overview

The `browser-debugger` CLI provides a Python-first interface to Chrome DevTools Protocol operations. It prioritizes agent ergonomics (single command workflows), structured output (JSON), and composability (subcommands for advanced scenarios).

## Design Review Summary

**Key Refinements Made** (from design review feedback):

1. ✅ **Flag semantics clarified**: Separated `--format` (output format) from subcommand `--output FILE` (destination); added `--json` alias
2. ✅ **Mutual exclusion enforced**: `--target` and `--url` use `argparse.add_mutually_exclusive_group()` with explicit error messages
3. ✅ **Wait-for selector added**: `dom dump` and `orchestrate` support `--wait-for SELECTOR` for post-form interactions
4. ✅ **Network body capture safety**: `--include-bodies` defaults OFF, added `--max-body-size` limit (1MB), help text warnings
5. ✅ **Orchestrate failure handling**: Defined exit codes (0/2/4/6), partial artifact preservation, status field in JSON output
6. ✅ **Stdin support for query**: Added `--params-file -` for large payloads and CDP pipelines
7. ✅ **JSON alias added**: `--json` flag as shorthand for `--format json` (common muscle memory)

## Entry Point

```bash
# Main entry point
python -m scripts.cdp.cli [OPTIONS] COMMAND [ARGS]

# Or via installed skill (future)
browser-debugger [OPTIONS] COMMAND [ARGS]
```

## Global Options

Available for all commands:

```bash
--chrome-host HOST          # Chrome debugging host (default: localhost)
--chrome-port PORT          # Chrome debugging port (default: 9222)
--timeout SECONDS           # Command timeout in seconds (default: 30.0)
--log-level LEVEL           # Logging level: DEBUG|INFO|WARNING|ERROR (default: INFO)
--format FORMAT             # Output format: json|text|raw (default: json)
--json                      # Shorthand for --format json (common muscle memory)
--quiet                     # Suppress non-essential output
--verbose                   # Enable verbose logging (equivalent to --log-level DEBUG)
--config FILE               # Load configuration from file
```

**Flag Semantics**:
- `--format`: Controls **output format** (json/text/raw) for stdout
- Subcommand `--output FILE`: Controls **output destination** (file path)
- `--json`: Alias for `--format json` (common CLI pattern)
- These flags are independent and can be combined: `--format json --output /tmp/result.json`

## Command Matrix

### 1. `session` - Session Management

Manage Chrome debugging sessions and target discovery.

#### `session list`

List available CDP targets (pages, workers, extensions).

```bash
python -m scripts.cdp.cli session list [OPTIONS]

Options:
  --type TYPE         # Filter by target type: page|worker|iframe|other
  --url PATTERN       # Filter by URL regex pattern
  --format FORMAT     # Output format: json|table (default: json)

Output (JSON):
[
  {
    "id": "E4B3C...",
    "type": "page",
    "title": "Example Domain",
    "url": "https://example.com",
    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/E4B3C..."
  }
]

Output (table):
ID       TYPE   TITLE            URL
E4B3C... page   Example Domain   https://example.com
```

**Examples**:
```bash
# List all page targets
python -m scripts.cdp.cli session list --type page

# Find target by URL
python -m scripts.cdp.cli session list --url "localhost:3000"

# Human-readable table
python -m scripts.cdp.cli session list --format table
```

#### `session info`

Show detailed information about a specific target.

```bash
python -m scripts.cdp.cli session info TARGET_ID [OPTIONS]

Options:
  --include-capabilities  # Show supported CDP domains

Output (JSON):
{
  "id": "E4B3C...",
  "type": "page",
  "title": "Example Domain",
  "url": "https://example.com",
  "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/E4B3C...",
  "capabilities": ["Console", "Network", "Runtime", "DOM"]
}
```

### 2. `eval` - JavaScript Evaluation

Execute JavaScript expressions in the page context.

```bash
python -m scripts.cdp.cli eval EXPRESSION [OPTIONS]

Options:
  --target TARGET_ID      # Explicit target ID (mutually exclusive with --url)
  --url PATTERN           # Connect to first target matching URL pattern (mutually exclusive with --target)
  --await                 # Await promise result
  --return-by-value       # Return result as JSON value (default: true)
  --context-id ID         # Execution context ID (default: main frame)

Arguments:
  EXPRESSION              # JavaScript expression to evaluate

Output (JSON):
{
  "type": "number",
  "value": 2
}

Output (text):
2
```

**Target Selection**:
- Exactly one of `--target` or `--url` must be provided
- Enforced via `argparse.add_mutually_exclusive_group()`
- Missing both: Error with hint to provide target selection
- Providing both: Error indicating mutual exclusion

**Examples**:
```bash
# Simple expression
python -m scripts.cdp.cli eval "1 + 1"

# Target by URL
python -m scripts.cdp.cli eval "document.title" --url "example.com"

# Await async result
python -m scripts.cdp.cli eval "fetch('/api/data').then(r => r.json())" --await

# Complex expression with quoting
python -m scripts.cdp.cli eval 'document.querySelectorAll("input").length'
```

### 3. `dom` - DOM Operations

Extract and inspect DOM structure.

#### `dom dump`

Extract full DOM as HTML.

```bash
python -m scripts.cdp.cli dom dump [OPTIONS]

Options:
  --target TARGET_ID      # Explicit target ID (mutually exclusive with --url)
  --url PATTERN           # Connect to first target matching URL pattern (mutually exclusive with --target)
  --output FILE           # Write to file (default: stdout)
  --selector SELECTOR     # Extract specific element by CSS selector
  --wait-for SELECTOR     # Wait for element to exist before dumping (timeout: 30s)
  --pretty                # Pretty-print HTML (requires html5lib)

Output:
<!DOCTYPE html><html>...</html>
```

**Wait Behavior**:
- `--wait-for SELECTOR`: Blocks until element matching CSS selector exists
- Uses CDP `Runtime.evaluate` with polling (100ms intervals, 30s timeout)
- Useful for post-form interactions where content loads dynamically
- Example: `--wait-for "div.result"` waits for result div to appear

**Examples**:
```bash
# Dump full DOM
python -m scripts.cdp.cli dom dump --url "example.com" > page.html

# Extract specific element
python -m scripts.cdp.cli dom dump --selector "form#login" --url "localhost:3000"

# Wait for dynamic content before dumping
python -m scripts.cdp.cli dom dump --wait-for "div.results" --url "example.com"

# Pretty-printed output
python -m scripts.cdp.cli dom dump --pretty --output /tmp/page.html
```

#### `dom query`

Query DOM elements and extract properties.

```bash
python -m scripts.cdp.cli dom query SELECTOR [OPTIONS]

Options:
  --target TARGET_ID      # Explicit target ID (or use --url)
  --url PATTERN           # Connect to first target matching URL pattern
  --property PROP         # Extract specific property (e.g., value, checked)
  --all                   # Return all matching elements (default: first)

Output (JSON):
[
  {
    "tagName": "input",
    "id": "username",
    "type": "text",
    "value": "alice@example.com"
  }
]
```

**Examples**:
```bash
# Find all form inputs
python -m scripts.cdp.cli dom query "form input" --all

# Extract input value
python -m scripts.cdp.cli dom query "#username" --property value

# Complex selector
python -m scripts.cdp.cli dom query "button[type='submit']:not([disabled])"
```

### 4. `console` - Console Monitoring

Stream console messages from the page.

```bash
python -m scripts.cdp.cli console stream [OPTIONS]

Options:
  --target TARGET_ID      # Explicit target ID (or use --url)
  --url PATTERN           # Connect to first target matching URL pattern
  --duration SECONDS      # Stream duration (default: 60)
  --level LEVEL           # Filter by level: log|info|warning|error (multiple allowed)
  --output FILE           # Write to file (default: stdout)
  --format FORMAT         # Output format: json|text (default: json)

Output (JSON - one per line):
{"timestamp": 1234567890.123, "level": "log", "text": "User logged in", "source": "console-api"}
{"timestamp": 1234567890.456, "level": "error", "text": "Network timeout", "source": "network"}

Output (text):
[12:34:56.123] [LOG] User logged in
[12:34:56.456] [ERROR] Network timeout
```

**Examples**:
```bash
# Stream all console messages for 30 seconds
python -m scripts.cdp.cli console stream --duration 30 --url "localhost:3000"

# Filter errors only
python -m scripts.cdp.cli console stream --level error --duration 60

# Text output
python -m scripts.cdp.cli console stream --format text --output /tmp/console.log
```

### 5. `network` - Network Monitoring

Record and analyze network activity.

```bash
python -m scripts.cdp.cli network record [OPTIONS]

Options:
  --target TARGET_ID      # Explicit target ID (mutually exclusive with --url)
  --url PATTERN           # Connect to first target matching URL pattern (mutually exclusive with --target)
  --duration SECONDS      # Recording duration (default: 60)
  --output FILE           # Write to file (default: stdout)
  --include-bodies        # Capture response bodies (default: off, see warning below)
  --max-body-size BYTES   # Max response body size to capture (default: 1MB, prevents memory explosion)
  --filter-url PATTERN    # Filter requests by URL regex
  --filter-status CODE    # Filter by HTTP status code (e.g., 404, 5xx)
  --format FORMAT         # Output format: json|har (default: json)

Output (JSON):
[
  {
    "requestId": "ABC123",
    "url": "https://example.com/api/data",
    "method": "GET",
    "status": 200,
    "mimeType": "application/json",
    "requestHeaders": {...},
    "responseHeaders": {...},
    "body": "..." # Only if --include-bodies
  }
]
```

**Response Body Capture Warning**:
- `--include-bodies` is **OFF by default** to prevent memory exhaustion
- When enabled, only captures bodies ≤ `--max-body-size` (default: 1MB)
- Large responses (images, videos, large JSON) are truncated with warning
- Help text includes explicit warning about size impact
- Recommendation: Use `--filter-url "/api/"` to limit scope when capturing bodies

**Examples**:
```bash
# Record all network activity for 30 seconds
python -m scripts.cdp.cli network record --duration 30 --url "localhost:3000"

# Capture failed requests
python -m scripts.cdp.cli network record --filter-status 5xx --duration 60

# Export as HAR (Chrome DevTools compatible)
python -m scripts.cdp.cli network record --format har --output trace.har

# Include response bodies for API debugging
python -m scripts.cdp.cli network record --include-bodies --filter-url "/api/"
```

### 6. `orchestrate` - High-Level Workflows

Execute pre-defined multi-step debugging workflows.

```bash
python -m scripts.cdp.cli orchestrate WORKFLOW URL [OPTIONS]

Workflows:
  headless              # Automated capture: DOM + console + network
  interactive           # Interactive session: headed Chrome, manual control

Options:
  --duration SECONDS    # Workflow duration (default: 60)
  --output-dir DIR      # Output directory for artifacts (default: /tmp)
  --include-console     # Enable console monitoring
  --include-network     # Enable network monitoring
  --wait-for SELECTOR   # Wait for element before starting capture (timeout: 30s)
  --idle SECONDS        # Idle detection timeout (default: 5)
  --summary FORMAT      # Generate summary: text|json|both (default: both)

Output (success):
{
  "workflow": "headless",
  "url": "https://example.com",
  "status": "completed",
  "artifacts": {
    "dom": "/tmp/dom-1234567890.html",
    "console": "/tmp/console-1234567890.jsonl",
    "network": "/tmp/network-1234567890.json",
    "summary": "/tmp/summary-1234567890.txt"
  },
  "stats": {
    "consoleMessages": 42,
    "networkRequests": 15,
    "errors": 3
  }
}

Output (Chrome launch failure):
{
  "workflow": "headless",
  "url": "https://example.com",
  "status": "failed",
  "error": "Failed to launch Chrome: port 9222 already in use",
  "artifacts": {},  # Empty - no artifacts created
  "recovery_hint": "Kill existing Chrome process: pkill -f 'chrome.*9222'"
}

Output (partial failure - Chrome crashed mid-workflow):
{
  "workflow": "headless",
  "url": "https://example.com",
  "status": "partial",
  "error": "Chrome connection lost after 30s",
  "artifacts": {
    "console": "/tmp/console-1234567890.jsonl",  # Partial console log
    "network": "/tmp/network-1234567890.json",   # Partial network trace
    "summary": "/tmp/summary-1234567890.txt"     # Summary of captured data
  },
  "stats": {
    "consoleMessages": 12,
    "networkRequests": 5,
    "errors": 1
  },
  "recovery_hint": "Check Chrome logs for crash details"
}
```

**Exit Codes for Orchestrate**:
- `0`: Workflow completed successfully, all artifacts created
- `2`: Chrome launch failed (no artifacts created)
- `6`: Chrome crashed mid-workflow (partial artifacts saved)
- `4`: Timeout waiting for `--wait-for` selector (no artifacts created)

**Partial Failure Handling**:
- All artifacts saved before failure are preserved and paths returned in JSON
- Summary includes analysis of partial data
- Logs indicate at what point failure occurred
- Artifact files include timestamp to prevent overwrites on retry

**Examples**:
```bash
# Automated headless capture
python -m scripts.cdp.cli orchestrate headless https://example.com \
  --include-console --include-network --duration 30

# Interactive headed session
python -m scripts.cdp.cli orchestrate interactive http://localhost:3000/signin \
  --include-console --output-dir /tmp/debug-session

# Custom idle detection
python -m scripts.cdp.cli orchestrate headless https://example.com \
  --idle 10 --summary json
```

### 7. `query` - Ad-Hoc CDP Commands

Execute arbitrary CDP commands (power users).

```bash
python -m scripts.cdp.cli query METHOD [PARAMS] [OPTIONS]

Options:
  --target TARGET_ID      # Explicit target ID (mutually exclusive with --url)
  --url PATTERN           # Connect to first target matching URL pattern (mutually exclusive with --target)
  --params JSON           # JSON-encoded parameters (alternative to positional PARAMS)
  --params-file FILE      # Read parameters from file (use '@file.json' or '-' for stdin)

Arguments:
  METHOD                  # CDP method name (e.g., Runtime.evaluate)
  PARAMS                  # JSON-encoded parameters (optional, use if not using --params or --params-file)

Output (JSON):
{
  "result": {...}
}
```

**Examples**:
```bash
# Simple command
python -m scripts.cdp.cli query Runtime.evaluate '{"expression": "window.location.href"}'

# Using --params flag
python -m scripts.cdp.cli query Runtime.evaluate \
  --params '{"expression": "document.title", "returnByValue": true}'

# Large payload from file
python -m scripts.cdp.cli query Runtime.evaluate --params-file params.json

# Read from stdin (useful for piping)
echo '{"expression": "document.title"}' | python -m scripts.cdp.cli query Runtime.evaluate --params-file -

# Complex command
python -m scripts.cdp.cli query Network.getResponseBody \
  '{"requestId": "ABC123"}' --url "example.com"
```

**Parameter Input Precedence** (highest to lowest):
1. `--params-file FILE` (explicit file or stdin via `-`)
2. `--params JSON` (inline JSON string)
3. Positional `PARAMS` argument

**Stdin Support**:
- Use `--params-file -` to read parameters from stdin
- Enables piping: `cat params.json | python -m scripts.cdp.cli query ... --params-file -`
- Useful for advanced users building CDP pipelines

## Logging Output

### Log Levels

| Level | Purpose | Example Output |
|-------|---------|----------------|
| DEBUG | Verbose debugging | `[DEBUG] Sending CDP command: Runtime.evaluate` |
| INFO | Progress updates | `[INFO] Connected to ws://localhost:9222/devtools/page/E4B3C...` |
| WARNING | Recoverable issues | `[WARNING] Reconnecting after connection loss (attempt 1/3)` |
| ERROR | Fatal errors | `[ERROR] Failed to connect: Chrome not running on port 9222` |

### Log Format

**Text output** (--output text or --format text):
```
[2025-10-24 12:34:56] [INFO] Connected to target: Example Domain (https://example.com)
[2025-10-24 12:34:57] [DEBUG] Executing command: Runtime.evaluate
[2025-10-24 12:34:58] [INFO] Command completed in 0.123s
```

**JSON output** (--output json):
```json
{
  "timestamp": "2025-10-24T12:34:56.789Z",
  "level": "INFO",
  "message": "Connected to target: Example Domain",
  "context": {
    "target_id": "E4B3C...",
    "url": "https://example.com"
  }
}
```

### Quiet Mode

`--quiet`: Suppresses INFO and DEBUG logs, only shows command output and errors.

```bash
# Only show DOM output, no progress logs
python -m scripts.cdp.cli dom dump --quiet --url "example.com" > page.html
```

### Verbose Mode

`--verbose`: Enables DEBUG-level logging, shows all CDP messages.

```bash
# Show all CDP traffic
python -m scripts.cdp.cli eval "1+1" --verbose
```

Output:
```
[DEBUG] Loading configuration from environment
[DEBUG] Connecting to Chrome at localhost:9222
[DEBUG] Fetching targets from http://localhost:9222/json
[DEBUG] Found 3 targets: 2 pages, 1 worker
[DEBUG] Connecting to ws://localhost:9222/devtools/page/E4B3C...
[DEBUG] WebSocket connected
[DEBUG] Sending CDP command: Runtime.evaluate
[DEBUG] Sent: {"id": 1, "method": "Runtime.evaluate", "params": {"expression": "1+1", "returnByValue": true}}
[DEBUG] Received: {"id": 1, "result": {"type": "number", "value": 2}}
[INFO] Command completed in 0.045s
2
```

## Error Handling

### Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success | Command completed successfully |
| 1 | General error | Unknown command or invalid arguments |
| 2 | Connection error | Chrome not running or unreachable |
| 3 | Target not found | No page matching URL filter |
| 4 | Command timeout | CDP command exceeded timeout |
| 5 | Command error | CDP returned error response |
| 6 | Context destroyed | Page navigated during operation |

### Error Output Format

**Text format**:
```
ERROR: Failed to connect to Chrome
  Reason: Connection refused to localhost:9222
  Recovery: Start Chrome with --remote-debugging-port=9222
  Command: google-chrome --headless=new --remote-debugging-port=9222
```

**JSON format**:
```json
{
  "error": {
    "type": "ConnectionError",
    "message": "Failed to connect to Chrome",
    "details": {
      "reason": "Connection refused to localhost:9222"
    },
    "recovery": {
      "hint": "Start Chrome with --remote-debugging-port=9222",
      "command": "google-chrome --headless=new --remote-debugging-port=9222"
    }
  }
}
```

## Configuration

### Precedence (highest to lowest)

1. Command-line flags (`--chrome-port 9222`)
2. Environment variables (`CDP_CHROME_PORT=9222`)
3. Config file (`~/.cdprc` or via `--config`)
4. Built-in defaults

### Environment Variables

```bash
# Connection settings
CDP_CHROME_HOST=localhost
CDP_CHROME_PORT=9222

# Timeout settings
CDP_TIMEOUT=30.0
CDP_MAX_RETRIES=3
CDP_RETRY_DELAY=1.0

# Logging
CDP_LOG_LEVEL=INFO
CDP_LOG_FORMAT=json

# Output
CDP_OUTPUT_FORMAT=json
CDP_OUTPUT_DIR=/tmp
```

### Config File Format (.cdprc)

```ini
[connection]
chrome_host = localhost
chrome_port = 9222
timeout = 30.0
max_retries = 3
retry_delay = 1.0

[logging]
level = INFO
format = json

[output]
format = json
output_dir = /tmp
```

**Load via `--config`**:
```bash
python -m scripts.cdp.cli --config ~/.cdprc dom dump --url "example.com"
```

## Integration with Existing Scripts

### Migration Path

**Current** (Bash orchestrator):
```bash
./scripts/core/debug-orchestrator.sh "https://example.com" 15 /tmp/output.log \
  --include-console --summary=both
```

**New** (Python CLI):
```bash
python -m scripts.cdp.cli orchestrate headless https://example.com \
  --duration 15 --include-console --include-network \
  --output-dir /tmp --summary both
```

**Compatibility Wrapper** (during transition):
```bash
# scripts/core/debug-orchestrator.sh becomes a thin wrapper
#!/usr/bin/env bash
exec python -m scripts.cdp.cli orchestrate headless "$@"
```

## Agent Ergonomics

### Single Command Workflows

**Goal**: Agents should accomplish common tasks with a single command.

✅ **Good (single command)**:
```bash
# Extract DOM in one command
python -m scripts.cdp.cli dom dump --url "example.com" > page.html

# Stream console for debugging
python -m scripts.cdp.cli console stream --url "localhost:3000" --level error
```

❌ **Bad (multi-step)**:
```bash
# Don't require agents to manually discover targets
targets=$(python -m scripts.cdp.cli session list)
target_id=$(echo "$targets" | jq -r '.[0].id')
python -m scripts.cdp.cli dom dump --target "$target_id"
```

### Composability for Advanced Scenarios

**Goal**: Power users can compose commands via pipes and scripts.

```bash
# Find target ID and extract DOM
python -m scripts.cdp.cli session list --url "example.com" \
  | jq -r '.[0].id' \
  | xargs -I {} python -m scripts.cdp.cli dom dump --target {}

# Filter console errors and count by source
python -m scripts.cdp.cli console stream --level error --format json \
  | jq -r '.source' \
  | sort | uniq -c

# Extract all form inputs and values
python -m scripts.cdp.cli dom query "form input" --all \
  | jq '[.[] | {id, value}]'
```

## Help System

### Command Help

```bash
# Show all commands
python -m scripts.cdp.cli --help

# Show command-specific help
python -m scripts.cdp.cli dom dump --help

# Show examples
python -m scripts.cdp.cli dom dump --examples
```

### Help Output Format

```
Usage: python -m scripts.cdp.cli dom dump [OPTIONS]

Extract DOM as HTML from a Chrome page.

Options:
  --target TARGET_ID      Explicit target ID (mutually exclusive with --url)
  --url PATTERN           Connect to first target matching URL pattern
  --output FILE           Write to file (default: stdout)
  --selector SELECTOR     Extract specific element by CSS selector
  --pretty                Pretty-print HTML (requires html5lib)
  -h, --help              Show this message and exit

Examples:
  # Dump full DOM
  python -m scripts.cdp.cli dom dump --url "example.com" > page.html

  # Extract specific element
  python -m scripts.cdp.cli dom dump --selector "form#login" --url "localhost:3000"

See also: dom query, eval, session list
```

## Implementation Architecture

### CLI Module Structure

```
scripts/cdp/
├── __init__.py
├── cli.py                 # Main entry point, argparse setup
├── commands/
│   ├── __init__.py
│   ├── session.py         # session list, session info
│   ├── eval.py            # eval
│   ├── dom.py             # dom dump, dom query
│   ├── console.py         # console stream
│   ├── network.py         # network record
│   ├── orchestrate.py     # orchestrate headless, orchestrate interactive
│   └── query.py           # query (ad-hoc CDP commands)
├── connection.py          # CDPConnection, CDPSession (from previous design)
├── config.py              # Configuration loading and validation
├── output.py              # Output formatting (JSON, text, table)
└── util/
    ├── logging.py         # Structured logging setup
    ├── errors.py          # Error handling and recovery hints
    └── validators.py      # Input validation helpers
```

### Argparse Structure

```python
# cli.py
import argparse
from scripts.cdp.commands import session, eval_cmd, dom, console, network, orchestrate, query

def main():
    parser = argparse.ArgumentParser(
        prog="python -m scripts.cdp.cli",
        description="Chrome DevTools Protocol CLI"
    )

    # Global options
    parser.add_argument("--chrome-host", default="localhost")
    parser.add_argument("--chrome-port", type=int, default=9222)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    parser.add_argument("--output", choices=["json", "text", "raw"], default="json")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--config", type=str)

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", required=True)

    # session list, session info
    session.setup_parser(subparsers)

    # eval
    eval_cmd.setup_parser(subparsers)

    # dom dump, dom query
    dom.setup_parser(subparsers)

    # console stream
    console.setup_parser(subparsers)

    # network record
    network.setup_parser(subparsers)

    # orchestrate headless, orchestrate interactive
    orchestrate.setup_parser(subparsers)

    # query
    query.setup_parser(subparsers)

    args = parser.parse_args()

    # Execute command
    # Each command module has a run(args) function
    # ...
```

### Command Implementation Pattern

```python
# commands/dom.py
def setup_parser(subparsers):
    """Add dom subcommands to argparse"""
    dom_parser = subparsers.add_parser("dom", help="DOM operations")
    dom_subparsers = dom_parser.add_subparsers(dest="dom_command", required=True)

    # dom dump
    dump_parser = dom_subparsers.add_parser("dump", help="Extract DOM as HTML")

    # Mutual exclusion: --target OR --url (but not both, not neither)
    target_group = dump_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--target", type=str, help="Explicit target ID")
    target_group.add_argument("--url", type=str, help="Connect to first target matching URL pattern")

    dump_parser.add_argument("--output", type=str, help="Write to file (default: stdout)")
    dump_parser.add_argument("--selector", type=str, help="Extract specific element by CSS selector")
    dump_parser.add_argument("--wait-for", type=str, dest="wait_for", help="Wait for element to exist before dumping")
    dump_parser.add_argument("--pretty", action="store_true", help="Pretty-print HTML")

    # dom query
    query_parser = dom_subparsers.add_parser("query", help="Query DOM elements")
    query_parser.add_argument("selector", type=str, help="CSS selector to query")

    # Mutual exclusion for target selection
    target_group = query_parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--target", type=str, help="Explicit target ID")
    target_group.add_argument("--url", type=str, help="Connect to first target matching URL pattern")

    query_parser.add_argument("--property", type=str, help="Extract specific property")
    query_parser.add_argument("--all", action="store_true", help="Return all matching elements")

async def run(args):
    """Execute dom command"""
    if args.dom_command == "dump":
        await run_dump(args)
    elif args.dom_command == "query":
        await run_query(args)

async def run_dump(args):
    """Implement dom dump logic"""
    from scripts.cdp.connection import CDPSession
    from scripts.cdp.output import format_output

    session = CDPSession(chrome_port=args.chrome_port)

    # Connect to target
    if args.url:
        conn = await session.connect_to_page(url_filter=args.url)
    elif args.target:
        conn = await session.connect_to_page(page_id=args.target)
    else:
        raise ValueError("Must specify --url or --target")

    # Extract DOM
    result = await conn.execute("Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True
    })

    html = result["result"]["value"]

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(html)
    else:
        print(html)
```

## Testing Strategy

### CLI Integration Tests

```python
import subprocess
import json

def test_dom_dump_cli():
    """Test dom dump command via subprocess"""
    result = subprocess.run(
        ["python", "-m", "scripts.cdp.cli", "dom", "dump", "--url", "example.com"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "<html" in result.stdout

def test_eval_cli():
    """Test eval command via subprocess"""
    result = subprocess.run(
        ["python", "-m", "scripts.cdp.cli", "eval", "1+1", "--output", "json"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["value"] == 2
```

### Help Text Validation

```python
def test_help_output():
    """Ensure all commands have help text"""
    commands = ["session", "eval", "dom", "console", "network", "orchestrate", "query"]
    for cmd in commands:
        result = subprocess.run(
            ["python", "-m", "scripts.cdp.cli", cmd, "--help"],
            capture_output=True
        )
        assert result.returncode == 0
        assert b"Usage:" in result.stdout
```

## Open Questions & Decisions

### 1. Selector Syntax for `dom query`

**Decision Needed**: Support only CSS selectors or also XPath?

**Option A**: CSS selectors only (simpler, more common)
**Option B**: Support both via `--selector-type css|xpath`

**Recommendation**: Option A initially, add XPath if requested

### 2. Network Response Body Capture

**Decision Needed**: How to control which response bodies are captured?

**Option A**: `--include-bodies` flag (all or nothing)
**Option B**: `--include-bodies-filter PATTERN` (regex filter by URL)

**Recommendation**: Option B for flexibility (matches current `filter-flag-guide.md`)

### 3. Orchestrate Workflow Extensibility

**Decision Needed**: Should users be able to define custom workflows?

**Option A**: Hardcoded workflows (headless, interactive)
**Option B**: Support custom workflow scripts (e.g., YAML definitions)

**Recommendation**: Option A for MVP, Option B as future enhancement

## Performance Considerations

### Subprocess Overhead

- Each CLI invocation spawns a new Python process (~100-200ms overhead)
- **Mitigation**: For repeated operations, use `orchestrate` workflow or import as library

### JSON Parsing Large DOM

- Large DOM dumps (>10MB) may be slow to serialize/deserialize
- **Mitigation**: Provide `--raw` output format that bypasses JSON encoding

### Network Recording Memory Usage

- Capturing response bodies can consume significant memory
- **Mitigation**: Document recommended filters in help text, add memory warnings

## Documentation Requirements

### User-Facing Docs

1. **Quick Start Guide**: Common workflows with examples
2. **Command Reference**: Auto-generated from argparse help text
3. **Configuration Guide**: Environment variables and config file format
4. **Troubleshooting**: Common errors and recovery steps

### Developer Docs

1. **Adding New Commands**: Template for command modules
2. **Testing Guidelines**: How to write CLI integration tests
3. **Output Formatting**: How to implement custom output formats

## Migration Timeline

### Phase 1: Core Commands (Week 1-2)
- Implement `session list`, `eval`, `dom dump`
- Basic logging and error handling
- Integration tests with real Chrome

### Phase 2: Monitoring Commands (Week 3)
- Implement `console stream`, `network record`
- Event subscription system
- Performance benchmarks

### Phase 3: Orchestration (Week 4)
- Implement `orchestrate headless`, `orchestrate interactive`
- Compatibility wrapper for existing shell scripts
- Migration guide for users

### Phase 4: Polish (Week 5)
- Help text and examples
- Configuration file support
- Documentation and tutorials
