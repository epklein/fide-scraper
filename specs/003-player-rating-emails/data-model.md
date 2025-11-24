# Data Model: Player Rating Change Email Notifications

**Date**: 2025-11-23
**Feature**: 003-player-rating-emails
**Status**: ✅ Complete

---

## Entities

### 1. Player Record

**Source**: `players.csv`
**Purpose**: Unified input file defining players to track and their email preferences

**Fields**:

| Field | Type | Constraints | Example | Notes |
|-------|------|-------------|---------|-------|
| FIDE ID | String | Required, 4-10 digits, numeric, unique (ideally) | "12345678" | Primary identifier for lookup |
| email | String | Optional, valid email format or empty | "player@example.com" or "" | Empty = opt out of notifications |

**Validation Rules**:
- `FIDE ID`: Must be numeric, length 4-10, non-empty
- `email`: If non-empty, must match basic RFC pattern `\S+@\S+\.\S+`
- Duplicate FIDE IDs: Log warning, use first occurrence (or configurable strategy)
- Invalid entries: Log warning, skip row, continue processing

**Example**:
```csv
FIDE ID,email
12345678,alice@example.com
87654321,bob@example.com
11111111,
22222222,invalid-email-format
```

---

### 2. Rating Record (Historical)

**Source**: `fide_ratings.csv` (existing, appended by scraper)
**Purpose**: Stores player ratings over time for change detection

**Fields** (existing structure maintained):

| Field | Type | Constraints | Example | Notes |
|-------|------|-------------|---------|-------|
| Date | String (ISO 8601) | Required, YYYY-MM-DD format | "2025-11-23" | Sort key for finding latest |
| FIDE ID | String | Required, 4-10 digits | "12345678" | Links to Player Record |
| Player Name | String | Optional | "Alice Smith" | Display in notifications |
| Standard | Integer or empty | Optional, 0-3000 range | "2450" or "" | Rating value or unrated |
| Rapid | Integer or empty | Optional, 0-3000 range | "2300" or "" | Rating value or unrated |
| Blitz | Integer or empty | Optional, 0-3000 range | "2100" or "" | Rating value or unrated |

**Relationships**:
- Foreign key to `players.csv` via FIDE ID
- Latest record per player found by sorting on Date (descending)

**Example**:
```csv
Date,FIDE ID,Player Name,Standard,Rapid,Blitz
2025-11-23,12345678,Alice Smith,2450,2300,2100
2025-11-23,87654321,Bob Jones,2500,2400,
2025-11-22,12345678,Alice Smith,2440,2300,2100
```

---

### 3. Rating Change Record (Derived/Computed)

**Source**: Computed by comparing current fetch against historical data
**Purpose**: Identifies which ratings changed for a player, used to trigger notifications

**Fields**:

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| FIDE ID | String | Player identifier | "12345678" |
| Player Name | String | Display name | "Alice Smith" |
| Changed Ratings | Dict[str, Tuple] | Rating type → (old_value, new_value) | `{"Standard": (2440, 2450)}` |
| Detected At | String (ISO 8601) | Timestamp of detection | "2025-11-23T14:30:00Z" |

**Validation**:
- FIDE ID must exist in `players.csv`
- Player email must be non-empty in `players.csv` for notification
- At least one rating must have changed (Standard, Rapid, or Blitz)

**Example**:
```python
{
    "FIDE ID": "12345678",
    "Player Name": "Alice Smith",
    "Changed Ratings": {
        "Standard": (2440, 2450),  # Previous, New
        "Rapid": (2300, 2300)      # No change
    },
    "Detected At": "2025-11-23T14:30:00Z"
}
```

---

### 4. Email Notification Record

**Source**: Generated when sending email
**Purpose**: Audit trail of notifications sent

**Fields** (conceptual, logged but not persisted):

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| Recipient | String (email) | Player's email address | "alice@example.com" |
| CC | String (email) | Administrator email (optional) | "admin@example.com" or null |
| Subject | String | Email subject line | "Your FIDE Rating Update - Alice Smith" |
| Body | String (text/html) | Email content | "Your ratings have been updated..." |
| Sent At | String (ISO 8601) | Timestamp of send attempt | "2025-11-23T14:30:15Z" |
| Status | Enum | Success or error | "success" or "smtp_error" |
| Error Message | String (optional) | If status != success | "Connection timeout" |

