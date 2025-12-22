# Tasks: External Ratings API Integration

**Input**: Design documents from `/specs/005-ratings-api-integration/`
**Prerequisites**: plan.md (✓), spec.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓)

**Tests**: Unit tests included (pytest - existing project framework)

**Organization**: Tasks grouped by user story to enable independent implementation and validation

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3)
- **Exact file paths** included in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Environment variable configuration and dependency verification

- [x] T001 Verify requirements.txt contains requests and python-dotenv (already present)
- [x] T002 [P] Update .env.example with new API configuration variables in `/home/epklein/Sources/fide-scraper/.env.example`
- [x] T003 Create CI/CD tests to validate environment variables are set before deployment

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure for API integration that MUST complete before user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create load_api_config() function skeleton in `/home/epklein/Sources/fide-scraper/fide_scraper.py` to load FIDE_RATINGS_API_ENDPOINT and API_TOKEN from environment
- [x] T005 Create should_post_to_api() helper function in `/home/epklein/Sources/fide-scraper/fide_scraper.py` to check if both config variables are present
- [x] T006 Create post_rating_to_api() function skeleton in `/home/epklein/Sources/fide-scraper/fide_scraper.py` with timeout (5s) and retry (1x) configuration
- [x] T007 Add comprehensive logging imports and configuration to `/home/epklein/Sources/fide-scraper/fide_scraper.py` for API request tracking
- [x] T008 Identify main batch processing loop in `/home/epklein/Sources/fide-scraper/fide_scraper.py` where API posting will integrate (after rating updates written to CSV)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Send ratings update to external service after scrape (Priority: P1) 🎯 MVP

**Goal**: After FIDE rating scraper completes and updates player ratings in the system, automatically send each player's rating data to the external API endpoint

**Independent Test**: Can be fully tested by running a scrape operation that updates player ratings and verifying POST requests are sent with correct format, authentication, and the system continues processing regardless of API response

### Implementation for User Story 1

- [x] T009 [P] [US1] Implement rating data transformation from profile dict to API request format in `/home/epklein/Sources/fide-scraper/fide_scraper.py` (map 'Date' → 'date', 'FIDE ID' → 'fide_id', 'Player Name' → 'player_name', 'Standard' → 'standard_rating', 'Rapid' → 'rapid_rating', 'Blitz' → 'blitz_rating')
- [x] T010 [US1] Implement rating validation logic before API submission in `/home/epklein/Sources/fide-scraper/fide_scraper.py` (FIDE ID: 4-10 digits; player_name: non-empty; date: ISO 8601; ratings: integers >= 0 or None)
- [x] T011 [US1] Implement JSON POST request construction with Authorization header (Token {api_token}) in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T012 [US1] Implement HTTP status code checking: treat 200 OK as success in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T013 [US1] Implement success logging with player ID and rating data sent in `/home/epklein/Sources/fide-scraper/fide_scraper.py` using logging.info()
- [x] T014 [US1] Integrate post_rating_to_api() calls into main batch processing loop after CSV write in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T015 [P] [US1] Write pytest unit test test_post_rating_to_api_success() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (mock successful 200 OK response)
- [x] T016 [P] [US1] Write pytest unit test test_rating_transformation() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (verify dict transformation is correct)
- [x] T017 [P] [US1] Write pytest unit test test_rating_validation() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (test edge cases: null ratings, valid FIDE ID formats)

**Checkpoint**: User Story 1 complete - rating updates can be POSTed to external API with proper formatting and authentication. Test independently by running scraper with mock API endpoint.

---

## Phase 4: User Story 2 - Load API configuration from environment (Priority: P1)

**Goal**: Service reads API endpoint URL and authentication token from environment variables at startup, enabling environment-specific configuration without code changes

**Independent Test**: Can be fully tested by verifying environment variables are correctly loaded at initialization and used in API requests, with proper error messages for missing configuration

### Implementation for User Story 2

- [x] T018 [US2] Implement load_api_config() function to read FIDE_RATINGS_API_ENDPOINT and API_TOKEN from environment in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T019 [US2] Add validation in load_api_config() to ensure both variables are present, log clear error if missing in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T020 [US2] Call load_api_config() at application startup in main() function in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T021 [US2] Ensure loaded API endpoint and token are accessible to batch processing loop in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T022 [P] [US2] Write pytest unit test test_load_api_config_valid() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (mock environment with both variables set)
- [x] T023 [P] [US2] Write pytest unit test test_load_api_config_missing_endpoint() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (missing FIDE_RATINGS_API_ENDPOINT, should raise ValueError)
- [x] T024 [P] [US2] Write pytest unit test test_load_api_config_missing_token() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (missing API_TOKEN, should raise ValueError)
- [x] T025 [US2] Write pytest unit test test_should_post_to_api() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (both present: True; missing either: False)

