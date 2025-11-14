# Research: Batch FIDE Ratings Processing

**Date**: 2025-01-27  
**Purpose**: Resolve technical unknowns identified in Technical Context

## Player Name Extraction from FIDE Profile

**Decision**: Extract player name from `<h1 class="player-title">` element

**Rationale**:
- FIDE profile pages use a dedicated `<h1 class="player-title">` element for player names
- This selector provides direct access to the player name without parsing or text manipulation
- More reliable than title tag parsing which requires removing suffixes
- Semantic HTML element specifically designed for player name display

**HTML Structure Inspection**:

**Status**: ✅ **COMPLETE** - Selector identified: `<h1 class="player-title">`

**HTML Structure**:
```html
<h1 class="player-title">Magnus Carlsen</h1>
```

**Selector**:
- **Primary**: `h1.player-title` or `h1[class="player-title"]`
- **CSS Selector**: `h1.player-title`
- **BeautifulSoup**: `soup.select_one('h1.player-title')` or `soup.find('h1', class_='player-title')`

**Selector Reliability**:
- ✅ Direct semantic element for player name
- ✅ Consistent across FIDE profile pages
- ⚠️ Structure may change if FIDE updates their website (standard HTML structure, low risk)

**Fallback Strategy** (if primary selector fails):
- **Fallback 1**: Look for `<h1>` tag in profile header area (without class check)
- **Fallback 2**: Parse `<title>` tag and extract name (e.g., "Magnus Carlsen - FIDE Ratings" → "Magnus Carlsen")
- **Fallback 3**: Extract from meta tags (og:title, meta name="title")

**Implementation Notes**:
- Use BeautifulSoup to extract text from `h1.player-title` element
- Extract text directly: `soup.find('h1', class_='player-title').get_text(strip=True)`
- Handle cases where element is not found (return empty string or "Unknown")
- No text parsing needed - element contains clean player name
- Test with multiple player profiles to ensure consistent extraction

## CSV File Generation

**Decision**: Use Python's built-in `csv` module for CSV generation

**Rationale**:
- Standard library module, no additional dependencies
- Handles proper escaping of special characters (commas, quotes, newlines) automatically
- Cross-platform compatibility
- Widely used and well-documented
- Follows RFC 4180 CSV standard

**Alternatives considered**:
- **Manual CSV formatting**: Error-prone, requires manual escaping logic
- **pandas**: Overkill for simple CSV generation, adds heavy dependency
- **csvkit**: External tool, not suitable for library usage

**CSV Format Details**:
- Use `csv.DictWriter` for clean column-based writing
- Columns: FIDE ID, Player Name, Standard, Rapid, Blitz
- Proper escaping: Commas in player names will be automatically quoted
- Line endings: Use system default (csv module handles this)
- Encoding: UTF-8 for international character support

**Example Implementation Pattern**:
```python
import csv
from datetime import date

fieldnames = ['FIDE ID', 'Player Name', 'Standard', 'Rapid', 'Blitz']
with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow({
        'FIDE ID': fide_id,
        'Player Name': player_name,
        'Standard': standard_rating or '',
        'Rapid': rapid_rating or '',
        'Blitz': blitz_rating or ''
    })
```

## Date Format for Filename

**Decision**: Use ISO 8601 format (YYYY-MM-DD) for date in filename

**Rationale**:
- International standard, unambiguous
- Sorts chronologically when sorted alphabetically
- Widely recognized and understood
- No ambiguity between US/European date formats
- Example: `fide_ratings_2025-01-27.csv`

**Alternatives considered**:
- **MM-DD-YYYY**: US-centric, ambiguous internationally
- **DD-MM-YYYY**: European format, ambiguous internationally
- **Unix timestamp**: Not human-readable
- **YYYYMMDD** (no separators): Less readable but still sortable

**Filename Pattern**:
- Format: `fide_ratings_YYYY-MM-DD.csv`
- Example: `fide_ratings_2025-01-27.csv`
- Use `datetime.date.today().isoformat()` for date string

## Console Output Format

**Decision**: Display data in tabular format for readability

**Rationale**:
- Tabular format is more readable than CSV in console
- Aligns columns for easy scanning
- Can include separators and headers for clarity
- Matches user expectation for console output

