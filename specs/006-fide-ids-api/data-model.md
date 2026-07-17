# Data Model: FIDE IDs API Integration

## Overview

This document defines the data structures involved in fetching FIDE IDs from the API and merging them with the existing players CSV file.

## Entities

### FIDE ID

**Type**: String
**Format**: Variable length numeric string (e.g., "12345678")
**Source**:
- Existing CSV file (FIDE_PLAYERS_FILE column)
- External API response (fide_ids array)

**Uniqueness**: Each ID is globally unique within the FIDE system
**Validation**: Already validated by existing `validate_fide_id()` function in fide_scraper.py

**Lifecycle**:
1. Loaded from CSV file (if exists)
2. Fetched from API endpoint
3. Merged with deduplication
4. Written back to CSV file
5. Used for scraping FIDE ratings

### API Response

**Source**: `GET https://chesshub.cloud/api/fide-ids/`

**Structure**:
```json
{
  "fide_ids": ["12345678", "23456789", "34567890"],
  "count": 3
}
```

**Fields**:
- `fide_ids` (array of strings): List of FIDE IDs as strings
- `count` (integer): Total number of distinct IDs

**Properties**:
- IDs are pre-sorted alphabetically by API
- IDs are pre-deduplicated by API (server filters to active users only)
- Only IDs for active users with valid FIDE data are included

### Player CSV File

**Path**: Value of `FIDE_PLAYERS_FILE` environment variable
**Format**: CSV with headers

**Current Structure** (to be examined during implementation):
- Contains at minimum one column with FIDE IDs
- May contain additional columns (email, name, etc.) - preserved as-is
- Format and delimiters must be preserved exactly

**Expected output after merge**:
- Same headers and structure as input
- New unique FIDE IDs appended as new rows
- No duplicates
- No modification to existing rows

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Scraper Startup                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Load FIDE_IDS_API_ENDPOINT from env  │
        │ Load API_TOKEN from env              │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Validate both values present         │
        │ If missing: log warning, continue    │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ GET /api/fide-ids/ with Auth header  │
        │ Parse fide_ids array from response   │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Load existing FIDE_PLAYERS_FILE CSV  │
        │ Extract FIDE IDs from file           │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Merge & Deduplicate                  │
        │ Set(CSV IDs) ∪ Set(API IDs)         │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Create new rows for unique API IDs   │
        │ Preserve existing rows exactly       │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Write augmented CSV to file          │
        │ Preserve format, headers, delimiters │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Load augmented file into player list │
        │ Proceed with normal scraping         │
        └───────────────────────────────────────┘
```

## State Transitions

### API Fetch State Machine

```
START
  │
  ├─(no endpoint/token)──→ SKIP → log warning → CONTINUE_WITH_FILE_ONLY
  │
  ├─(endpoint + token)──→ REQUEST → RESPONSE
  │
RESPONSE
  ├─(200 OK)──────────────→ PARSE ──→ SUCCESS
  │
  ├─(4xx/5xx error)───────→ ERROR ──→ log error → CONTINUE_WITH_FILE_ONLY
  │
  └─(timeout/network)─────→ ERROR ──→ log error → CONTINUE_WITH_FILE_ONLY
```

### File Merge State Machine

```
START
  │
  ├─(file missing)──────────→ CREATE_EMPTY
  │
  ├─(file exists)──────────→ LOAD
  │
LOAD
  ├─(read error)──────────→ ERROR ──→ fail with error message
  │
  ├─(parse error)─────────→ ERROR ──→ log & continue (preserve original file)
  │
  └─(success)────────────→ EXTRACT_IDS
  │
EXTRACT_IDS ──→ DEDUPLICATE ──→ BUILD_NEW_ROWS ──→ WRITE ──→ SUCCESS
```

## Validation Rules

### FIDE ID Validation
- Must be non-empty string
- Must be numeric characters only (0-9)
- Length: 4-10 digits (enforced by existing `validate_fide_id()`)
- Case-insensitive comparison (all treated as strings)

### CSV Format Validation
- Must be valid CSV (enforced by Python csv module)
- Must have headers (first row)
- Must have at least one column for FIDE IDs
- Delimiters and quoting must be detected and preserved

### API Response Validation
- Must be valid JSON
- Must contain `fide_ids` key (array)
- Must contain `count` key (integer)
- `fide_ids` array values must be strings
- `count` must equal length of `fide_ids` array

## Deduplication Strategy

**Approach**: String-based set membership test

**Algorithm**:
```
api_ids = set(response['fide_ids'])          # Set of strings from API
csv_ids = set(existing_ids_from_file)       # Set of strings from CSV
new_ids = api_ids - csv_ids                 # IDs only in API response
all_ids = csv_ids | api_ids                 # Union of all unique IDs

For each new_id in new_ids:
    Create new CSV row with new_id
    (preserve any additional columns as empty or default value)
```

**Complexity**: O(n + m) where n = CSV IDs, m = API IDs
**Duplicate Detection**: Case-sensitive string comparison (IDs are canonical strings)

## Missing or Unknown Values

### Scenario: API returns empty array
- Log: "API returned 0 FIDE IDs"
- Result: No new rows appended, continue with existing file

### Scenario: CSV file doesn't exist
- Create empty players file with headers
- Append all API IDs

### Scenario: CSV file is malformed
- Log error with details
- Attempt recovery: preserve original file, continue with API IDs only
- Do not write corrupted file

### Scenario: API is unavailable
- Log error (status, timeout, connection refused, etc.)
- Continue with existing file
- Scraper proceeds normally
