# FIDE Rating Scraper

A simple Python script that scrapes the FIDE website to retrieve current chess ratings for players by their FIDE ID.

**Note:** This project is my first experiment using [spec-kit](https://github.com/github/spec-kit) for structured, machine-readable specs. I've implemented it within the [Cursor](https://www.cursor.so/) editor.

I had to step in during the research phase to provide HTML examples that support the planning phase for proper implementation of the scraping code.

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

## Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   Or install manually:
   ```bash
   pip install requests beautifulsoup4
   ```

## Usage

The script supports two modes: **Single FIDE ID mode** (for one player) and **Batch Processing mode** (for multiple players from a file).

### Single FIDE ID Mode

Run the script with a FIDE ID as an argument:

```bash
python fide_scraper.py 538026660
```

**Example Output**:
```
Standard: 2830
Rapid: 2780
Blitz: 2760
```

**Player with missing rating**:
```
Standard: 2500
Rapid: 2450
Blitz: Unrated
```

**Error - Invalid FIDE ID**:
```
Error: Invalid FIDE ID format. Must be numeric (4-10 digits).
```

**Error - Player not found**:
```
Error: Player not found (FIDE ID: 99999999)
```

**Error - Network issue**:
```
Error: Unable to connect to FIDE website. Please check your internet connection.
```

### Batch Processing Mode

Process multiple FIDE IDs from a file and output results to both a CSV file and the console.

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
Processed 2 IDs successfully, 0 errors
```

**CSV Output File**:
- **Filename**: `fide_ratings_YYYY-MM-DD.csv` (includes current date in ISO 8601 format)
- **Location**: Current working directory
- **Format**: Standard CSV with proper escaping for special characters
- **Columns**: FIDE ID, Player Name, Standard, Rapid, Blitz

**Example CSV Content**:
```csv
FIDE ID,Player Name,Standard,Rapid,Blitz
1503014,Magnus Carlsen,2830,2780,2760
2016192,Hikaru Nakamura,2758,2800,2790
```

**Error Handling in Batch Mode**:
The script continues processing even when individual FIDE IDs fail:

```
Processing FIDE IDs from file: fide_ids.txt

FIDE ID      Player Name          Standard  Rapid  Blitz
----------------------------------------------------------
1503014      Magnus Carlsen       2830      2780   2760
Error: Invalid FIDE ID format: abc123 (skipped)
2016192      Hikaru Nakamura       2758      2800   2790
Error: Player not found (FIDE ID: 99999999) (skipped)

Output written to: fide_ratings_2025-01-27.csv
Processed 2 IDs successfully, 2 errors
```

**Batch Processing Features**:
- Processes all valid FIDE IDs in the file
- Skips invalid IDs and continues processing
- Handles network errors gracefully (continues with remaining IDs)
- Generates CSV file with date-stamped filename
- Displays results in both CSV and console
- Provides summary of successful and failed processing

## Finding a FIDE ID

FIDE IDs can be found on:
- FIDE ratings website: https://ratings.fide.com
- Player profile pages
- Tournament results

FIDE IDs are typically 6-8 digit numbers (4-10 digits valid).

## Output Files

### CSV File Format

When using batch processing mode, the script generates a CSV file with the following characteristics:

- **Filename**: `fide_ratings_YYYY-MM-DD.csv` (date in ISO 8601 format)
- **Encoding**: UTF-8
- **Delimiter**: Comma
- **Header Row**: Yes (FIDE ID, Player Name, Standard, Rapid, Blitz)
- **Special Characters**: Automatically escaped (commas in names are quoted)
- **Missing Ratings**: Empty cell for missing/unrated ratings

The CSV file can be opened in:
- Microsoft Excel
- Google Sheets
- Any spreadsheet application
- Text editors

**Note**: If opening in Excel, you may need to specify UTF-8 encoding during import.

## Testing

Run the test suite:

```bash
pytest tests/
```

Run specific test file:

```bash
pytest tests/test_fide_scraper.py
```

## Troubleshooting

### "Module not found" error
- Ensure dependencies are installed: `pip install -r requirements.txt`

### Network timeout errors
- Check your internet connection
- FIDE website may be temporarily unavailable
- Try again after a few moments
- In batch mode, individual timeouts won't stop processing of remaining IDs

### "Player not found" error
- Verify the FIDE ID is correct
- Check that the player exists on the FIDE website
- Ensure the FIDE ID is numeric only
- In batch mode, these errors are logged but don't stop processing

### Parsing errors
- FIDE website structure may have changed
- Check if the website is accessible in a browser
- Report the issue if the website structure has changed

### Batch Processing Issues

**"File not found" error**:
- Verify the file path is correct
- Use absolute path if relative path doesn't work: `python fide_scraper.py --file /full/path/to/file.txt`
- Check file permissions (must be readable)

**"Permission denied" error**:
- Check write permissions in current directory (needed for CSV output)
- Try running from a different directory with write access

**Empty CSV file**:
- Check that at least one FIDE ID in the file is valid
- Verify network connectivity
- Check console output for error messages

**Special characters in player names**:
- CSV file uses UTF-8 encoding
- Special characters should be preserved correctly
- If viewing in Excel, may need to specify UTF-8 import

