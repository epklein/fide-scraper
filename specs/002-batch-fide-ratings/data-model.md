# Data Model: Batch FIDE Ratings Processing

**Date**: 2025-01-27  
**Feature**: Batch FIDE Ratings Processing

## Entities

### FIDE ID

**Description**: A unique identifier for a chess player in the FIDE system.

**Attributes**:
- **Value**: String representation of numeric identifier
- **Format**: Numeric string (4-10 digits)
- **Validation**: Must be numeric, non-empty, within reasonable length range

**Validation Rules**:
- Cannot be empty
- Must contain only numeric characters
- Length should be between 4-10 digits (reasonable range for FIDE IDs)

**State Transitions**: N/A (immutable input value)

### Player Name

**Description**: The full name of the chess player as displayed on their FIDE profile page.

**Attributes**:
- **Value**: String (player's full name)
- **Source**: Extracted from FIDE profile HTML (`<h1 class="player-title">` element)
- **Format**: Free-form text, may contain special characters

**Validation Rules**:
- Can be empty if extraction fails (handle gracefully)
- May contain commas, quotes, or other special characters (requires CSV escaping)
- May contain international characters (UTF-8 encoding)

**State Transitions**: N/A (read-only data from FIDE website)

### Player Rating

**Description**: A numeric value representing a player's chess rating in a specific time control.

**Attributes**:
- **Value**: Integer (rating value, e.g., 2500) or None if unrated
- **Type**: Enumeration - "standard", "rapid", or "blitz"
- **Status**: Enumeration - "rated" or "unrated"

**Validation Rules**:
- Rating value must be a positive integer (typically 0-3000 range) or None
- Type must be either "standard", "rapid", or "blitz"
- Status indicates if player has a rating in this category

**State Transitions**: N/A (read-only data from FIDE website)

### Player Profile

**Description**: Aggregated data structure containing a player's information from FIDE website.

**Attributes**:
- **fide_id**: FIDE ID (string)
- **player_name**: Player Name (string) or empty string if extraction fails
- **standard_rating**: Player Rating (standard type) or None if unrated
- **rapid_rating**: Player Rating (rapid type) or None if unrated
- **blitz_rating**: Player Rating (blitz type) or None if unrated

**Relationships**:
- Contains exactly one FIDE ID
- Contains zero or one player name (may be empty if extraction fails)
- Contains zero or one standard rating
- Contains zero or one rapid rating
- Contains zero or one blitz rating

**Validation Rules**:
- FIDE ID must be valid
- At least one rating (standard, rapid, or blitz) should be present for a valid profile (or player name if ratings unavailable)
- Player name can be empty if extraction fails (still valid profile if ratings exist)

**State Transitions**: N/A (ephemeral data structure, not persisted)

### Input File

**Description**: A text file containing FIDE IDs, one per line.

**Attributes**:
- **Format**: Plain text file (UTF-8 encoding)
- **Structure**: One FIDE ID per line
- **Content**: May contain empty lines, whitespace, invalid entries

**Validation Rules**:
- File must exist and be readable
- File encoding should be UTF-8 (handle encoding errors gracefully)
- Empty lines are allowed (will be skipped)
- Whitespace around FIDE IDs is allowed (will be stripped)

**State Transitions**: N/A (read-only input)

### CSV Output File

**Description**: A comma-separated values file containing processed player data.

**Attributes**:
- **Format**: CSV (RFC 4180 standard)
- **Encoding**: UTF-8
- **Columns**: FIDE ID, Player Name, Standard, Rapid, Blitz
- **Filename**: Includes date in format `fide_ratings_YYYY-MM-DD.csv`

**Validation Rules**:
- Must be writable in output directory
- Proper CSV escaping for special characters (commas, quotes, newlines)
- Header row must be included
- Each row represents one successfully processed player

**State Transitions**: N/A (write-only output)

### Batch Processing Result

**Description**: Aggregated result of batch processing operation.

**Attributes**:
- **total_ids**: Integer (total FIDE IDs in input file)
- **processed_count**: Integer (number of successfully processed IDs)
- **error_count**: Integer (number of IDs that failed processing)
- **errors**: List of error messages (one per failed ID)
- **output_file**: String (path to generated CSV file)

**Relationships**:
- Contains summary statistics for batch operation
- Contains list of errors encountered during processing

**Validation Rules**:
- processed_count + error_count <= total_ids
- errors list length should equal error_count
- output_file should exist if processed_count > 0

**State Transitions**: N/A (ephemeral result structure)

## Data Flow

1. **Input**: Input File → File Reading → List of FIDE ID strings (with empty lines skipped)
2. **Validation**: FIDE ID string → Format Validation → Validated FIDE ID or Error
3. **Scraping**: Validated FIDE ID → HTTP Request → HTML Response → Parsing → Player Profile
4. **Extraction**: HTML Response → Player Name Extraction → Player Name string
5. **Aggregation**: Player Profile → CSV Row Data → CSV Output File
6. **Output**: CSV Output File + Console Display → User

## Error States

- **File Not Found**: Input file doesn't exist or path is invalid
- **File Permission Error**: Cannot read input file or write output file
- **Invalid FIDE ID Format**: FIDE ID doesn't match expected format (numeric, 4-10 digits)
- **Network Error**: HTTP request failure (timeout, connection error, DNS failure) for individual ID
- **HTTP Error**: Non-200 status code (404, 500, etc.) for individual ID
- **Player Not Found**: FIDE ID exists but player profile not found (404 response)
- **Parsing Error**: HTML structure changed or unexpected format for individual ID
- **Name Extraction Failure**: Player name cannot be extracted from HTML (non-fatal, continue processing)
- **Missing Ratings**: Player exists but no ratings found in expected format (non-fatal, include with empty ratings)

## Data Transformations

### FIDE ID Input Processing
```
Raw file line → strip() → validate_fide_id() → Valid FIDE ID or Skip
```

### Player Profile Construction
```
FIDE ID → fetch_fide_profile() → HTML → extract_player_name() → Player Name
FIDE ID → fetch_fide_profile() → HTML → extract_standard_rating() → Standard Rating
FIDE ID → fetch_fide_profile() → HTML → extract_rapid_rating() → Rapid Rating
FIDE ID → fetch_fide_profile() → HTML → extract_blitz_rating() → Blitz Rating
→ Combine → Player Profile
```

### CSV Row Generation
```
Player Profile → {
    'FIDE ID': fide_id,
    'Player Name': player_name or '',
    'Standard': standard_rating or '',
    'Rapid': rapid_rating or '',
    'Blitz': blitz_rating or ''
} → CSV Row (with proper escaping)
```

### Console Output Formatting
```
Player Profile → Format as table row → Console output
```

