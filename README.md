# FIDE Rating Scraper

A Python script that scrapes the FIDE website to retrieve current chess ratings for players by their FIDE ID.

**Note:** This project is my first experiment using [spec-kit](https://github.com/github/spec-kit) for structured, machine-readable specs. I've implemented it within the [VSCode](https://code.visualstudio.com/) editors.

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

Results are written to `/data/fide_ratings.csv` on your host machine (mounted from container).
The FIDE events sync keeps its state in `/data/fide_events_state.csv` (set `FIDE_EVENTS_STATE_FILE`).

### Scheduled Execution with Cron

To run the scraper automatically every 2 hours:

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
   FIDE_PLAYERS_FILE=/data/players.csv
   FIDE_OUTPUT_FILE=/data/fide_ratings.csv
   ```

## Usage

The script operates in **Batch Processing mode**, processing multiple players from a file.

### Step 1: Prepare Input File

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

### Step 2: Run Batch Processing

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

### Execution Modes

The scraper supports two execution modes:

#### Normal Mode (Default)
Processes all FIDE IDs from the `players.csv` file (including any newly added by the API).

```bash
python fide_scraper.py
```

Use this for:
- Complete batch runs that process all players
- Initial setup and full dataset synchronization
- Comprehensive data updates

#### Quick Mode (--quick)
Processes only new FIDE IDs returned by the external API, skipping existing players already in `players.csv`. This is much faster if your player list is large but you only have a few new players to process.

```bash
python fide_scraper.py --quick
```

Quick mode will:
1. Fetch new FIDE IDs from the configured API endpoint
2. Compare them with existing IDs in `players.csv`
3. Process **only the new IDs** (not in the current file)
4. Add new IDs to `players.csv` for future tracking
5. Still send notifications and API updates for new players

**Use quick mode when:**
- Running frequent incremental updates (e.g., multiple times per day)
- You want to focus on recently added players
- Your player list is large but new additions are infrequent
- You want faster execution during peak hours

**Example workflow:**
- Run `python fide_scraper.py --quick` every 4 hours (quick incremental updates)
- Run `python fide_scraper.py` once daily during off-peak hours (full sync)

**Note:** Quick mode requires the FIDE IDs API to be configured (see External API Integration section). If the API is unavailable, quick mode exits gracefully with no players processed.

### Step 3: View Results

All output goes through Python's `logging` module (to stderr). The default log level is `INFO`, which shows milestones and summaries. Set `LOG_LEVEL=DEBUG` to also see per-player detail and the ratings table.

**Default output (`INFO`)**:
```
2026-05-05 10:00:01 - INFO - Execution mode: normal
2026-05-05 10:00:01 - INFO - Current CSV contains 2 FIDE IDs
2026-05-05 10:00:01 - INFO - [NORMAL] Processing 2 players
2026-05-05 10:00:03 - INFO - Sending email notifications...
2026-05-05 10:00:03 - INFO - Posting rating updates to external API...
2026-05-05 10:00:03 - INFO - Summary: processed 2 IDs successfully, 0 errors
2026-05-05 10:00:03 - INFO - Output written to: fide_ratings.csv
2026-05-05 10:00:03 - INFO - Email notifications: 1 sent, 0 failed
2026-05-05 10:00:03 - INFO - API updates: 5 posted, 0 failed
```

**Verbose output (`LOG_LEVEL=DEBUG`)**:
```
2026-05-05 10:00:01 - INFO - Execution mode: normal
...
2026-05-05 10:00:03 - DEBUG - Latest FIDE Ratings:
Date         FIDE ID      Player Name                              Standard  Rapid  Blitz
-----------------------------------------------------------------------------------------
2025-01-27   1503014      Magnus Carlsen                           2830      2780   2760
2025-01-27   2016192      Hikaru Nakamura                          2758      2800   2790

2026-05-05 10:00:03 - DEBUG - Email sent to Magnus Carlsen (magnus@example.com)
2026-05-05 10:00:03 - DEBUG - API updates posted for Magnus Carlsen (1503014) - 1 months
...
```

Run locally with debug output:
```bash
LOG_LEVEL=DEBUG python fide_scraper.py
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
Dear Alice Smith,

Your FIDE ratings have been updated:

Standard Rating: 2440 → 2450 [CHANGED]
Rapid Rating: 2300 → 2300
Blitz Rating: 2100 → 2100

Last Updated: 2025-11-23
```

### Configuration

### Environment Variables

The script uses environment variables to configure input, output, and email settings:

#### Logging
- **`LOG_LEVEL`**: Logging verbosity (default: `INFO`). Set to `DEBUG` to see per-player detail and the ratings table. Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`.

#### Input/Output Files
- **`FIDE_PLAYERS_FILE`**: Path to unified player data file with emails (default: `players.csv`)
- **`FIDE_OUTPUT_FILE`**: Path to the output CSV file (default: `fide_ratings.csv`)

#### Email Notifications
- **`ADMIN_CC_EMAIL`**: Administrator email for CC'd copies (optional)
- **`SMTP_SERVER`**: SMTP server address (default: `localhost`)
- **`SMTP_PORT`**: SMTP server port (default: `587`)
- **`SMTP_USERNAME`**: SMTP authentication username (optional, used for SMTP login)
- **`SMTP_PASSWORD`**: SMTP authentication password (optional)
- **`FROM_EMAIL`**: Email address to use as the sender (From field). If not set, falls back to SMTP_USERNAME or default (optional)

#### External API Integration
- **`FIDE_IDS_API_ENDPOINT`**: URL to fetch additional FIDE IDs from external API (optional)
  - Example: `https://chesshub.cloud/api/fide-ids/`
  - When set, the scraper augments the players file with IDs from this API before rating retrieval
  - If not set or API is unavailable, scraper proceeds with existing players file only
- **`API_TOKEN`**: Authentication token for external APIs (required if using FIDE_IDS_API_ENDPOINT or FIDE_RATINGS_API_ENDPOINT)
  - Format: Token will be sent as `Authorization: Token {API_TOKEN}`
- **`FIDE_RATINGS_API_ENDPOINT`**: URL to post rating updates to external service (optional)
  - Example: `https://chesshub.cloud/api/fide-ratings/`
  - When set, each rating update is posted to this endpoint after scraping
- **`FIDE_EVENTS_API_ENDPOINT`**: URL to post FIDE events to Chess Hub (optional)
  - Example: `https://chesshub.cloud/api/fide-events/`
  - When set together with `API_TOKEN`, the [FIDE events sync](#fide-events-sync) runs after the ratings
- **`FIDE_EVENTS_STATE_FILE`**: Local file recording the newest FIDE list each player was checked for (default: `fide_events_state.csv`; Docker: `/data/fide_events_state.csv`)
- **`FIDE_EVENTS_MAX_REQUESTS`**: Maximum FIDE requests the events sync makes per run (default: `300`)

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

## FIDE Events Sync

When `FIDE_EVENTS_API_ENDPOINT` and `API_TOKEN` are set, each run also sends to Chess Hub the tournaments the players took part in. It reads them from the AJAX endpoints behind the Calculations tab of the FIDE profile. FIDE has no endpoint for a player's whole history, so the events are read one rating period and one time control at a time. The sync fetches only what Chess Hub does not have yet:

1. It runs after the ratings: CSV, notifications and the ratings API. A failure in the sync never changes them or the exit code.
2. It reads `GET /api/fide-events/latest-periods/` once: the latest rating period Chess Hub stores for each player.
3. It considers a player once per FIDE list. The newest list is the newest month in the rating histories scraped in the same run. A player already checked for that list in `FIDE_EVENTS_STATE_FILE` costs no request.
4. It lists the player's periods (`a_calculations.phtml`). It fetches each period and time control from the stored period on, that period included, oldest first (`a_indv_calculation.php`). Each one is posted to `POST /api/fide-events/` right away.
5. The player is marked checked for the list only after all of their periods are posted.

**Cost.** In steady state: one listing request per player per monthly list, plus one request per new period and time control. The first sync of a player is a full backfill, typically a dozen or more requests.

**Backfill across runs.** The sync stops for the run when it reaches `FIDE_EVENTS_MAX_REQUESTS` or when FIDE throttles. Because periods are sent oldest first, Chess Hub's stored period tells the next run where to resume, with no gaps. Other errors (network, parsing, a rejected post) skip only that player, who is retried in the next run.

**Log.** Each run logs one summary line:

```
FIDE events sync: stop=completed, due=3, completed=3, failed=0, periods_posted=4, events_created=2, events_updated=0, fide_requests=7
```

`stop` is `completed`, `cap`, `throttled` or `skipped` (no rating history in the run, or `latest-periods/` unavailable).

**Resetting.** Deleting `FIDE_EVENTS_STATE_FILE`, or a player's row in it, makes the players due again in the next run. That costs one listing request each, plus a re-send of their latest stored period. It does not re-send older periods. Chess Hub's stored period still bounds what is fetched.

## Testing

Run the test suite:

```bash
pytest tests/
```

Run specific test file:

```bash
pytest tests/test_fide_scraper.py
```
