# Implementation Plan: FIDE Rating Scraper (with Blitz Rating Support)

**Branch**: `001-fide-rating-scraper` | **Date**: 2025-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-fide-rating-scraper/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Extend the existing FIDE rating scraper to include blitz rating extraction alongside standard and rapid ratings. The implementation follows the same pattern as existing rating extraction functions, using the documented HTML selector `div.profile-blitz` from research.md. This enhancement requires adding a new extraction function, updating the output formatting, and extending test coverage.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: requests>=2.31.0, beautifulsoup4>=4.12.0  
**Storage**: N/A (ephemeral data, no persistence)  
**Testing**: pytest  
**Target Platform**: Cross-platform (Linux, macOS, Windows)  
**Project Type**: Single script (CLI tool)  
**Performance Goals**: < 5 seconds response time under normal network conditions  
**Constraints**: Single HTTP request per execution, 10-second timeout, no retries  
**Scale/Scope**: Single-user CLI tool, processes one FIDE ID per execution

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Code Quality ✅
- **Status**: PASS
- **Rationale**: Implementation follows existing patterns (extract_standard_rating, extract_rapid_rating), maintains consistent code style, and adds clear documentation

### II. Testing ✅
- **Status**: PASS
- **Rationale**: New blitz rating extraction function will have unit tests following existing test patterns. Integration tests will verify end-to-end blitz rating retrieval

### III. Simplicity ✅
- **Status**: PASS
- **Rationale**: Feature adds minimal complexity - single new extraction function following established pattern, no architectural changes required

**Overall**: All constitution gates pass. Feature is a straightforward extension of existing functionality.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
fide_scraper.py          # Main script with rating extraction functions
requirements.txt         # Python dependencies
README.md               # Project documentation

tests/
├── test_fide_scraper.py    # Unit tests for rating extraction functions
└── test_integration.py     # Integration tests for end-to-end flows
```

**Structure Decision**: Single script project. The project uses a flat structure with the main script at the root and tests in a `tests/` directory. This structure is appropriate for a simple CLI tool with minimal complexity.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - all constitution gates pass. Feature is a simple extension of existing functionality.
