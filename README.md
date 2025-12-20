# FIDE Rating Scraper

A simple Python script that scrapes the FIDE website to retrieve current chess ratings for players by their FIDE ID.

**Note:** This project is my first experiment using [spec-kit](https://github.com/github/spec-kit) for structured, machine-readable specs. I've implemented it within the [Cursor](https://www.cursor.so/) editor.

I had to step in during the research phase to provide HTML examples that support the planning phase for proper implementation of the scraping code.

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- **Docker (optional)**: For containerized deployment

## Docker Deployment

Run the scraper in a Docker container without installing Python locally.

### Quick Start

```bash
# Build the Docker image
docker-compose build

# Run batch processing
docker-compose up
```

### Configuration

The Docker setup includes:
- **Input**: `players.csv` mounted from `./data/` on host
- **Output**: Results saved to `./output/fide_ratings.csv` on the host
- **SMTP**: Optional MailHog service for email testing
- **FIDE IDs API** (optional): Automatic player file augmentation from external API endpoint (see External API Integration section for details)

**Directory structure:**
```
.
├── data/
│   └── players.csv          # Input file (mount from host)
├── output/
│   └── fide_ratings.csv     # Output file (mount from host)
├── docker-compose.yaml
├── Dockerfile
└── ...
```

### Environment Setup

### Output Files

Results are written to `./output/fide_ratings.csv` on your host machine (mounted from container).

### Scheduled Execution with Cron

To run the scraper automatically every 2 hours (recommended for production):

**Step 1: Setup cron job**
```bash
./setup-cron.sh
```

This adds: `0 */2 * * * /app/run-scraper.sh`

**Step 2: Verify cron is configured**
```bash
crontab -l                    # View all scheduled jobs
tail -f logs/scraper.log      # View latest logs
```

**Step 3: Manage cron job**
```bash
crontab -e                # Edit or change schedule
crontab -r                # Remove cron job
```

**How it works:**
- Runs every 2 hours at the top of the hour (0, 2, 4, 6, ... 22)
- `run-scraper.sh` executes the Docker container once
- Logs saved to `logs/scraper.log`
- No container auto-restart needed

### Troubleshooting

**Issue**: "Permission denied" on output directory
- Solution: `docker-compose down && docker system prune -f`

**Issue**: Container exits immediately
- Solution: Check logs with `docker-compose logs fide-scraper`

**Issue**: Cron job not running
- Solution: `crontab -l` to verify job exists, check system mail for errors: `mail`
- Make sure your user has cron permission: `sudo usermod -a -G cron username`

## Installation (Local Setup)

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
   FIDE_PLAYERS_FILE=data/players.csv
   FIDE_OUTPUT_FILE=output/fide_ratings.csv
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

**Example** (`players.csv`):
```
FIDE ID,email
1503014,magnus@example.com
2016192,nakamura@example.com
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

The script will read from the file specified in `FIDE_PLAYERS_FILE` environment variable (default: `players.csv`) and write to `FIDE_OUTPUT_FILE` (default: `fide_ratings.csv`).

To customize file paths, create/edit a `.env` file in the project root:
```env
FIDE_PLAYERS_FILE=players.csv
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

- **Filename**: `FIDE_OUTPUT_FILE` (default: `fide_ratings.csv`)
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

## Rating Change Notifications (Email Alerts)

The scraper can automatically send email notifications to players when their ratings change. This feature requires a unified player configuration file.

### Setup

1. **Create `players.csv`** with player data and email preferences:
   ```csv
   FIDE ID,email
   1503014,magnus@example.com
   2016192,nakamura@example.com
   ```
   - **FIDE ID**: Player's FIDE ID (4-10 digits)
   - **email**: Player's email address (optional - leave empty to opt out of notifications)

2. **Configure environment variables** (in `.env`):
   ```env
   FIDE_PLAYERS_FILE=players.csv
   ADMIN_CC_EMAIL=admin@example.com
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

### Features

- **Automatic Notifications**: Emails sent when ratings change (any of Standard, Rapid, or Blitz)
- **Admin Monitoring**: All notifications CC'd to admin email for oversight
- **Opt-in by Email**: Players with empty email field don't receive notifications
- **All Players Tracked**: Ratings tracked for all players, notifications sent only to those with email configured
- **Graceful Error Handling**: Missing or misconfigured SMTP doesn't crash the scraper
- **Detailed Logging**: All email send attempts are logged for debugging

### Example

If player with FIDE ID 12345678 has rating change from 2440 → 2450 (Standard rating), they receive:

**Subject**: Your FIDE Rating Update - Alice Smith

**Body**:
```
Dear Alice,

Your FIDE ratings have been updated:

Standard Rating: 2440 → 2450 [CHANGED]
Rapid Rating: 2300 → 2300
Blitz Rating: 2100 → 2100

Last Updated: 2025-11-23
```

### Configuration

### Environment Variables

The script uses environment variables to configure input, output, and email settings:

#### Input/Output Files
- **`FIDE_PLAYERS_FILE`**: Path to unified player data file with emails (default: `players.csv`)
- **`FIDE_OUTPUT_FILE`**: Path to the output CSV file (default: `fide_ratings.csv`)

#### Email Notifications
- **`ADMIN_CC_EMAIL`**: Administrator email for CC'd copies (optional)
- **`SMTP_SERVER`**: SMTP server address (default: `localhost`)
- **`SMTP_PORT`**: SMTP server port (default: `587`)
- **`SMTP_USERNAME`**: SMTP authentication username (optional)
- **`SMTP_PASSWORD`**: SMTP authentication password (optional)

#### External API Integration
- **`FIDE_IDS_API_ENDPOINT`**: URL to fetch additional FIDE IDs from external API (optional)
  - Example: `https://eduklein.cloud/api/fide-ids/`
  - When set, the scraper augments the players file with IDs from this API before rating retrieval
  - If not set or API is unavailable, scraper proceeds with existing players file only
- **`API_TOKEN`**: Authentication token for external APIs (required if using FIDE_IDS_API_ENDPOINT or FIDE_RATINGS_API_ENDPOINT)
  - Format: Token will be sent as `Authorization: Token {API_TOKEN}`
- **`FIDE_RATINGS_API_ENDPOINT`**: URL to post rating updates to external service (optional)
  - Example: `https://eduklein.cloud/api/fide-ratings/`
  - When set, each rating update is posted to this endpoint after scraping

### Setting Environment Variables

#### Option 1: `.env` File (Recommended)

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your preferred paths:

```env
FIDE_PLAYER_FILE=my_players.csv
FIDE_OUTPUT_FILE=my_ratings_history.csv
```

#### Option 2: Direct Environment Variables

Export variables before running the script:

```bash
export FIDE_INPUT_FILE=my_players.csv
export FIDE_OUTPUT_FILE=my_ratings_history.csv
python fide_scraper.py
```

#### Option 3: Command Line (Inline)

```bash
FIDE_PLAYERS_FILE=my_players.csv FIDE_OUTPUT_FILE=my_ratings_history.csv python fide_scraper.py
```

**Note**: If no environment variables are set, the script uses the default filenames: `players.csv` and `fide_ratings.csv`.

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