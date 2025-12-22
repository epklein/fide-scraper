# Quickstart Guide: Batch FIDE Ratings Processing

**Date**: 2025-01-27  
**Feature**: Batch FIDE Ratings Processing

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Existing FIDE scraper installation (from feature 001)

## Installation

1. **Navigate to the project directory**:
   ```bash
   cd /path/to/fide-scraper
   ```

2. **Ensure dependencies are installed**:
   ```bash
   pip install -r requirements.txt
   ```

   Or install manually:
   ```bash
   pip install requests beautifulsoup4
   ```

## Usage

### Batch Processing Mode (New Feature)

#### Step 1: Prepare Input File

Create a text file containing FIDE IDs, one per line:

**Example** (`fide_ids.txt`):
```
1503014
538026660
538020459
538027038
538042827
```

**Notes**:
- One FIDE ID per line
- Empty lines are allowed (will be skipped)
- Whitespace around IDs is automatically stripped
- File should be UTF-8 encoded

#### Step 2: Run Batch Processing

```bash
python fide_scraper.py --file fide_ids.txt
```

Or using short form:
```bash
python fide_scraper.py -f fide_ids.txt
```

#### Step 3: View Results

**Console Output**:
```
Processing FIDE IDs from file: fide_ids.txt

FIDE ID      Player Name          Standard  Rapid  Blitz
----------------------------------------------------------
1503014      Magnus Carlsen       2830      2780   2760
2016192      Hikaru Nakamura       2758      2800   2790

Output written to: fide_ratings_2025-01-27.csv
Processed 3 IDs successfully, 0 errors
```

**CSV File**:
- Filename: `fide_ratings_YYYY-MM-DD.csv` (includes current date)
- Location: Current working directory
- Format: Standard CSV, can be opened in Excel, Google Sheets, etc.

**Example CSV Content**:
```csv
FIDE ID,Player Name,Standard,Rapid,Blitz
1503014,Magnus Carlsen,2830,2780,2760
2016192,Hikaru Nakamura,2758,2800,2790
```

## Example Scenarios

### Scenario 1: Process Multiple Players

**Input File** (`players.txt`):
```
538026660
2016892
1503014
8603677
```

**Command**:
```bash
python fide_scraper.py --file players.txt
```

**Result**: CSV file `fide_ratings_2025-01-27.csv` with ratings for all 4 players, plus console output.

### Scenario 2: Handle Errors Gracefully

**Input File** (`mixed.txt`):
```
1503014
invalid_id
538026660
538020459
538027038
538042827
```

**Command**:
```bash
python fide_scraper.py --file mixed.txt
```

**Console Output**:
```
Processing FIDE IDs from file: mixed.txt

FIDE ID      Player Name          Standard  Rapid  Blitz
----------------------------------------------------------
538026660    Magnus Carlsen       2830      2780   2760
Error: Invalid FIDE ID format: invalid_id (skipped)
2016892      Hikaru Nakamura       2758      2800   2790
Error: Player not found (FIDE ID: 99999999) (skipped)

Output written to: fide_ratings_2025-01-27.csv
Processed 2 IDs successfully, 2 errors
```

**Result**: CSV file contains only successfully processed players (2 players). Invalid IDs are skipped with error messages.

### Scenario 3: Large Batch Processing

**Input File** (`large_batch.txt`):
```
1503014
538026660
538020459
538027038
538042827
... (100+ FIDE IDs)
```

**Command**:
```bash
python fide_scraper.py --file large_batch.txt
```

**Result**: Processes all valid FIDE IDs sequentially. May take several minutes for large batches. Progress is shown in console output.

## Finding FIDE IDs

FIDE IDs can be found on:
- FIDE ratings website: https://ratings.fide.com
- Player profile pages
- Tournament results
- Chess databases

FIDE IDs are typically 6-8 digit numbers.

## Output File Details

### Filename Format
- Pattern: `fide_ratings_YYYY-MM-DD.csv`
- Example: `fide_ratings_2025-01-27.csv`
- Date format: ISO 8601 (YYYY-MM-DD)

### File Location
- Created in the current working directory
- Overwrites existing file with same date if run multiple times on same day

### CSV Format
- **Encoding**: UTF-8
- **Delimiter**: Comma
- **Header Row**: Yes (FIDE ID, Player Name, Standard, Rapid, Blitz)
- **Special Characters**: Automatically escaped (commas in names are quoted)
- **Missing Ratings**: Empty cell or "Unrated" (to be determined in implementation)

### Opening CSV Files
- **Excel**: Double-click to open (may require UTF-8 import settings)
- **Google Sheets**: File → Import → Upload → Select CSV file
- **Text Editor**: Can view raw CSV content

## Testing

Run the test suite:

```bash
pytest tests/
```

Run specific test file:

```bash
pytest tests/test_fide_scraper.py
pytest tests/test_integration.py
```

## Troubleshooting

### "File not found" error
- Verify the file path is correct
- Use absolute path if relative path doesn't work: `python fide_scraper.py --file /full/path/to/file.txt`
- Check file permissions (must be readable)

### "Permission denied" error
- Check write permissions in current directory (needed for CSV output)
- Try running from a different directory with write access

### Network timeout errors
- Check your internet connection
- FIDE website may be temporarily unavailable
- Individual ID failures won't stop batch processing

### "Player not found" errors
- Verify FIDE IDs are correct
- Check that players exist on FIDE website
- These errors are expected for invalid IDs and won't stop batch processing

### Empty CSV file
- Check that at least one FIDE ID in the file is valid
- Verify network connectivity
- Check console output for error messages

### Parsing errors
- FIDE website structure may have changed
- Check if the website is accessible in a browser
- Report the issue if the website structure has changed

### Special characters in player names
- CSV file uses UTF-8 encoding
- Special characters should be preserved correctly
- If viewing in Excel, may need to specify UTF-8 import

## Performance Tips

- **Large batches**: Processing 100+ IDs may take 10+ minutes
- **Network speed**: Faster internet = faster processing
- **Sequential processing**: IDs are processed one at a time (respectful scraping)
- **Error handling**: Invalid IDs are skipped, so processing continues

## Next Steps

- Review the [specification](spec.md) for detailed requirements
- Check the [implementation plan](plan.md) for technical details
- See [data model](data-model.md) for data structures
- Review [CLI contract](contracts/cli-contract.md) for command interface details

