# CDP CLI Examples

Practical examples for all browser-debugger CDP commands.

## Installation

```bash
# Development mode (from repository root)
pip install -e .

# Production mode
pip install browser-debugger
```

## Configuration

The CDP CLI supports multiple configuration sources with precedence:

**CLI flags > Environment variables > Config file > Defaults**

### Config File (~/.cdprc)

```json
{
  "chrome_port": 9222,
  "timeout": 30,
  "log_level": "INFO",
  "log_format": "text"
}
```

### Environment Variables

```bash
export CDP_CHROME_PORT=9333
export CDP_TIMEOUT=60
export CDP_LOG_LEVEL=DEBUG
export CDP_LOG_FORMAT=json
```

## Examples by Command

- [Session Management](./session-examples.md) - List and inspect Chrome targets
- [JavaScript Evaluation](./eval-examples.md) - Execute JavaScript in pages
- [DOM Extraction](./dom-examples.md) - Extract and save page DOM
- [Console Monitoring](./console-examples.md) - Stream console logs
- [Network Recording](./network-examples.md) - Capture network traffic
- [Orchestration](./orchestrate-examples.md) - Automated debugging workflows
- [Query](./query-examples.md) - Execute arbitrary CDP commands

## Quick Start

### 1. List Available Targets

```bash
cdp session list
```

Output (JSON):
```json
[
  {
    "id": "E7B3...",
    "type": "page",
    "title": "Example Domain",
    "url": "https://example.com",
    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/E7B3..."
  }
]
```

### 2. Execute JavaScript

```bash
cdp eval --url example.com "document.title"
```

Output (JSON):
```json
{
  "type": "string",
  "value": "Example Domain"
}
```

### 3. Extract DOM

```bash
cdp dom dump --url example.com --output example-dom.html
```

Output:
```
DOM saved to: example-dom.html (1234 bytes)
```

### 4. Monitor Console (30 seconds)

```bash
cdp console stream --url example.com --duration 30
```

Output (JSONL):
```json
{"timestamp": "2025-10-25T00:00:00Z", "level": "log", "text": "Page loaded"}
{"timestamp": "2025-10-25T00:00:01Z", "level": "warn", "text": "Resource missing"}
```

### 5. Record Network Activity

```bash
cdp network record --url example.com --duration 30 --include-bodies
```

Output (JSONL):
```json
{"type": "request", "url": "https://example.com/", "method": "GET"}
{"type": "response", "url": "https://example.com/", "status": 200, "size": 1234}
```

### 6. Automated Workflow (Headless)

```bash
cdp orchestrate headless https://example.com --include-console --summary=both
```

Output:
- Console logs saved to `/tmp/console-*.jsonl`
- Network logs saved to `/tmp/network-*.jsonl`
- DOM saved to `/tmp/dom-*.html`
- Summary generated in text and JSON formats

## Global Options

All commands support these global options:

```bash
--chrome-host HOST       # Chrome host (default: localhost)
--chrome-port PORT       # Chrome debugging port (default: 9222)
--timeout SECONDS        # Command timeout (default: 30.0)
--format {json|text}     # Output format (default: json)
--log-level LEVEL        # Logging level (debug|info|warning|error)
--quiet                  # Suppress non-essential output
--verbose                # Enable debug output
```

## Output Formats

### JSON (machine-parseable, default)

```bash
cdp session list --format json
```

### Text (human-readable)

```bash
cdp session list --format text
```

### Quiet Mode (errors only)

```bash
cdp dom dump --url example.com --output dom.html --quiet
```

### Verbose Mode (debug logging)

```bash
cdp orchestrate headless https://example.com --verbose
```

## Troubleshooting

### Chrome Not Running

```bash
# Start Chrome with remote debugging
chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug

# Or use headed mode orchestration (auto-launches Chrome)
cdp orchestrate headed https://example.com
```

### Port Conflicts

```bash
# Use custom port
cdp session list --chrome-port 9333
```

### Timeout Issues

```bash
# Increase timeout for slow pages
cdp eval --url slow-site.com "document.title" --timeout 60
```

## See Also

- [Chrome DevTools Protocol Documentation](https://chromedevtools.github.io/devtools-protocol/)
- [Browser Debugger Repository](https://github.com/anthropics/claude-code-skills)
- [Troubleshooting Guide](../guides/troubleshooting.md)
