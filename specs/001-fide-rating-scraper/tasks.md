# Tasks: FIDE Rating Scraper

**Input**: Design documents from `/specs/001-fide-rating-scraper/`
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

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project structure: tests/ directory at repository root
- [x] T002 [P] Create requirements.txt with requests and beautifulsoup4 dependencies
- [x] T003 [P] Create README.md with basic usage instructions per quickstart.md
- [x] T004 [P] Initialize gitignore for Python (.pyc, __pycache__, venv/, etc.)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core script structure that MUST be complete before user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Create main script file fide_scraper.py with basic structure (main function, argument parsing skeleton)
- [x] T006 [P] Create test directory structure: tests/test_fide_scraper.py and tests/test_integration.py with basic test class skeletons

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Retrieve Player Ratings by FIDE ID (Priority: P1) 🎯 MVP

**Goal**: Accept a FIDE ID, scrape the FIDE website, and output standard and rapid ratings in a human-readable format.

**Independent Test**: Run the script with a known FIDE ID (e.g., `python fide_scraper.py 538026660`) and verify that both standard and rapid ratings are retrieved and displayed correctly.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T007 [P] [US1] Unit test for FIDE ID validation function in tests/test_fide_scraper.py (test valid/invalid formats)
- [x] T008 [P] [US1] Unit test for rating extraction/parsing with mocked HTML in tests/test_fide_scraper.py
- [x] T009 [P] [US1] Unit test for error handling (network errors, HTTP errors, parsing errors) in tests/test_fide_scraper.py
- [x] T010 [P] [US1] Integration test for end-to-end flow with real FIDE ID in tests/test_integration.py (requires network)

### Implementation for User Story 1

- [x] T011 [US1] Implement FIDE ID validation function in fide_scraper.py (validates numeric, 4-10 digits per data-model.md)
- [x] T012 [US1] Implement function to construct FIDE profile URL in fide_scraper.py (format: https://ratings.fide.com/profile/{fide_id})
- [x] T013 [US1] Implement HTTP request function with timeout (10 seconds) and error handling in fide_scraper.py
- [x] T014 [US1] Implement HTML parsing function to extract standard rating from FIDE profile page in fide_scraper.py (use selectors documented in research.md HTML Structure Inspection section)
- [x] T015 [US1] Implement HTML parsing function to extract rapid rating from FIDE profile page in fide_scraper.py (use selectors documented in research.md HTML Structure Inspection section)
- [x] T016 [US1] Implement function to format and display ratings output (handles unrated cases) in fide_scraper.py
- [x] T017 [US1] Implement main function with command-line argument parsing (accepts FIDE ID as argument) in fide_scraper.py
- [x] T018 [US1] Implement stdin input handling (if no argument provided, read from stdin) in fide_scraper.py
- [x] T019 [US1] Integrate all functions: validation → request → parsing → output in main function in fide_scraper.py
- [x] T020 [US1] Implement proper exit codes (0 for success, 1 for errors, 2 for invalid format) per CLI contract in fide_scraper.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Run `python fide_scraper.py <FIDE_ID>` to verify.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Improvements, documentation, and final validation

- [x] T021 [P] Add docstrings to all functions in fide_scraper.py per Constitution Principle I (Code Quality)
- [x] T022 [P] Update README.md with complete usage examples, troubleshooting, and FIDE ID finding instructions
- [x] T023 [P] Add error message improvements for better user experience (more specific error messages per FR-006)
- [x] T024 [P] Run quickstart.md validation: verify all examples work correctly
- [x] T025 Code cleanup and refactoring: ensure code follows Python best practices
- [x] T026 [P] Add integration test for edge cases (unrated player, missing ratings) in tests/test_integration.py
- [x] T027 Verify all acceptance scenarios from spec.md work correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **Polish (Phase 4)**: Depends on User Story 1 completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within User Story 1

- Tests (T007-T010) MUST be written and FAIL before implementation
- Validation (T011) before URL construction (T012)
- URL construction (T012) before HTTP request (T013)
- HTTP request (T013) before parsing (T014, T015)
- Parsing (T014, T015) before formatting (T016)
- All components before integration (T019)
- Integration (T019) before exit codes (T020)

### Parallel Opportunities

- **Setup Phase**: T002, T003, T004 can run in parallel
- **Foundational Phase**: T006 can run in parallel with T005 (different files)
- **User Story 1 Tests**: T007, T008, T009, T010 can all run in parallel (different test functions)
- **User Story 1 Implementation**: 
  - T014 and T015 can run in parallel (different parsing functions)
  - T021, T022, T023, T024, T026 can run in parallel in Polish phase

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for FIDE ID validation function in tests/test_fide_scraper.py"
Task: "Unit test for rating extraction/parsing with mocked HTML in tests/test_fide_scraper.py"
Task: "Unit test for error handling in tests/test_fide_scraper.py"
Task: "Integration test for end-to-end flow in tests/test_integration.py"

# Launch parsing functions in parallel:
Task: "Implement HTML parsing function to extract standard rating in fide_scraper.py"
Task: "Implement HTML parsing function to extract rapid rating in fide_scraper.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently with `python fide_scraper.py <FIDE_ID>`
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add Polish improvements → Test → Deploy/Demo
4. Each phase adds value without breaking previous work

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: Write tests for User Story 1 (T007-T010)
   - Developer B: Implement validation and URL construction (T011-T012)
3. After tests written:
   - Developer A: Implement HTTP request and parsing (T013-T015)
   - Developer B: Implement formatting and main function (T016-T019)
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
- HTML selectors for FIDE website will need to be determined by inspecting actual website structure
- Consider rate limiting and respectful scraping practices

