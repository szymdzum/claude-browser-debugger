# Bash to Python CLI Migration Guide

**Status**: The Bash orchestrator (`scripts/legacy/debug-orchestrator.sh`) is **DEPRECATED** as of the Python CDP migration (User Story 8).

**Action Required**: Migrate all workflows to the Python CDP CLI.

## Quick Reference

### Installation

```bash
# Install the Python CDP package
pip3 install -e .

# Or use directly without installation
python3 -m scripts.cdp.cli.main --help
```

### Command Mapping

| Old Bash Command | New Python Command |
|------------------|-------------------|
| `./scripts/legacy/debug-orchestrator.sh <URL>` | `python3 -m scripts.cdp.cli.main orchestrate <URL>` |
| `./scripts/legacy/debug-orchestrator.sh <URL> --mode=headed` | `python3 -m scripts.cdp.cli.main orchestrate <URL> --mode headed` |
| `./scripts/legacy/debug-orchestrator.sh <URL> --include-console` | `python3 -m scripts.cdp.cli.main orchestrate <URL> --console` |
| `./scripts/legacy/debug-orchestrator.sh <URL> --summary=both` | `python3 -m scripts.cdp.cli.main orchestrate <URL> --summary both` |
| `./scripts/collectors/cdp-console.py <PAGE_ID>` | `python3 -m scripts.cdp.cli.main console --target <PAGE_ID>` |
| `./scripts/collectors/cdp-network.py <PAGE_ID>` | `python3 -m scripts.cdp.cli.main network --target <PAGE_ID>` |

## Detailed Migration Examples

### Example 1: Headless Website Debugging

**Old Bash approach:**
```bash
./scripts/legacy/debug-orchestrator.sh "https://example.com" 15 /tmp/debug.log \
  --include-console --summary=both
```

**New Python approach:**
```bash
python3 -m scripts.cdp.cli.main orchestrate "https://example.com" \
  --duration 15 \
  --output /tmp/debug.log \
  --console \
  --summary both
```

### Example 2: Headed Interactive Debugging

**Old Bash approach:**
```bash
./scripts/legacy/debug-orchestrator.sh "http://localhost:3000/signin" \
  --mode=headed --include-console
```

**New Python approach:**
```bash
python3 -m scripts.cdp.cli.main orchestrate "http://localhost:3000/signin" \
  --mode headed \
  --console
```

### Example 3: Console Monitoring Only

**Old Bash approach:**
```bash
# Start Chrome manually
chrome --headless=new --remote-debugging-port=9222 "https://example.com" &
sleep 2

# Get page ID
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)

# Run console collector
python3 scripts/legacy/collectors/cdp-console.py "$PAGE_ID"
```

**New Python approach:**
```bash
# All-in-one command
python3 -m scripts.cdp.cli.main console "https://example.com" \
  --duration 60 \
  --output /tmp/console.jsonl
```

### Example 4: Network Traffic Capture

**Old Bash approach:**
```bash
# Start Chrome manually
chrome --headless=new --remote-debugging-port=9222 "https://example.com" &
sleep 2

# Get page ID
PAGE_ID=$(curl -s http://localhost:9222/json | jq -r '.[] | select(.type == "page") | .id' | head -1)

# Run network collector
python3 scripts/legacy/collectors/cdp-network.py "$PAGE_ID"
```

**New Python approach:**
```bash
# All-in-one command with response body capture
python3 -m scripts.cdp.cli.main network "https://example.com" \
  --duration 60 \
  --output /tmp/network.jsonl \
  --include-bodies
```

### Example 5: DOM Extraction

**Old Bash approach:**
```bash
# Via orchestrator
./scripts/legacy/debug-orchestrator.sh "https://example.com" 5 /tmp/out.log

# Manual extraction
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.documentElement.outerHTML","returnByValue":true}}' \
  | websocat -n1 -B 1048576 "$WS_URL" \
  | jq -r '.result.result.value' > /tmp/dom.html
```

**New Python approach:**
```bash
# Direct DOM dump
python3 -m scripts.cdp.cli.main dom "https://example.com" \
  --output /tmp/dom.html \
  --wait-for "body.loaded"
```

### Example 6: JavaScript Evaluation

**Old Bash approach:**
```bash
# Manual via websocat
WS_URL=$(curl -s http://localhost:9222/json | jq -r '.[0].webSocketDebuggerUrl')
echo '{"id":1,"method":"Runtime.evaluate","params":{"expression":"document.title","returnByValue":true}}' \
  | websocat -n1 "$WS_URL" \
  | jq -r '.result.result.value'
```

