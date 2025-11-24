# Implementation Plan: Player Rating Change Email Notifications

**Branch**: `003-player-rating-emails` | **Date**: 2025-11-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-player-rating-emails/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Integrate email notification capability into the FIDE rating scraper. The system will:
1. Load player data from a unified `players.csv` file (with optional email addresses)
2. Detect rating changes for all players (comparing to previous records in the historical CSV)
3. Send email notifications only to players who have configured email addresses and experienced rating changes
4. CC all notifications to an administrator email address (`ADMIN_CC_EMAIL`)

This feature consolidates player input data into a single CSV file format (replacing separate `fide_ids.txt`) while adding selective email notification capability based on player opt-in status.

## Technical Context

**Language/Version**: Python 3.x (existing project standard, inferred from codebase)
**Primary Dependencies**:
- `requests` - HTTP client for FIDE profile fetching (existing)
- `beautifulsoup4` - HTML parsing (existing)
- `python-dotenv` - Environment variable management (existing)
- `smtplib` - Email sending (Python standard library)
- `email.mime` - Email message composition (Python standard library)

**Storage**: CSV files (existing approach) - `fide_ratings.csv` (historical ratings), new `players.csv` (player input with optional emails)
**Testing**: `pytest` (existing project uses pytest, visible in test structure)
**Target Platform**: Linux/WSL server environment (batch-oriented, no UI)
**Project Type**: Single CLI script for batch rating scraping with integrated email notifications
**Performance Goals**: Process 100+ players per batch run within 5-minute notification delivery window (SC-001)
**Constraints**:
- No external API for email sending; use SMTP (environment-configured)
- Handle missing SMTP gracefully; don't crash scraper (FR-013)
- Process all players regardless of email presence (FR-002)

**Scale/Scope**:
- Player base: Initially assumed 100-1000 players (from edge case testing: 100 concurrent notifications)
- Data: One CSV file for player data (`players.csv`), one historical CSV for rating records (`fide_ratings.csv`)
- Notifications: Only for players with configured emails experiencing rating changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Principles Applied**:

| Principle | Requirement | Status |
|-----------|-------------|--------|
| I. Code Quality | Clear structure, documentation, best practices | ✓ OK - Adding modular email/notification functions with docstrings |
| II. Testing | Tests for critical functionality | ✓ OK - Email sending, change detection, CSV parsing require tests |
| III. Simplicity | Simple, maintainable codebase | ✓ OK - Extending existing scraper without major refactoring |
| IV. Documentation | Keep README.md up to date | ✓ OK - Will document new `players.csv` format and env vars |

**Gate Status**: ✅ **PASS** - Feature design aligns with all constitution principles. No violations or justifications needed.

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
# Single CLI Python script (existing structure maintained)
fide_scraper.py           # Main script - will be extended with email notification logic

# Input/Output files
players.csv               # NEW: Unified player data file (FIDE ID, optional email)
fide_ratings.csv          # EXISTING: Historical rating records (date-indexed)

# Configuration
.env                      # EXISTING: Contains FIDE_PLAYERS_FILE, ADMIN_CC_EMAIL, SMTP config

