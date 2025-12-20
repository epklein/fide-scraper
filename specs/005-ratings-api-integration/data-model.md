# Data Model: External Ratings API Integration

**Feature**: 005-ratings-api-integration
**Date**: 2024-12-18

---

## Entities

### RatingUpdate

**Purpose**: Represents a single FIDE player's rating snapshot to be transmitted to the external API.

**Source**: Derived from player profile after FIDE scrape completes and ratings are updated in fide_ratings.csv

**Scope**: This is an API transmission object, not a new persistent entity. It combines:
- Date: From current scrape run (ISO 8601)
- FIDE ID: From players.csv or scraped profile
- Player Name: Scraped from FIDE website
- Ratings: Scraped values for Standard, Rapid, Blitz time controls

**Fields**:

| Field | Type | Required | Range | Format | Example | Source |
|-------|------|----------|-------|--------|---------|--------|
| date | string (date) | YES | - | ISO 8601 YYYY-MM-DD | "2024-12-18" | Current run date |
| fide_id | string | YES | 4-10 chars | Numeric digits only | "12345678" | players.csv / scraped |
| player_name | string | YES | 1-255 chars | UTF-8 text | "John Doe" | Scraped from FIDE |
| standard_rating | integer or null | YES | 0-4000+ | Integer | 2500 | Scraped (null if unrated) |
| rapid_rating | integer or null | YES | 0-4000+ | Integer | 2400 | Scraped (null if unrated) |
| blitz_rating | integer or null | YES | 0-4000+ | Integer | 2300 | Scraped (null if unrated) |

**Constraints**:

```python
# FIDE ID validation (existing function used)
assert 4 <= len(fide_id) <= 10
assert fide_id.isdigit()

# Player name validation (non-empty)
assert len(player_name.strip()) > 0

# Rating validation (existing in project)
# - null represents unrated (per spec requirement)
# - Integer values: >= 0
# - Typical range: 0-4000 (can exceed for titled players)
if standard_rating is not None:
    assert isinstance(standard_rating, int)
    assert standard_rating >= 0

if rapid_rating is not None:
    assert isinstance(rapid_rating, int)
    assert rapid_rating >= 0

if blitz_rating is not None:
    assert isinstance(blitz_rating, int)
    assert blitz_rating >= 0

# Date validation
from datetime import datetime
assert datetime.fromisoformat(date)  # ISO format validation
```

**Python Representation** (TypedDict for type hints):

```python
from typing import TypedDict, Optional
from datetime import date

class RatingUpdate(TypedDict):
    """Single player rating snapshot for external API."""
    date: str              # ISO 8601 "2024-12-18"
    fide_id: str           # "12345678"
    player_name: str       # "John Doe"
    standard_rating: Optional[int]  # 2500 or None
    rapid_rating: Optional[int]     # 2400 or None
    blitz_rating: Optional[int]     # 2300 or None

# In practice, constructed from existing profile dict:
profile = {
    'Date': '2024-12-18',
    'FIDE ID': '12345678',
    'Player Name': 'John Doe',
    'Standard': 2500,
    'Rapid': 2400,
    'Blitz': 2300
}

# Map to API format:
rating_update = {
    'date': profile['Date'],
    'fide_id': profile['FIDE ID'],
    'player_name': profile['Player Name'],
    'standard_rating': profile.get('Standard'),
    'rapid_rating': profile.get('Rapid'),
    'blitz_rating': profile.get('Blitz')
}
```

---

## Relationships

**RatingUpdate → External API**:
- One-way POST transmission
- No persistent storage in scraper (only in external API)
- Tracked in local logs for error recovery

**RatingUpdate ← Existing Entities**:
- Derives from: Player (FIDE ID) + Rating scraped data
- No new entities created; uses existing CSV structure
- No new database tables required

---

## State Transitions

**RatingUpdate Lifecycle**:

```
1. CREATED: Player profile scraped and ratings updated locally
   ↓
2. PREPARED: Convert profile dict to API format
   ↓
3a. POSTED: HTTP POST request sent to API
   ├─→ SUCCESSFUL (200 OK): Response received, logged
   ├─→ FAILED_TIMEOUT: Timeout after 5s, retry once
   ├─→ FAILED_CONNECTION: Connection error, retry once
   └─→ FAILED_HTTP_ERROR: Non-2xx response, don't retry
   ↓
4. LOGGED: Result (success or failure) logged with context
   ↓
5. DISCARDED: Object released (not persisted locally)
```

**Persistence**: None in scraper (only in external API and logs)

---

## API Payloads

**Request Body** (sent to external API):

