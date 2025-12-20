# Quickstart Guide: Implementing FIDE IDs API Integration

## Overview

This guide walks through the implementation of fetching FIDE IDs from an external API and merging them with the existing players CSV file.

## Key Design Decisions

### 1. Architecture
- **Integrated into fide_scraper.py**: No new modules or packages
- **Three new functions** in the main script:
  - `fetch_fide_ids_from_api()` - API request & parsing
  - `merge_player_ids()` - Deduplication logic
  - `augment_players_file()` - CSV I/O & merge
- **Called before main scraping loop** in the existing `main()` function

### 2. Error Handling Strategy
- **API unavailable**: Log warning, continue with existing file (graceful degradation)
- **CSV file issues**: Log error, attempt recovery (preserve original file)
- **Validation failures**: Log details, skip invalid data, continue with safe subset
- **Never block scraper**: Feature is an enhancement, not a blocker

### 3. Data Handling
- **FIDE IDs as strings**: Match API response format exactly
- **Case-sensitive comparison**: IDs are canonical strings, no normalization
- **CSV format preservation**: Read original format, preserve exactly on write (delimiters, quoting, etc.)
- **Append-only**: Never modify existing rows, only add new ones

### 4. Performance Approach
- **Simplicity over optimization**: Set-based deduplication is O(n+m) and sufficient
- **Single pass**: Load file once, merge once, write once
- **No caching**: Fresh API fetch each run (acceptable for daily scraper execution)
- **Timeout**: 30-second HTTP timeout prevents hanging

## Implementation Workflow

### Phase 1: API Fetch Function

**Location**: Add to `fide_scraper.py` (after existing function definitions)

**Signature**:
```python
def fetch_fide_ids_from_api(api_endpoint: str, api_token: str) -> Optional[List[str]]:
    """
    Fetch FIDE IDs from external API endpoint.

    Args:
        api_endpoint: Full URL to API endpoint (e.g., https://eduklein.cloud/api/fide-ids/)
        api_token: Authentication token for API

    Returns:
        List of FIDE ID strings if successful, None if API unavailable

    Raises:
        None - errors are logged and handled gracefully
    """
```

**Responsibilities**:
1. Validate inputs (endpoint and token not empty)
2. Build Authorization header: `Authorization: Token <token>`
3. Send GET request with 30-second timeout
4. Parse JSON response
5. Extract `fide_ids` array (strings)
6. Log success/failure with details
7. Return list of IDs or None on failure

**Error Handling**:
- `requests.Timeout`: Log as timeout error, return None
- `requests.ConnectionError`: Log connection error, return None
- `requests.HTTPError`: Log HTTP status code, return None
- `json.JSONDecodeError`: Log parse error, return None
- Validation errors: Log details, return None

### Phase 2: Merge Function

**Location**: Add to `fide_scraper.py`

**Signature**:
```python
def merge_player_ids(csv_ids: List[str], api_ids: List[str]) -> Tuple[List[str], List[str]]:
    """
    Merge FIDE IDs from CSV and API, with deduplication.

    Args:
        csv_ids: List of IDs from existing CSV file
        api_ids: List of IDs from API response

    Returns:
        Tuple of:
        - all_ids: Sorted list of all unique IDs (CSV + API)
        - new_ids: List of IDs only from API (for logging)
    """
```

**Responsibilities**:
1. Convert to sets for deduplication
2. Compute union of IDs
3. Identify new IDs (API - CSV)
4. Return both lists (for logging stats)
5. Log merge summary: "Merged X CSV IDs + Y API IDs → Z unique IDs, +W new"

**Algorithm**:
```python
csv_set = set(csv_ids)
api_set = set(api_ids)
new_ids = api_set - csv_set
all_ids = list(csv_set | api_set)
return sorted(all_ids), list(new_ids)
```

### Phase 3: File Augmentation Function

**Location**: Add to `fide_scraper.py`

**Signature**:
```python
def augment_players_file(csv_path: str, new_ids: List[str]) -> bool:
    """
    Append new FIDE IDs to existing CSV file while preserving format.

    Args:
        csv_path: Path to FIDE_PLAYERS_FILE
        new_ids: List of new IDs to append (from merge operation)

    Returns:
        True if successful, False if error occurred (logged)

    Notes:
        - Preserves original CSV format, delimiters, quoting
        - Reads file to detect format (dialect, delimiter)
        - Creates new rows for each new ID (other columns empty/default)
    """
```

**Responsibilities**:
1. Check if file exists
2. If not exists: Create with headers
3. If exists:
   - Detect CSV dialect (comma vs semicolon, etc.)
   - Read all existing rows (preserve exactly)
   - Append new rows with new IDs
4. Validate write succeeded
5. Log result: "Updated players file: +X new IDs"

**Error Handling**:
- File locked: Log error, return False (scraper continues with original file)
- Permission denied: Log error, return False
- Disk full: Log error, return False
- CSV parse error: Log error, revert to original, return False

### Phase 4: Main Function Integration

**Location**: Modify existing `main()` function in `fide_scraper.py`

