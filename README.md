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
   pip install requests beautifulsoup4 python-dotenv
   ```

2. **Configure batch processing (optional)**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` to customize input/output file paths (defaults are used if `.env` doesn't exist):
   ```env
   FIDE_INPUT_FILE=fide_ids.txt
   FIDE_OUTPUT_FILE=fide_ratings.csv
   ```

## Usage

The script supports two modes: **Batch Processing mode** (default, for multiple players from a file) and **Single FIDE ID mode** (for one player).

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

Simply run the script without arguments (it will use the configured input file):

```bash
python fide_scraper.py
```

The script will read from the file specified in `FIDE_INPUT_FILE` environment variable (default: `fide_ids.txt`) and write to `FIDE_OUTPUT_FILE` (default: `fide_ratings.csv`).

To customize file paths, create/edit a `.env` file in the project root:
```env
FIDE_INPUT_FILE=my_players.txt
FIDE_OUTPUT_FILE=ratings_history.csv
```

#### Step 3: View Results

**Console Output**:
```
Processing FIDE IDs from file: fide_ids.txt

Date         FIDE ID      Player Name          Standard  Rapid  Blitz
--------------------------------------------------------------------
2025-01-27   1503014      Magnus Carlsen       2830      2780   2760
2025-01-27   2016192      Hikaru Nakamura      2758      2800   2790

Output written to: fide_ratings.csv
Processed 2 IDs successfully, 0 errors
```

**CSV Output File**:
- **Filename**: `fide_ratings.csv` (persistent single file)
- **Location**: Current working directory
- **Format**: Standard CSV with proper escaping for special characters
- **Columns**: Date, FIDE ID, Player Name, Standard, Rapid, Blitz
- **Behavior**: Runs on the same day replace previous data for that day; runs on different dates preserve history

**Example CSV Content**:
```csv
Date,FIDE ID,Player Name,Standard,Rapid,Blitz
2025-01-27,1503014,Magnus Carlsen,2830,2780,2760
2025-01-27,2016192,Hikaru Nakamura,2758,2800,2790
2025-01-28,1503014,Magnus Carlsen,2831,2781,2761
2025-01-28,2016192,Hikaru Nakamura,2759,2801,2791
```

**Batch Processing Features**:
- Processes all valid FIDE IDs in the file
- Skips invalid IDs and continues processing
- Handles network errors gracefully (continues with remaining IDs)
- Appends results to single persistent CSV file (fide_ratings.csv)
- Preserves complete history of all rating retrievals across multiple runs
- Displays results in the console
- Provides summary of successful and failed processing

## Finding a FIDE ID

FIDE IDs can be found on:
- FIDE ratings website: https://ratings.fide.com
- Player profile pages
- Tournament results

FIDE IDs are typically 6-8 digit numbers (4-10 digits valid).

## Output Files

### CSV File Format

When using batch processing mode, the script appends data to a persistent CSV file with the following characteristics:

- **Filename**: `fide_ratings.csv` (always the same file)
- **Location**: Current working directory
- **Encoding**: UTF-8
- **Delimiter**: Comma
- **Header Row**: Yes (Date, FIDE ID, Player Name, Standard, Rapid, Blitz)
- **Special Characters**: Automatically escaped (commas in names are quoted)
- **Missing Ratings**: Empty cell for missing/unrated ratings
- **History**: New entries are appended on subsequent runs; all previous entries are preserved
- **Date Format**: ISO 8601 (YYYY-MM-DD) for each entry

The CSV file can be opened in:
- Microsoft Excel
- Google Sheets
- Any spreadsheet application
- Text editors

**Note**: If opening in Excel, you may need to specify UTF-8 encoding during import.

### File Behavior

The script manages the output CSV file intelligently to balance history preservation with fresh data:

**First Run**:
- Creates the output file (default: `fide_ratings.csv`) with headers and initial data

**Subsequent Runs**:
- If you run the script **on a different date**: New entries are appended, preserving all previous entries
- If you run the script **on the same day**: Previous data for that day is replaced with new data
- This ensures you always have the latest information for each date, while maintaining complete history across different dates

## Configuration

### Environment Variables

The script uses environment variables to configure input and output file paths:

- **`FIDE_INPUT_FILE`**: Path to the input file containing FIDE IDs (default: `fide_ids.txt`)
- **`FIDE_OUTPUT_FILE`**: Path to the output CSV file (default: `fide_ratings.csv`)

### Setting Environment Variables

#### Option 1: `.env` File (Recommended)

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your preferred paths:

```env
FIDE_INPUT_FILE=my_fide_ids.txt
FIDE_OUTPUT_FILE=my_ratings_history.csv
```

#### Option 2: Direct Environment Variables

Export variables before running the script:

```bash
export FIDE_INPUT_FILE=my_fide_ids.txt
export FIDE_OUTPUT_FILE=my_ratings_history.csv
python fide_scraper.py
```

#### Option 3: Command Line (Inline)

```bash
FIDE_INPUT_FILE=players.txt FIDE_OUTPUT_FILE=ratings.csv python fide_scraper.py
```

**Note**: If no environment variables are set, the script uses the default filenames: `fide_ids.txt` and `fide_ratings.csv`.

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

