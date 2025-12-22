# CLI Contract: Batch FIDE Ratings Processing

**Date**: 2025-01-27  
**Feature**: Batch FIDE Ratings Processing

## Command Interface

### Command Name
`fide_scraper.py` (or `python fide_scraper.py`)

### Usage

```bash
python fide_scraper.py --file <INPUT_FILE>
# or
python fide_scraper.py -f <INPUT_FILE>
```

### Arguments

| Argument | Type | Required | Description | Validation |
|----------|------|----------|-------------|------------|
| `--file` / `-f` | string | Yes | Path to input file containing FIDE IDs (one per line) | File must exist and be readable |

### Input File Format

**File Structure**:
- Plain text file (UTF-8 encoding)
- One FIDE ID per line
- Empty lines are allowed (will be skipped)
- Whitespace around FIDE IDs is allowed (will be stripped)

**Example Input File** (`fide_ids.txt`):
```
1503014
538026660
538020459
538027038
538042827
```

### Output Format

**Batch Processing Mode**:

**Console Output** (tabular format):
```
Processing FIDE IDs from file: fide_ids.txt

FIDE ID      Player Name          Standard  Rapid  Blitz
----------------------------------------------------------
1503014      Magnus Carlsen       2830      2780   2760
2016192      Hikaru Nakamura      2758      2800   2790

Output written to: fide_ratings_2025-01-27.csv
Processed 2 IDs successfully, 0 errors
```

**CSV Output File**:
- Filename: `fide_ratings_YYYY-MM-DD.csv` (e.g., `fide_ratings_2025-01-27.csv`)
- Location: Current working directory
- Format: CSV with header row
- Columns: FIDE ID, Player Name, Standard, Rapid, Blitz

**Example CSV Content**:
```csv
FIDE ID,Player Name,Standard,Rapid,Blitz
1503014,Magnus Carlsen,2830,2780,2760
2016192,Hikaru Nakamura,2758,2800,2790
```

**Error Handling**:
```
Processing FIDE IDs from file: fide_ids.txt

FIDE ID      Player Name          Standard  Rapid  Blitz
----------------------------------------------------------
1503014      Magnus Carlsen       2830      2780   2760
Error: Invalid FIDE ID format: abc123 (skipped)
2016192      Hikaru Nakamura      2758      2800   2790
Error: Player not found (FIDE ID: 99999999) (skipped)

Output written to: fide_ratings_2025-01-27.csv
Processed 2 IDs successfully, 2 errors
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - all valid FIDE IDs processed |
| 1 | Error - file not found, network error, or parsing failure |
| 2 | Error - file cannot be read |

### Behavior

1. **File Reading**: Read input file, parse FIDE IDs (one per line), skip empty lines
2. **Validation**: Validate each FIDE ID format before processing
3. **Processing**: For each valid FIDE ID:
   - Make HTTP GET request to FIDE website
   - Extract player name from HTML
   - Extract standard, rapid, and blitz ratings from HTML
   - Add to results
4. **Error Handling**: Continue processing remaining IDs if individual IDs fail
5. **CSV Generation**: Write all successfully processed players to CSV file with date-stamped filename
6. **Console Output**: Display results in tabular format
7. **Summary**: Print processing summary (success count, error count)

### Performance Requirements

- Process 100+ FIDE IDs within 10 minutes under normal network conditions
- Sequential processing (one FIDE ID at a time)
- Timeout: 10 seconds per HTTP request
- Retry: No automatic retries (fail fast with clear error message, continue to next ID)

### Dependencies

- Python 3.11+
- requests library
- beautifulsoup4 library
- csv module (standard library)
- datetime module (standard library)

