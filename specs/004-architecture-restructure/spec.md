# Feature Specification: Architecture Restructure

**Feature Branch**: `004-architecture-restructure`
**Created**: 2025-10-24
**Status**: Draft
**Input**: User description: "Restructure codebase architecture with optimized folder organization, token-efficient SKILL.md following Skills best practices, and improved progressive disclosure patterns"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - AI Agent Can Navigate Skill Efficiently (Priority: P1)

When an AI agent (Claude) needs to use the browser debugger skill, it should be able to quickly find relevant information without loading excessive context. The agent should read only the main SKILL.md file initially, then progressively load additional reference files as needed for specific tasks.

**Why this priority**: This is the core value proposition. Token efficiency directly impacts agent performance, cost, and context window utilization. Without this, the skill cannot scale to complex debugging scenarios.

**Independent Test**: Can be fully tested by invoking the skill with various debugging requests and measuring tokens consumed. Should see <500 lines loaded initially from SKILL.md, with additional context loaded only when needed.

**Acceptance Scenarios**:

1. **Given** AI agent receives a request to extract DOM from a webpage, **When** agent loads the skill, **Then** agent reads SKILL.md (under 500 lines) with clear navigation to DOM extraction workflow
2. **Given** AI agent needs Chrome 136+ requirements, **When** agent reads SKILL.md, **Then** agent finds reference link to chrome-136-requirements.md and loads only that file
3. **Given** AI agent needs to troubleshoot CDP connection issues, **When** agent navigates skill, **Then** agent finds reference to troubleshooting.md and loads it independently from other docs

---

### User Story 2 - Developer Can Locate Scripts by Function (Priority: P1)

When a developer or AI agent needs to run a specific script (collector, utility, orchestrator), they should find it organized by function in clearly named subdirectories with an index explaining each script's purpose.

**Why this priority**: Current root-level clutter makes scripts hard to discover. This directly impacts usability for both humans and agents. Essential for adoption and maintenance.

**Independent Test**: Can be tested by navigating the scripts/ directory and verifying all scripts are categorized correctly with a README index.

**Acceptance Scenarios**:

1. **Given** developer needs to run console log collector, **When** they check scripts directory, **Then** they find cdp-console.py in scripts/collectors/ with description in scripts/README.md
2. **Given** AI agent needs to launch Chrome with CDP, **When** agent reads SKILL.md, **Then** agent sees clear path to scripts/core/chrome-launcher.sh
3. **Given** developer wants to clean up Chrome processes, **When** they explore utilities, **Then** they find scripts/utilities/cleanup-chrome.sh with usage docs

---

### User Story 3 - Maintainer Can Update Documentation Without Affecting Core (Priority: P2)

When documentation needs updates (new workflows, troubleshooting tips, CDP command examples), maintainer should be able to edit reference files in docs/ without touching SKILL.md or breaking existing references.

**Why this priority**: Supports long-term maintenance. Lower priority than P1 because it's about maintainability rather than immediate functionality, but still critical for sustainable development.

**Independent Test**: Can be tested by adding new content to docs/guides/workflows.md and verifying SKILL.md references work correctly without modification.

**Acceptance Scenarios**:

1. **Given** maintainer wants to add new troubleshooting entry, **When** they edit docs/guides/troubleshooting.md, **Then** change is available to agents via existing SKILL.md reference
2. **Given** maintainer updates Chrome 136 requirements, **When** they edit docs/reference/chrome-136-requirements.md, **Then** SKILL.md links continue to work without updates
3. **Given** maintainer adds new workflow pattern, **When** they edit docs/guides/workflows.md, **Then** pattern is discoverable via SKILL.md workflow section

---

### User Story 4 - Team Member Can Onboard Quickly (Priority: P3)

When a new team member or contributor joins the project, they should understand the project structure by reading clear documentation that explains folder organization, script categories, and navigation patterns.

**Why this priority**: Nice to have for team growth but not blocking core functionality. Can be addressed after core restructuring is validated.

**Independent Test**: Can be tested by having someone unfamiliar with the project read CLAUDE.md and README.md, then successfully run a workflow.

**Acceptance Scenarios**:

1. **Given** new contributor reads CLAUDE.md, **When** they want to understand project layout, **Then** they see clear explanation of scripts/core, scripts/collectors, scripts/utilities organization
2. **Given** new contributor wants to add a CDP collector, **When** they check scripts/README.md, **Then** they see examples and understand where to place new collectors
3. **Given** new contributor needs to run tests, **When** they check project docs, **Then** they find clear paths to tests/ and know how to execute smoke tests

---

### Edge Cases

