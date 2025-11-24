# Function Contracts: Player Rating Change Email Notifications

**Date**: 2025-11-23
**Feature**: 003-player-rating-emails

---

## CSV Loading Functions

### `load_player_data_from_csv(filepath: str) -> Dict[str, Dict[str, str]]`

**Purpose**: Load player data from unified CSV file

**Parameters**:
- `filepath` (str): Path to `players.csv` file

**Returns**: Dictionary mapping FIDE ID to player data
```python
{
    "12345678": {"email": "alice@example.com"},
    "87654321": {"email": ""},
    "11111111": {"email": "charlie@example.com"}
}
```

**Exceptions**:
- `FileNotFoundError`: If file doesn't exist
- `ValueError`: If CSV format invalid (missing headers)

**Side Effects**:
- Logs warnings for invalid entries (malformed FIDE IDs, invalid emails)
- Skips invalid rows, continues processing valid ones

**Example**:
```python
player_data = load_player_data_from_csv("players.csv")
assert "12345678" in player_data
assert player_data["12345678"]["email"] == "alice@example.com"
```

---

### `load_historical_ratings_by_player(filepath: str) -> Dict[str, Dict[str, Any]]`

**Purpose**: Load historical rating records, indexed by player (latest per player)

**Parameters**:
- `filepath` (str): Path to `fide_ratings.csv` file

**Returns**: Dictionary with structure:
```python
{
    "12345678": {
        "Date": "2025-11-22",
        "Player Name": "Alice Smith",
        "Standard": 2440,
        "Rapid": 2300,
        "Blitz": 2100
    },
    "87654321": {
        "Date": "2025-11-22",
        "Player Name": "Bob Jones",
        "Standard": 2500,
        "Rapid": 2400,
        "Blitz": None
    }
}
```

**Exceptions**:
- `FileNotFoundError`: If file doesn't exist (handled gracefully; return empty dict for first run)

**Side Effects**:
- None (read-only)

**Example**:
```python
history = load_historical_ratings_by_player("fide_ratings.csv")
latest = history.get("12345678", {})
old_standard = latest.get("Standard")
```

---

## Validation Functions

### `validate_fide_id(fide_id: str) -> bool`

**Purpose**: Validate FIDE ID format

**Parameters**:
- `fide_id` (str): FIDE ID to validate

**Returns**: True if valid, False otherwise

**Validation Rules**:
- Numeric only
- Length 4-10 characters
- Non-empty

**Example**:
```python
assert validate_fide_id("12345678") is True
assert validate_fide_id("123") is False  # Too short
assert validate_fide_id("abc12345") is False  # Non-numeric
```

---

### `validate_email(email: str) -> bool`

**Purpose**: Validate email format (basic RFC pattern)

**Parameters**:
- `email` (str): Email address to validate

**Returns**: True if valid, False otherwise (empty string considered valid/skipped)

**Validation Rules**:
- Pattern: `\S+@\S+\.\S+` (non-whitespace@non-whitespace.non-whitespace)
- No full RFC 5322 validation (simplified for practical use)
- Empty string is valid (means opted out)

**Example**:
```python
assert validate_email("alice@example.com") is True
assert validate_email("invalid.email") is False
assert validate_email("") is True  # Empty is valid (opt-out)
```

---

## Change Detection Functions

### `detect_rating_changes(fide_id: str, new_ratings: Dict[str, Optional[int]], historical_data: Dict[str, Dict]) -> Dict[str, Tuple[Optional[int], Optional[int]]]`

**Purpose**: Detect which ratings changed for a player

**Parameters**:
- `fide_id` (str): Player's FIDE ID
- `new_ratings` (dict): Latest ratings fetched
  ```python
  {"Standard": 2450, "Rapid": 2300, "Blitz": 2100}
  ```
- `historical_data` (dict): Dictionary with latest record per player (from `load_historical_ratings_by_player`)

**Returns**: Dictionary of changed ratings
```python
{
    "Standard": (2440, 2450),  # (old, new)
    "Rapid": (2300, 2300)       # No change but included for completeness
}
```
Empty dict `{}` if no changes detected

**Side Effects**:
- None (read-only)

**Example**:
```python
changes = detect_rating_changes(
    "12345678",
    {"Standard": 2450, "Rapid": 2300, "Blitz": 2100},
    historical_data
)
if changes:
    print(f"Changes detected: {changes}")
```

---

## Email Composition Functions

### `compose_notification_email(player_name: str, fide_id: str, changes: Dict[str, Tuple[Optional[int], Optional[int]]], recipient_email: str, cc_email: Optional[str] = None) -> Tuple[str, str]`

**Purpose**: Compose email subject and body for rating change notification

**Parameters**:
- `player_name` (str): Player's name (e.g., "Alice Smith")
- `fide_id` (str): Player's FIDE ID
- `changes` (dict): Dictionary of changed ratings from `detect_rating_changes()`
  ```python
  {"Standard": (2440, 2450)}
  ```
- `recipient_email` (str): Player's email address
- `cc_email` (str, optional): Admin CC email (for logging, not used in composition)

**Returns**: Tuple of (subject, body)
```python
(
    "Your FIDE Rating Update - Alice Smith",
    "Dear Alice,\n\nYour FIDE ratings have been updated:\n\nStandard: 2440 → 2450\n..."
)
```

**Side Effects**:
- None (pure function)

