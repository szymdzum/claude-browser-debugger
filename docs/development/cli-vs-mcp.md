# Teaching Agents CLI Skills Instead of Installing MCP

## Purpose
Help other teams understand why we’ve chosen to invest in high-quality CLI workflows (e.g., `gh`, `glab`, `browser-debugger` CLI) instead of deploying additional MCP services. This document will later be adapted into a public article or tutorial.

## Context
- Environment: remote shell provided by Claude Code / Codex, limited control over daemons and networking.
- Existing tooling: rich CLIs already installed or easy to install (`gh`, `glab`, Chrome launcher scripts, future Python CDP CLI).
- Challenge: MCP-based integrations (GitHub MCP, GitLab MCP, custom CDP MCP) have been fragile to configure and costly in tokens, leading to poor agent reliability.

## Observations From Experiments
1. **Configuration Overhead**
   - MCP servers require discovery URLs, TLS certs, ports, version compatibility, and JSON schema definitions.
   - Any mismatch (port blocked, schema typo, missing dependency) causes total failure. Agents cannot self-diagnose.
2. **Token Consumption**
   - MCP responses often include large schema payloads or verbose metadata.
   - In remote-shell contexts, each MCP call adds measurable latency and cost, discouraging frequent use.
3. **Debugging Difficulty**
   - Failures present as “tool unavailable” with minimal clues.
   - Requires toggling logs, editing config files, or restarting services—operations that agents struggle to perform without human intervention.
4. **CLI Success Cases**
   - `gh` and `glab` integrate authentication, pagination, and sensible defaults.
   - Agents handle them exceptionally well: they can read `--help`, parse JSON output (`gh api`, `glab api`), and recover from errors by re-running commands.
   - No extra services to manage; the CLI is the contract.
5. **Existing Shell Constraints**
   - We already juggle network sandboxing, limited background processes, and timeouts.
   - Adding long-lived MCP services increases the moving parts and failure surface.

## Advantages of the “Teach the CLI” Approach
| Aspect | CLI Usage | MCP Deployment |
|--------|-----------|----------------|
| **Setup** | Install binary once (`brew install gh`), no daemon | Requires server config, auth, schema |
| **Observability** | CLI stdout/stderr captured naturally | Need separate logs/endpoints |
| **Agent Learning** | Read `--help`, reuse examples, combine pipes | Must internalize custom schema semantics |
| **Error Recovery** | Re-run command, inspect exit code | Often opaque “tool unavailable” errors |
| **Token Efficiency** | Only command output counted | Extra metadata inflates tokens |
| **Portability** | Works offline/air-gapped | Needs network access to MCP host |

## Practical Guidelines
1. **Document CLI Workflows**
   - Provide copy-pastable commands for common tasks.
   - Include `--json`/`--format` flags so agents can parse results.
2. **Expose Examples in Repos**
   - README snippets showing `gh pr status`, `glab issue list`, etc.
   - Agents follow these patterns reliably.
3. **Automate Auth Once**
   - Use `gh auth login` or `glab auth login` during environment setup.
   - Store tokens via CLI’s native keychain support; agents inherit the session.
4. **Prefer Deterministic Output**
   - Encourage `--jq`/`--template` flags to minimize parsing ambiguity.
5. **Fallback Strategy**
   - When a CLI lacks a feature, extend it with small helper scripts rather than introducing an MCP endpoint.
6. **Monitoring**
   - Log CLI commands executed by agents (already captured by Codex shell transcripts) for auditing.

## When MCP Still Makes Sense
Use MCP if:
1. There is no reliable CLI or API equivalent.
2. You need strongly typed, multi-step workflows with validation beyond shell scripting.
3. The environment supports long-lived services and you can invest in monitoring/ops.

## Recommendation
For our browser-debugger migration (and similar projects), continue prioritizing:
1. High-quality, well-documented CLI commands.
2. Python CLI packaging with `setup.py`/`pyproject` so agents can run `python -m ...`.
3. Thin wrappers around external services (GitHub/GitLab) using their native CLIs.

This strategy has proven more dependable than MCP integrations in our environment, reduces token usage, and keeps agents productive with minimal configuration.
