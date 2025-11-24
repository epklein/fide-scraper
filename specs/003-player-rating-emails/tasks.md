# Implementation Tasks: Player Rating Change Email Notifications

**Feature**: 003-player-rating-emails
**Date**: 2025-11-23
**Status**: Ready for Implementation
**Specification**: [spec.md](spec.md)

---

## Overview & Implementation Strategy

This feature adds email notification capability to the FIDE rating scraper. The implementation is organized into **5 phases** aligned with user story priorities, enabling incremental delivery and independent testing.

### MVP Scope (First Increment)

**Minimum Viable Product**: Complete User Story 1 (Load Player Data)
- Load `players.csv` with FIDE IDs and optional emails
- Validate data with graceful error handling
- Provides foundation for all subsequent stories
- Independently testable: CSV loading works before email sending is implemented

### Incremental Delivery Path

1. **Phase 1 (Setup)**: Project infrastructure (env vars, config)
2. **Phase 2 (Foundational)**: Core utilities (validation functions, CSV loading)
3. **Phase 3 (US1)**: Load Player Data - CSV handling
4. **Phase 4 (US2)**: Detect Rating Changes - historical comparison logic
5. **Phase 5 (US3)**: Send Email Notifications - SMTP integration
6. **Phase 6 (US4)**: CC Default Email - admin monitoring
7. **Phase 7 (Polish)**: Documentation, README, edge cases

### Parallelization Opportunities

- **Within US1**: Validation functions (email, FIDE ID) can be developed in parallel
- **Within US2**: Historical data loading and change detection can be developed concurrently
- **Within US3**: Email composition and SMTP sending can be parallelized
- **Between Stories**: Once US1 complete, team can split: some work on US2, others on US3

### Independent Testing per Story

Each user story can be tested independently without later stories:
- **US1 tested alone**: Load players.csv, verify data structures
- **US1+US2 tested together**: Load players, detect changes vs mock historical data
- **US1+US2+US3**: Full pipeline with test email account
- **US1+US2+US3+US4**: Complete feature with CC monitoring

---

## Phase 1: Setup & Configuration

**Goal**: Prepare environment and configuration for feature implementation

### Setup Tasks

