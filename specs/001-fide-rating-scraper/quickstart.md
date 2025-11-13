# Quickstart Guide: FIDE Rating Scraper

**Date**: 2025-01-27  
**Feature**: FIDE Rating Scraper

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

## Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd /path/to/fide-scraper
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   Or install manually:
   ```bash
   pip install requests beautifulsoup4
   ```

## Usage

### Basic Usage

Run the script with a FIDE ID as an argument:

```bash
python fide_scraper.py 538026660
```

### Example Output

**Success**:
```
Standard: 2500
Rapid: 2450
```

**Player with missing rating**:
```
Standard: 2500
Rapid: Unrated
```

**Error - Invalid FIDE ID**:
```
Error: Invalid FIDE ID format. Must be numeric.
```

**Error - Player not found**:
```
Error: Player not found (FIDE ID: 99999999)
```

**Error - Network issue**:
```
Error: Unable to connect to FIDE website. Please check your internet connection.
```

## Finding a FIDE ID

FIDE IDs can be found on:
- FIDE ratings website: https://ratings.fide.com
- Player profile pages
- Tournament results

FIDE IDs are typically 6-8 digit numbers.

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

### "Player not found" error
- Verify the FIDE ID is correct
- Check that the player exists on the FIDE website
- Ensure the FIDE ID is numeric only

### Parsing errors
- FIDE website structure may have changed
- Check if the website is accessible in a browser
- Report the issue if the website structure has changed

## Next Steps

- Review the [specification](spec.md) for detailed requirements
- Check the [implementation plan](plan.md) for technical details
- See [data model](data-model.md) for data structures

