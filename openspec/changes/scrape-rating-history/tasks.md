# Implementation Tasks: Scrape Rating History

**Change ID:** `scrape-rating-history`

**Status:** Ready for implementation approval

---

## Phase 1: Core History Extraction

### Task 1.1: Implement Month Parsing Utility
- [x] Create `_parse_portuguese_month(month_abbr: str) -> int` function
  - Parse Portuguese month abbreviations: Jan, Fev, Mar, Abr, Mai, Jun, Jul, Ago, Set, Out, Nov, Dez
  - Return month number (1-12) or raise ValueError for invalid months
  - Add docstring with test examples
- [ ] Create `_calculate_month_end_date(year: int, month: int) -> date` function
  - Use `calendar.monthrange()` to find last day of month
  - Return date object for last day of month
  - Handle leap years correctly
- [ ] Add unit tests for month parsing
  - Test all 12 Portuguese months
  - Test edge cases (February leap/non-leap years)
  - Test invalid month names

**Acceptance Criteria:**
- `_parse_portuguese_month("Nov")` returns 11
- `_parse_portuguese_month("Fev")` returns 2
- `_calculate_month_end_date(2025, 11)` returns date(2025, 11, 30)
- `_calculate_month_end_date(2024, 2)` returns date(2024, 2, 29) (leap year)

---

### Task 1.2: Extract Month/Year String from Table Rows
- [ ] Create `_parse_month_year_string(month_year_str: str) -> Optional[date]` function
  - Input: "Nov/2025" or "Out/2025"
  - Parse month and year from string
  - Return date of last day of month using utilities from Task 1.1
  - Return None on invalid format
  - Add docstring with examples (e.g., "Nov/2025" -> date(2025, 11, 30))
- [ ] Add unit tests
  - Test valid Portuguese month/year combinations
  - Test invalid formats (typos, reversed order, etc.)
  - Test all month abbreviations with sample year

**Acceptance Criteria:**
- `_parse_month_year_string("Nov/2025")` returns date(2025, 11, 30)
- `_parse_month_year_string("Out/2025")` returns date(2025, 10, 31)
- `_parse_month_year_string("Invalid/2025")` returns None
- `_parse_month_year_string("")` returns None

---

### Task 1.3: Extract All Rows from Rating History Table
- [ ] Rename/refactor `_extract_rating_from_fide_table()` function to `_extract_all_history_rows(html: str) -> List[Dict]`
  - Find `ContentPlaceHolder1_gdvRating` table in HTML
  - Extract ALL TR elements (not just row[1])
  - Skip header row (row[0])
  - For each data row, extract: month/year string, standard, rapid, blitz ratings
  - Return list of dicts: `[{"month_year_str": "Nov/2025", "standard": 1800, "rapid": 1884, "blitz": 1800}, ...]`
  - Handle missing/unrated values as None
  - Return empty list if table not found
- [ ] Add unit tests with real HTML samples (current test data in test files)
  - Test with multiple rows
  - Test with single row
  - Test with missing table
  - Test with unrated values

**Acceptance Criteria:**
- Returns list of dicts with all rows
- Standard/Rapid/Blitz are integers or None
- Empty list returned for missing table (not error)
- Correctly handles "unrated" and empty values

---

### Task 1.4: Deduplicate Monthly Records (Keep Topmost)
- [ ] Create `_deduplicate_history_by_month(history_rows: List[Dict]) -> List[Dict]` function
  - Input: List of history row dicts (from Task 1.3)
  - When same month appears multiple times, keep first occurrence (topmost)
  - Return deduplicated list in same order
  - Add docstring with example
- [ ] Add unit tests
  - Test with duplicate months
  - Test with unique months (no deduplication needed)
  - Test with single month
  - Test empty list

**Acceptance Criteria:**
- Duplicate June entries: keep first, discard rest
- Returns list with same order as input
- No duplicates in output
- Preserves all unique months

---

