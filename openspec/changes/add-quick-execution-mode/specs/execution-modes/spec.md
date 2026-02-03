# Specification: Execution Modes

## Overview

Support multiple execution modes for the FIDE scraper: normal (default) and quick (API-only new IDs).

## ADDED Requirements

### Requirement: Quick Execution Mode Flag

The system SHALL support a `--quick` command-line argument to enable quick execution mode.

**ID:** `EM-001`

#### Scenario: Quick flag provided
- **WHEN** the scraper is invoked with `--quick` flag
- **THEN** the scraper SHALL enter quick execution mode
- **AND** only new FIDE IDs from the API are processed

#### Scenario: Quick flag not provided
- **WHEN** the scraper is invoked without any flags (default behavior)
- **THEN** the scraper SHALL enter normal execution mode
- **AND** all FIDE IDs from players.csv are processed

---

### Requirement: Quick Mode ID Selection

In quick execution mode, the system SHALL fetch FIDE IDs from the API and process only the new IDs (those not already in players.csv).

**ID:** `EM-002`

#### Scenario: New IDs from API in quick mode
Given the API returns IDs: [1001, 1002, 1003]
And players.csv currently contains: [1001, 1002]
When the scraper runs with `--quick` flag
Then it SHALL select [1003] for processing
And skip processing [1001, 1002]

#### Scenario: All API IDs are new in quick mode
Given the API returns IDs: [2001, 2002, 2003]
And players.csv currently is empty
When the scraper runs with `--quick` flag
Then it SHALL select all [2001, 2002, 2003] for processing

#### Scenario: No new IDs in quick mode
Given the API returns IDs: [1001, 1002]
And players.csv already contains: [1001, 1002]
When the scraper runs with `--quick` flag
Then no IDs SHALL be selected for processing
And the run succeeds with no players processed

#### Scenario: API unavailable in quick mode
Given the API endpoint is unavailable
When the scraper runs with `--quick` flag
And API fetch fails
Then the scraper SHALL log the failure
And exit gracefully with error code indicating no players processed

---

### Requirement: Quick Mode Player File Augmentation

In quick execution mode, new IDs SHALL still be added to players.csv to track them for future runs.

**ID:** `EM-003`

#### Scenario: Augment players.csv in quick mode
Given the API returns new IDs: [4001, 4002]
And players.csv currently contains: [1001, 1002]
When the scraper runs with `--quick` flag and new IDs are processed
Then players.csv SHALL be updated to contain: [1001, 1002, 4001, 4002]

#### Scenario: Augmentation failure in quick mode
Given augmentation of players.csv fails
When the scraper is running in quick mode
Then it SHALL log the failure
And continue processing new IDs that were already fetched

---

### Requirement: Normal Mode Unchanged

Normal execution mode (default, no flag) SHALL remain unchanged and process all FIDE IDs from players.csv.

**ID:** `EM-004`

#### Scenario: Normal mode processes all IDs
Given the scraper is invoked without any flags
And players.csv contains: [1001, 1002, 1003, 1004]
When normal mode runs
Then all [1001, 1002, 1003, 1004] SHALL be selected for processing

#### Scenario: API is still used in normal mode
Given the scraper is invoked without any flags
And the API is configured and available
When normal mode runs
Then players.csv SHALL be augmented with new API IDs
And all IDs from the updated players.csv SHALL be processed

---

## Implementation Notes

- Quick mode depends on `fetch_fide_ids_from_api()` and `merge_player_ids()` existing and working correctly
- Quick mode should not require changes to notification, API update, or CSV output logic
- Exit code semantics:
  - 0: Success (at least one player processed)
  - 1: Failure (no players processed, errors occurred)
  - 2: Configuration/validation error
- Quick mode gracefully handles empty API response (0 new IDs) - this is a valid scenario, not an error
- Error messages should clearly indicate when running in quick mode vs. normal mode
