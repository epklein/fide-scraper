# Feature Specification: Player Rating Change Email Notifications

**Feature Branch**: `003-player-rating-emails`
**Created**: 2025-11-23
**Status**: Draft
**Input**: User description: "I want to send an e-mail for a player when any of their ratings have changed. We need a file with FIDE ID,email so that when the player has an e-mail configured, and a change was detected, an e-mail is sent. all e-mails should also be CC to a default e-mail configured in the .env file."

## Clarifications

### Session 2025-11-23

- Q1: Should the system support only `players.csv` or both `fide_ids.txt` and `players.csv`? → A: Support only `players.csv` - fully migrate away from `fide_ids.txt`
- Q2: Should the scraper process all players in `players.csv` or only those with email addresses? → A: Process all players, send notifications only for those with email addresses configured
- Q3: What environment variable name for the `players.csv` file path? → B: `FIDE_PLAYERS_FILE` - More explicit that it's chess player data

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Load Player Data with Optional Email Configuration (Priority: P1)

A system administrator maintains a unified player data file (`players.csv`) containing FIDE IDs and optional email addresses. The system must read this consolidated file to identify which players to track and which players to notify when ratings change.

**Why this priority**: This is the foundational data requirement that enables the entire notification system. Without a way to specify player data and email preferences in a unified file, the feature cannot function at all.

**Independent Test**: Can be fully tested by loading a `players.csv` file and verifying that the system correctly reads all players and their associated email addresses (including handling of empty/missing email values), providing a foundation for subsequent email delivery.

**Acceptance Scenarios**:

1. **Given** a CSV file named `players.csv` with headers "FIDE ID,email" and rows with both FIDE IDs and email addresses, **When** the system loads the file, **Then** all valid player-to-email mappings are successfully stored and can be retrieved

2. **Given** a CSV file with some rows having FIDE IDs but empty/missing email values, **When** the system loads the file, **Then** the system handles missing emails gracefully (logs info) and processes all players regardless of email presence

3. **Given** a CSV file with malformed FIDE IDs or invalid email formats, **When** the system loads the file, **Then** the system validates entries gracefully (logs warnings) and proceeds with valid entries

4. **Given** a `players.csv` file that doesn't exist or is inaccessible, **When** the system attempts to load it, **Then** the system provides a clear error message and allows graceful degradation

---

### User Story 2 - Detect Rating Changes (Priority: P1)

When the rating scraper runs and retrieves player ratings, the system needs to detect when a player's rating has changed from the previous recorded value.

**Why this priority**: Detecting changes is the core logic that triggers notifications. Without accurate change detection, the system won't know which players need to be notified.

**Independent Test**: Can be fully tested by comparing new rating data against historical data and verifying that changed ratings are correctly identified for all rating types (standard, rapid, blitz).

**Acceptance Scenarios**:

1. **Given** a player with previously recorded standard rating of 2500, **When** the new rating is fetched as 2510, **Then** the system detects a change in the standard rating

2. **Given** a player with unchanged rapid rating of 2400, **When** the rating scraper runs again, **Then** the system correctly identifies no change in the rapid rating

3. **Given** a player with a previous unrated status in blitz, **When** the player now has a blitz rating of 2100, **Then** the system detects this as a change (unrated → rated)

4. **Given** a player with multiple rating types, **When** only one rating type changes (e.g., standard changes but rapid stays same), **Then** the system correctly identifies which specific rating(s) changed

---

### User Story 3 - Send Email Notifications to Players (Priority: P1)

When a player's rating has changed and an email address is configured for that player, the system needs to send an email notification to that player about their rating change.

**Why this priority**: This is the core feature that delivers value to players—notifying them of their rating changes. Without sending emails, detected changes provide no benefit.

**Independent Test**: Can be fully tested by triggering rating change detection for a player with a configured email and verifying that an email is successfully sent with the correct rating change information.

**Acceptance Scenarios**:

1. **Given** a player with a detected rating change and a configured email address, **When** the email notification is sent, **Then** the player receives an email containing their FIDE ID, player name, and the updated ratings

2. **Given** a player with no configured email address despite a rating change, **When** the scraper runs, **Then** the system skips email notification for that player (no errors)

3. **Given** an email delivery failure (e.g., invalid email address, SMTP error), **When** the system attempts to send the notification, **Then** the failure is logged and the process continues with other players

---

### User Story 4 - CC Default Email Address (Priority: P2)

All rating change notification emails must be sent with a CC to a default email address configured in the environment, allowing administrators to monitor player notifications.

**Why this priority**: Monitoring player notifications helps administrators verify the notification system is working and maintain transparency. It's valuable but not essential for the core feature.

**Independent Test**: Can be fully tested by sending a notification email and verifying that the CC address from environment configuration is correctly included on the message.

**Acceptance Scenarios**:

1. **Given** a notification email being sent and a default CC email configured in .env, **When** the email is composed, **Then** the CC recipient address is included in the email headers