### Task 1.5: Convert Raw History to Monthly Records
- [ ] Create `_convert_raw_history_to_records(raw_history: List[Dict]) -> List[Dict]` function
  - Input: Raw history from Task 1.3 (before deduplication)
  - Call deduplication function (Task 1.4)
  - For each deduplicated row, parse month/year string to date (Task 1.2)
  - Build final record: `{"date": date_obj, "standard": int|None, "rapid": int|None, "blitz": int|None}`
  - Return list of final records
- [ ] Add unit tests
  - Test with real example data from proposal
  - Test with missing ratings
  - Test with invalid month strings (should be skipped or handled gracefully)

**Acceptance Criteria:**
- Returns list of dicts with keys: date, standard, rapid, blitz
- Dates are date objects
- Handles all edge cases from earlier tasks
- Empty list for empty input

---

### Task 1.6: Integrate History Extraction into Profile Fetching
- [ ] Create public function `extract_rating_history(html: str) -> List[Dict]`
  - Calls internal functions from Tasks 1.2-1.5 in sequence
  - Returns complete list of monthly records with dates
  - Handles all error cases gracefully
  - Add comprehensive docstring with example
- [ ] Update `process_batch()` to call `extract_rating_history()` instead of individual rating extractors
  - Scrape history for each player
  - Store history in result dict: `result['rating_history'] = [...]`
- [ ] Add integration tests
  - Test with real FIDE HTML samples
  - Test change detection still works with new data structure

**Acceptance Criteria:**
- `extract_rating_history()` returns same structure as Task 1.5
- `process_batch()` populates 'rating_history' key
- Backward compatible with existing change detection (initially)

---

## Phase 2: Monthly Storage Model

### Task 2.1: Update CSV Storage to Monthly Format
- [ ] Modify `write_csv_output()` function
  - Change column from "Date" to "Month"
  - For each player in results, iterate over rating_history list
  - Write one row per month (not one row per day)
  - When same (FIDE ID, Month) exists, replace it (read/filter/write pattern)
  - Month values should be ISO 8601 strings (e.g., "2025-11-30")
- [ ] Handle CSV file format migration
  - If old "Date" column exists, consider it a breaking change
  - Option: Delete old file or fail with clear error
  - Document migration strategy
- [ ] Add unit tests
  - Test appending new months
  - Test replacing existing month
  - Test multiple players
  - Test month sorting/order preservation

**Acceptance Criteria:**
- CSV headers are correct: Month,FIDE ID,Player Name,Standard,Rapid,Blitz
- One row per month per player
- Existing months are replaced (idempotent)
- ISO 8601 month dates in CSV

---

### Task 2.2: Update Historical Ratings Loading
- [ ] Rename/refactor `load_historical_ratings_by_player()` to `load_historical_ratings_by_player_monthly()`
  - Read CSV with "Month" column (not "Date")
  - Build dict: `{fide_id: [{"date": date_obj, "standard": int|None, ...}, ...]}`
  - Maintain list of all months per player (not just latest)
  - Return empty dict if file missing (first run)
- [ ] Add unit tests
  - Test loading monthly data
  - Test with missing file
  - Test with empty file
  - Test with multiple players/months

**Acceptance Criteria:**
- Returns dict keyed by FIDE ID
- Values are lists of month records
- Each record has date and rating fields
- Empty dict for missing file

---

### Task 2.3: Validate CSV Format on Load
- [ ] Add validation to `load_historical_ratings_by_player_monthly()`
  - Check for "Month" column (not "Date")
  - Log clear error if old format detected
  - Either skip old file or raise error (decide strategy)
- [ ] Add unit tests for format validation
  - Test with new format
  - Test with old format (should error clearly)

**Acceptance Criteria:**
- Clear error message if old format encountered
- No silent failures
- Documented migration path for users

---

## Phase 3: Change Detection

### Task 3.1: Detect New Months in History
- [ ] Create `detect_new_months(fide_id: str, scraped_history: List[Dict], stored_history: Dict) -> List[Dict]` function
  - Input: scraped_history from Task 1.5, stored_history from Task 2.2
  - Extract month dates from stored_history[fide_id] (or empty list if not found)
  - Compare scraped months against stored months
  - Return only months that exist in scraped but not in stored
  - Handle first run (empty stored history) - all months are new
