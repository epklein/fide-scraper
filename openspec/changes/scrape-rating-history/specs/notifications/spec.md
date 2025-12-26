# Specification: Notifications (New Months Only)

## Overview

Email and API notifications are triggered only when new months are detected in a player's rating history, not on every scrape or rating value change.

## MODIFIED Requirements

### Requirement: Send Notifications Only for New Months

The system SHALL send email and API notifications when a player has new months detected. The system SHALL skip players with no new months.

**ID:** `NOTIF-001`
**Previous Behavior:** Notify on any rating value change
**New Behavior:** Notify only when new months are added to history

#### Scenario: New month triggers notification
Given player 94157 with a newly detected May 2025 record
When email notification is sent
Then the recipient should be informed about the new May 2025 rating data
And the notification should include the May 2025 ratings

#### Scenario: Updated existing month does not trigger
Given player 94157 where November 2025 already existed but rating changed
When change detection runs
Then no notification should be triggered (month is not new)

#### Scenario: Multiple new months in one run
Given player 94157 with April and May 2025 detected as new
When notification is sent
Then the email should list both new months
Or it should note that multiple new records were found

---

### Requirement: Email Content Format

Email notifications SHALL clearly indicate that new historical months were found and SHALL list the new month data.

**ID:** `NOTIF-002`

#### Scenario: Email subject
Given a player with new months detected
When email is composed
Then the subject should indicate new rating history was found
Example: "New Rating History Found - Eduardo Pavinato Klein"

#### Scenario: Email body format
Given new months for a player
When email body is composed
Then it should include:
  - Player name and FIDE ID
  - List of newly detected months
  - For each new month: month date and three ratings (Standard, Rapid, Blitz)
  - Link to FIDE player profile

#### Scenario: Single month
Given one new month (e.g., May 2025)
When email is composed
Then it should clearly present that single month's data

#### Scenario: Multiple new months
Given several new months (e.g., March, April, May 2025)
When email is composed
Then all months should be listed in chronological order or reverse chronological order
And all ratings should be clearly presented

---

### Requirement: API Notification Content

API notifications SHALL POST the new month data to the external ratings API when configured.

**ID:** `NOTIF-003`

#### Scenario: API endpoint call
Given a player with new months and API endpoint configured
When API notification runs
Then it should POST to the configured endpoint
And include all new month data in the request

#### Scenario: API request format
Given new months to post
When composing API request
Then it should include:
  - `date`: Month date (ISO 8601)
  - `fide_id`: Player's FIDE ID
  - `player_name`: Player name
  - `standard_rating`: Standard rating (or null)
  - `rapid_rating`: Rapid rating (or null)
  - `blitz_rating`: Blitz rating (or null)

#### Scenario: Multiple month posts
Given multiple new months for one player
When posting to API
Then each month should be posted as a separate request
Or they should be batched in a single request (specify if applicable)

---

### Requirement: Handle Players with No Changes

Players with no new months detected SHALL be completely skipped in notification processing.

**ID:** `NOTIF-004`

#### Scenario: Skip notification for unchanged players
Given a batch of 10 players, where 3 have new months
When notification processing runs
Then only 3 players should receive notifications
And 7 players should be skipped silently

#### Scenario: Opt-out unchanged players
Given unchanged players in the results
When checking for new_months
Then empty list or falsy new_months should result in skip
And no error should be raised for skipped players

---

## Implementation Notes

- Only iterate over players with non-empty new_months list in notification modules
- Preserve backward compatibility: email/API format changes but content is still meaningful
- New month sorting: could be chronological order or reverse (specify preferred order)
- Error handling: continue processing other players if one notification fails
- Logging: log which players received notifications and which were skipped
