# Specification: Rating History Extraction

## Overview

Extract complete rating history (all monthly records) from a FIDE player profile instead of just the most recent record.

## ADDED Requirements

### Requirement: Extract All History Rows from Table

The system SHALL extract all data rows from the FIDE rating history table (`ContentPlaceHolder1_gdvRating`), not just the first row. Each row represents one monthly record with month/year and three rating categories (Standard, Rapid, Blitz).

**ID:** `RHE-001`
**Priority:** High

#### Scenario: Player with multiple months of history
Given a FIDE profile HTML with a rating history table containing 7 rows (Mar/2025 through Nov/2025)
When we extract rating history
Then we should receive 7 monthly records, one per row
And each record should contain month/year string and three rating values

#### Scenario: Empty or single-month profile
Given a FIDE profile with only one month in the rating table
When we extract rating history
Then we should receive exactly 1 record
And the system should not fail (minimum viable result)

---

### Requirement: Deduplicate by Month (Keep Topmost)

When a month appears multiple times in the scraped table, the system SHALL keep only the topmost (most recent) entry and discard lower entries.

**ID:** `RHE-002`
**Priority:** High

#### Scenario: Duplicate month entries
Given a FIDE profile where June/2025 appears twice in the table (at positions 3 and 5)
When we extract and deduplicate history
Then we should keep the June/2025 from the topmost position (position 3)
And discard the lower June/2025 entry (position 5)

#### Scenario: All months unique
Given a FIDE profile where all months are unique
When we deduplicate
Then all records should be preserved (no data loss)

---

### Requirement: Parse Month/Year String to Date

The system SHALL convert Portuguese month/year strings (e.g., "Nov/2025", "Out/2025") to ISO 8601 date format using the last day of the month.

**ID:** `RHE-003`
**Priority:** High

#### Scenario: November mapping
Given the month/year string "Nov/2025"
When we parse the date
Then we should get "2025-11-30" (last day of November)

#### Scenario: October mapping (Portuguese)
Given the month/year string "Out/2025"
When we parse the date
Then we should get "2025-10-31" (October is "Out" in Portuguese)

#### Scenario: February with leap year
Given the month/year string "Fev/2024" (leap year)
When we parse the date
Then we should get "2024-02-29"

#### Scenario: Invalid month string
Given an invalid month/year string like "Inv/2025" (invalid Portuguese month)
When we parse the date
Then we should return None (graceful error handling)

---

### Requirement: Return Structured History List

The system SHALL return extracted history as a list of dictionaries, each containing month date and three rating values.

**ID:** `RHE-004`
**Priority:** High

#### Scenario: Complete history structure
Given a scraped HTML table
When we extract history
Then each record should contain:
  - `date`: ISO 8601 date string (last day of month)
  - `standard`: Integer rating or None
  - `rapid`: Integer rating or None
  - `blitz`: Integer rating or None

#### Scenario: Unrated categories
Given a profile where a month has "unrated" or empty values for some categories
When we extract that month
Then those categories should be None in the returned record
And we should not exclude the entire month

---

## Implementation Notes

- Portuguese month abbreviations: Jan, Fev, Mar, Abr, Mai, Jun, Jul, Ago, Set, Out, Nov, Dez
- Uses `calendar.monthrange()` to calculate last day of month correctly
- Gracefully handles malformed HTML or missing table
- Returns empty list if no valid records found (not an error condition)
