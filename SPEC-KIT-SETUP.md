# Spec-Kit Setup Guide

This project uses [GitHub Spec-Kit](https://github.com/github/spec-kit) for spec-driven development. Since `.claude/` is gitignored (to prevent credential leakage), you'll need to install spec-kit commands locally.

## Prerequisites

- Python 3.11+
- Git
- `uv` package manager ([installation guide](https://github.com/astral-sh/uv))
- Claude Code CLI or another supported AI agent

## Installation

### 1. Install Spec-Kit CLI

```bash
# Persistent installation (recommended)
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# Verify installation
specify check
```

### 2. Initialize Spec-Kit for This Project

Since the `.specify/` directory is already set up with templates and scripts, you only need to install the slash commands locally:

```bash
# From the project root
specify init browser-debugger --ai claude

# This will create a browser-debugger subdirectory with .claude/commands
# Copy the commands to the project root
cp browser-debugger/.claude/commands/*.md .claude/commands/

# Remove the subdirectory
rm -rf browser-debugger
```

**Alternative:** If you're starting fresh, the above commands are already integrated in the repo setup.

### 3. Verify Installation

Check that the commands are available:

```bash
ls .claude/commands/
```

You should see 8 spec-kit command files:
- `speckit.analyze.md`
- `speckit.checklist.md`
- `speckit.clarify.md`
- `speckit.constitution.md`
- `speckit.implement.md`
- `speckit.plan.md`
- `speckit.specify.md`
- `speckit.tasks.md`

## Usage

### Core Workflow

Use these slash commands in Claude Code in order:

1. **`/speckit.constitution`** - Establish project principles and development guidelines
2. **`/speckit.specify`** - Define functional requirements
3. **`/speckit.plan`** - Create technical architecture
4. **`/speckit.tasks`** - Generate actionable tasks
5. **`/speckit.implement`** - Execute implementation

### Optional Enhancement Commands

- **`/speckit.clarify`** - Resolve underspecified requirements (before `/speckit.plan`)
- **`/speckit.analyze`** - Validate consistency across artifacts (after `/speckit.tasks`)
- **`/speckit.checklist`** - Generate quality checklists (after `/speckit.plan`)

## Project Structure

```
.
├── .claude/
│   └── commands/           # Spec-kit slash commands (gitignored)
│       ├── speckit.*.md
│       └── ...
├── .specify/
│   ├── templates/          # Document templates (committed)
│   │   ├── agent-file-template.md
│   │   ├── checklist-template.md
│   │   ├── plan-template.md
│   │   ├── spec-template.md
│   │   └── tasks-template.md
│   ├── scripts/            # Helper scripts (committed)
│   │   └── bash/
│   │       ├── check-prerequisites.sh
│   │       ├── common.sh
│   │       ├── create-new-feature.sh
│   │       ├── setup-plan.sh
│   │       └── update-agent-context.sh
│   └── memory/             # Generated artifacts (gitignored)
│       ├── constitution.md
│       ├── specifications/
│       ├── plans/
│       └── tasks/
```

## Git Ignore Policy

Per spec-kit security recommendations:

- **`.claude/`** - Gitignored (may contain agent credentials/tokens)
- **`.specify/memory/`** - Gitignored (contains generated specs that may reference internal systems)
- **`.specify/templates/`** - Committed (generic templates)
- **`.specify/scripts/`** - Committed (generic helper scripts)

## Troubleshooting

### "specify: command not found"

```bash
# Check if uv is installed
which uv

# If not, install uv first
curl -LsSf https://astral.sh/uv/install.sh | sh

# Then install specify
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
```

### Slash commands not appearing

1. Restart Claude Code CLI
2. Verify files exist: `ls .claude/commands/speckit.*.md`
3. Check file permissions: `chmod 644 .claude/commands/*.md`

### "No such file or directory: .claude/commands"

```bash
# Create the directory
mkdir -p .claude/commands

# Re-run the setup commands above
```

## Resources

- [Spec-Kit GitHub Repository](https://github.com/github/spec-kit)
- [Spec-Kit Documentation](https://github.com/github/spec-kit#readme)
- [uv Package Manager](https://github.com/astral-sh/uv)

## Example Workflow

```bash
# 1. Start with a constitution
# In Claude Code:
/speckit.constitution
# Define 3-5 core principles for the project

# 2. Create a specification for a new feature
/speckit.specify
# Describe what you want to build

# 3. Generate a technical plan
/speckit.plan
# Creates architecture aligned with your tech stack

# 4. Break down into tasks
/speckit.tasks
# Generates actionable task list

# 5. Implement
/speckit.implement
# Execute tasks systematically
```

## Benefits of Spec-Driven Development

- **Clarity First**: Define *what* and *why* before *how*
- **Reduced Rework**: Catch issues in specs before coding
- **Better Collaboration**: Specs serve as single source of truth
- **Incremental Refinement**: Multi-step refinement vs one-shot generation
- **Quality Assurance**: Built-in consistency checks and checklists
