# Tasks: Architecture Restructure

**Input**: Design documents from `/specs/004-architecture-restructure/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/file-operations.md

**Tests**: No test tasks included (tests were not requested in the feature specification)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure for script reorganization

- [x] T001 Create scripts/core/ directory
- [x] T002 Create scripts/collectors/ directory
- [x] T003 Create scripts/utilities/ directory

**Checkpoint**: Directory structure ready for file moves

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: File reorganization that MUST be complete before ANY documentation work can begin

**⚠️ CRITICAL**: No documentation work can begin until this phase is complete

- [x] T004 Move cdp-console.py to scripts/collectors/cdp-console.py
- [x] T005 Move cdp-dom-monitor.py to scripts/collectors/cdp-dom-monitor.py
- [x] T006 Move cdp-network.py to scripts/collectors/cdp-network.py
- [x] T007 Move cdp-network-with-body.py to scripts/collectors/cdp-network-with-body.py
- [x] T008 Move cdp-summarize.py to scripts/collectors/cdp-summarize.py
- [x] T009 Move chrome-launcher.sh to scripts/core/chrome-launcher.sh
- [x] T010 Move debug-orchestrator.sh to scripts/core/debug-orchestrator.sh
- [x] T011 Move scripts/cdp-query.sh to scripts/utilities/cdp-query.sh
- [x] T012 Move scripts/cleanup-chrome.sh to scripts/utilities/cleanup-chrome.sh
- [x] T013 Move scripts/resume-session.sh to scripts/utilities/resume-session.sh
- [x] T014 Move scripts/save-session.sh to scripts/utilities/save-session.sh
- [x] T015 Verify all scripts execute from new locations by running tests/smoke-test-cleanup.sh successfully (exit code 0)

**T015 Acceptance Criteria**:
- Run `bash tests/smoke-test-cleanup.sh` from repository root
- Test exits with code 0 (success)
- All scripts referenced by test execute without "command not found" errors
- Chrome launches successfully with CDP enabled

**Checkpoint**: Foundation ready - all scripts relocated, documentation updates can now begin in parallel

---

## Phase 3: User Story 1 - AI Agent Can Navigate Skill Efficiently (Priority: P1) 🎯 MVP

**Goal**: Enable AI agents to quickly find relevant information without loading excessive context by reducing SKILL.md to <500 lines with progressive disclosure pattern

**Independent Test**: Invoke the skill with various debugging requests and verify SKILL.md is <500 lines with clear navigation to reference documentation. Agent should load only needed context on demand.

### Implementation for User Story 1

- [x] T016 [P] [US1] Extract Chrome 136 requirements section from SKILL.md and create docs/chrome-136-requirements.md
- [x] T017 [P] [US1] Extract workflows section from SKILL.md and create docs/workflows.md
- [x] T018 [P] [US1] Extract CDP commands section from SKILL.md and create docs/cdp-commands.md
- [x] T019 [P] [US1] Extract troubleshooting section from SKILL.md and create docs/troubleshooting.md
- [x] T020 [US1] Rewrite SKILL.md to under 500 lines with progressive disclosure links to docs/chrome-136-requirements.md, docs/workflows.md, docs/cdp-commands.md, docs/troubleshooting.md
- [x] T021 [US1] Verify SKILL.md is under 500 lines and all reference links work correctly

**Checkpoint**: At this point, User Story 1 should be fully functional - SKILL.md <500 lines with working progressive disclosure pattern

---

## Phase 4: User Story 2 - Developer Can Locate Scripts by Function (Priority: P1)

**Goal**: Enable developers and AI agents to find scripts organized by function in clearly named subdirectories with an index

**Independent Test**: Navigate the scripts/ directory and verify all scripts are categorized correctly with README index. Developer can locate any script purpose within 30 seconds.

### Implementation for User Story 2

- [x] T022 [US2] Create scripts/README.md with organization overview and script index table covering all 12 scripts in core/, collectors/, and utilities/
- [x] T023 [US2] Update SKILL.md to add reference link to scripts/README.md in progressive disclosure section
- [x] T024 [US2] Verify scripts/README.md lists all scripts with descriptions and correct paths

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - token-efficient SKILL.md + organized script catalog

---

## Phase 5: User Story 3 - Maintainer Can Update Documentation Without Affecting Core (Priority: P2)

**Goal**: Enable maintainers to update reference files in docs/ without touching SKILL.md or breaking existing references

**Independent Test**: Add new content to docs/workflows.md and verify SKILL.md references work correctly without modification. Verify reference files have table of contents if >100 lines.

### Implementation for User Story 3

- [x] T025 [P] [US3] Add table of contents to docs/workflows.md (if >100 lines per FR-013)
- [x] T026 [P] [US3] Add table of contents to docs/cdp-commands.md (if >100 lines per FR-013)
- [x] T027 [P] [US3] Add table of contents to docs/troubleshooting.md (if >100 lines per FR-013)
- [x] T028 [US3] Verify all reference files follow one-level deep pattern from SKILL.md (no nested references)
- [x] T029 [US3] Test adding new section to docs/workflows.md and verify SKILL.md link resolves to file, new content is accessible, and SKILL.md requires no modification

**Checkpoint**: All user stories should now be independently functional - maintainable documentation structure validated

---

## Phase 6: User Story 4 - Team Member Can Onboard Quickly (Priority: P3)

**Goal**: Enable new team members to understand project structure by reading clear documentation

**Independent Test**: Have someone unfamiliar with the project read CLAUDE.md and README.md, then successfully run a workflow.

### Implementation for User Story 4

- [x] T030 [P] [US4] Update CLAUDE.md project structure section with new scripts/core, scripts/collectors, scripts/utilities organization
- [x] T031 [P] [US4] Update README.md with new script paths in examples and usage documentation
- [x] T032 [US4] Update install.sh to handle new script paths in both symlink and copy modes (per FR-010)
- [x] T033 [US4] Verify install.sh works in symlink mode with new structure
- [x] T034 [US4] Verify install.sh works in copy mode with new structure

**Checkpoint**: Complete onboarding documentation with working installation

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup that affects multiple user stories

- [x] T035 [P] Update all documentation files (README.md, CLAUDE.md, docs/*.md) to replace old script paths with new categorized paths
- [x] T036 [P] Grep repository for old script paths (cdp-console.py, chrome-launcher.sh at root) and fix any remaining references
- [x] T036.5 [P] Validate all file paths use forward slashes (Unix-style) by grepping for backslashes in documentation and script files
- [x] T037 Run tests/smoke-test-cleanup.sh to validate all scripts work from new locations (SC-003)
- [x] T038 Verify zero broken references in documentation by checking all links in SKILL.md and docs/*.md files resolve to existing files (SC-005)

**T038 Validation Procedure**:
1. Extract all relative file links from SKILL.md: `grep -o 'docs/[^)]*\.md' SKILL.md`
2. For each link, verify file exists: `test -f <path> && echo "✓" || echo "✗ BROKEN"`
3. Repeat for docs/*.md files referencing other docs
4. All links must resolve (no broken references)
- [x] T039 Verify SKILL.md line count is <500 lines (SC-001)
- [x] T040 Verify all 12 scripts organized into 3 categories with 100% moved from root (SC-004)
- [x] T041 Verify all documentation files consistently reference new paths (SC-007)
- [x] T042 Run quickstart.md validation by following Phase 1-9 steps

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P1): Can start after Foundational - Depends on US1 for SKILL.md reference link (T023)
  - User Story 3 (P2): Can start after US1 (needs reference files created)
  - User Story 4 (P3): Can start after Foundational - Updates different files (README.md, CLAUDE.md, install.sh)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Creates reference documentation files
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Needs US1 complete for SKILL.md reference link update (T023 depends on T020)
- **User Story 3 (P2)**: Can start after US1 (needs docs/workflows.md, docs/cdp-commands.md, docs/troubleshooting.md from T016-T019)
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Independent of other user stories (different files)

### Within Each User Story

**User Story 1**:
- T016-T019 (extract docs) can run in parallel [P]
- T020 (rewrite SKILL.md) depends on T016-T019 completing
- T021 (verify) depends on T020

**User Story 2**:
- T022 (create scripts/README.md) can start after Foundational
- T023 (update SKILL.md link) depends on T020 (US1) and T022
- T024 (verify) depends on T022

**User Story 3**:
- T025-T027 (add TOCs) can run in parallel [P]
- T028 (verify one-level deep) can run after T025-T027
- T029 (test workflow update) can run after T016 (US1)

**User Story 4**:
- T030-T031 (update docs) can run in parallel [P]
- T032 (update install.sh) can run in parallel with docs
- T033-T034 (verify install) must run sequentially after T032

### Parallel Opportunities

- **Setup (Phase 1)**: All 3 directory creation tasks (T001-T003) can run as single `mkdir -p` command
- **Foundational (Phase 2)**: All file moves (T004-T014) can run in parallel using multiple `git mv` commands
- **User Story 1**: Extract tasks (T016-T019) can run in parallel [P]
- **User Story 2**: After US1 complete, all tasks independent
- **User Story 3**: TOC tasks (T025-T027) can run in parallel [P]
- **User Story 4**: Doc updates (T030-T031) and install.sh (T032) can run in parallel [P]
- **Polish (Phase 7)**: Doc path updates (T035-T036) can run in parallel [P]

---

## Parallel Example: User Story 1

```bash
# Launch all extract tasks for User Story 1 together:
Task: "Extract Chrome 136 requirements section from SKILL.md and create docs/chrome-136-requirements.md"
Task: "Extract workflows section from SKILL.md and create docs/workflows.md"
Task: "Extract CDP commands section from SKILL.md and create docs/cdp-commands.md"
Task: "Extract troubleshooting section from SKILL.md and create docs/troubleshooting.md"