2. **Given** no default CC email configured in .env, **When** the system sends a notification, **Then** the system handles the missing configuration gracefully (either skips CC or shows a warning)

3. **Given** a notification being sent to a player, **When** the player receives the email, **Then** the CC recipient also receives the same email

### Edge Cases

- What happens when a player's rating goes from rated to unrated (e.g., due to inactivity)?
- How does the system handle duplicate FIDE IDs in the `players.csv` file? (Only first occurrence used? Error? Last occurrence wins?)
- What happens if the same FIDE ID appears multiple times in `players.csv` with different email addresses?
- How should the system behave if a row in `players.csv` has a FIDE ID but no email column value (empty/blank)?
- How should the system behave if SMTP configuration is missing or invalid when attempting to send emails?
- What happens if a rating changes multiple times on the same day when the scraper runs multiple times?
- What happens if `players.csv` exists but is empty (only headers)?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST load player data from a CSV file named `players.csv` (or path specified by `FIDE_PLAYERS_FILE` env var) with headers "FIDE ID,email"

- **FR-002**: System MUST process ALL players in `players.csv`, regardless of whether they have an email address configured

- **FR-003**: System MUST validate FIDE IDs in the player data file and skip invalid entries with appropriate logging

- **FR-004**: System MUST validate email addresses in the player data file when present and skip entries with invalid email formats (leaving the email field empty in such cases)

- **FR-005**: System MUST handle empty/missing email values gracefully (a missing email indicates the player has not opted in for notifications)

- **FR-006**: System MUST compare current fetched ratings (standard, rapid, blitz) against the most recent previously recorded ratings for each player

- **FR-007**: System MUST detect changes in any rating type (a player changed from unrated to rated, or a rating value changed)

- **FR-008**: System MUST identify which specific rating types have changed for each player

- **FR-009**: System MUST send an email notification ONLY to players who have a configured email address AND have experienced a rating change

- **FR-010**: System MUST include the player's name, FIDE ID, and all updated rating values (standard, rapid, blitz) in notification emails

- **FR-011**: System MUST include the change detection in the email notification (show previous vs. new values, or clearly indicate which ratings changed)

- **FR-012**: System MUST CC a default email address (configured via environment variable) on all player rating change notifications

- **FR-013**: System MUST handle missing or invalid SMTP configuration gracefully without crashing the rating scraper

- **FR-014**: System MUST log all email send attempts and failures for debugging and audit purposes

- **FR-015**: System MUST continue processing remaining players even if email delivery fails for one player

- **FR-016**: System MUST read the default CC email address from the .env file as `ADMIN_CC_EMAIL` environment variable

### Key Entities *(include if feature involves data)*

- **Player Record** (`players.csv`): A unified CSV file containing player data with optional email addresses
  - Attributes: FIDE ID (unique identifier, 4-10 digits), email address (optional contact point for notifications, may be empty)
  - Relationships: Links to player ratings data from the scraper; one email per player

- **Rating Change Record**: Captured data about rating changes detected between scraper runs
  - Attributes: FIDE ID, player name, rating type (standard/rapid/blitz), previous value, current value, detection timestamp
  - Relationships: Triggers email notification if player has a non-empty email address in `players.csv`

- **Email Notification**: Sent when a rating change is detected for a player with a configured email
  - Attributes: recipient email, CC email, player info, rating changes, send timestamp, delivery status
  - Relationships: Based on rating change record and player email configuration in `players.csv`

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Players with configured emails receive notification within 5 minutes of rating change detection during batch runs

- **SC-002**: 99% of players with valid email addresses successfully receive notifications when their ratings change

- **SC-003**: All configured CC recipients receive copies of player notification emails sent by the system

- **SC-004**: System handles at least 100 concurrent player email notifications without errors or timeouts

- **SC-005**: Administrators can easily verify notification system operation by reviewing CC'd emails received at the default email address

- **SC-006**: System processes player email configurations with no performance degradation compared to baseline scraper performance (rating data should be retrieved and processed in same time window)

## Assumptions

- The unified player data file is named `players.csv` (default location) or specified via `FIDE_PLAYERS_FILE` environment variable
- The `players.csv` file uses CSV format with "FIDE ID,email" headers
- Email values in `players.csv` can be empty/blank to indicate a player has not opted in for notifications
- The system processes ALL players in `players.csv` for rating updates, but sends notifications only for players with non-empty email addresses
- Email sending uses standard SMTP configuration (following existing project patterns with environment variables)
- Default CC email (`ADMIN_CC_EMAIL`) is optional—if not configured, emails are sent only to the player (and no CC)
- Rating change comparison uses the most recent previous record from the CSV history for each player
- Players may have multiple rating types (standard, rapid, blitz) and notification should mention all types that changed
- Email addresses should be validated using standard email format validation (basic RFC pattern, not full RFC 5322 compliance)
- The system will not delete or archive the player data file; it will be maintained by administrators
- The legacy `fide_ids.txt` format is no longer used; all player data is consolidated in `players.csv`
