# Task Breakdown: Fetch FIDE IDs from API and Augment Players File

**Feature Branch**: `006-fide-ids-api`
**Feature Spec**: [spec.md](spec.md)
**Implementation Plan**: [plan.md](plan.md)
**Date**: 2025-12-19

## Summary

This feature adds functionality to fetch FIDE IDs from an external API endpoint and merge them with the existing players CSV file. Three core functions will be implemented in `fide_scraper.py` with comprehensive testing. The feature is designed to be optional (gracefully degrades if API is unavailable) and integrates seamlessly with the existing scraper workflow.

**MVP Scope**: User Story 1 (Fetch API IDs) + User Story 2 (Merge & Deduplicate)

## Task Organization

Tasks are organized by user story and can be completed in parallel where noted. Each user story is independently testable and deployable.

### User Stories (from spec.md)

1. **User Story 1 (P1)**: Fetch FIDE IDs from API endpoint
   - Independent test: API called with correct auth, response parsed, failures logged gracefully
   - Acceptance: All 3 scenarios pass (valid config, JSON response, empty array)

2. **User Story 2 (P1)**: Append API IDs to players file with deduplication
   - Independent test: Merge logic tested with CSV file, duplicates removed, format preserved
   - Acceptance: All 3 scenarios pass (merge accuracy, duplicate handling, format preservation)

3. **User Story 3 (P1)**: Continue scraping with expanded player list
   - Independent test: Full scraper cycle with augmented file, both original and API IDs processed
   - Acceptance: All 3 scenarios pass (augmented file processed, API IDs scraped, downstream compatibility)

## Implementation Phases

### Phase 1: Setup & Configuration

- [x] T001 Update .env.example with FIDE_IDS_API_ENDPOINT configuration parameter
- [x] T002 Update README.md with documentation for FIDE_IDS_API_ENDPOINT and usage instructions
- [x] T003 Review existing fide_scraper.py structure and identify insertion points for new functions

### Phase 2: Foundational Functions (Blocking Prerequisites)

These functions are required by all user stories and should be completed first.

- [x] T004 [P] Examine existing FIDE_PLAYERS_FILE CSV structure to understand format and column layout
- [x] T005 [P] Create helper function `load_csv_fide_ids()` to extract FIDE IDs from existing CSV file in fide_scraper.py
- [x] T006 [P] Create helper function `load_existing_ids()` to safely read CSV with error handling in fide_scraper.py

### Phase 3: User Story 1 - Fetch FIDE IDs from API endpoint (P1)

**Independent Test Criteria**: API fetch function successfully retrieves and parses response; gracefully handles errors (invalid auth, timeout, malformed JSON); logs all outcomes

- [x] T007 [US1] Create unit tests for `fetch_fide_ids_from_api()` function in tests/test_fide_scraper.py (covers success, empty array, missing config, auth error, timeout, malformed JSON)
- [x] T008 [US1] Implement `fetch_fide_ids_from_api(api_endpoint: str, api_token: str)` function in fide_scraper.py with:
  - Validation of inputs (endpoint and token not empty)
  - GET request with 30-second timeout
  - JSON response parsing
  - Extract `fide_ids` array as strings
  - Error handling for Timeout, ConnectionError, HTTPError, JSONDecodeError
  - Comprehensive logging for success and failures
- [x] T009 [US1] Create integration test for API fetch in tests/test_integration.py that mocks the API endpoint and verifies request format/headers

### Phase 4: User Story 2 - Append API IDs to players file with deduplication (P1)

**Independent Test Criteria**: Merge logic correctly deduplicates IDs; CSV file updated with new entries only; original file format preserved; file I/O errors handled gracefully

- [x] T010 [US2] Create unit tests for `merge_player_ids()` function in tests/test_fide_scraper.py (covers no duplicates, with duplicates, empty CSV, empty API, all from API)
- [x] T011 [US2] Implement `merge_player_ids(csv_ids: List[str], api_ids: List[str])` function in fide_scraper.py with:
  - Convert both lists to sets
  - Compute union for all unique IDs
  - Identify new IDs (API - CSV)
  - Return sorted all_ids and new_ids list
  - Log merge summary with counts
- [x] T012 [US2] Create unit tests for `augment_players_file()` function in tests/test_fide_scraper.py (covers file creation, append, format preservation, locked file, permission error)
- [x] T013 [US2] Implement `augment_players_file(csv_path: str, new_ids: List[str])` function in fide_scraper.py with:
  - Check if file exists; create with headers if not
  - Detect CSV dialect/delimiter from existing file
  - Read all existing rows and preserve exactly
  - Append new rows for each new ID
  - Validate write success
  - Handle file I/O errors gracefully (locked, permission, disk full)
  - Log result with count of new IDs added
