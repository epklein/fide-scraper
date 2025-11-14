# Tasks: Batch FIDE Ratings Processing

**Input**: Design documents from `/specs/002-batch-fide-ratings/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included per Constitution Principle II (Testing) and plan.md test structure definition.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: Script at repository root, `tests/` directory at repository root
- Paths: `fide_scraper.py`, `tests/test_fide_scraper.py`, `tests/test_integration.py`

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Core functionality that MUST be complete before user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T001 Implement player name extraction function `extract_player_name(html: str) -> Optional[str]` in fide_scraper.py using selector `h1.player-title` from research.md
- [x] T002 [P] Unit test for player name extraction function with mocked HTML in tests/test_fide_scraper.py (test successful extraction, missing element, fallback scenarios)

**Checkpoint**: Foundation ready - player name extraction available for batch processing

---

## Phase 2: User Story 1 - Process Multiple FIDE IDs from File (Priority: P1) 🎯 MVP

**Goal**: Accept a file containing FIDE IDs (one per line), process each ID, extract player names and ratings, and output results to both a CSV file (with date-stamped filename) and the console.

**Independent Test**: Create a file with multiple FIDE IDs (one per line), run `python fide_scraper.py --file fide_ids.txt`, and verify that:
1. A CSV file is created with the correct filename format (including date)
2. The CSV contains all expected columns (FIDE ID, Player Name, Standard, Rapid, Blitz)
3. All valid FIDE IDs are processed and their ratings are included
4. The same content is displayed in the console
5. Invalid FIDE IDs are handled gracefully without stopping the entire batch

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] [US1] Unit test for file reading function `read_fide_ids_from_file` in tests/test_fide_scraper.py (test valid file, empty lines, file not found, permission errors)
- [x] T004 [P] [US1] Unit test for CSV generation function in tests/test_fide_scraper.py (test proper escaping, special characters, empty values, header row)
- [x] T005 [P] [US1] Unit test for date-stamped filename generation function in tests/test_fide_scraper.py (test ISO 8601 format, filename pattern)
- [x] T006 [P] [US1] Unit test for console output formatting function in tests/test_fide_scraper.py (test tabular format, column alignment, missing ratings)
- [x] T007 [P] [US1] Unit test for batch processing error handling in tests/test_fide_scraper.py (test invalid IDs skipped, network errors continue, player not found continues)
- [x] T008 [P] [US1] Integration test for end-to-end batch processing with real FIDE IDs in tests/test_integration.py (requires network, test file input, CSV output, console output)
- [x] T009 [P] [US1] Integration test for batch processing with mixed valid/invalid FIDE IDs in tests/test_integration.py (test error handling, partial success)

### Implementation for User Story 1

- [x] T010 [US1] Implement file reading function `read_fide_ids_from_file(filepath: str) -> List[str]` in fide_scraper.py (read file, skip empty lines, strip whitespace, handle encoding errors)
- [x] T011 [US1] Implement date-stamped filename generation function `generate_output_filename() -> str` in fide_scraper.py (format: `fide_ratings_YYYY-MM-DD.csv` using ISO 8601 format)
- [x] T012 [US1] Implement CSV generation function `write_csv_output(filename: str, player_profiles: List[Dict]) -> None` in fide_scraper.py (use csv.DictWriter, proper escaping, columns: FIDE ID, Player Name, Standard, Rapid, Blitz)
- [x] T013 [US1] Implement console output formatting function `format_console_output(player_profiles: List[Dict]) -> str` in fide_scraper.py (tabular format with aligned columns, handle missing ratings)
- [x] T014 [US1] Implement batch processing function `process_batch(fide_ids: List[str]) -> Tuple[List[Dict], List[str]]` in fide_scraper.py (process each ID, extract name and ratings, collect results and errors, continue on individual failures)
- [x] T015 [US1] Implement CLI argument parsing for `--file` / `-f` option in main function in fide_scraper.py (use argparse, maintain backward compatibility with single FIDE ID mode)
- [x] T016 [US1] Integrate batch processing: file reading → validation → batch processing → CSV writing → console output in main function in fide_scraper.py
- [x] T017 [US1] Implement error summary reporting in main function in fide_scraper.py (print success count, error count, error messages to stderr)
- [x] T018 [US1] Implement proper exit codes for batch mode in main function in fide_scraper.py (0 for success, 1 for file errors, 2 for file not found/permission denied per CLI contract)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Run `python fide_scraper.py --file fide_ids.txt` to verify batch processing works correctly.

---

## Phase 3: Polish & Cross-Cutting Concerns

**Purpose**: Improvements, documentation, and final validation

- [ ] T019 [P] Add docstrings to all new functions in fide_scraper.py per Constitution Principle I (Code Quality)
- [ ] T020 [P] Update README.md with batch processing usage examples, file format documentation, and troubleshooting guide
- [ ] T021 [P] Add error message improvements for batch processing (more specific error messages for file errors, network errors per FR-014)
- [ ] T022 [P] Run quickstart.md validation: verify all batch processing examples work correctly
- [ ] T023 Code cleanup and refactoring: ensure batch processing code follows Python best practices and existing code patterns
- [ ] T024 [P] Add integration test for edge cases in batch processing (empty file, file with only invalid IDs, very large file) in tests/test_integration.py
- [ ] T025 Verify all acceptance scenarios from spec.md work correctly (test each acceptance scenario independently)
- [ ] T026 [P] Verify backward compatibility: ensure single FIDE ID mode still works correctly after batch processing changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies - can start immediately
- **User Story 1 (Phase 2)**: Depends on Foundational completion (player name extraction required)
- **Polish (Phase 3)**: Depends on User Story 1 completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 1) - No dependencies on other stories

### Within User Story 1

- Tests (T003-T009) MUST be written and FAIL before implementation
- File reading (T010) before batch processing (T014)
- Filename generation (T011) before CSV writing (T012)
- CSV generation (T012) before batch processing integration (T016)
- Console formatting (T013) before batch processing integration (T016)
- Batch processing (T014) before CLI integration (T015, T016)
- CLI argument parsing (T015) before main integration (T016)
- All components before error summary (T017) and exit codes (T018)

### Parallel Opportunities

- **Foundational Phase**: T002 can run in parallel with T001 (different files)
- **User Story 1 Tests**: T003, T004, T005, T006, T007, T008, T009 can all run in parallel (different test functions)
- **User Story 1 Implementation**: 
  - T010, T011, T012, T013 can run in parallel (different utility functions)
  - T019, T020, T021, T022, T024, T026 can run in parallel in Polish phase

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for file reading function in tests/test_fide_scraper.py"
Task: "Unit test for CSV generation function in tests/test_fide_scraper.py"
Task: "Unit test for date-stamped filename generation function in tests/test_fide_scraper.py"
Task: "Unit test for console output formatting function in tests/test_fide_scraper.py"
Task: "Unit test for batch processing error handling in tests/test_fide_scraper.py"
Task: "Integration test for end-to-end batch processing in tests/test_integration.py"
Task: "Integration test for batch processing with mixed valid/invalid FIDE IDs in tests/test_integration.py"

# Launch utility functions in parallel:
Task: "Implement file reading function in fide_scraper.py"
Task: "Implement date-stamped filename generation function in fide_scraper.py"
Task: "Implement CSV generation function in fide_scraper.py"
Task: "Implement console output formatting function in fide_scraper.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Foundational (player name extraction)
2. Complete Phase 2: User Story 1 (batch processing)
3. **STOP and VALIDATE**: Test User Story 1 independently with `python fide_scraper.py --file fide_ids.txt`
4. Deploy/demo if ready

### Incremental Delivery

1. Complete Foundational → Player name extraction ready
2. Add file reading and CSV generation → Test independently
3. Add batch processing logic → Test independently
4. Add CLI integration → Test end-to-end
5. Add Polish improvements → Test → Deploy/Demo
6. Each phase adds value without breaking previous work

### Parallel Team Strategy

With multiple developers:

1. Team completes Foundational together
2. Once Foundational is done:
   - Developer A: Write tests for User Story 1 (T003-T009)
   - Developer B: Implement utility functions (T010-T013)
3. After tests written:
   - Developer A: Implement batch processing function (T014)
   - Developer B: Implement CLI integration (T015-T016)
4. Integration and polish together

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] label maps task to User Story 1 for traceability
- User Story 1 should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts
- Player name extraction uses selector `h1.player-title` from research.md
- CSV generation uses Python's csv module (standard library) per research.md
- Date format uses ISO 8601 (YYYY-MM-DD) per research.md
- Maintain backward compatibility with single FIDE ID mode
- Sequential processing (one FIDE ID at a time) per research.md
- Error handling: continue processing on individual failures per FR-008, FR-012, FR-013

