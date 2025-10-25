# CLI Design Review - Response Summary

## Review Date
2025-10-24

## Review Feedback Addressed

### ✅ 1. Clarify `--output` Flag Semantics

**Issue**: `--output` is used as both a global flag (format) and subcommand flag (file path), causing semantic collision.

**Resolution**:
- **Global flag**: `--format FORMAT` controls output format (json/text/raw)
- **Subcommand flag**: `--output FILE` controls output destination (file path)
- **New alias**: `--json` as shorthand for `--format json` (common muscle memory)
- These flags are independent and can be combined: `--format json --output /tmp/result.json`

**Location**: `cli-design.md:21-37`

**Examples**:
```bash
# Format to JSON, output to stdout
python -m scripts.cdp.cli dom dump --format json --url "example.com"

# Shorthand for JSON format
python -m scripts.cdp.cli dom dump --json --url "example.com"

# JSON format, write to file
python -m scripts.cdp.cli dom dump --json --output /tmp/page.html --url "example.com"
```

---

### ✅ 2. Enforce Mutual Exclusion for `--target` and `--url`

**Issue**: Subcommands should fail fast when both `--target` and `--url` are omitted or both are provided.

**Resolution**:
- Use `argparse.add_mutually_exclusive_group(required=True)` for all commands with target selection
- Enforced in: `eval`, `dom dump`, `dom query`, `console stream`, `network record`, `query`
- Error message: "error: one of the arguments --target --url is required"
- If both provided: "error: argument --url: not allowed with argument --target"

**Location**: `cli-design.md:133-137, 845-862`

**Implementation**:
```python
target_group = dump_parser.add_mutually_exclusive_group(required=True)
target_group.add_argument("--target", type=str, help="Explicit target ID")
target_group.add_argument("--url", type=str, help="Connect to first target matching URL pattern")
```

---

### ✅ 3. Add `--wait-for` Selector Option

**Issue**: Post-form interactions need to wait for dynamic content before DOM extraction.

**Resolution**:
- Added `--wait-for SELECTOR` option to `dom dump` and `orchestrate` commands
- Uses CDP `Runtime.evaluate` with polling (100ms intervals, 30s timeout)
- Blocks until element matching CSS selector exists
- Exit code 4 if timeout exceeded

**Location**: `cli-design.md:170, 177-181, 341`

**Examples**:
```bash
# Wait for result div before dumping DOM
python -m scripts.cdp.cli dom dump --wait-for "div.results" --url "example.com"

# Wait in orchestrate workflow
python -m scripts.cdp.cli orchestrate headless https://example.com \
  --wait-for "form#complete" --include-console
```

**Implementation Notes**:
- Polling interval: 100ms (balance between responsiveness and CDP overhead)
- Default timeout: 30s (configurable via global `--timeout` flag)
- Error message includes selector: "Timeout waiting for selector 'div.results'"

---

### ✅ 4. Network Body Capture Safety

**Issue**: `--include-bodies` can explode memory with large responses (images, videos, large JSON).

**Resolution**:
- **Default**: `--include-bodies` is OFF
- **Added**: `--max-body-size BYTES` limit (default: 1MB)
- **Help text warning**: Explicit warning about size impact
- **Behavior**: Large responses truncated with warning in logs
- **Recommendation**: Use `--filter-url "/api/"` to limit scope

**Location**: `cli-design.md:282-308`

**Examples**:
```bash
# Capture API responses only (recommended)
python -m scripts.cdp.cli network record --include-bodies --filter-url "/api/" \
  --url "example.com"

# Custom body size limit (5MB)
python -m scripts.cdp.cli network record --include-bodies --max-body-size 5242880 \
  --url "example.com"
```

**Warning in Help Text**:
```
--include-bodies
    Capture response bodies (default: off)

    WARNING: Can significantly increase memory usage and output size.
    Large responses (>1MB by default) are truncated.
    Consider using --filter-url to limit scope.
    Use --max-body-size to adjust limit (in bytes).
```

---

### ✅ 5. Orchestrate Failure Handling

**Issue**: Unclear what happens if Chrome fails to launch mid-workflow, and whether partial artifacts are returned.

**Resolution**:

**Exit Codes Defined**:
- `0`: Workflow completed successfully
- `2`: Chrome launch failed (no artifacts created)
- `4`: Timeout waiting for `--wait-for` selector
- `6`: Chrome crashed mid-workflow (partial artifacts saved)

**JSON Output Status**:
- Success: `"status": "completed"`
- Launch failure: `"status": "failed", "artifacts": {}`
- Partial failure: `"status": "partial", "artifacts": {...}` (includes all saved artifacts)

**Partial Artifact Preservation**:
- All artifacts saved before failure are preserved
- Artifact paths returned in JSON output
- Summary includes analysis of partial data
- Logs indicate at what point failure occurred
- Artifact files include timestamp to prevent overwrites on retry

**Location**: `cli-design.md:345-403`

**Example Outputs**:

```json
// Chrome launch failure
{
  "workflow": "headless",
  "url": "https://example.com",
  "status": "failed",
  "error": "Failed to launch Chrome: port 9222 already in use",
  "artifacts": {},
  "recovery_hint": "Kill existing Chrome process: pkill -f 'chrome.*9222'"
}

// Partial failure (Chrome crashed after 30s)
{
  "workflow": "headless",
  "url": "https://example.com",
  "status": "partial",
  "error": "Chrome connection lost after 30s",
  "artifacts": {
    "console": "/tmp/console-1234567890.jsonl",
    "network": "/tmp/network-1234567890.json",
    "summary": "/tmp/summary-1234567890.txt"
  },
  "stats": {
    "consoleMessages": 12,
    "networkRequests": 5,
    "errors": 1
  },
  "recovery_hint": "Check Chrome logs for crash details"
}
```

---

### ✅ 6. Stdin Support for `query` Command

**Issue**: Advanced users need to pass large payloads without hitting shell argument limits.

**Resolution**:
- Added `--params-file FILE` option to `query` command
- Use `--params-file -` to read from stdin
- Enables piping: `cat params.json | python -m scripts.cdp.cli query ... --params-file -`
- Useful for building CDP pipelines

**Location**: `cli-design.md:431, 463-471`

**Parameter Input Precedence** (highest to lowest):
1. `--params-file FILE` (explicit file or stdin via `-`)
2. `--params JSON` (inline JSON string)
3. Positional `PARAMS` argument

**Examples**:
```bash
# Large payload from file
python -m scripts.cdp.cli query Runtime.evaluate --params-file params.json

# Read from stdin (piping)
echo '{"expression": "document.title"}' | python -m scripts.cdp.cli query Runtime.evaluate --params-file -

# Pipeline example
cat complex-params.json | python -m scripts.cdp.cli query DOM.querySelector --params-file - --url "example.com"
```

---

### ✅ 7. Add `--json` Alias

**Issue**: `--json` is common muscle memory from other CLIs (curl, aws-cli, etc.).

**Resolution**:
- Added `--json` flag as alias for `--format json`
- Global flag available for all commands
- Can be combined with `--output FILE` for file output

**Location**: `cli-design.md:27`

**Examples**:
```bash
# Using --json alias
python -m scripts.cdp.cli dom dump --json --url "example.com"

# Equivalent to --format json
python -m scripts.cdp.cli dom dump --format json --url "example.com"

# Combined with file output
python -m scripts.cdp.cli dom dump --json --output /tmp/page.html --url "example.com"
```

---

## Open Questions from Review (Not Implemented)

None - all suggestions were implemented.

---

## Implementation Checklist

### Phase 1: Global Options & Target Selection
- [ ] Implement `--format` vs `--output` separation
- [ ] Add `--json` alias to global parser
- [ ] Implement `add_mutually_exclusive_group()` for all target selection
- [ ] Write tests for mutual exclusion error messages

### Phase 2: Wait-For Functionality
- [ ] Implement `--wait-for` polling logic in `dom dump`
- [ ] Implement `--wait-for` in `orchestrate` command
- [ ] Add timeout handling with exit code 4
- [ ] Integration tests for wait-for behavior

### Phase 3: Network Body Capture
- [ ] Implement `--max-body-size` limit in network recorder
- [ ] Add help text warnings for `--include-bodies`
- [ ] Implement body truncation with logging
- [ ] Performance tests with large responses

### Phase 4: Orchestrate Failure Handling
- [ ] Define exit codes (0/2/4/6) in orchestrator
- [ ] Implement partial artifact preservation
- [ ] Add `"status"` field to JSON output
- [ ] Write tests for all failure scenarios

### Phase 5: Query Stdin Support
- [ ] Implement `--params-file FILE` option
- [ ] Handle stdin via `--params-file -`
- [ ] Implement parameter precedence logic
- [ ] Add tests for large payloads from stdin

---

## Changes to Original Design

| Aspect | Original Design | Updated Design | Rationale |
|--------|-----------------|----------------|-----------|
| Output flags | `--output FORMAT` (dual purpose) | `--format FORMAT` + `--output FILE` | Clear separation of format vs destination |
| JSON shorthand | Not specified | `--json` alias | Common muscle memory from other CLIs |
| Target selection | No explicit validation | `add_mutually_exclusive_group(required=True)` | Fail fast with clear error messages |
| DOM wait | Not specified | `--wait-for SELECTOR` | Post-form interaction support |
| Network bodies | No size limit | `--max-body-size BYTES` (default: 1MB) | Prevent memory exhaustion |
| Orchestrate failures | Success-only output | Status field + exit codes + partial artifacts | Agent-friendly failure handling |
| Query params | Inline only | `--params-file FILE` + stdin support | Large payload support for power users |

---

## Migration Impact

### Breaking Changes
None - this is a new CLI being designed from scratch.

### Compatibility Notes
- Existing Bash `debug-orchestrator.sh` will be wrapped to call Python CLI
- Wrapper ensures backward compatibility during transition
- No impact on current users (shell scripts remain functional)

---

## Next Steps

1. **Review open questions** with stakeholders (none pending)
2. **Begin implementation** of Phase 1 (global options & target selection)
3. **Write argparse tests** for mutual exclusion and flag validation
4. **Validate `--wait-for`** with real Chrome and dynamic content

---

## Sign-off

**Reviewer**: (Your review feedback)
**Designer**: Claude Code Agent
**Status**: Design finalized, ready for implementation
**Date**: 2025-10-24