**SMTP Headers**:
```
From: [SMTP_USERNAME or default]
To: [Recipient]
CC: [CC or absent]
Subject: [Subject]
Content-Type: text/plain; charset=utf-8
```

---

## State Transitions

### Player Processing Flow

```
┌─────────────────┐
│  Load players   │
│  from CSV       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Validate       │
│  (FIDE ID, email)
└────────┬────────┘
         │
    ┌────┴──────────────┐
    │                   │
    ▼ Valid            ▼ Invalid
┌─────────┐        ┌────────────┐
│ Process │        │ Log warning│
│ rating  │        │ Skip row   │
└────┬────┘        └────────────┘
     │
     ▼
┌──────────────────────┐
│ Fetch FIDE profile   │
│ Extract ratings      │
└────────┬─────────────┘
         │
         ▼
┌──────────────────────┐
│ Detect changes       │
│ (compare vs history) │
└────────┬─────────────┘
         │
    ┌────┴─────────┐
    │              │
    ▼ Changed      ▼ Unchanged
┌──────────────┐  (No action)
│ Has email?   │
└────┬─────────┘
     │
  ┌──┴──────────┐
  │             │
  ▼ Yes        ▼ No
┌──────────┐  (Skip email)
│ Send     │
│ email    │
└──────────┘
```

### Email Notification State

```
┌───────────────────┐
│ Compose email     │
│ (subject, body,   │
│  CC)              │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ Open SMTP conn    │
│ (with error       │
│  handling)        │
└────────┬──────────┘
         │
    ┌────┴──────────────┐
    │                   │
    ▼ Connected        ▼ Error
┌──────────────┐   ┌─────────────┐
│ Send message │   │ Log error   │
└────┬─────────┘   │ Continue    │
     │             └─────────────┘
     ▼
┌──────────────┐
│ Close conn   │
└────┬─────────┘
     │
  ┌──┴────────┐
  │           │
  ▼ Success   ▼ Failure
┌────────┐   ┌────────────┐
│ Log OK │   │ Log error  │
└────────┘   │ Continue   │
             └────────────┘
```

---

## Constraints & Validation

### CSV Format Constraints

**Players.csv**:
- Must have headers: "FIDE ID,email"
- FIDE ID: numeric, 4-10 digits, non-empty
- email: must be valid RFC email or empty string
- No extra columns allowed (strict parsing)
- UTF-8 encoding

**Fide_ratings.csv**:
- Must have headers: "Date,FIDE ID,Player Name,Standard,Rapid,Blitz"
- Date: ISO 8601 format (YYYY-MM-DD)
- Ratings: numeric or empty, 0-3000 range

### Business Logic Constraints

1. **Change Detection**:
   - Compare only latest record per player
   - Treat empty (null) as different from numeric rating
   - If all three rating types unchanged → no notification

2. **Email Filtering**:
   - Send only if: email ≠ empty AND changed ratings exist
   - Missing email → skip notification (no error)
   - Invalid email format → log warning, skip

3. **Rate Limiting**:
   - No explicit rate limiting (batch process runs once per interval)
   - SMTP server may rate-limit; handled by catch-and-log

4. **Duplicate Detection**:
   - Duplicate FIDE IDs in `players.csv`: Use first occurrence
   - Log warning for each duplicate found

---

## Data Storage & Retrieval

### File-Based Storage

**Input**: `players.csv`
- Location: `${FIDE_PLAYERS_FILE}` env var (default: `players.csv`)
- Format: CSV (UTF-8)
- Access: Read-only during batch run
- Frequency: Loaded once per batch run

**Historical Reference**: `fide_ratings.csv`
- Location: `${FIDE_OUTPUT_FILE}` env var (default: `fide_ratings.csv`)
- Format: CSV (UTF-8), date-indexed
- Access: Read for change detection, append for new records
- Frequency: Read at start, appended at end

**Audit Trail** (logging only):
- Email send attempts logged to stdout/stderr
- Rotation/archiving: TBD by project policy

### In-Memory Processing

