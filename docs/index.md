# Browser Debugger Documentation Index

**Quick navigation guide for AI agents and developers.**

## Getting Started

- **Project Overview**: See [../README.md](../README.md)
- **Agent Instructions**: See [../SKILL.md](../SKILL.md)
- **Claude Code Setup**: See [../CLAUDE.md](../CLAUDE.md)

## User Guides

**Core Workflows:**
- [guides/workflows.md](guides/workflows.md) - Common debugging workflows (headless/headed capture, DOM extraction, network monitoring)
- [guides/troubleshooting.md](guides/troubleshooting.md) - Common issues and solutions

**Headed Mode (Interactive Debugging):**
- [guides/workflow-guide.md](guides/workflow-guide.md) - Step-by-step interactive debugging workflow
- [guides/interactive-workflow-design.md](guides/interactive-workflow-design.md) - Architecture and design patterns
- [guides/filter-flag-guide.md](guides/filter-flag-guide.md) - Network body capture filtering
- [guides/launcher-contract.md](guides/launcher-contract.md) - chrome-launcher.sh API specification
- [guides/chrome-136-incident.md](guides/chrome-136-incident.md) - Chrome 136+ security policy change (required reading for headed mode)

## Technical Reference

**Protocol & Browser:**
- [reference/cdp-commands.md](reference/cdp-commands.md) - Chrome DevTools Protocol command reference
- [reference/websocat-analysis.md](reference/websocat-analysis.md) - WebSocket/CDP internals and buffer tuning

**Browser Internals:**
- [reference/chrome-dom.md](reference/chrome-dom.md) - Chrome DOM extraction techniques

## Development

**Agent Education:**
- [development/agent-cli-guide.md](development/agent-cli-guide.md) - **Educational guide**: How agents use DOM/console/network CLI (recommended first read)

**Skill Development:**
- [development/skills.md](development/skills.md) - Claude Code skill system fundamentals
- [development/skills-best-practices.md](development/skills-best-practices.md) - Best practices for skill authoring

## Scripts

See [../scripts/README.md](../scripts/README.md) for script documentation:
- **Python CDP CLI**: orchestrate, console, network, dom, session, eval, query subcommands
- **Core**: chrome-launcher.sh (Chrome process management)
- **Utilities**: cdp-query.sh, cleanup-chrome.sh, save-session.sh, extract-state.sh

## Quick Lookups

### Find Information By Task

| Task | Document |
|------|----------|
| Launch Chrome in headed mode | [guides/workflows.md](guides/workflows.md) |
| Extract DOM from live page | [reference/cdp-commands.md](reference/cdp-commands.md) → Runtime.evaluate |
| Capture network request bodies | [guides/filter-flag-guide.md](guides/filter-flag-guide.md) |
| Fix "CDP connection blocked" | [guides/chrome-136-incident.md](guides/chrome-136-incident.md) |
| Clean up Chrome processes | [guides/troubleshooting.md](guides/troubleshooting.md) → Port conflicts |
| Send custom CDP commands | [reference/cdp-commands.md](reference/cdp-commands.md) + [../scripts/README.md](../scripts/README.md) |
| Monitor console logs | [guides/workflows.md](guides/workflows.md) → Console monitoring |
| Track form field changes | [reference/cdp-commands.md](reference/cdp-commands.md) → DOM.attributeModified |

### Find Information By Component

| Component | Primary Docs |
|-----------|--------------|
| chrome-launcher.sh | [guides/launcher-contract.md](guides/launcher-contract.md) |
| Python CDP CLI (orchestrate) | [guides/workflows.md](guides/workflows.md) |
| Python CDP CLI (console) | [../scripts/README.md](../scripts/README.md) |
| Python CDP CLI (network) | [../scripts/README.md](../scripts/README.md) |
| websocat | [reference/websocat-analysis.md](reference/websocat-analysis.md) |

## Token-Efficient Reading Strategy

**For agents working on specific tasks, read in this order:**

1. **First-time setup (educational)**: [development/agent-cli-guide.md](development/agent-cli-guide.md) - Learn how DOM/console/network CLI works
2. **Quick reference**: [../SKILL.md](../SKILL.md) - Comprehensive agent guide with examples
3. **Headed mode debugging**: [guides/workflow-guide.md](guides/workflow-guide.md)
4. **Custom CDP commands**: [reference/cdp-commands.md](reference/cdp-commands.md)
5. **Troubleshooting**: [guides/troubleshooting.md](guides/troubleshooting.md)
6. **Advanced internals**: [reference/websocat-analysis.md](reference/websocat-analysis.md)

**Avoid reading unless needed:**
- `development/skills*.md` - Only for skill authoring
- `guides/chrome-136-incident.md` - Only if CDP connection fails