**Example**:
```python
subject, body = compose_notification_email(
    "Alice Smith",
    "12345678",
    {"Standard": (2440, 2450)},
    "alice@example.com",
    "admin@example.com"
)
print(f"Subject: {subject}")
print(f"Body:\n{body}")
```

---

## Email Sending Functions

### `send_email_notification(recipient: str, cc: Optional[str], subject: str, body: str) -> bool`

**Purpose**: Send email notification via SMTP

**Parameters**:
- `recipient` (str): Recipient email address
- `cc` (str, optional): CC recipient email (or None for no CC)
- `subject` (str): Email subject
- `body` (str): Email body (plain text)

**Returns**: True if sent successfully, False if error occurred

**Side Effects**:
- Sends email via SMTP (uses `SMTP_*` env vars)
- Logs all attempts and errors to stdout/stderr
- Never raises exception (logs and returns False on error)

**Environment Variables Used**:
- `SMTP_SERVER` (default: localhost)
- `SMTP_PORT` (default: 587)
- `SMTP_USERNAME` (optional, if empty: anonymous)
- `SMTP_PASSWORD` (optional)

**Error Handling**:
- Missing SMTP config: Log warning, return False (don't crash)
- Connection failure: Log error, return False
- Invalid recipient email: Log error, return False
- Authentication failure: Log error, return False

**Example**:
```python
success = send_email_notification(
    "alice@example.com",
    "admin@example.com",
    "Your FIDE Rating Update",
    "Your ratings have changed..."
)
if not success:
    print("Failed to send email, but batch continues")
```

---

## Integrated Batch Processing

### `process_batch_with_notifications(fide_ids: List[str], player_data: Dict[str, Dict[str, str]], historical_ratings: Dict[str, Dict]) -> Tuple[List[Dict], List[str]]`

**Purpose**: Process batch of player ratings with email notifications

**Parameters**:
- `fide_ids` (list): List of FIDE IDs to process
- `player_data` (dict): Player data from `load_player_data_from_csv()`
- `historical_ratings` (dict): Historical data from `load_historical_ratings_by_player()`

**Returns**: Tuple of (results, errors)
```python
(
    [
        {"FIDE ID": "12345678", "Player Name": "Alice Smith", "Standard": 2450, ...},
        ...
    ],
    ["Invalid FIDE ID: abc", "Network error for 87654321", ...]
)
```

**Side Effects**:
- Fetches player profiles from FIDE website
- Sends email notifications (logs attempts)
- Appends successful results to `fide_ratings.csv`

**Algorithm**:
1. For each FIDE ID:
   a. Validate FIDE ID (skip if invalid, log error)
   b. Get player email from `player_data`
   c. Fetch profile from FIDE (skip if not found)
   d. Extract ratings
   e. Detect changes vs `historical_ratings`
   f. If changes and email: Send notification
   g. Add to results
2. Write new records to CSV
3. Return (results, errors)

**Example**:
```python
results, errors = process_batch_with_notifications(
    ["12345678", "87654321"],
    player_data,
    historical_ratings
)
print(f"Processed {len(results)} players, {len(errors)} errors")
for error in errors:
    print(f"  Error: {error}")
```

---

## Data Structure Definitions

### Player Record

```python
PlayerRecord = Dict[str, str]
# Example: {"email": "alice@example.com"}
# or: {"email": ""}  # Opted out
```

### Historical Rating

```python
HistoricalRating = Dict[str, Any]
# Example:
# {
#     "Date": "2025-11-22",
#     "Player Name": "Alice Smith",
#     "Standard": 2450,  # or None if unrated
#     "Rapid": 2300,
#     "Blitz": None
# }
```

### Rating Change

```python
RatingChange = Dict[str, Tuple[Optional[int], Optional[int]]]
# Example: {"Standard": (2440, 2450), "Rapid": (2300, 2300)}
```

### Batch Result

```python
BatchResult = Dict[str, Any]
# Example:
# {
#     "FIDE ID": "12345678",
#     "Player Name": "Alice Smith",
#     "Standard": 2450,
#     "Rapid": 2300,
#     "Blitz": 2100
# }
```

---

## Error Codes & Logging

### Email Sending Status

| Status | Log Level | Action |
|--------|-----------|--------|
| success | INFO | "Email sent to alice@example.com (CC: admin@example.com)" |
| invalid_email | WARNING | "Invalid email format for alice: not-an-email" |
| no_changes | INFO | "No rating changes for FIDE ID 12345678, notification skipped" |
| no_email | INFO | "No email configured for FIDE ID 12345678, notification skipped" |
| smtp_error | ERROR | "SMTP error: Connection timed out" |
| smtp_missing | WARNING | "SMTP not configured, email notifications disabled" |
| invalid_recipient | ERROR | "Invalid recipient email: invalid@" |

---

## Implementation Notes

### Thread Safety

Current implementation (single batch script): No threading concerns.

If future enhancement adds async email sending:
- Use `asyncio` + `aiosmtplib` for concurrent sends
- Maintain error logging per player
- Continue on any single failure

### Memory Management

- Player data: ~100KB for 1000 players
- Historical ratings: ~1MB for 100k records
- Email composition: Temporary objects garbage collected
- No memory leaks expected

### Performance Targets

- Player data loading: < 1s for 1000 rows
- Change detection: O(1) per player
- Email sending: ~1-5s per email (SMTP latency dominant)
- Total batch: < 5 minutes for 100 players (SC-001)

---

End of Function Contracts.