**Changes**:
```python
def main():
    # ... existing initialization code ...

    # NEW: Load API configuration
    api_endpoint = os.getenv('FIDE_IDS_API_ENDPOINT', '').strip()
    api_token = os.getenv('API_TOKEN', '').strip()

    # NEW: Augment players file if API is configured
    if api_endpoint and api_token:
        api_ids = fetch_fide_ids_from_api(api_endpoint, api_token)
        if api_ids:
            csv_ids = load_existing_ids(FIDE_PLAYERS_FILE)
            all_ids, new_ids = merge_player_ids(csv_ids, api_ids)
            success = augment_players_file(FIDE_PLAYERS_FILE, new_ids)
            if success:
                logging.info(f"Players file augmented with {len(new_ids)} new IDs")

    # ... rest of existing scraping logic (unchanged) ...
```

## Configuration

### Environment Variables

**New Variable**: `FIDE_IDS_API_ENDPOINT`
- **Value**: Full URL to API endpoint
- **Example**: `https://eduklein.cloud/api/fide-ids/`
- **Default**: Not set (feature is optional)
- **Required**: Only if you want to use API ID augmentation

**Existing Variable**: `API_TOKEN`
- **Used for**: Both ratings API (feature 005) and IDs API (this feature)
- **Same token** for both endpoints (per spec assumptions)

### .env File Example

```bash
# Existing configuration
FIDE_PLAYERS_FILE=players.csv
FIDE_OUTPUT_FILE=fide_ratings.csv
FIDE_RATINGS_API_ENDPOINT=https://eduklein.cloud/api/fide-ratings/
API_TOKEN=your_api_token_here

# NEW: FIDE IDs API endpoint
FIDE_IDS_API_ENDPOINT=https://eduklein.cloud/api/fide-ids/
```

## Testing Strategy

### Unit Tests

**Test File**: `tests/test_fide_scraper.py` (extend existing)

**Tests to Add**:
1. `test_fetch_fide_ids_success()` - Mock API returns valid response
2. `test_fetch_fide_ids_empty_array()` - API returns empty list
3. `test_fetch_fide_ids_missing_endpoint()` - No endpoint configured
4. `test_fetch_fide_ids_missing_token()` - No token configured
5. `test_fetch_fide_ids_http_error()` - API returns 401/500
6. `test_fetch_fide_ids_timeout()` - Request times out
7. `test_merge_no_duplicates()` - All IDs unique
8. `test_merge_with_duplicates()` - Some overlap between CSV and API
9. `test_merge_all_from_api()` - CSV empty, all IDs from API
10. `test_augment_players_file_success()` - File created/updated correctly
11. `test_augment_preserves_csv_format()` - Delimiters, quoting preserved
12. `test_augment_empty_csv()` - Create file from scratch
13. `test_augment_file_locked()` - Permission/lock error handled

### Integration Tests

**Test File**: `tests/test_integration.py` (extend existing)

**Tests to Add**:
1. `test_full_api_augmentation_flow()` - End-to-end: fetch API → merge → write → verify
2. `test_augmentation_with_real_csv_format()` - Test with actual CSV from project
3. `test_graceful_degradation_api_down()` - API unavailable, scraper proceeds

## Implementation Checklist

- [ ] **Phase 1**: Implement `fetch_fide_ids_from_api()`
  - [ ] API request with error handling
  - [ ] JSON parsing
  - [ ] Logging
  - [ ] Unit tests (5 tests)

- [ ] **Phase 2**: Implement `merge_player_ids()`
  - [ ] Set-based deduplication
  - [ ] Return new IDs for logging
  - [ ] Unit tests (3 tests)

- [ ] **Phase 3**: Implement `augment_players_file()`
  - [ ] CSV format detection & preservation
  - [ ] File I/O with error handling
  - [ ] New row creation
  - [ ] Unit tests (5 tests)

- [ ] **Phase 4**: Integrate with `main()`
  - [ ] Call augmentation before scraping
  - [ ] Handle optional configuration
  - [ ] Integration tests (3 tests)

- [ ] **Phase 5**: Configuration & Documentation
  - [ ] Update .env.example
  - [ ] Update README.md
  - [ ] Add docstrings to new functions

- [ ] **Testing**: Run full test suite
  - [ ] Unit tests pass
  - [ ] Integration tests pass
  - [ ] No regressions in existing functionality

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| API is slow/hangs | 30-second timeout; scraper continues if timeout |
| API returns malformed data | JSON validation; skip invalid responses |
| CSV file gets corrupted | Preserve original on error; log details |
| Unexpected API format | Robust parsing with try-catch; fallback to no augmentation |
| Duplicate entries in CSV | Set-based deduplication prevents duplicates |
| File locking on shared system | Check if file exists before write; skip on lock |

## Deployment Notes

### Docker Environment
- Ensure `FIDE_IDS_API_ENDPOINT` is set in docker-compose environment or Kubernetes ConfigMap
- Token should come from secret management (not in Dockerfile)

### Kubernetes Deployment (Hostinger)
- Add ConfigMap entry for `FIDE_IDS_API_ENDPOINT`
- Verify network access to `eduklein.cloud` API (may need firewall rules)
- Monitor API availability via logs

### Backward Compatibility
- Feature is **opt-in**: If `FIDE_IDS_API_ENDPOINT` is not set, no API calls occur
- Existing scraper behavior unchanged if configuration is absent
- Safe to deploy without breaking existing setups