- [x] T001 Update `.env.example` with new variables: `FIDE_PLAYERS_FILE`, `ADMIN_CC_EMAIL`, `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- [x] T002 Update `.env` file with actual values for local development (create sample `players.csv` path, test email)
- [x] T003 Create `players.csv` sample file in project root with 5-10 test players (mix of with/without emails)
- [x] T004 Update `README.md` with new feature description, configuration section, and example `players.csv` format

**Phase 1 Dependencies**: None (foundation for all following work)

---

## Phase 2: Foundational Functions & Utilities

**Goal**: Implement shared validation and utility functions needed by all user stories

### Foundational Tasks

- [x] T005 Implement `validate_fide_id(fide_id: str) -> bool` in `fide_scraper.py`
  - Validation rules: numeric, 4-10 digits, non-empty
  - Tests included in function docstring examples

- [x] T006 Implement `validate_email(email: str) -> bool` in `fide_scraper.py`
  - Pattern: `^[^\s@]+@[^\s@]+\.[^\s@]+$` (basic RFC)
  - Empty string treated as valid (opt-out)
  - Tests: valid email, invalid email, empty string

- [x] T007 Create test fixtures directory `tests/fixtures/` with sample data files
  - `tests/fixtures/players.csv` - test players with various email configurations
  - `tests/fixtures/fide_ratings_history.csv` - historical rating data for change detection

- [x] T008 Implement unit test file `tests/test_validation.py` for FIDE ID and email validation
  - Test `validate_fide_id()` with edge cases (3-digit, 11-digit, non-numeric)
  - Test `validate_email()` with valid/invalid formats
  - Both tests should pass with implementations from T005 & T006
  - ✅ All 11 tests passing

**Phase 2 Dependencies**: Phase 1 complete

---

## Phase 3: User Story 1 - Load Player Data with Optional Email Configuration (P1)

**Goal**: Enable system to read unified `players.csv` and make player data available for all downstream processing

**User Story Summary**: Load `players.csv` with FIDE IDs and optional emails, validate gracefully, handle errors

**Independent Test Criteria**:
- Can load valid `players.csv` file
- Can handle missing/empty email values gracefully
- Can validate FIDE IDs and emails with appropriate warnings
- Can handle missing/inaccessible files with clear error messages

### US1 - Player Data Loading Tasks

- [ ] T009 [US1] Implement `load_player_data_from_csv(filepath: str) -> Dict[str, Dict[str, str]]` in `fide_scraper.py`
  - Use `csv.DictReader` to parse `players.csv`
  - Validate each row (FIDE ID, email format)
  - Log warnings for invalid entries, skip them
  - Raise `FileNotFoundError` if file missing
  - Raise `ValueError` if CSV headers invalid
  - Return dict: `{fide_id: {"email": "..."}, ...}`
  - Reference: See contracts/functions.md for full signature

- [ ] T010 [US1] Implement `load_historical_ratings_by_player(filepath: str) -> Dict[str, Dict[str, Any]]` in `fide_scraper.py`
  - Load `fide_ratings.csv` (existing history file)
  - Index by FIDE ID, find latest record per player
  - Return empty dict if file doesn't exist (first run)
  - Structure: `{fide_id: {Date, Player Name, Standard, Rapid, Blitz}, ...}`
  - Reference: See contracts/functions.md for full signature

- [ ] T011 [US1] Add unit tests to `tests/test_fide_scraper.py` for player data loading
  - `test_load_player_data_from_csv_valid()` - load valid players.csv
  - `test_load_player_data_from_csv_invalid_email()` - handle invalid email
  - `test_load_player_data_from_csv_missing_email()` - handle empty email
  - `test_load_player_data_from_csv_file_not_found()` - handle missing file
  - `test_load_player_data_from_csv_invalid_headers()` - handle bad CSV format
  - All tests should pass

- [ ] T012 [US1] Integrate player data loading into existing `main()` function in `fide_scraper.py`
  - Replace `read_fide_ids_from_file(INPUT_FILENAME)` with `load_player_data_from_csv(FIDE_PLAYERS_FILE)`
  - Update error handling to use new exceptions
  - Ensure batch processing still works with new data structure
  - Run existing integration tests to verify no regression

**Phase 3 Dependencies**: Phase 2 complete
**Phase 3 Completion Criteria**: US1 independently testable and working

---

## Phase 4: User Story 2 - Detect Rating Changes (P1)

**Goal**: Identify which player ratings have changed between scraper runs

**User Story Summary**: Compare current ratings against historical data, detect changes in any rating type

**Independent Test Criteria**:
- Can detect numeric rating changes (e.g., 2440 → 2450)
- Can detect unrated → rated transitions
- Can detect which specific rating types changed (standard, rapid, blitz)
- Can correctly identify no changes when ratings stay the same

### US2 - Change Detection Tasks

- [ ] T013 [US2] Implement `detect_rating_changes(fide_id: str, new_ratings: Dict[str, Optional[int]], historical_data: Dict[str, Dict]) -> Dict[str, Tuple[Optional[int], Optional[int]]]` in `fide_scraper.py`
  - Compare new ratings against most recent historical record
  - Return dict of changed ratings: `{rating_type: (old, new), ...}`
  - Handle null/None values (unrated) vs numeric ratings
  - Return empty dict if no changes
  - Reference: See contracts/functions.md for full signature

- [ ] T014 [US2] Add unit tests to `tests/test_fide_scraper.py` for change detection
  - `test_detect_rating_changes_numeric_change()` - 2440 → 2450
  - `test_detect_rating_changes_unrated_to_rated()` - None → 2100
  - `test_detect_rating_changes_rated_to_unrated()` - 2100 → None
  - `test_detect_rating_changes_multiple_types()` - only some ratings changed
  - `test_detect_rating_changes_no_changes()` - all ratings same
  - `test_detect_rating_changes_missing_player()` - first time seeing player
  - All tests should pass

- [ ] T015 [US2] Update `process_batch()` function in `fide_scraper.py` to detect changes
  - Load historical data at start of batch
  - After fetching each player's ratings, call `detect_rating_changes()`
  - Store changes in player results structure
  - Update to return: `(results_with_changes, errors)`
  - Preserve all existing batch processing logic

- [ ] T016 [US2] Add integration test to `tests/test_integration.py` for change detection
  - `test_batch_with_change_detection()` - full pipeline: load players, load history, fetch ratings, detect changes
  - Verify changed ratings correctly identified
  - Verify unchanged ratings correctly identified
  - Run existing tests to verify no regression

**Phase 4 Dependencies**: Phase 3 (US1) complete
**Phase 4 Completion Criteria**: US2 independently testable, change detection working

---

## Phase 5: User Story 3 - Send Email Notifications to Players (P1)

**Goal**: Send email notifications when player ratings change

**User Story Summary**: Compose and send emails to players with changed ratings (if email configured)

**Independent Test Criteria**:
- Can compose properly formatted email with player info and rating changes
- Can send email via SMTP to valid recipient
- Can skip notification for players without configured email
- Can log and continue on email delivery failures

### US3 - Email Notification Tasks

- [ ] T017 [US3] Implement `compose_notification_email(player_name: str, fide_id: str, changes: Dict[str, Tuple[Optional[int], Optional[int]]], recipient_email: str, cc_email: Optional[str]) -> Tuple[str, str]` in `fide_scraper.py`
  - Compose subject: "Your FIDE Rating Update - [Player Name]"
  - Compose body with player info, changed ratings (before → after)
  - Handle multiple rating types
  - Return (subject, body)
  - Reference: See contracts/functions.md for full signature

- [ ] T018 [US3] Implement `send_email_notification(recipient: str, cc: Optional[str], subject: str, body: str) -> bool` in `fide_scraper.py`
  - Use `smtplib` + `email.mime` (Python stdlib)
  - Read SMTP config from env vars: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
  - Handle missing/invalid SMTP config gracefully (log warning, return False)
  - Handle connection failures (log error, return False)
  - Handle invalid recipient email (log error, return False)
  - Return True on success, False on any error
  - Never raise exception (always return bool)
  - Log all attempts with result (success/failure + reason)
  - Reference: See contracts/functions.md for full signature

- [ ] T019 [US3] Add unit tests to `tests/test_fide_scraper.py` for email functionality
  - `test_compose_notification_email_basic()` - verify subject and body format
  - `test_compose_notification_email_multiple_changes()` - multiple rating types changed
  - `test_compose_notification_email_content()` - verify FIDE ID, player name, old→new values included
  - Create `tests/fixtures/mock_smtp.py` with mock SMTP server for testing
  - `test_send_email_notification_success()` - successful send with mocked SMTP
  - `test_send_email_notification_missing_smtp_config()` - graceful failure when SMTP not configured
  - `test_send_email_notification_invalid_recipient()` - graceful failure for invalid email
  - `test_send_email_notification_smtp_error()` - graceful failure on connection error
  - All tests should pass

- [ ] T020 [US3] Integrate email sending into `process_batch()` in `fide_scraper.py`
  - After detecting changes for a player:
    - If changes detected AND email configured (non-empty):
      - Compose email
      - Send email notification
      - Log result
    - If no email configured: Log info "No email configured for FIDE ID X"
    - If email fails: Log error, continue with next player
  - Maintain all existing batch processing (CSV output, result tracking)

- [ ] T021 [US3] Add integration test to `tests/test_integration.py`
  - `test_batch_with_email_notifications()` - full pipeline with email sending
  - Use mock SMTP server
  - Verify emails sent only for players with changes + email configured
  - Verify emails skipped for players without email
  - Verify batch continues after email failure
  - Run all existing tests to verify no regression

**Phase 5 Dependencies**: Phase 4 (US1 + US2) complete
**Phase 5 Completion Criteria**: US3 independently testable, email notifications working

---

## Phase 6: User Story 4 - CC Default Email Address (P2)

**Goal**: Send CC to administrator for monitoring

**User Story Summary**: Include admin email on all notifications for oversight

**Independent Test Criteria**:
- Can compose email with CC header when admin email configured
- Can skip CC when admin email not configured (graceful degradation)
- Admin receives copy of player notification emails

### US4 - Admin CC Tasks

- [ ] T022 [US4] Update `send_email_notification()` to include CC header
  - Modify `compose_notification_email()` to accept and use `cc_email` parameter
  - Update email headers to include CC (via `email.mime.text.MIMEText` or multipart message)
  - If `cc_email` provided: Include CC header
  - If `cc_email` is None/empty: Skip CC header
  - Reference: See contracts/functions.md for updated signature

- [ ] T023 [US4] Update `process_batch()` to pass admin CC email to notification functions
  - Read `ADMIN_CC_EMAIL` from environment (optional, defaults to None)
  - Pass to `compose_notification_email()` and `send_email_notification()`
  - If not configured: all notifications still sent (no CC)

- [ ] T024 [US4] Add unit tests to `tests/test_fide_scraper.py` for CC functionality
  - `test_send_email_with_cc()` - verify CC included in email headers
  - `test_send_email_without_cc()` - verify email sent without CC when not configured
  - `test_compose_email_cc_handling()` - verify CC email formatted correctly
  - Update mock SMTP tests to verify CC in message

- [ ] T025 [US4] Add integration test to `tests/test_integration.py`
  - `test_batch_with_admin_cc()` - verify admin receives CC'd emails
  - Test with admin email configured and not configured
  - Verify admin receives exact same email as player
  - Run all existing tests to verify no regression

**Phase 6 Dependencies**: Phase 5 (US1 + US2 + US3) complete
**Phase 6 Completion Criteria**: US4 independently testable, admin monitoring working

---

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Complete documentation, handle edge cases, ensure production readiness

### Documentation & Configuration

- [ ] T026 Create sample `players.csv.example` file with documented format
  - Header: FIDE ID,email
  - Include 5 example rows with comments
  - Show example of opted-out player (empty email)
  - Place in root directory

- [ ] T027 Update `README.md` with complete feature documentation
  - Section: "Rating Change Notifications"
  - Configuration: new env vars and format
  - Usage: how to set up `players.csv`
  - Example batch run with notifications
  - Troubleshooting: missing SMTP config, invalid emails, etc.

- [ ] T028 Update `.env.example` with documentation for new variables
  - Add inline comments explaining each new variable
  - Provide example values
  - Note which are optional vs required

### Edge Case Handling & Error Messages

- [ ] T029 Add handling for duplicate FIDE IDs in `players.csv`
  - Current behavior: Use first occurrence
  - Log warning: "Duplicate FIDE ID X, using first occurrence"
  - Add test case: `test_duplicate_fide_ids_in_players_csv()`

- [ ] T030 Add handling for empty `players.csv` (only headers)
  - Graceful behavior: Process with empty player list
  - Log info: "No players to process in players.csv"
  - Existing batch continues, output file appended with current date
  - Add test case: `test_empty_players_csv()`

- [ ] T031 Add handling for rated → unrated transitions
  - Current behavior: Treated as change (value → None)
  - Add email notification for this transition
  - Update email body to note "now unrated due to inactivity"
  - Add test case: `test_rated_to_unrated_transition()`

- [ ] T032 Add rate-limiting / retry logic for SMTP
  - If SMTP timeout on email send:
    - Log: "SMTP timeout for recipient, will retry next batch"
    - Continue with next player (don't crash)
    - Future enhancement: exponential backoff
  - Add test case with timeout simulation

### Code Quality & Testing

- [ ] T033 Add logging configuration for email operations
  - Create consistent log format: timestamp, level, message
  - Log email attempts: recipient, CC, result
  - Log errors with full context
  - Reference: research.md error handling section

- [ ] T034 Add docstrings and type hints to all new functions
  - All 8 functions from contracts/functions.md have docstrings
  - All parameters and return types annotated
  - Examples provided in docstrings
  - Follow existing project code style

- [ ] T035 Run full test suite and verify coverage
  - All unit tests pass: `pytest tests/test_validation.py tests/test_fide_scraper.py`
  - All integration tests pass: `pytest tests/test_integration.py`
  - No regression in existing tests
  - Coverage: >80% for new functions

- [ ] T036 Manual testing with real SMTP
  - Set up local test email account (or use test SMTP service)
  - Run scraper in batch mode with real ratings fetch
  - Verify emails arrive with correct content
  - Verify CC emails are delivered
  - Verify logging is clear and helpful

### Final Integration & Deployment

- [ ] T037 Update project documentation (README, CONTRIBUTING)
  - Document new feature for contributors
  - Add troubleshooting section
  - Update installation/setup guide

- [ ] T038 Create example CSV files for documentation
  - `examples/players-basic.csv` - simple example
  - `examples/players-mixed.csv` - with various configurations
  - Include in repo or docs

- [ ] T039 Verify git status and prepare for merge
  - Review all changes: `git status`
  - Ensure branch is up to date with main
  - Create pull request with description linking to spec
  - All tests green in CI/CD (if available)

**Phase 7 Dependencies**: Phase 6 complete

---

## Task Summary & Statistics

### Total Task Count: 39 Implementation Tasks

| Phase | Name | Task Count | Purpose |
|-------|------|-----------|---------|
| 1 | Setup & Configuration | 4 | Environment, config files, documentation skeleton |
| 2 | Foundational Functions | 4 | Shared utilities, validation, test fixtures |
| 3 | US1: Load Player Data | 4 | CSV loading, validation integration |
| 4 | US2: Detect Changes | 4 | Change detection logic, historical comparison |
| 5 | US3: Send Emails | 5 | Email composition, SMTP sending, error handling |
| 6 | US4: Admin CC | 4 | CC functionality, admin monitoring |
| 7 | Polish & Documentation | 10 | Edge cases, documentation, quality assurance |
| **TOTAL** | **All Phases** | **39 tasks** | **Ready for implementation** |

### Task Count by Type

- **Configuration & Setup**: 4 tasks (T001-T004)
- **Implementation (Core Functions)**: 14 tasks (T005-T018)
- **Testing**: 12 tasks (unit, integration, validation)
- **Integration & Refactoring**: 5 tasks (T019-T023, T035)
- **Documentation & Polish**: 4 tasks (T026-T028, T037-T039)

### Parallelization Opportunities

**Within Phase 3 (US1)**:
- T009 & T010 can be developed in parallel (independent CSV loading functions)
- T011 (testing) starts once T009-T010 drafted

**Within Phase 5 (US3)**:
- T017 (email composition) and T018 (SMTP sending) can be started in parallel
- T019 (unit tests) can proceed concurrently with implementation

**Between Phases**:
- Once Phase 3 complete: Team can split into two tracks:
  - Track A: US2 (change detection) - 1 developer
  - Track B: US1 refactoring/testing - 1 developer

### Recommended MVP Increments

**Increment 1 (MVP)**: Phases 1-3
- User Story 1 complete: Load player data
- Configuration ready
- Provides foundation, independent test capability
- Estimated: 2-3 days for single developer

**Increment 2 (Minimal Feature)**: Add Phase 4
- User Stories 1-2 complete: Load data + detect changes
- Core business logic functional
- Still no email sending yet
- Estimated: +2 days

**Increment 3 (Complete Feature)**: Add Phases 5-6
- User Stories 1-4 complete: Full feature with notifications + CC
- Production-ready
- Estimated: +4-5 days

**Increment 4 (Polish)**: Phase 7
- Documentation, edge cases, quality
- Estimated: +2 days

---

## Task Dependencies & Execution Order

### Strict Dependencies (Cannot run in parallel)

```
Phase 1 (Setup) → Must complete first
  ↓