- [x] T014 [US2] Create integration test for full augmentation flow in tests/test_integration.py using real CSV file format

### Phase 5: User Story 3 - Continue scraping with expanded player list (P1)

**Independent Test Criteria**: Scraper processes all IDs from augmented file; API-sourced IDs are scraped for ratings; downstream operations work identically for all IDs

- [x] T015 [US3] Modify `main()` function in fide_scraper.py to call augmentation before scraping:
  - Load FIDE_IDS_API_ENDPOINT and API_TOKEN from environment
  - Call fetch_fide_ids_from_api() if both configured
  - Load existing CSV IDs using helper function
  - Call merge_player_ids() to deduplicate
  - Call augment_players_file() to update CSV
  - Log augmentation results
  - Proceed with existing scraping logic using augmented file
- [x] T016 [US3] Create integration test for end-to-end scraper flow with API augmentation in tests/test_integration.py
- [x] T017 [US3] Create integration test for graceful degradation when API is unavailable in tests/test_integration.py

### Phase 6: Testing & Documentation

- [x] T018 [P] Run full test suite (unit + integration) and verify all tests pass
- [x] T019 [P] Run pytest with coverage report for new functions (target: >90% coverage)
- [ ] T020 [P] Test scraper manually with real FIDE_IDS_API_ENDPOINT and verify augmented file is created
- [x] T021 Add docstrings to all new functions following existing code style in fide_scraper.py
- [x] T022 Update README.md Configuration section with example .env entries for FIDE_IDS_API_ENDPOINT
- [x] T023 Create CHANGELOG entry documenting the new feature and breaking changes (none expected)

### Phase 7: Polish & Deployment

- [x] T024 [P] Test with missing/invalid API configuration to verify graceful handling
- [x] T025 [P] Test with malformed CSV file to verify error recovery
- [x] T026 [P] Test with large API response (1000+ IDs) to verify performance (<10 seconds)
- [x] T027 Verify error messages are clear and actionable for operators
- [x] T028 Update docker-compose.yaml environment to include FIDE_IDS_API_ENDPOINT (set to empty by default)
- [x] T029 Verify deployment to Kubernetes includes FIDE_IDS_API_ENDPOINT in ConfigMap
- [x] T030 Add note to deployment docs that feature is optional (graceful if not configured)

## Task Dependency Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ↓
Phase 3 (US1) ──┐
                │ (independent)
Phase 4 (US2) ──┤ (both depend on Phase 2)
                │
Phase 5 (US3) ──┘ (depends on Phase 4 completion)
    ↓
Phase 6 (Testing)
    ↓
Phase 7 (Polish)
```

## Parallel Execution Opportunities

### Within Phase 2 (Foundational)
```
T004 (examine CSV structure)  ──┐
T005 (load CSV IDs helper)      │ (can run in parallel)
T006 (error handling helper)  ──┘
```

### Within Phase 3 (User Story 1)
```
T007 (unit tests) ──┐
T008 (implementation) (T007 informative but not blocking)
T009 (integration test) (can start after T008)
```

### Within Phase 4 (User Story 2)
```
T010 (merge unit tests)       ──┐
T011 (merge implementation)      │ (can start in parallel)
T012 (augment unit tests)     ──┤
T013 (augment implementation)    │
T014 (integration test)       ──┘
```

### Within Phase 6 (Testing)
```
T018 (run test suite)  ──┐
T019 (coverage report)    (can run in parallel)
T020 (manual testing)  ──┘
```

### Within Phase 7 (Polish)
```
T024 (missing config test) ──┐
T025 (malformed CSV test)    │ (can run in parallel)
T026 (performance test)    ──┘
```

## Recommended MVP Scope

**Scope**: Phases 1-4 (Setup through User Story 2 completion)

**Deliverables**:
- Configuration in .env.example and README.md
- API fetch function with comprehensive error handling
- Merge & deduplication logic
- CSV augmentation with format preservation
- Full test coverage for US1 and US2
- Manual testing verification

**Value**: Administrators can configure the API endpoint and the scraper will automatically augment the players file with new IDs on each run, with graceful degradation if API is unavailable.

**Time estimate**: 4-6 hours of implementation and testing

**Post-MVP (Future)**:
- Phase 5: Integration with main scraper loop (verify ratings are scraped for augmented IDs)
- Phase 7: Deployment, monitoring, and operational hardening

## Independent Test Examples

### User Story 1 Independent Test
```bash
# Configure API endpoint and token
export FIDE_IDS_API_ENDPOINT="https://chesshub.cloud/api/fide-ids/"
export API_TOKEN="test_token"

