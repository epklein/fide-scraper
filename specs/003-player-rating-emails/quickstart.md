# Quick Start: Player Rating Change Email Notifications

**Date**: 2025-11-23
**Feature**: 003-player-rating-emails
**Audience**: Developers implementing this feature

---

## Overview

This feature extends the FIDE rating scraper with email notification capability. When a player's rating changes, an automated email is sent to the player (if they have an email configured) and CC'd to an administrator.

**Key Changes**:
- Unified player input: `players.csv` (replacing separate `fide_ids.txt`)
- Optional email field: Players opt in for notifications by providing an email
- Email library: Python stdlib `smtplib` + `email.mime`
- Change detection: Compare against historical data in `fide_ratings.csv`

---

## Environment Setup

### 1. Update `.env` File

Add the following new variables:

```bash
# New: Player data file (consolidates fide_ids.txt)
FIDE_PLAYERS_FILE=players.csv

# New: Administrator email for CC'd notifications
ADMIN_CC_EMAIL=admin@example.com

# New: SMTP Configuration (if not already present)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Notes**:
- `ADMIN_CC_EMAIL` is optional (no CC if not set)
- `SMTP_*` vars can use existing system SMTP if available
- For Gmail, use "app password" (not account password)

### 2. Create `players.csv`

Replace `fide_ids.txt` with a unified `players.csv`:

```csv
FIDE ID,email
12345678,player1@example.com
87654321,player2@example.com
11111111,
22222222,player4@example.com
```

**Format**:
- Headers: "FIDE ID,email" (required)
- FIDE ID: 4-10 digit number
- email: Valid email or empty string (empty = opt out)

---

## Code Architecture

### New Functions (to be added to `fide_scraper.py`)

#### 1. Player Data Loading

```python
def load_player_data_from_csv(filepath: str) -> Dict[str, Dict[str, str]]:
    """
    Load player data from CSV file.

    Returns: {fide_id: {"email": "...or empty"}, ...}
    Handles: Invalid FIDE IDs, malformed emails (logs warnings, skips)
    """
    # Implementation: csv.DictReader, validation
```

#### 2. Change Detection

```python
def detect_rating_changes(
    fide_id: str,
    new_ratings: Dict[str, Optional[int]],
    historical_data: Dict[str, Dict]
) -> Dict[str, Tuple[Optional[int], Optional[int]]]:
    """
    Detect which ratings changed for a player.

    Returns: {"Standard": (old, new), "Rapid": (old, new), ...}
             or {} if no changes
    """
    # Implementation: Compare new vs most recent record
```

#### 3. Email Composition

```python
def compose_notification_email(
    player_name: str,
    fide_id: str,
    changes: Dict[str, Tuple[Optional[int], Optional[int]]],
    recipient_email: str,
    cc_email: Optional[str] = None
) -> Tuple[str, str]:
    """
    Compose email subject and body.

    Returns: (subject, body)
    Example subject: "Your FIDE Rating Update - Alice Smith"
    """
    # Implementation: Format email content
```

#### 4. Email Sending

```python
def send_email_notification(
    recipient: str,
    cc: Optional[str],
    subject: str,
    body: str
) -> bool:
    """
    Send email via SMTP.

    Returns: True if successful, False if error (logs error, continues)
    Handles: Missing SMTP config, connection errors, invalid addresses
    """
    # Implementation: smtplib connection, send with CC
```

#### 5. Integration with Existing Code

Modify `process_batch()`:
```python
def process_batch(fide_ids: List[str]) -> Tuple[List[Dict], List[str]]:
    """
    Existing function - extend to support email notifications.

    Changes:
    - Load player data from players.csv (not fide_ids.txt)
    - After fetching each player's ratings, detect changes
    - If changes detected and email configured, send notification
    - Log email send attempts
    """
```

---

## Implementation Checklist

### Phase 1: Data Loading & Validation

- [ ] Create `load_player_data_from_csv()` function
- [ ] Implement `validate_fide_id()` check
- [ ] Implement `validate_email()` check (basic RFC)
- [ ] Handle CSV parsing errors gracefully
- [ ] Log warnings for invalid entries

**Test**:
```python
def test_load_player_data_from_csv():
    # Test valid CSV
    # Test invalid emails (skip)
    # Test missing FIDE ID (skip)
    # Test empty file
```

### Phase 2: Change Detection

- [ ] Create `detect_rating_changes()` function
- [ ] Load historical data from `fide_ratings.csv`
- [ ] Compare current vs most recent record per player
- [ ] Handle null/empty ratings (unrated → rated transition)

**Test**:
```python
def test_detect_rating_changes():
    # Test numeric change
    # Test unrated → rated transition
    # Test no change scenario
    # Test multiple rating types changing
