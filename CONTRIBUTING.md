# Contributing to Claude Browser Debugger

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Quality Standards](#quality-standards)
- [Submitting Changes](#submitting-changes)
- [Automated Processes](#automated-processes)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

## Code of Conduct

This project follows GitHub's community guidelines. Be respectful, inclusive, and constructive in all interactions.

## Getting Started

### Prerequisites

- **Python 3.10+** (3.10, 3.11, 3.12 tested in CI)
- **Chrome/Chromium** browser (version 136+)
- **git** for version control
- **gh CLI** (optional, for GitHub operations)

### Initial Setup

1. **Fork and clone the repository**:
   ```bash
   gh repo fork szymdzum/claude-browser-debugger --clone
   cd claude-browser-debugger
   ```

2. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Verify installation**:
   ```bash
   python3 -m pytest tests/ -v
   ```

4. **Install pre-commit hooks** (optional but recommended):
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Development Workflow

### Creating a Feature Branch

```bash
# Create a branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### Making Changes

1. Write your code following our [coding standards](#coding-standards)
2. Add or update tests for your changes
3. Run tests locally: `pytest tests/ -v`
4. Run linting: `pylint scripts/cdp/`
5. Run type checking: `mypy scripts/cdp/ --ignore-missing-imports`
6. Update documentation if needed

### Commit Messages

Follow conventional commit format:

```
type(scope): brief description

Longer description if needed

Closes #issue-number
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions or changes
- `refactor`: Code restructuring without behavior change
- `chore`: Maintenance tasks (dependencies, build, etc.)

**Examples**:
```
feat(cli): add --timeout flag to orchestrate command

fix(connection): handle WebSocket reconnection on Chrome crash

docs(readme): update installation instructions for Python 3.12

test(integration): add tests for headed mode workflow
```

## Quality Standards

### CI Requirements

All pull requests must pass the following checks before merging:

#### 1. **Tests** (Python 3.10, 3.12)
- All tests must pass: `pytest tests/ -v --tb=short`
- Tested on minimum (3.10) and latest (3.12) versions
- No regressions in existing tests
- New features must include tests

#### 2. **Linting** (pylint)
- Code must pass linting: `pylint scripts/cdp/ --disable=missing-docstring,too-few-public-methods`
- Follow PEP 8 style guidelines
- Address all linting errors (warnings acceptable with justification)

#### 3. **Type Checking** (mypy)
- Code must pass type checking: `mypy scripts/cdp/ --ignore-missing-imports --explicit-package-bases`
- Use type hints for new functions
- Gradual typing acceptable for refactored code

### Coding Standards

- **Python style**: Follow PEP 8
- **Docstrings**: Use Google-style docstrings for public APIs
- **Type hints**: Required for new code, encouraged for refactored code
- **Error handling**: Use custom exceptions from `scripts/cdp/exceptions.py`
- **Logging**: Use structured logging with `scripts/cdp/logging.py`

### Code Quality Checklist

Before submitting a PR, verify:

- [ ] All tests pass locally
- [ ] Linting passes without errors
- [ ] Type checking passes
- [ ] No unintended changes (check `git diff`)
- [ ] Commit messages follow conventions
- [ ] Documentation updated if needed
- [ ] No secrets or sensitive data in code

## Submitting Changes

### Pull Request Process

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a pull request**:
   ```bash
   gh pr create --title "feat: your feature title" --body "Description of changes"
   ```

3. **PR Requirements**:
   - Clear title and description
   - Reference related issues: `Closes #123`
   - All CI checks passing
   - At least 1 approval from maintainers

4. **Address review feedback**:
   - Make requested changes
   - Push updates to the same branch
   - CI will re-run automatically

5. **Merge**:
   - Maintainers will merge after approval and passing CI
   - Branch will be auto-deleted after merge

### First-Time Contributors

First-time contributors require workflow approval:

- **Why**: GitHub security policy requires maintainer approval for first CI run
- **Process**: A maintainer will review and approve your PR for CI execution
- **Timeline**: Usually within 24-48 hours

## Automated Processes

### Dependabot PRs

Dependabot automatically creates PRs for dependency updates:

**How to handle**:

1. **Review the changelog**: Check what changed in the dependency
2. **Check CI status**: Ensure tests pass with the update
3. **Merge or close**:
   - **Merge**: If tests pass and changes are safe
   - **Close**: If update is unnecessary or breaks compatibility

**Grouped updates**: Patch and minor versions are grouped weekly to reduce PR noise.

### CodeQL Scanning

CodeQL scans code for security vulnerabilities:

**Handling alerts**:

1. **Review findings** in the Security tab
2. **Fix legitimate issues**: Follow GitHub's guidance
3. **Suppress false positives**:
   ```python
   # codeql[python/sql-injection] - Safe: input is validated
   query = f"SELECT * FROM users WHERE id = {user_id}"
   ```
4. **Document suppressions**: Add inline comments with justification

**Review frequency**: Quarterly review of all suppressed alerts

### Secret Scanning

Automatically detects leaked credentials:

**If a secret is detected**:

1. **Immediate action**: Rotate the exposed secret
2. **Remove from history**: Use BFG Repo-Cleaner or `git filter-branch`
3. **Push protection**: Push will be blocked until secret is removed

## Testing Guidelines

### Test Structure

```
tests/
├── unit/              # Fast, isolated unit tests
├── integration/       # Tests requiring Chrome
└── conftest.py        # Shared fixtures
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_connection.py -v

# Run tests matching pattern
pytest tests/ -k "test_console" -v

# Run with coverage
pytest tests/ --cov=scripts/cdp/ --cov-report=html
```

### Writing Tests

```python
import pytest
from scripts.cdp.connection import CDPConnection

def test_connection_lifecycle():
    """Test CDP connection establishment and cleanup."""
    conn = CDPConnection("ws://localhost:9222/test")

    # Test behavior
    assert not conn.is_connected

    # Async test with pytest-asyncio
    @pytest.mark.asyncio
    async def test_async_command():
        async with conn:
            result = await conn.execute_command("Runtime.evaluate", {
                "expression": "1 + 1"
            })
            assert result["result"]["value"] == 2
```

### Integration Test Requirements

- **Chrome fixture**: Use `chrome_instance` fixture from `conftest.py`
- **Cleanup**: Ensure Chrome processes are terminated
- **Timeouts**: Use reasonable timeouts (5-10 seconds)
- **Idempotence**: Tests should be runnable multiple times

## Documentation

### What to Document

- **New features**: Update README.md and relevant guides
- **API changes**: Update SKILL.md if agent-facing
- **Configuration**: Update CLAUDE.md for project-specific instructions
- **Breaking changes**: Highlight in PR description and CHANGELOG

### Documentation Style

- **Clear and concise**: Avoid jargon
- **Examples**: Include code examples for new features
- **Links**: Reference related documentation
- **Up-to-date**: Update examples if code changes

## Emergency Hotfix Process

For critical bugs requiring immediate fixes:

### Admin Override Policy

Maintainers with admin access can bypass branch protection:

**When to use**:
- Critical security vulnerabilities
- Production-breaking bugs
- Data loss issues

**Process**:
1. Create hotfix branch: `git checkout -b hotfix/critical-bug`
2. Make minimal fix
3. Test locally
4. Force push to main (admins only): `git push origin hotfix/critical-bug:main`
5. Create follow-up PR with comprehensive tests

**Documentation**: Document in PR why emergency process was used.

## Questions?

- **GitHub Discussions**: For general questions
- **Issues**: For bug reports and feature requests
- **Email**: szymon@kumak.dev for private matters

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

Thank you for contributing! Your efforts help make this project better for everyone.