- [ ] Add unit tests
  - Test new month detection
  - Test existing month (not new)
  - Test empty stored history
  - Test multiple new months

**Acceptance Criteria:**
- Returns list of new month dicts
- Each dict has: date, standard, rapid, blitz
- Empty list if no new months
- First run returns all scraped months

---

### Task 3.2: Update process_batch() for Monthly Change Detection
- [ ] Modify `process_batch()` to:
  - Load historical data with monthly format (Task 2.2)
  - For each player, call `detect_new_months()` (Task 3.1)
  - Store result in: `result['new_months'] = [...]`
  - Keep 'changes' key for backward compatibility (can be empty dict or deprecated)
- [ ] Add integration tests
  - Test change detection with new data structure
  - Test batch processing end-to-end

**Acceptance Criteria:**
- 'new_months' key populated in results
- Correct new months identified
- Backward compatible structure

---

## Phase 4: Notifications

### Task 4.1: Update Email Notification Logic
- [ ] Modify `send_batch_notifications()` to:
  - Skip players with empty 'new_months' list (no notification)
  - For players with new months, compose email (Task 4.2)
  - Send email via `_send_email_notification()`
- [ ] Update notification subject line
  - Example: "New Rating History Found - Eduardo Pavinato Klein"
- [ ] Add unit tests
  - Test with new months (should send)
  - Test without new months (should skip)
  - Test multiple new months

**Acceptance Criteria:**
- Email sent only for players with new_months
- No error on skipped players
- Subject line indicates new history

---

### Task 4.2: Compose Email for New Months
- [ ] Create `_compose_new_months_email(player_name: str, fide_id: str, new_months: List[Dict], ...)`
  - Build email subject: "New Rating History Found - {player_name}"
  - Build email body with:
    - Player greeting
    - Statement about new rating history found
    - List of new months with dates and ratings (Standard, Rapid, Blitz)
    - Link to FIDE profile
    - Footer with contact info
  - Return (subject, body)
- [ ] Add unit tests
  - Test with single new month
  - Test with multiple new months
  - Test month ordering

**Acceptance Criteria:**
- Subject and body returned
- All new month data included
- Clear formatting
- Professional tone

---

### Task 4.3: Update API Notification Logic
- [ ] Modify `send_batch_api_updates()` to:
  - Skip players with empty 'new_months' list
  - For each new month, POST to API (or batch if applicable)
  - Use existing `_post_rating_to_api()` (may need to adapt for multiple months)
- [ ] Add unit tests
  - Test with new months (should post)
  - Test without new months (should skip)

**Acceptance Criteria:**
- API POST sent for new months only
- Correct data format
- Error handling for failed posts

---

### Task 4.4: Update Email and API for Missing Fields
- [ ] Ensure rating_history output includes all necessary fields for notifications
  - date, standard, rapid, blitz for each month
- [ ] Handle None values in notifications
  - Display "unrated" or similar in email
  - Send null or skip in API (verify spec)
- [ ] Add tests for edge cases

**Acceptance Criteria:**
- Unrated values handled gracefully
- No crashes on missing data
- Clear presentation in emails

---

## Phase 5: Testing & Validation

### Task 5.1: Update Existing Unit Tests
- [ ] Review `test_fide_scraper.py` and update tests
  - Tests for single-row extraction need updating for multi-row
  - Create fixtures with multi-month HTML samples
  - Update test expectations
- [ ] Review `test_integration.py` and update integration tests
  - Test full scrape-to-storage-to-notification flow
  - Test with real CSV files (monthly format)
- [ ] Review `test_validation.py` and add edge case tests

**Acceptance Criteria:**
- All existing tests updated or passing
- Coverage for new functions
- Integration tests pass end-to-end

---