```json
{
  "date": "2024-12-18",
  "fide_id": "12345678",
  "player_name": "John Doe",
  "standard_rating": 2500,
  "rapid_rating": 2400,
  "blitz_rating": 2300
}
```

**Response Body** (received from external API, 200 OK):

```json
{
  "id": 1,
  "date": "2024-12-18",
  "fide_id": "12345678",
  "player_name": "John Doe",
  "standard_rating": 2500,
  "rapid_rating": 2400,
  "blitz_rating": 2300,
  "ingested_at": "2024-12-18T11:30:45.123456Z"
}
```

**Note**: Response body is informational only. HTTP status code (200 OK) is authoritative success indicator.

---

## Existing Related Entities (No Changes)

### Player (from players.csv - unchanged)
```python
{
    'FIDE ID': '12345678',
    'email': 'player@example.com'  # Optional
}
```

### RatingRecord (from fide_ratings.csv - unchanged)
```python
{
    'Date': '2024-12-18',
    'FIDE ID': '12345678',
    'Player Name': 'John Doe',
    'Standard': 2500,
    'Rapid': 2400,
    'Blitz': 2300
}
```

### EmailNotification (existing pattern - similar to API posting)
```python
# Used as reference for similar error handling/retry pattern
{
    'recipient': 'player@example.com',
    'subject': 'Your FIDE ratings changed',
    'body': '...'
}
```

---

## Validation Rules

**RatingUpdate Validation** (before API POST):

```python
def validate_rating_update(update: dict) -> tuple[bool, str]:
    """
    Validate RatingUpdate before transmission.

    Returns:
        (is_valid, error_message)
    """
    # Required fields present
    required = ['date', 'fide_id', 'player_name']
    for field in required:
        if field not in update or update[field] is None:
            return False, f"Missing required field: {field}"

    # FIDE ID format
    if not (4 <= len(update['fide_id']) <= 10 and update['fide_id'].isdigit()):
        return False, f"Invalid FIDE ID format: {update['fide_id']}"

    # Player name non-empty
    if not update['player_name'].strip():
        return False, "Player name cannot be empty"

    # Date ISO 8601 format
    try:
        datetime.fromisoformat(update['date'])
    except ValueError:
        return False, f"Invalid date format: {update['date']} (expected ISO 8601)"

    # Ratings (if present, must be non-negative integers)
    for rating_field in ['standard_rating', 'rapid_rating', 'blitz_rating']:
        if rating_field in update and update[rating_field] is not None:
            if not isinstance(update[rating_field], int) or update[rating_field] < 0:
                return False, f"Invalid rating: {rating_field}={update[rating_field]}"

    return True, ""
```

---

## Integration with Existing Code

### Source: Existing Player Profile Dict

The RatingUpdate is constructed from the existing player profile dictionary used in main scraping flow:

```python
# Existing profile structure (no changes):
profile = {
    'Date': '2024-12-18',
    'FIDE ID': '12345678',
    'Player Name': 'John Doe',
    'Standard': 2500,
    'Rapid': 2400,
    'Blitz': 2300
}

# Convert for API (snake_case, rename keys):
api_payload = {
    'date': profile['Date'],
    'fide_id': profile['FIDE ID'],
    'player_name': profile['Player Name'],
    'standard_rating': profile.get('Standard'),
    'rapid_rating': profile.get('Rapid'),
    'blitz_rating': profile.get('Blitz')
}
```

### Integration Point: Main Batch Processing

```python
# In main() function after local CSV write:

if api_enabled:
    for profile in player_profiles:
        rating_update = {
            'date': profile['Date'],
            'fide_id': profile['FIDE ID'],
            'player_name': profile['Player Name'],
            'standard_rating': profile.get('Standard'),
            'rapid_rating': profile.get('Rapid'),
            'blitz_rating': profile.get('Blitz')
        }

        # Validate before sending
        is_valid, error_msg = validate_rating_update(rating_update)
        if not is_valid:
            logging.error(f"Invalid rating update for {profile['FIDE ID']}: {error_msg}")
            continue

        # POST to API
        post_rating_to_api(
            rating_update,
            api_endpoint=api_config['endpoint'],
            api_token=api_config['token']
        )
```

---

## No Schema Changes

**Database/Storage**: No changes required
- fide_ratings.csv: No schema changes (RatingUpdate is derived from existing fields)
- players.csv: No schema changes
- New .env variables: FIDE_RATINGS_API_ENDPOINT, API_TOKEN (no database impact)

**Backward Compatibility**: Fully compatible
- Existing CSV format unchanged
- Email notifications unaffected
- Configuration is additive (optional API posting)