**New Python approach:**
```bash
# Direct eval command
python3 -m scripts.cdp.cli.main eval "https://example.com" \
  --expression "document.title" \
  --format text
```

### Example 7: Target Discovery

**Old Bash approach:**
```bash
# Manual HTTP request
curl -s http://localhost:9222/json | jq '.[] | {id, title, url, type}'
```

**New Python approach:**
```bash
# Built-in session command
python3 -m scripts.cdp.cli.main session list --format table

# Or filter by type
python3 -m scripts.cdp.cli.main session list --type page --format json
```

## New Features in Python CLI

The Python CLI provides several improvements over the Bash orchestrator:

### 1. Unified Interface
All debugging operations available through a single command with subcommands:
```bash
python3 -m scripts.cdp.cli.main <subcommand> [options]
```

Subcommands:
- `session` - List and manage CDP targets
- `eval` - Execute JavaScript expressions
- `dom` - Extract DOM snapshots
- `console` - Stream console logs
- `network` - Capture network traffic
- `orchestrate` - Full debugging workflow
- `query` - Execute arbitrary CDP commands

### 2. Automatic Chrome Management
No need to manually start Chrome or manage processes:
```bash
# Python CLI handles Chrome lifecycle automatically
python3 -m scripts.cdp.cli.main orchestrate "https://example.com"
```

### 3. Configuration File Support
Store default settings in `~/.cdprc`:
```json
{
  "chrome_host": "localhost",
  "chrome_port": 9222,
  "timeout": 30,
  "format": "json"
}
```

### 4. Structured Logging
Choose output format based on use case:
```bash
# JSON for programmatic consumption
python3 -m scripts.cdp.cli.main --format json orchestrate "https://example.com"

# Text for human readability
python3 -m scripts.cdp.cli.main --format text orchestrate "https://example.com"
```

### 5. Better Error Handling
Structured exceptions with recovery hints:
```bash
$ python3 -m scripts.cdp.cli.main eval "https://example.com" --expression "invalid(("
Error: Command 'Runtime.evaluate' failed
Reason: SyntaxError: Unexpected token '('
Recovery: Check JavaScript syntax and try again
```

### 6. Automatic Reconnection
Built-in Chrome crash recovery with domain replay:
```bash
# If Chrome crashes, Python CLI automatically reconnects and restores monitoring state
python3 -m scripts.cdp.cli.main console "https://example.com" --duration 300
```

## Breaking Changes

### 1. Flag Syntax
- Old: `--mode=headed` → New: `--mode headed` (space instead of `=`)
- Old: `--include-console` → New: `--console` (shorter flag)
- Old: `--summary=both` → New: `--summary both`

### 2. Output Format
- Console logs: JSONL format (one JSON object per line) instead of custom format
- Network traces: Structured JSON with request/response metadata
- DOM snapshots: Raw HTML (unchanged)

### 3. Session Management
- Old: Manual Chrome startup with `chrome --remote-debugging-port=9222`
- New: Automatic Chrome lifecycle managed by Python CLI

### 4. Port Allocation
- Old: Fixed port 9222
- New: Dynamic port allocation with `--port auto` (default: 9222)

## Migration Checklist

- [ ] Install Python CDP package: `pip3 install -e .`
- [ ] Update shell scripts to use `python3 -m scripts.cdp.cli.main`
- [ ] Replace `--include-console` with `--console`
- [ ] Replace `--mode=<value>` with `--mode <value>`
- [ ] Update output parsing for new JSONL format
- [ ] Remove manual Chrome startup commands
- [ ] Test all critical workflows with Python CLI
- [ ] Update CI/CD pipelines to use Python commands
- [ ] Archive or delete Bash orchestrator references

## Rollback Plan

If you encounter issues with the Python CLI, the legacy Bash orchestrator remains available at `scripts/legacy/debug-orchestrator.sh` with a deprecation warning. However, it will be removed in a future release.

**Temporary fallback:**
```bash
# Still works but shows deprecation warning
./scripts/legacy/debug-orchestrator.sh "https://example.com"
```

**Report issues:** https://github.com/your-repo/issues

## Timeline

- **Now**: Bash orchestrator deprecated, Python CLI is primary interface
- **Next Release**: Legacy Bash scripts will be removed entirely
- **Action**: Migrate all workflows before next major release

## Support

For migration assistance:
1. Check this guide for command mappings
2. Run `python3 -m scripts.cdp.cli.main <subcommand> --help` for detailed options
3. Review examples in `docs/examples/`
4. Open an issue if you encounter migration blockers

---

**Last Updated**: 2025-10-25
**Migration Path**: Bash → Python CDP CLI
**Status**: Bash orchestrator deprecated, removal planned for next release
