# Specification: Change Detection (New Months)

## Overview

Detect when new monthly records are added to a player's rating history. Notifications are triggered only when months that didn't exist in the previous scrape are found in the current scrape.

## MODIFIED Requirements

### Requirement: Detect New Months in History

The system SHALL compare the complete scraped monthly history against the stored monthly history to identify months that are new (exist in scraped but not in stored history).

**ID:** `CD-001`
**Previous Behavior:** Detect rating value changes between daily records
**New Behavior:** Detect new months added to the rating history

#### Scenario: New month added
Given stored history for player 94157: [March 2025, April 2025]
And scraped history: [May 2025, April 2025, March 2025]
When change detection runs
Then it should identify May 2025 as new
And return one new month in the results

#### Scenario: Existing month updated
Given stored history: [November 2025 with Rapid=1914]
And scraped history: [November 2025 with Rapid=1920]
When change detection runs
Then it should identify November 2025 as new
And return one new month in the results

#### Scenario: Multiple new months
Given stored history: [March 2025]
And scraped history: [May 2025, April 2025, March 2025]
When change detection runs
Then it should identify both April and May as new
And return two new months in the results

#### Scenario: No new months
Given stored history: [May 2025, April 2025, March 2025]
And scraped history: [May 2025, April 2025, March 2025]
When change detection runs
Then no new months should be detected
And result should be empty list (no changes)

---

### Requirement: Handle Incomplete History

When stored history is empty or partial (first run or scraper was inactive), the system SHALL treat all scraped months as new to ensure complete history is captured.

**ID:** `CD-002`

#### Scenario: First run (empty history)
Given stored history: [] (empty)
And scraped history: [May 2025, April 2025, March 2025]
When change detection runs
Then all three months should be identified as new
And a notification should be triggered for the most recent month

#### Scenario: Partial history catch-up
Given stored history: [May 2025] (scraper was inactive for March-April)
And scraped history: [May 2025, April 2025, March 2025]
When change detection runs
Then April and March should be identified as new
And no notifications should be triggered

---

### Requirement: Return Only New Months

Change detection results SHALL contain only the new months, with sufficient detail for notifications.

**ID:** `CD-003`

#### Scenario: New month record structure
Given a detected new month
When returned in change detection results
Then it should contain:
  - `date`: ISO 8601 date of the month (last day)
  - `standard`: Standard rating value (or None)
  - `rapid`: Rapid rating value (or None)
  - `blitz`: Blitz rating value (or None)

#### Scenario: Result for player with no changes
Given a player with no new months detected
When included in results
Then the result should indicate no changes (empty list for new_months key)

---

## Implementation Notes

- Comparison is based on month date (YYYY-MM-DD), not the rating values
- A month is "new" if its date doesn't exist in stored history
- Month comparison is case-insensitive for date strings
- System handles gap-filling: if player had months M1, M2, and now has M1, M3, M4, then M3 and M4 are new (not "re-discovery")
- Missing stored history (first run) should not block change detection; treat as empty history
