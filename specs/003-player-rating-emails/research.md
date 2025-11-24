# Research Phase: Player Rating Change Email Notifications

**Date**: 2025-11-23
**Feature**: 003-player-rating-emails
**Status**: ✅ Complete - All NEEDS CLARIFICATION resolved during spec clarification phase

## Email Sending Mechanism

**Decision**: Use Python standard library `smtplib` + `email.mime` modules

**Rationale**:
- No external dependencies required (already using minimal dependencies)
- Standard SMTP protocol support via environment-configured server
- Sufficient for text and HTML email composition
- Aligns with project principle of simplicity (Principle III)

**Alternatives Considered**:
1. Third-party services (SendGrid, Mailgun) - Rejected: Adds external dependency, requires API key management
2. `yagmail` library - Rejected: Extra dependency not worth complexity; stdlib sufficient

**Implementation Pattern**:
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration from .env
SMTP_SERVER = os.getenv('SMTP_SERVER', 'localhost')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

# Send via TLS connection (port 587) or SSL (port 465)
# Handle missing SMTP gracefully - log and continue
```

---

## CSV Player Data Format & Parsing

**Decision**: Extend existing CSV handling pattern; use `csv.DictReader` for player data

**Rationale**:
- Already using `csv` module for rating output (`fide_ratings.csv`)
- Consistent with existing code style
- Easy to validate and handle missing emails (empty string)

**Format**:
```csv
FIDE ID,email
12345,player1@example.com
67890,
12346,player3@example.com
```

**Implementation Pattern**:
- Use `csv.DictReader` to parse `players.csv` with "FIDE ID" and "email" headers
- Validate FIDE IDs (4-10 digits, numeric)
- Validate emails (basic RFC pattern: `\S+@\S+\.\S+`)
- Log warnings for invalid entries, skip them
- Process all players regardless of email presence

---

## Rating Change Detection

**Decision**: Compare latest record per player from historical CSV

**Rationale**:
- Historical data already stored in `fide_ratings.csv` with Date column
- Leverage existing structure: `[Date, FIDE ID, Player Name, Standard, Rapid, Blitz]`
- Simple comparison logic (null/missing vs value, or value comparison)

**Algorithm**:
1. Load all existing records from `fide_ratings.csv` into memory
2. Group by FIDE ID, find most recent (latest date) for each player
3. Compare new fetched ratings against most recent record
4. Detect changes in any rating type (standard, rapid, blitz)
5. Track which specific ratings changed for notification content

**Implementation Pattern**:
```python
def detect_rating_changes(fide_id, new_ratings, historical_data):
    """
    Compare new ratings against most recent record.
    Returns dict with changed rating types and (old, new) values.
    """
    latest_record = historical_data.get(fide_id, {})
    changes = {}

    for rating_type in ['Standard', 'Rapid', 'Blitz']:
        old_val = latest_record.get(rating_type)
        new_val = new_ratings.get(rating_type)

        if old_val != new_val:  # Handles None vs value changes
            changes[rating_type] = (old_val, new_val)

    return changes
```

---

## Environment Variables & Configuration

**Variables to Add**:

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `FIDE_PLAYERS_FILE` | Path to player data CSV | `players.csv` | `/data/players.csv` |
| `ADMIN_CC_EMAIL` | Admin CC recipient | (optional, no CC if missing) | `admin@example.com` |
| `SMTP_SERVER` | SMTP server hostname | `localhost` | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` | `587` |
| `SMTP_USERNAME` | SMTP authentication username | (empty) | `sender@example.com` |
| `SMTP_PASSWORD` | SMTP authentication password | (empty) | `app-password-here` |

**Rationale**:
- `FIDE_PLAYERS_FILE` explicitly names the new consolidated input format
- `ADMIN_CC_EMAIL` is optional (supports both CC and no-CC modes per FR-012)
- SMTP configuration follows standard patterns
- Graceful degradation: missing SMTP config doesn't crash scraper (FR-013)

---

## Email Notification Content

**Decision**: Include player name, FIDE ID, all rating types, and previous vs. current values

**Email Structure**:
- **Subject**: "Your FIDE Rating Update - [Player Name]"
- **Body (text/html hybrid)**:
  ```
  Dear [Player Name],

  Your FIDE ratings have been updated:

  Standard Rating: [Old Value] → [New Value] [CHANGED indicator if applicable]
  Rapid Rating: [Old Value] → [New Value]
  Blitz Rating: [Old Value] → [New Value]

  Last Updated: [Date]

  Best regards,
  FIDE Scraper
  ```

**Headers**:
- `To`: Player's email address
- `CC`: `ADMIN_CC_EMAIL` (if configured)
- `From`: Sender address (from SMTP_USERNAME or default)
- `Subject`: Per above pattern

---

## Error Handling & Logging Strategy

**Principle**: Never crash the scraper due to email failures (FR-013, FR-014)

**Handling Patterns**:

1. **Missing SMTP Configuration**:
   - Log warning: "SMTP not configured, email notifications disabled"
   - Continue processing ratings
   - No CC attempted

2. **Invalid Email Address**:
   - Log error: "Invalid email format for player [FIDE ID]: [email]"
   - Skip notification for that player
   - Continue with other players

3. **SMTP Connection Failure**:
   - Log error: "Failed to connect to SMTP server: [error]"
   - Skip all notifications in this batch
   - Continue processing ratings (next batch may succeed)

4. **Email Delivery Failure (SMTPException)**:
   - Log error: "Failed to send notification to [email]: [error]"
   - Continue with next player (FR-013)
   - Attempt rate-limiting recovery if timeout

**Logging Output**:
- All email attempts logged with timestamp, recipient, and result
- Errors directed to stderr (matching existing error reporting)
- Info/warning messages to stdout

---

## Testing Strategy

**Unit Tests Required**:
- `test_load_player_data_from_csv()` - Valid/invalid emails, missing fields
- `test_detect_rating_changes()` - All rating type combinations
- `test_validate_fide_id()` - Boundary cases (3-digit, 11-digit, non-numeric)
- `test_validate_email()` - Valid/invalid formats
- `test_compose_notification_email()` - Content structure, variable substitution
- `test_send_email_with_smtp_mock()` - SMTP interaction (mocked)

**Integration Tests Required**:
- End-to-end with sample `players.csv` and rating data
- Verify notifications only sent for changed ratings
- Verify CC recipient receives copy
- Verify missing SMTP config doesn't crash scraper

**Test Fixtures**:
- `fixtures/players.csv` - Sample player data with mixed email presence
- `fixtures/fide_ratings_history.csv` - Historical data for change detection
- Mock SMTP server responses

---

## Summary of Design Decisions

| Component | Decision | Key Benefit |
|-----------|----------|------------|
| Email Library | stdlib `smtplib` + `email.mime` | No new dependencies, aligns with simplicity principle |
| CSV Parsing | `csv.DictReader` for players.csv | Consistent with existing code patterns |
| Change Detection | Historical CSV comparison | Leverages existing data structure |
| Error Handling | Log and continue pattern | Never crashes scraper (FR-013) |
| Configuration | Environment variables | Flexible deployment, secrets management |
| Email Content | Structured format with before/after | Clear, actionable notifications |

All research questions resolved. Design ready for Phase 1 implementation.