### Task 5.2: Add New Unit Tests for Monthly Model
- [ ] Create comprehensive tests for:
  - Month parsing (Task 1.1)
  - Month/year string parsing (Task 1.2)
  - All history row extraction (Task 1.3)
  - Deduplication (Task 1.4)
  - History conversion (Task 1.5)
- [ ] Create fixtures with sample HTML tables
  - 7-month history (from proposal example)
  - Single month
  - Duplicate months
  - Missing/unrated values

**Acceptance Criteria:**
- Test files created/updated
- All new functions have tests
- Tests are clear and maintainable
- Coverage > 80% for new code

---

### Task 5.3: Test CSV Format Transition
- [ ] Create integration test for:
  - Writing new monthly CSV format
  - Reading monthly CSV format
  - Replacing existing months
  - Appending new months
- [ ] Test error handling:
  - Old format detection
  - Migration failure
  - Partial data

**Acceptance Criteria:**
- CSV round-trip tests pass
- Format validation works
- Error messages are clear

---

### Task 5.4: Test Change Detection Accuracy
- [ ] Create tests for:
  - New months correctly identified
  - Existing months not marked as new
  - First run (empty history) correctly identifies all as new
  - Multiple new months in one run
- [ ] Test with various player scenarios:
  - No previous history
  - Partial history
  - Complete history (no new months)

**Acceptance Criteria:**
- All scenarios tested
- Detection is accurate
- No false positives/negatives

---

### Task 5.5: Test Notification Triggering
- [ ] Create tests for:
  - Players with new months receive notifications
  - Players without new months are skipped
  - Email content is correct
  - API POST data is correct
- [ ] Test with batch of mixed players

**Acceptance Criteria:**
- Only new-month players notified
- No crashes on empty new_months
- Notification content is correct

---

### Task 5.6: Run Full Regression Tests
- [ ] Execute entire test suite
- [ ] Check for any regressions
- [ ] Verify backward compatibility (if applicable)
- [ ] Test with real FIDE data (if possible)

**Acceptance Criteria:**
- All tests passing
- No regressions
- Ready for merge

---

## Phase 6: Documentation & Final Review

### Task 6.1: Update Code Comments and Docstrings
- [ ] Add/update docstrings for all new functions
  - Include Args, Returns, Examples
  - Reference related tasks/specs
- [ ] Add inline comments for complex logic
- [ ] Update function signatures to match specs

**Acceptance Criteria:**
- All public functions documented
- Examples provided
- Clear and accurate

---

### Task 6.2: Update Project Documentation
- [ ] Update README or docs to explain:
  - New monthly storage format
  - Monthly notification triggers
  - CSV migration strategy (if needed)
- [ ] Add example output showing new format

**Acceptance Criteria:**
- Users can understand new behavior
- Migration path clear
- Examples provided

---

### Task 6.3: Code Review and Cleanup
- [ ] Review all changed code
- [ ] Check for:
  - Unused variables or imports
  - Inconsistent style
  - Missing error handling
  - Performance issues
- [ ] Clean up any debugging code

**Acceptance Criteria:**
- Code is clean and professional
- No unused code
- Consistent with project style

---

### Task 6.4: Final Validation
- [ ] Run `openspec validate scrape-rating-history --strict`
- [ ] Ensure all tasks are completed
- [ ] Verify all acceptance criteria met
- [ ] Prepare for merge

**Acceptance Criteria:**
- OpenSpec validation passes
- All tasks marked complete
- Ready for production

---

## Dependencies & Sequencing

**Critical Path:**
1. Phase 1: Core extraction (1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6)
2. Phase 3.1: Change detection (depends on Phase 1 & 2)
3. Phase 4: Notifications (depends on Phase 3)
4. Phase 5 & 6: Testing and cleanup (can run in parallel with above)

**Parallelizable:**
- Phase 2 (storage) can be developed alongside Phase 1 (they depend on each other)
- Unit tests (5.1, 5.2, 5.3, 5.4) can be written as code is developed

**Implementation Notes:**
- Each task should have a clear, testable definition
- Commit frequently after completing related tasks
- Run tests after each phase
- Update this file as tasks are completed
