# Specification: Rating Storage (Monthly Model)

## Overview

Store player rating records with monthly granularity (one row per month per player) instead of daily granularity. Each month is identified by the last day of that month.

## MODIFIED Requirements

### Requirement: Store Ratings by Month (Replace Daily Model)

The CSV output file SHALL store one record per unique month-year combination per player. When the same month is scraped again, the previous record SHALL be replaced (UPDATE semantics).

**ID:** `RS-001`
**Previous Behavior:** One row per day per player
**New Behavior:** One row per month per player

#### Scenario: Append new month
Given an existing CSV with records for March and April 2025 for player 94157
When May 2025 is scraped
Then May 2025 should be appended as a new row
And the file should now contain 3 monthly records for that player

#### Scenario: Update existing month
Given an existing CSV with November 2025 data for player 94157 showing Rapid=1914
When November 2025 is scraped again with Rapid=1920
Then the existing November row should be replaced (not duplicated)
And the file should still contain one November entry with the new rating

#### Scenario: Multiple players
Given a CSV with records for players 94157 and 12345
When new months are scraped for both players
Then both players' monthly records should be stored
And the file should contain M months for player1 and N months for player2

---

### Requirement: CSV Column Format

The CSV output file SHALL continue using the "Date" column, but values now represent the last day of each month (ISO 8601 format) instead of the current date.

**ID:** `RS-002`
**Breaking Change:** No (column name preserved, semantics change only)

#### Scenario: CSV headers
Given a new CSV output file
When headers are written
Then the columns should be: `Date,FIDE ID,Player Name,Standard,Rapid,Blitz` (unchanged from previous format)

#### Scenario: Date format in CSV
Given a player with records for November 2025 and October 2025
When written to CSV
Then the Date column should contain values like:
  - `2025-11-30` (last day of November)
  - `2025-10-31` (last day of October)

---

### Requirement: Handle Month Replacement

When writing CSV output, the system SHALL replace any existing row with the same (FIDE ID, Month) combination, preserving all other records.

**ID:** `RS-003`

#### Scenario: Idempotent writes
Given a CSV with November 2025 data
When the same player's November 2025 is scraped and written again
Then the file should still contain exactly one November row (not duplicated)

#### Scenario: Preserve other months
Given a CSV with data for March, April, May, and June 2025
When only May is updated
Then March, April, and June should remain unchanged
And May should be updated with new values

---

## Implementation Notes

- Use ISO 8601 date format for month values (YYYY-MM-DD)
- Calculate last day of month using `calendar.monthrange()` or equivalent
- Read entire CSV on write, filter out matching months, append updated months (for simplicity)
- Preserve month order in CSV (optional - can be any order, or can sort by month)
- Empty string represents unrated/missing values in rating columns (backward compatible)
