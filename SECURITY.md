# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main branch | :white_check_mark: |
| 0.x (development) | :white_check_mark: |

**Note**: This project is currently in active development (pre-1.0). Security updates are applied to the main branch only.

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities via public GitHub issues.**

Instead, please report security vulnerabilities privately using one of the following methods:

1. **GitHub Security Advisories** (preferred):
   - Go to the [Security tab](https://github.com/szymdzum/claude-browser-debugger/security/advisories)
   - Click "Report a vulnerability"
   - Fill out the form with details

2. **Email**: Send details to szymon@kumak.dev

### What to Include

When reporting a vulnerability, please include:

- **Description**: Clear explanation of the vulnerability
- **Steps to reproduce**: Detailed steps to demonstrate the issue
- **Potential impact**: What an attacker could do with this vulnerability
- **Affected versions**: Which versions/commits are affected
- **Suggested fix** (optional): If you have ideas for mitigation

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Fix timeline**: Depends on severity
  - **Critical**: 7 days
  - **High**: 14 days
  - **Medium/Low**: 30 days

### Disclosure Policy

- We follow coordinated disclosure practices
- Security advisories will be published after fixes are released
- We will credit researchers who report vulnerabilities (unless they prefer to remain anonymous)

## Security Best Practices for Users

### Running CDP with Chrome

- **Never expose Chrome debugging port (9222) to untrusted networks**
  - Chrome debugging protocol has no authentication
  - Exposed ports allow complete browser control
  - Only use on localhost or trusted networks

- **Use isolated Chrome profiles for debugging**
  - The tool uses `--user-data-dir` to isolate debug sessions
  - Never use your main Chrome profile for debugging
  - Debug profiles are stored at `$HOME/.chrome-debug-profile` by default

- **Validate URLs before debugging**
  - The tool validates HTTP status codes before launching Chrome
  - Avoid debugging untrusted or malicious websites
  - Use headed mode for manual URL verification

### Dependency Security

- **Keep dependencies updated**
  - Review and merge Dependabot PRs promptly
  - Check CI status before merging dependency updates
  - Review changelogs for breaking changes

- **Verify installation source**
  - Install from official PyPI (when published) or GitHub releases
  - Verify checksums/signatures when available
  - Use `pip install -e .` for development installs

### Configuration Files

- **Protect `.cdprc` configuration**
  - Never commit `.cdprc` with sensitive data
  - Use environment variables for secrets
  - Ensure `.cdprc` has appropriate file permissions (0600)

- **Review GitHub Actions secrets**
  - Don't store credentials in workflow files
  - Use GitHub encrypted secrets for sensitive data
  - Rotate secrets regularly

## Known Security Considerations

### Chrome DevTools Protocol (CDP)

CDP provides **full access** to the browser, including:
- JavaScript execution in page context
- Network request interception and modification
- Cookie and localStorage access
- File system access (in some configurations)

**Implications**:
- Only debug trusted websites
- Never expose CDP port to public networks
- Treat CDP connections as privileged access

### Python Code Execution

This tool executes Python code and shell scripts:
- Uses `subprocess` to launch Chrome
- Executes CDP commands from user input
- Writes files to disk (logs, DOM dumps)

**Mitigations**:
- No arbitrary code execution from external sources
- File paths are validated before writing
- Chrome launch uses explicit arguments (no shell=True)

## Security Features

- **Secret scanning**: Enabled via GitHub (detects leaked credentials)
- **Dependabot alerts**: Monitors dependencies for known vulnerabilities
- **CodeQL analysis**: Scans code for security issues
- **CI validation**: All PRs require passing tests
- **Branch protection**: Direct pushes to main blocked

## Out of Scope

The following are **not** considered security vulnerabilities:

- Chrome or Chromium browser vulnerabilities (report to Chrome Security)
- Issues requiring physical access to the machine
- Denial of service via resource exhaustion on localhost
- Issues in dependencies (report to upstream projects)
- Social engineering attacks

## Questions?

For general security questions (not vulnerabilities), feel free to:
- Open a GitHub discussion
- Email szymon@kumak.dev with [SECURITY] in the subject

Thank you for helping keep this project secure!