```

### Phase 3: Email Composition & Sending

- [ ] Create `compose_notification_email()` function
- [ ] Create `send_email_notification()` function
- [ ] Implement SMTP connection logic (smtplib)
- [ ] Handle SMTP errors gracefully (don't crash scraper)
- [ ] Support optional CC recipient

**Test**:
```python
def test_compose_notification_email():
    # Test email format
    # Test variable substitution

def test_send_email_notification():
    # Mock SMTP server
    # Test successful send
    # Test SMTP error handling
    # Test missing SMTP config
```

### Phase 4: Integration & End-to-End

- [ ] Update `main()` to use `FIDE_PLAYERS_FILE` instead of `FIDE_INPUT_FILE`
- [ ] Update `process_batch()` to trigger email notifications
- [ ] Update `.env.example` with new variables
- [ ] Update README.md with new configuration
- [ ] Test full batch run with sample data

**Test**:
```python
def test_integration_batch_with_notifications():
    # Full end-to-end test
    # Load players, fetch ratings, detect changes, send emails
```

---

## Error Handling Reference

### Graceful Failure Modes

| Error | Handling | Result |
|-------|----------|--------|
| Missing `SMTP_SERVER` | Log warning, skip all email | Ratings still processed, no notifications |
| Invalid player email | Log warning, skip notification | Ratings still processed, other players notified |
| SMTP connection failure | Log error, skip all notifications | Ratings still processed |
| Malformed player CSV | Log warning, skip invalid rows | Valid rows processed, notifications sent |

**Key Principle**: Never crash the scraper due to email errors. Always log and continue.

---

## Testing Strategy

### Unit Tests

Located in `tests/test_fide_scraper.py`:

```python
def test_load_player_data_from_csv_valid():
    """Test loading valid players.csv"""

def test_load_player_data_from_csv_invalid_email():
    """Test invalid email handling"""

def test_detect_rating_changes_all_scenarios():
    """Test all rating change combinations"""

def test_validate_email_formats():
    """Test email validation"""

def test_compose_email_content():
    """Test email message formatting"""

def test_send_email_smtp_mock():
    """Test SMTP sending with mock server"""

def test_send_email_missing_smtp():
    """Test graceful failure when SMTP unavailable"""
```

### Integration Tests

Located in `tests/test_integration.py`:

```python
def test_batch_with_notifications():
    """Full end-to-end batch run with email notifications"""
```

### Test Fixtures

Create `tests/fixtures/`:
```
tests/fixtures/
├── players.csv          # Sample players with mixed email presence
├── fide_ratings_history.csv  # Historical data for change detection
└── mock_smtp.py         # Mock SMTP server for testing
```

---

## Deployment Checklist

- [ ] Update `.env` with SMTP configuration
- [ ] Create `players.csv` with player data
- [ ] Run full test suite (unit + integration)
- [ ] Verify `fide_ratings.csv` has historical data or is empty
- [ ] Test with sample player (email to test address)
- [ ] Verify admin CC email receives copy
- [ ] Update README.md with new feature documentation
- [ ] Deploy to production environment

---

## Key Files & Artifacts

| File | Purpose | Status |
|------|---------|--------|
| `spec.md` | Feature specification | ✅ Complete |
| `research.md` | Design decisions & rationale | ✅ Complete |
| `data-model.md` | Entity definitions & relationships | ✅ Complete |
| `plan.md` | Implementation plan (this phase) | ✅ Complete |
| `fide_scraper.py` | Main script (to be extended) | 📝 To be modified |
| `players.csv` | Player input data (new) | 📝 To be created |
| `.env` | Configuration (to be updated) | 📝 To be updated |
| `tests/` | Unit & integration tests (to be added) | 📝 To be added |

---

## Performance Considerations

**Current Assumptions** (from spec SC-001):
- Notification delivery within 5 minutes during batch runs
- Support 100+ concurrent player updates
- No performance degradation vs baseline scraper

**Optimization Notes**:
- Email sending: Consider thread pool for multiple players (if > 100)
- CSV loading: Adequate with dict-based in-memory storage
- Change detection: O(1) lookup per player in historical dict

---

## Next Steps

1. Read `data-model.md` for detailed entity definitions
2. Review `research.md` for design decisions & rationale
3. Check `contracts/` directory for function signatures
4. Start implementation with Phase 1: Data Loading (see checklist above)
5. Run tests after each phase
6. Update `.env.example` and README.md
7. Create `players.csv` sample file
8. Test end-to-end before deployment

---

## FAQ

**Q: What if a player has no email configured?**
A: They'll still be tracked for ratings, but no notification sent.

**Q: What if the email address format is invalid?**
A: It's logged as a warning and skipped; other players continue normally.

**Q: What if SMTP is misconfigured?**
A: Rated changes are still processed and saved; notifications skipped. No crash.

**Q: Can I disable admin CC?**
A: Yes, simply don't set `ADMIN_CC_EMAIL` (or leave it empty).

**Q: How often should I run the scraper?**
A: Depends on FIDE update frequency; typically daily or weekly.

---

End of Quick Start Guide.
