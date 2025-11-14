# Data Model: FIDE Rating Scraper

**Date**: 2025-01-27  
**Feature**: FIDE Rating Scraper

## Entities

### FIDE ID

**Description**: A unique identifier for a chess player in the FIDE system.

**Attributes**:
- **Value**: String representation of numeric identifier
- **Format**: Numeric string (typically 6-8 digits)
- **Validation**: Must be numeric, non-empty, within reasonable length range

**Validation Rules**:
- Cannot be empty
- Must contain only numeric characters
- Length should be between 4-10 digits (reasonable range for FIDE IDs)

**State Transitions**: N/A (immutable input value)

### Player Rating

**Description**: A numeric value representing a player's chess rating in a specific time control.

**Attributes**:
- **Value**: Integer (rating value, e.g., 2500)
- **Type**: Enumeration - "standard", "rapid", or "blitz"
- **Status**: Enumeration - "rated" or "unrated"

**Validation Rules**:
- Rating value must be a positive integer (typically 0-3000 range)
- Type must be either "standard", "rapid", or "blitz"
- Status indicates if player has a rating in this category

**State Transitions**: N/A (read-only data from FIDE website)

### Player Profile

**Description**: Aggregated data structure containing a player's ratings from FIDE website.

**Attributes**:
- **fide_id**: FIDE ID (string)
- **standard_rating**: Player Rating (standard type) or null if unrated
- **rapid_rating**: Player Rating (rapid type) or null if unrated
- **blitz_rating**: Player Rating (blitz type) or null if unrated

**Relationships**:
- Contains exactly one FIDE ID
- Contains zero or one standard rating
- Contains zero or one rapid rating
- Contains zero or one blitz rating

**Validation Rules**:
- At least one rating (standard, rapid, or blitz) should be present for a valid profile
- FIDE ID must be valid

**State Transitions**: N/A (ephemeral data structure, not persisted)

## Data Flow

1. **Input**: FIDE ID (string) → Validation → Validated FIDE ID
2. **Scraping**: Validated FIDE ID → HTTP Request → HTML Response → Parsing → Player Profile
3. **Output**: Player Profile → Formatting → Human-readable string output

## Error States

- **Invalid FIDE ID**: Input validation failure
- **Network Error**: HTTP request failure (timeout, connection error, DNS failure)
- **HTTP Error**: Non-200 status code (404, 500, etc.)
- **Parsing Error**: HTML structure changed or unexpected format
- **Missing Data**: Player exists but ratings not found in expected format

