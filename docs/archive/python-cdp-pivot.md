# Python-First CDP Architecture Roadmap

## Guiding Principles
- Treat browser-debugger as a Python-first CLI with modular CDP services; shell acts only as a thin shim.
- Reuse existing collectors but consolidate them into a cohesive package with typed interfaces and tests.
- Prioritise reliability: strong error handling, deterministic retries, structured logging, and integration tests against real Chrome.
- Maintain agent ergonomics: single command to launch workflows, composable subcommands for advanced scenarios.

## Proposed Architecture

```
scripts/
  cdp/
    __init__.py
    cli.py
    config.py
    connection.py
    commands/
        runtime.py
        dom.py
        console.py
        network.py
    pipelines/
        interactive.py
        headless.py
    util/
        json_tools.py
        tempfile.py
        logging.py
collectors/
  (refactored to import from scripts.cdp.*)
core/
  debug_orchestrator.py (optional shell wrapper calling Python CLI)
```

- `connection.py` manages CDP session lifecycle.
- Command modules expose typed helpers (`get_dom`, `evaluate_expression`).
- Pipelines orchestrate multi-step flows using those primitives.
- Utils handle JSON encoding, temp files, structured logging.

## CLI Design
- Entry point: `python -m scripts.cdp.cli`.
- Subcommands: `eval`, `dom dump`, `console stream`, `network record`, `session orchestrate`.
- Options for JSON/raw output, timeouts, selectors, profiles, headless vs headed.
- Uses `argparse` with subparsers; supports `.env` / config overrides.

## Session & Chrome Management
- `SessionManager` class to fetch WebSocket URLs, auto-reconnect, and expose context managers.
- Optional background tasks for console/network using `asyncio`.
- Launch Chrome via Python (`subprocess.Popen`) with configurable flags; fallback to existing shell script if necessary.

## Error Handling & Logging
- Custom exception hierarchy for CDP failures (e.g., `ContextDestroyed`, `RuntimeError`).
- Structured logging with human-friendly summaries and verbose mode.
- Non-zero exit codes on failure; actionable hints surfaced to agents.

## Testing Strategy
- Unit tests (pytest + pytest-asyncio) for commands and connection logic with mocked WebSockets.
- Integration tests spinning up headless Chrome to validate DOM dumps and eval paths.
- Golden-file tests for DOM outputs.
- CLI smoke tests via `subprocess.run`.

## Migration Plan
1. Implement `connection.py`, `runtime.eval`, `dom dump`; mirror current shell behaviour.
2. Port console/network collectors to shared connection code; update orchestrator to call Python CLI.
3. Deprecate shell pipelines in documentation; keep `websocat` recipes under troubleshooting.
4. Achieve ≥80% coverage for new modules; integrate lint (`ruff`), formatter (`black`), typing (`mypy`).

## Developer Experience
- Provide dependency management (`requirements.txt`, optional `poetry`/`uv`).
- Add `Makefile` targets (`make cli`, `make test`, `make lint`).
- Document module responsibilities and Python-first workflows in README.

## Resilience Enhancements
- Implement retry/backoff for transient CDP errors.
- Validate DOM dumps (size thresholds, optional diffing) before reporting success.
- Emit structured JSON outputs for agent parsing.

## Long-Term Extensions
- Abstract CDP transport to allow alternate clients.
- Offer REST/MCP-like service wrapper if remote control becomes necessary.
- Enable scripted interactions (form filling) using shared command primitives.

## Why Python
- Eliminates shell `eval` and quoting fragility.
- Native JSON handling and async support simplify CDP usage.
- Existing team expertise and collectors reduce ramp-up.
- Enables robust testing and observability that shell cannot match.