**Checkpoint**: User Story 2 complete - API configuration can be loaded from environment with proper validation. Test independently by setting environment variables and verifying configuration is accessible.

---

## Phase 5: User Story 3 - Handle API failures gracefully (Priority: P2)

**Goal**: When POST requests fail (timeout, network error, HTTP errors), system logs error details, continues processing other rating updates, and does not crash or halt the scraper workflow

**Independent Test**: Can be tested by simulating API failures (network timeouts, HTTP 500/4xx errors) and verifying system handles gracefully, logs appropriately, and continues processing

### Implementation for User Story 3

- [x] T026 [US3] Implement network timeout handling (requests.Timeout) in post_rating_to_api() in `/home/epklein/Sources/fide-scraper/fide_scraper.py` (catch, retry once, log error with FIDE ID)
- [x] T027 [US3] Implement connection error handling (requests.ConnectionError) in post_rating_to_api() in `/home/epklein/Sources/fide-scraper/fide_scraper.py` (catch, retry once, log error)
- [x] T028 [US3] Implement HTTP error handling for 4xx responses (no retry) in post_rating_to_api() in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T029 [US3] Implement HTTP error handling for 5xx responses (retry once) in post_rating_to_api() in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T030 [US3] Implement error logging with full context (FIDE ID, status code, error message) in `/home/epklein/Sources/fide-scraper/fide_scraper.py` using logging.error()
- [x] T031 [US3] Ensure post_rating_to_api() returns False on failure but does NOT raise exceptions in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T032 [US3] Verify batch processing loop continues to next player regardless of post_rating_to_api() result in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T033 [P] [US3] Write pytest unit test test_post_rating_to_api_timeout() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (mock timeout, verify retry and logging)
- [x] T034 [P] [US3] Write pytest unit test test_post_rating_to_api_connection_error() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (mock connection error, verify retry and logging)
- [x] T035 [P] [US3] Write pytest unit test test_post_rating_to_api_500_error() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (mock HTTP 500, verify retry once)
- [x] T036 [P] [US3] Write pytest unit test test_post_rating_to_api_400_error() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (mock HTTP 400, verify no retry, log error)
- [x] T037 [P] [US3] Write pytest integration test test_batch_continues_on_api_failure() in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (simulate one API failure, verify other ratings still processed)

**Checkpoint**: User Story 3 complete - API failures are handled gracefully without blocking scraper. Test independently by simulating various failure scenarios and confirming batch processing continues.

---

## Phase 6: Integration & Documentation

**Purpose**: Integrate all user stories and ensure complete system works end-to-end

- [x] T038 [P] Run all pytest tests together to verify no conflicts between user stories in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py`
- [x] T039 [P] Run end-to-end integration test: execute fide_scraper.py with --batch flag and verify all three user stories work together
- [x] T040 Verify logging output includes both successful and failed API requests with clear diagnostics
- [x] T041 Document new functions in fide_scraper.py with docstrings: load_api_config(), post_rating_to_api(), should_post_to_api()
- [x] T042 Update .env.example with example API configuration (endpoint and token placeholders)
- [x] T043 Update fide_scraper.py module docstring to mention new API integration feature
- [x] T044 Validate quickstart.md instructions match actual implementation in `/home/epklein/Sources/fide-scraper/specs/005-ratings-api-integration/quickstart.md`

**Checkpoint**: All user stories integrated and working together. Full feature is operational.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements, validation, and deployment readiness

- [x] T045 [P] Add type hints to all new functions (load_api_config, post_rating_to_api, should_post_to_api) in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T046 [P] Code review: verify error messages are user-friendly and helpful for operators in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T047 [P] Code review: verify all logging statements include sufficient context for debugging in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T048 [P] Verify requests library timeout behavior matches 5-second specification in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- [x] T049 Validate Docker configuration still works with new environment variables in `/home/epklein/Sources/fide-scraper/docker-compose.yaml`
- [x] T050 Test with Docker: verify FIDE_RATINGS_API_ENDPOINT and API_TOKEN are properly injected from environment in `/home/epklein/Sources/fide-scraper/docker-compose.yaml`
- [x] T051 [P] Run linting/formatting (if configured) on all modified files
- [x] T052 Verify backward compatibility: existing scraper functionality unchanged when FIDE_RATINGS_API_ENDPOINT/API_TOKEN not set
- [x] T053 Final: Execute fide_scraper.py --batch with mock API endpoint and verify all output is correct

**Checkpoint**: Feature is production-ready

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001-T003) - BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational phase completion
  - **US1 & US2**: Both marked P1, can run in parallel after Foundational
  - **US3**: Marked P2, depends on Foundational but can start after or during US1/US2
- **Integration (Phase 6)**: Depends on all user stories being complete
- **Polish (Phase 7)**: Depends on Integration phase being complete

### User Story Dependencies

- **User Story 1 (P1)**: Core API posting functionality - foundation for others
- **User Story 2 (P1)**: Configuration loading - needed before US1 can fully work, but can be developed in parallel
- **User Story 3 (P2)**: Error handling - depends on US1 logic, can start after Foundational

### Within User Stories

- Tests (marked [P]) can be written in parallel within a story
- Implementation tasks follow logical order: transformation → validation → request building → status handling → integration

### Parallel Opportunities

**After Foundational (Phase 2) completes**:
- US1 and US2 can be worked on in parallel by different developers (different functions in same file)
- All tests for a story marked [P] can run in parallel
- All unit tests across stories can be run in parallel (pytest runs them concurrently)

**Example parallel execution within US1**:
```
Parallel task group:
  - T015: Write success test
  - T016: Write transformation test
  - T017: Write validation test

