#!/usr/bin/env bash
# GitHub Repository Settings Automation Script
# Purpose: Configure repository settings via gh CLI for feature 009-github-maintenance
#
# Prerequisites:
# - gh CLI installed and authenticated (gh auth status)
# - Repository admin access
# - Repository must be public (for free CodeQL and secret scanning)
#
# Usage:
#   ./scripts/setup-github-repo.sh [--dry-run]
#
# Options:
#   --dry-run    Show what would be changed without making changes

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DRY_RUN=false
REPO_OWNER="szymdzum"
REPO_NAME="claude-browser-debugger"
REPO="${REPO_OWNER}/${REPO_NAME}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--dry-run]"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

run_command() {
    local description="$1"
    shift

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would execute: $*"
        return 0
    fi

    log_info "$description"
    if "$@"; then
        log_success "$description - Done"
        return 0
    else
        log_error "$description - Failed"
        return 1
    fi
}

# Verify prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check gh CLI installed
    if ! command -v gh &> /dev/null; then
        log_error "gh CLI not found. Install it from https://cli.github.com/"
        exit 1
    fi

    # Check gh authentication
    if ! gh auth status &> /dev/null; then
        log_error "Not authenticated with gh CLI. Run: gh auth login"
        exit 1
    fi

    # Check repository access
    if ! gh repo view "$REPO" &> /dev/null; then
        log_error "Cannot access repository $REPO. Check permissions."
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Phase 1: Repository Metadata
configure_repository_metadata() {
    log_info "=== Phase 1: Repository Metadata ==="

    run_command "Setting repository description" \
        gh repo edit "$REPO" \
        --description "Python CLI for Chrome DevTools Protocol - lightweight browser debugging for AI agents"

    run_command "Adding repository topics" \
        gh repo edit "$REPO" \
        --add-topic python \
        --add-topic cli \
        --add-topic chrome-devtools-protocol \
        --add-topic cdp \
        --add-topic browser-automation \
        --add-topic debugging \
        --add-topic devtools \
        --add-topic chrome \
        --add-topic playwright-alternative \
        --add-topic puppeteer-alternative \
        --add-topic testing-tools

    run_command "Enabling auto-delete head branches" \
        gh repo edit "$REPO" \
        --delete-branch-on-merge
}

# Phase 2: Security Features
configure_security_features() {
    log_info "=== Phase 2: Security Features ==="

    run_command "Enabling secret scanning" \
        gh repo edit "$REPO" \
        --enable-secret-scanning

    run_command "Enabling secret scanning push protection" \
        gh repo edit "$REPO" \
        --enable-secret-scanning-push-protection

    log_info "Dependabot alerts and security updates must be enabled via GitHub UI:"
    log_info "  1. Go to: https://github.com/$REPO/settings/security_analysis"
    log_info "  2. Enable 'Dependabot alerts'"
    log_info "  3. Enable 'Dependabot security updates'"

    log_info "CodeQL scanning must be enabled via GitHub UI:"
    log_info "  1. Go to: https://github.com/$REPO/settings/security_analysis"
    log_info "  2. Click 'Set up' → 'Default' for Code scanning"
    log_info "  3. Click 'Enable CodeQL'"
}

# Phase 3: Branch Protection
configure_branch_protection() {
    log_info "=== Phase 3: Branch Protection ==="

    # Check if CI workflow exists and has run
    local workflow_exists=false
    if gh run list --workflow=ci.yml --limit=1 &> /dev/null; then
        workflow_exists=true
    fi

    if [ "$workflow_exists" = false ]; then
        log_warning "CI workflow hasn't run yet. Status checks will be available after first CI run."
        log_info "Branch protection rule will be created but status checks must be added manually later."
    fi

    local protection_json
    protection_json=$(cat <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "test (3.10)",
      "test (3.11)",
      "test (3.12)",
      "lint",
      "typecheck"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismissal_restrictions": {},
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
EOF
)

    if [ "$DRY_RUN" = false ]; then
        log_info "Configuring branch protection for 'main'"
        if echo "$protection_json" | gh api \
            --method PUT \
            -H "Accept: application/vnd.github+json" \
            -H "X-GitHub-Api-Version: 2022-11-28" \
            "/repos/$REPO/branches/main/protection" \
            --input - &> /dev/null; then
            log_success "Branch protection configured"
        else
            log_warning "Branch protection configuration failed or partially applied"
            log_info "You may need to configure some settings manually in the GitHub UI"
        fi
    else
        log_info "[DRY RUN] Would configure branch protection with:"
        echo "$protection_json" | jq .
    fi
}

# Phase 4: Verification
verify_configuration() {
    log_info "=== Phase 4: Verification ==="

    log_info "Verifying repository settings..."

    # Get repository info
    local repo_info
    repo_info=$(gh repo view "$REPO" --json description,topics,visibility,deleteBranchOnMerge)

    echo "$repo_info" | jq .

    log_info "Checking branch protection..."
    if gh api "/repos/$REPO/branches/main/protection" &> /dev/null; then
        log_success "Branch protection is configured"
    else
        log_warning "Branch protection not found or not accessible"
    fi

    log_info "Security features status:"
    log_info "  - Secret scanning: Check at https://github.com/$REPO/settings/security_analysis"
    log_info "  - Dependabot: Check at https://github.com/$REPO/settings/security_analysis"
    log_info "  - CodeQL: Check at https://github.com/$REPO/security/code-scanning"
}

# Main execution
main() {
    echo ""
    log_info "GitHub Repository Setup Script"
    log_info "Repository: $REPO"
    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN MODE - No changes will be made"
    fi
    echo ""

    check_prerequisites
    echo ""

    configure_repository_metadata
    echo ""

    configure_security_features
    echo ""

    configure_branch_protection
    echo ""

    verify_configuration
    echo ""

    log_success "GitHub repository setup complete!"
    echo ""
    log_info "Next steps:"
    log_info "  1. Enable Dependabot alerts and security updates via GitHub UI"
    log_info "  2. Enable CodeQL scanning via GitHub UI"
    log_info "  3. Wait for CI workflow to run, then verify status checks in branch protection"
    log_info "  4. Test branch protection by attempting a direct push to main (should be blocked)"
    echo ""
    log_info "Configuration guide: specs/009-github-maintenance/checklists/github-settings.md"
}

main