# Then sequentially:
Task: "Rewrite SKILL.md to under 500 lines with progressive disclosure links"
Task: "Verify SKILL.md is under 500 lines and all reference links work"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T015) - CRITICAL foundation
3. Complete Phase 3: User Story 1 (T016-T021) - Token-efficient SKILL.md
4. Complete Phase 4: User Story 2 (T022-T024) - Script organization
5. **STOP and VALIDATE**: Test that SKILL.md <500 lines, scripts organized, progressive disclosure works
6. Deploy/demo if ready (core value delivered: token efficiency + organization)

### Incremental Delivery

1. Complete Setup + Foundational → File structure ready
2. Add User Story 1 → Test SKILL.md token efficiency → MVP delivered!
3. Add User Story 2 → Test script discoverability → Enhanced MVP
4. Add User Story 3 → Test maintainability → Production ready
5. Add User Story 4 → Test onboarding → Fully polished

### Single Developer Strategy

Execute in priority order:
1. Setup + Foundational (atomic, must complete together)
2. User Story 1 (P1) - Core value: token efficiency
3. User Story 2 (P1) - Core value: script organization
4. User Story 3 (P2) - Maintainability improvement
5. User Story 4 (P3) - Onboarding improvement
6. Polish - Final validation

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- This is a documentation refactoring project - no new functionality added
- All existing smoke tests must pass after completion (SC-003)
- Commit after each phase or user story completion
- Use `git mv` for file moves to preserve history
- Avoid: breaking existing script functionality, creating nested references beyond one level

---

## Task Summary

**Total Tasks**: 43

**Tasks per User Story**:
- Setup (Phase 1): 3 tasks
- Foundational (Phase 2): 12 tasks (BLOCKS all user stories)
- User Story 1 (P1 - Token Efficiency): 6 tasks
- User Story 2 (P1 - Script Organization): 3 tasks
- User Story 3 (P2 - Maintainability): 5 tasks
- User Story 4 (P3 - Onboarding): 5 tasks
- Polish (Phase 7): 9 tasks

**Parallel Opportunities**: 19 tasks marked [P]

**Independent Test Criteria**:
- US1: SKILL.md <500 lines, progressive disclosure links work
- US2: scripts/README.md exists with all 12 scripts indexed
- US3: Can update reference docs without touching SKILL.md
- US4: New contributor can follow README.md to run workflows

**Suggested MVP Scope**: User Story 1 + User Story 2 (core token efficiency + script organization value)

**Format Validation**: ✅ All tasks follow checklist format (checkbox, ID, labels, file paths)