# Testing
tests/
├── test_fide_scraper.py  # EXISTING: Extend with email notification tests
├── test_integration.py   # EXISTING: Extend with end-to-end tests
└── fixtures/             # NEW: Sample players.csv, mock email data
```

**Structure Decision**: Single script architecture. The existing `fide_scraper.py` will be extended with:
- New module functions for player data loading (`load_player_data_from_csv()`)
- Change detection logic (`detect_rating_changes()`)
- Email notification functions (`send_email_notification()`, `compose_notification_email()`)
- Integration into existing `main()` and `process_batch()` functions

No new files or subdirectories required. Maintains existing project simplicity (Principle III).

## Phase 0: Research & Resolution

**Status**: ✅ Complete - No NEEDS CLARIFICATION markers in spec. All critical ambiguities resolved during `/speckit.clarify`.

**Research Output**: See [research.md](research.md)

**Key Findings**:
1. **Email Library**: Python standard library `smtplib` + `email.mime` sufficient for SMTP-based notifications
2. **CSV Handling**: Leverage existing `csv` module usage in scraper
3. **Change Detection**: Compare latest record per player from historical CSV
4. **Error Handling**: Log and continue on email failures (don't crash scraper)

## Phase 1: Design & Contracts

**Status**: In Progress - Generating data model, contracts, and quickstart.

See generated artifacts:
- [data-model.md](data-model.md) - Player, Rating, and Notification entities
- [contracts/](contracts/) - Function signatures and data structures
- [quickstart.md](quickstart.md) - Quick reference for implementation

## Phase 1.5: Agent Context Update

**Status**: Pending - Will be executed after Phase 1 design completion.

Command: `.specify/scripts/bash/update-agent-context.sh claude`

This updates the AI agent context with new technology discoveries.

---

## Completion Status: Phase 1

✅ **COMPLETE** - All Phase 1 artifacts generated:

1. **research.md** (7.6 KB) - Design decisions & technology choices
   - Email library selection (smtplib + email.mime)
   - CSV parsing approach (csv.DictReader)
   - Change detection algorithm (historical CSV comparison)
   - Environment variables & configuration
   - Error handling strategy
   - Testing strategy

2. **data-model.md** (14.9 KB) - Complete entity definitions
   - Player Record entity (`players.csv`)
   - Rating Record entity (historical data structure)
   - Rating Change Record (computed)
   - Email Notification Record (audit trail)
   - State transitions & validation rules
   - Data storage & retrieval patterns
   - Sequence diagrams & example data flows

3. **quickstart.md** (10.0 KB) - Developer implementation guide
   - Environment setup (new env vars)
   - Code architecture (5 new functions + integration points)
   - Implementation checklist (4 phases)
   - Error handling reference
   - Testing strategy (unit, integration, fixtures)
   - Deployment checklist
   - Performance considerations

4. **contracts/functions.md** (10.2 KB) - API specifications
   - 8 function contracts (signatures, parameters, returns, exceptions)
   - CSV loading functions
   - Validation functions
   - Change detection functions
   - Email composition & sending functions
   - Integrated batch processing
   - Data structure definitions
   - Error codes & logging conventions

5. **plan.md** (This file) - Implementation roadmap
   - Technical context & dependencies
   - Constitution check (✅ PASS)
   - Project structure
   - Phase progression tracking

---

## Next Phase: Task Generation

**Next Command**: `/speckit.tasks`

This will:
1. Analyze all Phase 1 artifacts (research, data-model, quickstart, contracts)
2. Extract implementation tasks from the quickstart checklist
3. Generate `tasks.md` with dependency-ordered, actionable tasks
4. Each task mapped to specific function contracts & acceptance criteria
5. Ready for immediate implementation or team assignment

---

## Summary of Artifacts

| Artifact | Purpose | Size | Status |
|----------|---------|------|--------|
| spec.md | Feature requirements & acceptance criteria | 13.6 KB | ✅ Complete (earlier phase) |
| research.md | Design decisions & technology choices | 7.6 KB | ✅ Complete |
| data-model.md | Entity definitions & relationships | 14.9 KB | ✅ Complete |
| quickstart.md | Developer implementation guide | 10.0 KB | ✅ Complete |
| contracts/functions.md | API specifications & signatures | 10.2 KB | ✅ Complete |
| plan.md | Implementation roadmap (THIS FILE) | 6.3 KB | ✅ Complete |
| **Total** | **Phase 1 Design Artifacts** | **~62.6 KB** | **✅ COMPLETE** |

---

## Key Design Decisions Locked In

1. ✅ **Input Format**: Single `players.csv` (consolidates `fide_ids.txt`)
2. ✅ **Email Library**: Python stdlib `smtplib` + `email.mime` (no external deps)
3. ✅ **Change Detection**: Historical CSV comparison (O(1) per player)
4. ✅ **Error Handling**: Log and continue (never crash scraper)
5. ✅ **Configuration**: Environment variables (`FIDE_PLAYERS_FILE`, `ADMIN_CC_EMAIL`, `SMTP_*`)
6. ✅ **Testing**: pytest with mocked SMTP and fixtures
7. ✅ **Architecture**: Extend single `fide_scraper.py` (no new files/modules)

All decisions aligned with project principles:
- **Simplicity** ✓ (stdlib only, minimal additions)
- **Testability** ✓ (clear function contracts, mockable)
- **Maintainability** ✓ (error handling, logging, documentation)
- **Code Quality** ✓ (docstrings, type hints, consistent patterns)