During batch run:
1. Load `players.csv` into dict: `player_dict[fide_id] = {"email": "..."}` → O(n) space
2. Load latest records from `fide_ratings.csv` → O(m) space (m = # unique players in history)
3. Process batch, detect changes, send emails
4. Append new records to `fide_ratings.csv`

**Memory Assumptions**:
- Up to 1000 players: ~100KB
- Up to 100k historical records: ~1MB
- Email sending: Temporary objects garbage collected

---

## API/Function Signatures

See [contracts/](contracts/) directory for detailed signatures. Key functions:

```python
# Player data loading
load_player_data_from_csv(filepath: str) -> Dict[str, Dict[str, Optional[str]]]
validate_fide_id(fide_id: str) -> bool
validate_email(email: str) -> bool

# Rating change detection
detect_rating_changes(
    fide_id: str,
    new_ratings: Dict[str, Optional[int]],
    historical_data: Dict[str, Dict[str, Any]]
) -> Dict[str, Tuple[Optional[int], Optional[int]]]

# Email notification
compose_notification_email(
    player_name: str,
    fide_id: str,
    changes: Dict[str, Tuple],
    recipient_email: str,
    cc_email: Optional[str]
) -> Tuple[str, str]  # (subject, body)

send_email_notification(
    recipient: str,
    cc: Optional[str],
    subject: str,
    body: str
) -> bool

# Integration
process_batch_with_notifications(
    fide_ids: List[str],
    player_data: Dict[str, Dict],
    historical_ratings: Dict[str, Dict]
) -> Tuple[List[Dict], List[str]]  # (results, errors)
```

---

## Sequence Diagram

```
┌─────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│ Scraper │      │ CSV File │      │ FIDE API │      │ SMTP Srv │
└────┬────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
     │                │                  │                │
     │─Load players──→│                  │                │
     │←─Player dict───│                  │                │
     │                │                  │                │
     │─Load ratings──→│                  │                │
     │←─History dict──│                  │                │
     │                │                  │                │
     │              [For each player]    │                │
     │                │                  │                │
     │──Fetch profile───────────────────→│                │
     │←──Rating data─────────────────────│                │
     │                │                  │                │
     │  [Detect changes in ratings]      │                │
     │                │                  │                │
     │─Has email? Yes, changed? Yes      │                │
     │                │                  │                │
     │──Compose email─────────────────────────────────────│
     │──Send notification────────────────────────────────→│
     │←──Ack──────────────────────────────────────────────│
     │                │                  │                │
     │  [Append new rating record]       │                │
     │─Append record→ │                  │                │
     │                │                  │                │
     │  [Log completion]                 │                │
     │                │                  │                │
```

---

## Example Data Flow

### Scenario: Two Players, One Rating Change

**Input Files**:

`players.csv`:
```csv
FIDE ID,email
12345678,alice@example.com
87654321,bob@example.com
```

`fide_ratings.csv` (existing):
```csv
Date,FIDE ID,Player Name,Standard,Rapid,Blitz
2025-11-22,12345678,Alice Smith,2440,2300,2100
2025-11-22,87654321,Bob Jones,2500,2400,2200
```

**Batch Run (2025-11-23)**:

1. Load players → `{12345678: {email: alice@...}, 87654321: {email: bob@...}}`
2. Load history → Latest for each player loaded
3. Fetch from FIDE:
   - Alice: Standard=2450, Rapid=2300, Blitz=2100 (Standard changed!)
   - Bob: Standard=2500, Rapid=2400, Blitz=2200 (No change)
4. Detect changes:
   - Alice: `{"Standard": (2440, 2450)}`
   - Bob: `{}` (empty, no changes)
5. Send notifications:
   - Alice: Email sent (has email + has changes)
   - Bob: Skip (no changes)
6. Append to `fide_ratings.csv`:
   ```csv
   2025-11-23,12345678,Alice Smith,2450,2300,2100
   2025-11-23,87654321,Bob Jones,2500,2400,2200
   ```

**Audit Log**:
```
Email: Sending notification to alice@example.com (CC: admin@example.com) - Status: success
Email: No changes detected for bob@example.com - Skipped
```

---

## Validation Rules Summary

| Entity | Field | Rule | Action on Violation |
|--------|-------|------|---------------------|
| Player | FIDE ID | 4-10 digits, numeric | Log warning, skip row |
| Player | email | Valid RFC or empty | Log warning, treat as empty |
| RatingChange | Any rating type | 0-3000 or empty | Log warning, treat as invalid |
| Notification | Recipient | Non-empty email | Log error, skip notification |
| Notification | CC | Non-empty email or absent | Log warning if format invalid, skip CC |

---

End of Data Model document.