Then sequential:
  - T009-T014: Implementation (depends on test understanding)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

**Minimal Viable Product** - Delivers core value with least complexity:

1. ✅ Complete Phase 1: Setup (T001-T003)
2. ✅ Complete Phase 2: Foundational (T004-T008) - infrastructure required
3. ✅ Complete Phase 3: User Story 1 (T009-T017) - can POST ratings to API
4. **STOP and VALIDATE**:
   - Run `pytest tests/test_fide_scraper.py -k US1` to test independently
   - Execute `python fide_scraper.py` and verify POST request sent for each rating
   - Check logs for successful transmission
5. **Deploy MVP**: Feature is now operational for basic use case

### Incremental Delivery

After MVP (US1 validated):

1. Add User Story 2 (T018-T025): Configuration management
   - Improves operability and deployment flexibility
   - Test: `pytest tests/test_fide_scraper.py -k US2`

2. Add User Story 3 (T026-T037): Failure handling
   - Improves reliability and resilience
   - Test: `pytest tests/test_fide_scraper.py -k US3`

3. Integration (Phase 6): All stories work together
   - Final validation and documentation

### Parallel Team Strategy

With multiple developers (after Foundational completes):

1. **Developer A**: User Story 1 (MVP focus)
   - Writes tests T015-T017
   - Implements T009-T014
   - Validates independently

2. **Developer B**: User Story 2 (Configuration)
   - Writes tests T022-T025
   - Implements T018-T021
   - Validates independently

3. **Developer C**: User Story 3 (Resilience)
   - Writes tests T033-T037
   - Implements T026-T032
   - Validates independently

4. **All together**: Phase 6 Integration testing

---

## Task Statistics

**Total Tasks**: 53
**Setup Phase**: 3 tasks
**Foundational Phase**: 5 tasks (BLOCKING)
**User Story 1 (P1)**: 9 tasks (3 implementation, 4 tests, MVP focus)
**User Story 2 (P1)**: 8 tasks (4 implementation, 4 tests)
**User Story 3 (P2)**: 12 tasks (7 implementation, 5 tests)
**Integration Phase**: 7 tasks
**Polish Phase**: 9 tasks

**Critical Path**: T001-T008 (Foundational) → T009-T017 (US1) = 25 tasks minimum for MVP

---

## Execution Notes

### Best Practices

- Write tests FIRST, verify they FAIL before implementation
- Commit after each completed task (logical grouping okay)
- Run pytest frequently to catch regressions early
- Use mock/patch for API testing (don't hit real external API in tests)
- Keep each task focused and independent when marked [P]

### Common Pitfalls to Avoid

- ❌ Don't skip Foundational phase (T004-T008) - blocks everything
- ❌ Don't implement features without corresponding tests
- ❌ Don't commit directly to tests directory without running full suite
- ❌ Don't hardcode API endpoint/token - use environment variables only
- ❌ Don't catch exceptions silently - log with context for debugging

### Validation Checkpoints

At each checkpoint, verify:
1. All tests pass: `pytest tests/test_fide_scraper.py -v`
2. No linting errors: `python -m flake8 fide_scraper.py` (if configured)
3. Type hints valid: `mypy fide_scraper.py` (if configured)
4. Story is independently testable (can deploy this story alone)
5. No regressions to existing functionality

---

## Notes

- Single Python script project: all code in `/home/epklein/Sources/fide-scraper/fide_scraper.py`
- Tests in `/home/epklein/Sources/fide-scraper/tests/test_fide_scraper.py` (pytest framework)
- No database changes required (uses existing CSV storage)
- No new dependencies needed (uses existing requests, python-dotenv)
- Feature is additive: existing functionality remains unchanged when API not configured
- Follow existing code patterns from email notification integration (SMTP) for consistency