# Test 1: Valid API returns IDs
python -c "from fide_scraper import fetch_fide_ids_from_api; ids = fetch_fide_ids_from_api(...); assert len(ids) > 0"

# Test 2: Empty array handled
# (Mock API to return empty array)
assert fetch_fide_ids_from_api(...) is not None

# Test 3: API error handled gracefully
# (Mock API to return 500)
assert fetch_fide_ids_from_api(...) is None  # Returns None, doesn't crash
```

### User Story 2 Independent Test
```bash
# Test merge logic
csv_ids = ["100", "200", "300"]
api_ids = ["200", "300", "400", "500"]
all_ids, new_ids = merge_player_ids(csv_ids, api_ids)

assert all_ids == ["100", "200", "300", "400", "500"]
assert new_ids == ["400", "500"]
assert len(set(all_ids)) == len(all_ids)  # No duplicates

# Test CSV augmentation preserves format
# Create test CSV with specific format, augment it, verify format unchanged
```

### User Story 3 Independent Test
```bash
# Run scraper with augmented CSV
# Verify that IDs from API are scraped for ratings
# Check logs show expanded player count

scraper_output = main()
assert "Players file augmented with" in scraper_output.logs
assert scraped_count > original_count  # More players scraped
```

## File Modifications Summary

| File | Changes | Impact |
|------|---------|--------|
| `.env.example` | Add FIDE_IDS_API_ENDPOINT | Configuration documentation |
| `README.md` | Add FIDE IDs integration section | User documentation |
| `fide_scraper.py` | Add 5 new functions (fetch, merge, augment, helpers) + modify main() | Core feature implementation (~400 lines) |
| `tests/test_fide_scraper.py` | Add 13 unit tests | Feature test coverage |
| `tests/test_integration.py` | Add 3 integration tests | End-to-end validation |
| `docker-compose.yaml` | Add FIDE_IDS_API_ENDPOINT env var | Deployment configuration |
| `CHANGELOG.md` | Add entry for version X.Y.Z | Release notes |

## Success Criteria Mapping

| Success Criterion | Task(s) | Test |
|------------------|---------|------|
| SC-001: 100% API fetch success | T008 | T009 (mock success case) |
| SC-002: Deduplication 100% accurate | T011 | T010 (test all scenarios) |
| SC-003: No data loss | T013 | T014 (verify all IDs retained) |
| SC-004: CSV format preserved | T013 | T014 (format diff check) |
| SC-005: All IDs processed in scrape | T015 | T016 (verify all scraped) |
| SC-006: Graceful degradation | T008, T015 | T017 (API unavailable test) |
| SC-007: <10 second performance | T011, T013 | T020, T026 (timing checks) |
| SC-008: Clear logging | T008, T013, T015 | T020 (verify log output) |

## Risk Mitigation Checklist

- [ ] T008: Comprehensive error handling prevents crashes
- [ ] T013: File I/O error handling preserves original CSV on failure
- [ ] T015: Graceful degradation: scraper continues even if API unavailable
- [ ] T018-T020: Full test coverage (unit + integration + manual)
- [ ] T024-T026: Edge case testing (missing config, malformed data, performance)
- [ ] Documentation (T022): Clear setup and troubleshooting guides

## Acceptance Criteria per User Story

### User Story 1 (Fetch API IDs)
- [x] API endpoint is called with correct Authorization header
- [x] JSON response with fide_ids array is parsed correctly
- [x] Empty fide_ids array is handled (log and continue)
- [x] API errors (4xx, 5xx, timeout) are logged, function returns None
- [x] Invalid API configuration is handled gracefully

### User Story 2 (Merge & Augment)
- [x] CSV IDs and API IDs are merged with no duplicates
- [x] New IDs are appended to CSV file in same format as original
- [x] Original CSV rows are preserved exactly (no modifications)
- [x] CSV dialect and delimiters are detected and preserved
- [x] File I/O errors are logged, original file preserved on failure

### User Story 3 (Use Augmented File)
- [x] main() calls augmentation before scraping
- [x] Scraper uses augmented file for rating retrieval
- [x] API-sourced IDs are processed identically to original IDs
- [x] Merge results are logged with summary (count of new IDs)
- [x] Scraper continues if augmentation fails (graceful degradation)
