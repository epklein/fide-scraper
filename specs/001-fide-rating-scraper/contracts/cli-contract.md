# CLI Contract: FIDE Rating Scraper

**Date**: 2025-01-27  
**Feature**: FIDE Rating Scraper

## Command Interface

### Command Name
`fide_scraper.py` (or `python fide_scraper.py`)

### Usage
```bash
python fide_scraper.py <FIDE_ID>
```

### Arguments

| Argument | Type | Required | Description | Validation |
|----------|------|----------|-------------|------------|
| `FIDE_ID` | string | Yes | The FIDE ID of the player to look up | Must be numeric, non-empty, 4-10 digits |

### Input Methods

**Primary**: Command-line argument
```bash
python fide_scraper.py 538026660
```

**Alternative**: Standard input (if no argument provided)
```bash
echo "538026660" | python fide_scraper.py
# or
python fide_scraper.py
# Then enter FIDE ID when prompted
```

### Output Format

**Success Case** (Human-readable):
```
Standard: 2500
Rapid: 2450
```

**Success Case** (Unrated in one category):
```
Standard: 2500
Rapid: Unrated
```

**Error Cases**:
```
Error: Invalid FIDE ID format. Must be numeric.
```

```
Error: Player not found (FIDE ID: 538026660)
```

```
Error: Unable to connect to FIDE website. Please check your internet connection.
```

```
Error: Failed to retrieve ratings. HTTP status: 500
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - ratings retrieved and displayed |
| 1 | Error - invalid input, network error, or parsing failure |
| 2 | Error - invalid FIDE ID format |

### Behavior

1. **Input Validation**: Validate FIDE ID format before making network request
2. **Network Request**: Make HTTP GET request to FIDE website
3. **HTML Parsing**: Extract standard and rapid ratings from HTML response
4. **Output**: Display ratings in human-readable format
5. **Error Handling**: Display clear error messages for all failure cases

### Performance Requirements

- Response time: < 5 seconds under normal network conditions
- Timeout: 10 seconds for HTTP requests
- Retry: No automatic retries (fail fast with clear error message)

### Dependencies

- Python 3.11+
- requests library
- beautifulsoup4 library