- What happens when SKILL.md references are broken (file moved/renamed)? → Validation tests should catch broken links
- How does system handle very large reference files (>1000 lines)? → Should be split further or use table of contents pattern
- What if agent loads wrong reference file? → Clear, specific naming and strong descriptions in SKILL.md prevent mis-navigation
- How to handle legacy paths in old documentation? → Migration plan should update all docs atomically

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: SKILL.md MUST be reduced to under 500 lines following Skills best practices token efficiency guideline
- **FR-002**: System MUST organize scripts into three categories: core (orchestration), collectors (CDP monitors), and utilities (helpers)
- **FR-003**: SKILL.md MUST use progressive disclosure pattern with reference links to detailed documentation files
- **FR-004**: System MUST provide scripts/README.md index explaining purpose and usage of each script
- **FR-005**: All CDP collector scripts (cdp-console.py, cdp-network.py, cdp-network-with-body.py, cdp-dom-monitor.py, cdp-summarize.py) MUST be moved to scripts/collectors/
- **FR-006**: Core orchestration scripts (chrome-launcher.sh, debug-orchestrator.sh) MUST be moved to scripts/core/
- **FR-007**: Utility scripts (cdp-query.sh, cleanup-chrome.sh, save-session.sh, resume-session.sh) MUST be moved to scripts/utilities/
- **FR-008**: System MUST create domain-specific documentation files: chrome-136-requirements.md, workflows.md, cdp-commands.md, troubleshooting.md in docs/
- **FR-009**: All active documentation (README.md, CLAUDE.md, SKILL.md, docs/*.md, tests/*.sh) referencing script paths MUST be updated to reflect new structure (historical specs/001-003 excluded per Assumptions)
- **FR-010**: install.sh MUST be updated to handle new script paths for symlink/copy installation
- **FR-011**: CLAUDE.md MUST document new folder structure and navigation patterns
- **FR-012**: Reference files MUST be one level deep from SKILL.md (no nested references beyond SKILL.md → reference.md)
- **FR-013**: Longer reference files (>100 lines) MUST include table of contents at top
- **FR-014**: System MUST preserve all existing functionality while reorganizing structure
- **FR-015**: All file paths MUST use forward slashes (Unix-style) for cross-platform compatibility

### Non-Functional Requirements

- **NFR-001**: SKILL.md restructure must reduce initial token load to ≤500 lines (at least 55% reduction from 1114 lines baseline)
- **NFR-002**: Migration must be non-breaking - all existing scripts must work with updated paths
- **NFR-003**: Documentation updates must maintain consistency across all files (README.md, CLAUDE.md, SKILL.md, docs/*)
- **NFR-004**: New structure must be validated by running existing smoke tests successfully

### Key Entities *(data/file structure)*

- **SKILL.md**: Main entry point, under 500 lines, contains overview and navigation links to reference files
- **scripts/core/**: Orchestration layer (chrome-launcher.sh, debug-orchestrator.sh)
- **scripts/collectors/**: CDP monitoring scripts (cdp-console.py, cdp-network*.py, cdp-dom-monitor.py, cdp-summarize.py)
- **scripts/utilities/**: Helper scripts (cleanup, session management, CDP queries)
- **docs/**: Reference documentation split by domain (chrome-136-requirements.md, workflows.md, cdp-commands.md, troubleshooting.md)
- **scripts/README.md**: Script index and usage guide

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: SKILL.md reduces from 1114 lines to ≤500 lines (55%+ reduction)
- **SC-002**: AI agent initial context load is under 500 lines when skill is invoked
- **SC-003**: All existing smoke tests pass after restructure without modification
- **SC-004**: Scripts are organized into three clear categories with 100% of scripts moved from root
- **SC-005**: Zero broken references in documentation after migration (validated by link checker or manual review)
- **SC-006**: install.sh successfully installs skill with new structure in both symlink and copy modes
- **SC-007**: All documentation files consistently reference new paths (README.md, CLAUDE.md, SKILL.md, docs/*)

### Qualitative Outcomes

- Developer can locate any script's purpose and location within 30 seconds by reading scripts/README.md
- AI agent can navigate to specific functionality without loading irrelevant context
- New contributors can understand project structure from CLAUDE.md alone
- Maintainers can update domain-specific docs without touching SKILL.md

## Assumptions

- Existing specs/001-003 documentation does not need updates (they document historical features)
- Tests in tests/ directory remain in place with minimal path updates
- install.sh can be modified to support new paths without breaking existing installations
- No external tools or scripts outside this repository reference the current root-level script paths
- Skills best practices document (docs/skills-best-practices.md) remains authoritative for this restructure

## Out of Scope

- Creating new CDP functionality or debugging features
- Refactoring Python/Bash script internals (only moving files, not rewriting)
- Updating spec-kit integration beyond path references
- Creating automated link validation tools (manual validation sufficient for MVP)
- Performance optimizations beyond token efficiency improvements
- Adding new documentation content (only restructuring existing content)

## Dependencies

- Skills best practices document (docs/skills-best-practices.md, docs/skills.md)
- Existing install.sh installation mechanism
- Existing smoke tests for validation
- Git for version control and branch management

## Constraints

- Must maintain backward compatibility for skill invocation (users should not need to change how they invoke the skill)
- Cannot break existing workflow patterns that depend on script outputs
- SKILL.md must remain the single entry point (no multiple SKILL*.md files)
- Must follow Unix-style forward slashes for all paths