Phase 2 (Foundational) → Validation functions needed by all stories
  ↓
Phase 3 (US1) → Player loading; foundation for all downstream
  ↓
Phase 4 (US2) → Change detection; needs loaded player data
  ↓
Phase 5 (US3) → Email sending; needs change detection results
  ↓
Phase 6 (US4) → CC functionality; builds on US3
  ↓
Phase 7 (Polish) → Can partially overlap with Phase 6
```

### Independent Work Tracks (After Phase 3)

**Track A (Core Logic)**: Phase 4 (Change Detection)
- Tasks: T013-T016
- Input: Completed US1 from Track B
- Can work in parallel with Track B quality assurance

**Track B (Quality Assurance)**: Complete testing for Phase 3
- Tasks: T011-T012 + additional testing
- Input: Completed US1 implementation
- Can work in parallel with Track A

### Estimated Timeline (Single Developer, 8h/day)

| Phase | Days | Role |
|-------|------|------|
| Phase 1 | 0.5 | Setup |
| Phase 2 | 1.0 | Implementation |
| Phase 3 | 2.0 | Implementation + Testing |
| Phase 4 | 2.0 | Implementation + Testing |
| Phase 5 | 2.5 | Implementation + Testing |
| Phase 6 | 1.5 | Implementation + Testing |
| Phase 7 | 2.0 | Documentation + Edge Cases |
| **Total** | **11.5 days** | **~2 weeks** |

---

## Testing Strategy

### Unit Tests (Phases 2-6)

Each phase includes unit tests validating:
- Function parameters and return types
- Edge cases and boundary conditions
- Error handling and graceful degradation
- Data structure correctness

Run with: `pytest tests/test_*.py -v`

### Integration Tests (All Phases)

Full end-to-end testing:
- Load players → Detect changes → Send emails → Verify results
- Mock external dependencies (FIDE API, SMTP)
- Verify batch processing pipeline intact

Run with: `pytest tests/test_integration.py -v`

### Manual Testing (Phase 7)

- Test with real SMTP configuration
- Send test emails to real account
- Verify email format, CC delivery
- Check logging output for clarity

---

## Acceptance Criteria for Completion

### Feature Complete Checklist

- [ ] All 39 tasks completed
- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] All integration tests pass
- [ ] Code coverage >80% for new functions
- [ ] No regression in existing tests
- [ ] README.md updated with feature description
- [ ] `.env.example` includes new variables
- [ ] Edge cases documented and handled
- [ ] Pull request created with full feature link
- [ ] Team code review completed

### Performance Acceptance Criteria

- [ ] Batch processing time unchanged (SC-006)
- [ ] Email sending: <5 seconds per email
- [ ] Support 100+ notifications per batch without errors (SC-004)
- [ ] Notification delivery within 5 minutes of detection (SC-001)

### User Satisfaction Criteria

- [ ] 99% of valid emails successfully deliver (SC-002)
- [ ] All admin CC recipients receive copies (SC-003)
- [ ] Clear error messages in logs
- [ ] Configuration straightforward for admin setup

---

End of Tasks Document.