**Alternatives considered**:
- **CSV format in console**: Less readable, harder to scan
- **JSON format**: Too verbose for console output
- **One line per player**: Acceptable but less structured

**Console Output Pattern**:
```
FIDE ID      Player Name          Standard  Rapid  Blitz
----------------------------------------------------------
1503014      Magnus Carlsen       2830      2780   2760
2016192      Hikaru Nakamura      2758      2800   2790
```

**Implementation Notes**:
- Use string formatting for column alignment
- Handle long player names (truncate or wrap)
- Display "Unrated" or empty string for missing ratings
- Print header row for clarity
- Print separator line for readability

## Batch Processing Error Handling Strategy

**Decision**: Continue processing remaining FIDE IDs when individual IDs fail, with error logging

**Rationale**:
- User requirement (FR-008, FR-012, FR-013): Invalid IDs should not stop batch processing
- Better user experience: Process as many valid IDs as possible
- Allows partial success: Some players processed even if others fail
- Error information can be logged for user review

**Error Handling Approach**:
1. **Invalid FIDE ID format**: Skip with warning message, continue processing
2. **Network error for individual ID**: Log error, continue with next ID
3. **Player not found (404)**: Log error, continue with next ID
4. **HTML parsing error**: Log error, continue with next ID
5. **File I/O errors**: Stop processing (cannot continue without file access)

**Error Reporting**:
- Print error messages to stderr for invalid/missing players
- Continue processing remaining IDs
- Include error summary at end (e.g., "Processed 95/100 IDs successfully")
- Optionally: Include error details in a separate error log file

**Implementation Pattern**:
```python
success_count = 0
error_count = 0
errors = []

for fide_id in fide_ids:
    try:
        # Process FIDE ID
        result = process_fide_id(fide_id)
        if result:
            success_count += 1
            # Write to CSV and console
        else:
            error_count += 1
            errors.append(f"FIDE ID {fide_id}: Player not found")
    except Exception as e:
        error_count += 1
        errors.append(f"FIDE ID {fide_id}: {str(e)}")
        # Continue to next ID

# Print summary
print(f"\nProcessed {success_count} IDs successfully, {error_count} errors")
```

## File Input Processing

**Decision**: Read input file line-by-line, skip empty lines, strip whitespace

**Rationale**:
- Simple and efficient for text files
- Handles empty lines gracefully (FR-009)
- Strips whitespace to handle common formatting issues
- Memory-efficient for large files

**File Reading Pattern**:
```python
def read_fide_ids_from_file(filepath: str) -> List[str]:
    fide_ids = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:  # Skip empty lines
                fide_ids.append(line)
    return fide_ids
```

**Error Handling**:
- File not found: Print clear error message, exit with error code
- Permission denied: Print clear error message, exit with error code
- Invalid encoding: Try UTF-8 first, handle encoding errors gracefully

## Date-stamped Filename Conflict Handling

**Decision**: Overwrite existing file if filename conflicts (same date)

**Rationale**:
- Simple behavior: Most recent run overwrites previous run for same date
- User can manually rename files if they want to preserve multiple runs
- Avoids complexity of appending numbers or timestamps

**Alternatives considered**:
- **Append number**: `fide_ratings_2025-01-27_1.csv`, `fide_ratings_2025-01-27_2.csv` - More complex, may create many files
- **Include timestamp**: `fide_ratings_2025-01-27_14-30-00.csv` - More complex filename, less readable
- **Prompt user**: Interactive, breaks automation

**Implementation**:
- Use standard file open with 'w' mode (overwrites by default)
- No special conflict handling needed
- Document behavior in quickstart guide

## Performance Considerations

**Decision**: Sequential processing (one FIDE ID at a time)

**Rationale**:
- Simpler implementation and error handling
- Avoids overwhelming FIDE website with concurrent requests
- Respectful web scraping (no aggressive parallel requests)
- Easier to debug and test
- Sufficient performance for typical use cases (100 IDs in 10 minutes = ~6 seconds per ID)

**Alternatives considered**:
- **Parallel processing**: Faster but more complex, may violate website terms, harder error handling
- **Batch requests**: FIDE website doesn't support batch API endpoints

**Performance Targets**:
- 100 FIDE IDs processed in 10 minutes = ~6 seconds per ID average
- Includes network request time, HTML parsing, CSV writing
- Acceptable for batch processing use case

