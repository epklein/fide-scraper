# Implementation Tasks: Quick Execution Mode

## 1. CLI Interface Updates

- [x] 1.1 Add `--quick` argument to argparse in `main()` function
- [x] 1.2 Validate that `--quick` flag is a boolean option
- [x] 1.3 Update help text to describe quick mode behavior
- [x] 1.4 Write unit tests for CLI argument parsing with `--quick` flag

## 2. Quick Mode Logic Implementation

- [x] 2.1 Extract player ID selection logic into a separate function `select_fide_ids_for_processing()`
  - Takes: execution_mode (str), api_endpoint (str), api_token (str), csv_player_data (dict)
  - Returns: tuple of (selected_ids: List[str], new_ids: List[str])
  - Handles both normal and quick modes
- [x] 2.2 Implement quick mode ID filtering in the new function
  - Fetch API IDs
  - Compare against CSV IDs
  - Return only new IDs when in quick mode
  - Return all CSV IDs when in normal mode
- [x] 2.3 Update `main()` to use the new selection function based on `--quick` flag
- [x] 2.4 Write unit tests for `select_fide_ids_for_processing()` with various scenarios

## 3. Execution Flow Updates

- [x] 3.1 Ensure player file augmentation still occurs in quick mode
- [x] 3.2 Ensure selected IDs are passed to `process_batch()` correctly
- [x] 3.3 Test that notifications work for quick mode (same as normal)
- [x] 3.4 Test that API updates work for quick mode (same as normal)

## 4. Error Handling & Logging

- [x] 4.1 Add clear logging to indicate which execution mode is active
- [x] 4.2 Add logging for ID selection decisions (new vs. existing)
- [x] 4.3 Handle case where API is unavailable in quick mode
- [x] 4.4 Handle case where no new IDs are found (valid scenario)
- [x] 4.5 Write integration tests for error scenarios in quick mode

## 5. CSV Output & Integration

- [x] 5.1 Verify CSV output works correctly with quick mode results
- [x] 5.2 Ensure historical rating files are updated correctly with new players
- [x] 5.3 Test that new players added to players.csv are tracked on next run

## 6. Testing & Validation

- [x] 6.1 Unit tests for ID selection logic (quick vs. normal mode)
- [x] 6.2 Integration tests with mock API responses
- [x] 6.3 Integration tests with actual test CSV files
- [x] 6.4 Test exit codes in various scenarios (success, no new IDs, API failures)
- [x] 6.5 Test backward compatibility (normal mode unchanged)
- [x] 6.6 Manual testing with actual scraper run

## 7. Documentation Updates

- [x] 7.1 Update README.md with quick mode usage instructions
- [x] 7.2 Update .env.example comments if needed
- [x] 7.3 Document the execution modes and when to use each

## Validation Criteria

- [x] `--quick` flag is recognized and functional
- [x] Quick mode processes only new API IDs, not existing CSV IDs
- [x] Normal mode (default) remains unchanged
- [x] Players.csv is augmented in both modes
- [x] Notifications and API updates work the same in both modes
- [x] Error handling is graceful in both modes
- [x] All existing tests pass (43/43)
- [x] New tests validate quick mode behavior (7/7 tests)
