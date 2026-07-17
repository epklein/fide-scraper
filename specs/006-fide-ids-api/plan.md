# Implementation Plan: Fetch FIDE IDs from API and Augment Players File

**Branch**: `006-fide-ids-api` | **Date**: 2025-12-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-fide-ids-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Extend the FIDE scraper to fetch player FIDE IDs from an external API endpoint (`https://chesshub.cloud/api/fide-ids/`) and merge them with the existing `FIDE_PLAYERS_FILE` CSV, with automatic deduplication. The merged player list is then used by the existing scraper to fetch ratings for both original and newly discovered players. This expands player coverage without requiring manual updates to the configuration file.

**Key deliverable**: A startup routine that fetches API IDs, deduplicates them against the CSV file, appends new entries, and passes the augmented list to the scraper's main loop.

## Technical Context

**Language/Version**: Python 3.9+ (matches existing codebase)
**Primary Dependencies**: `requests` (already in use for FIDE and API calls), `python-dotenv` (for env vars)
**Storage**: CSV file (FIDE_PLAYERS_FILE) - existing players list
**Testing**: `pytest` (existing test framework in tests/)
**Target Platform**: Linux server (deployment via Docker/Hostinger K8s)
**Project Type**: Single CLI script + test suite
**Performance Goals**: API ID fetch + merge completes in <10 seconds for typical workloads (100-1000 IDs)
**Constraints**: Must not block scraper if API is unavailable; must preserve existing CSV format exactly
**Scale/Scope**: Integrates with existing `fide_scraper.py` main function; ~300-500 lines of new code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Requirements (from `.specify/memory/constitution.md`)**:

| Principle | Requirement | Status |
|-----------|------------|--------|
| **Code Quality** | Maintain clear structure, documentation, best practices | ✓ PASS - New functions will be modular, well-documented |
| **Testing** | Write tests for critical functionality | ✓ PASS - Merge logic, API fetch, and edge cases will have unit tests |
| **Simplicity** | Keep codebase simple, avoid unnecessary complexity | ✓ PASS - Reuses existing requests/CSV patterns; straightforward merge logic |
| **Documentation** | Keep README.md up to date | ✓ PASS - Will update README with FIDE_IDS_API_ENDPOINT configuration |

**Gate Status**: ✓ PASS - Feature aligns with all constitution principles

## Project Structure

### Documentation (this feature)

```text
specs/006-fide-ids-api/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command) - NOT NEEDED: API spec already provided
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command) - API contract definition
├── spec.md              # Feature specification
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

**Selected**: Option 1 - Single CLI script (existing pattern)

```text
# Existing structure - minimal changes
fide_scraper.py         # Main script - will add new functions here
  ├── fetch_fide_ids_from_api()     # NEW: Fetch IDs from API
  ├── merge_player_ids()             # NEW: Merge & deduplicate with CSV
  ├── augment_players_file()         # NEW: Write augmented CSV
  └── main()                          # MODIFY: Call augment before scraping

tests/
├── test_fide_scraper.py            # EXTEND: Add tests for new functions
├── test_integration.py             # EXTEND: Test full integration flow
└── test_validation.py              # Already covers CSV validation

.env                                 # MODIFY: Add FIDE_IDS_API_ENDPOINT config
.env.example                        # MODIFY: Add FIDE_IDS_API_ENDPOINT example
README.md                           # MODIFY: Document new configuration
```

**Structure Decision**: No new directories created. Feature is a cohesive set of functions integrated into the existing single-script architecture. Follows the pattern already established by the ratings API integration (feature 005-ratings-api-integration).

## Complexity Tracking

**No constitutional violations** - Feature is straightforward and fits existing patterns.
