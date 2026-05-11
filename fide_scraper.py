#!/usr/bin/env python3
"""
FIDE Rating Scraper

A simple script to retrieve chess player ratings from the FIDE website.
"""

import sys
import os
import requests
from bs4 import BeautifulSoup
from typing import Optional, Tuple, List, Dict
import csv
from datetime import date
import argparse
from dotenv import load_dotenv
import logging
from datetime import datetime
import calendar
from email_notifier import send_batch_notifications
from ratings_api import send_batch_api_updates

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper(), logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Constants and environment-based configuration
# Player data file (unified CSV with FIDE IDs and emails)
FIDE_PLAYERS_FILE = os.getenv('FIDE_PLAYERS_FILE', 'players.csv')
# Output ratings file (historical ratings)
OUTPUT_FILENAME = os.getenv('FIDE_OUTPUT_FILE', 'fide_ratings.csv')

def validate_fide_id(fide_id: str) -> bool:
    """
    Validate FIDE ID format.

    Args:
        fide_id: The FIDE ID to validate

    Returns:
        True if valid, False otherwise

    Rules:
        - Must be numeric
        - Must be between 4-10 digits
    """
    if not fide_id or not isinstance(fide_id, str):
        return False

    if not fide_id.isdigit():
        return False

    if len(fide_id) < 4 or len(fide_id) > 10:
        return False

    return True


def validate_email(email: str) -> bool:
    """
    Validate email address format using basic RFC pattern.

    Args:
        email: The email address to validate

    Returns:
        True if valid, False otherwise

    Rules:
        - Must match pattern: non-whitespace@non-whitespace.non-whitespace
        - Empty string is treated as valid (indicates opt-out)
        - Basic RFC pattern, not full RFC 5322 compliance
    """
    import re

    # Empty string is valid (opt-out from notifications)
    if not email or not isinstance(email, str):
        return True

    # If email is empty string, it's valid
    if email == "":
        return True

    # Basic RFC email pattern: something@something.something
    # Must have exactly one @ symbol, no spaces, and at least one dot after @
    pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return bool(re.match(pattern, email))


def _parse_english_month(month_abbr: str) -> int:
    """
    Parse English month abbreviation to month number (1-12).

    Args:
        month_abbr: English month abbreviation (Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec)

    Returns:
        Month number (1-12)

    Raises:
        ValueError: If month abbreviation is invalid

    Examples:
        >>> _parse_english_month("Nov")
        11
        >>> _parse_english_month("Feb")
        2
        >>> _parse_english_month("Oct")
        10
    """
    month_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }

    if month_abbr not in month_map:
        raise ValueError(f"Invalid English month abbreviation: {month_abbr}")
    
    return month_map[month_abbr]


def _calculate_month_end_date(year: int, month: int) -> date:
    """
    Calculate the last day of a given month/year.

    Args:
        year: Calendar year
        month: Month number (1-12)

    Returns:
        date object for the last day of the month

    Examples:
        >>> _calculate_month_end_date(2025, 11)
        datetime.date(2025, 11, 30)
        >>> _calculate_month_end_date(2024, 2)  # Leap year
        datetime.date(2024, 2, 29)
    """
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def _parse_month_year_string(month_year_str: str) -> Optional[date]:
    """
    Parse English Year-month string to ISO 8601 date (last day of month).

    Args:
        month_year_str: Year-Month string in format "Year-Month" (e.g., "2025-Nov", "2025-Oct")

    Returns:
        date object for the last day of the month, or None if parsing fails

    Examples:
        >>> _parse_month_year_string("2025-Nov")
        datetime.date(2025, 11, 30)
        >>> _parse_month_year_string("2025-Oct")
        datetime.date(2025, 10, 31)
        >>> _parse_month_year_string("Invalid/2025")
        None
    """
    if not month_year_str or not isinstance(month_year_str, str):
        return None

    try:
        # Split by '-'
        parts = month_year_str.strip().split('-')
        if len(parts) != 2:
            return None

        year_str = parts[0].strip()
        month_abbr = parts[1].strip()

        # Parse year
        year = int(year_str)

        # Parse month abbreviation
        month = _parse_english_month(month_abbr)

        # Calculate and return last day of month
        return _calculate_month_end_date(year, month)

    except (ValueError, IndexError):
        return None


def construct_fide_url(fide_id: str) -> str:
    """
    Construct FIDE profile URL from FIDE ID.
    
    Args:
        fide_id: Validated FIDE ID
        
    Returns:
        URL string for the FIDE profile page
    """
    return f"https://ratings.fide.com/profile/{fide_id}/chart"


def fetch_fide_profile(fide_id: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch FIDE profile HTML page.
    
    Args:
        fide_id: Validated FIDE ID
        timeout: Request timeout in seconds (default: 10)
        
    Returns:
        HTML content as string, or None on error
        
    Raises:
        ConnectionError: On network errors
        requests.Timeout: On timeout
        requests.HTTPError: On HTTP errors
    """
    url = construct_fide_url(fide_id)
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.ConnectionError as e:
        raise ConnectionError(f"Unable to connect to FIDE website: {e}")
    except requests.Timeout:
        raise requests.Timeout("Request to FIDE website timed out")
    except requests.HTTPError as e:
        if response.status_code == 404:
            return None
        raise requests.HTTPError(f"HTTP error {response.status_code}: {e}")


def _extract_all_history_rows(html: str) -> List[Dict]:
    """
    Extract all rating history rows from the FIDE rating history table.

    Extracts all data rows from the ContentPlaceHolder1_gdvRating table,
    returning one dict per row with month/year string and three ratings.

    Args:
        html: HTML content from FIDE profile page

    Returns:
        List of dicts with keys: month_year_str, standard, rapid, blitz
        Each rating value is an integer or None (for unrated)
        Returns empty list if table not found or parsing fails

    Examples:
        >>> extract_all_history_rows(html)
        [
            {'month_year_str': 'Nov/2025', 'standard': 1800, 'rapid': 1884, 'blitz': 1800},
            {'month_year_str': 'Out/2025', 'standard': 1800, 'rapid': 1914, 'blitz': 1800},
        ]
    """
    if not html:
        return []

    try:
        soup = BeautifulSoup(html, 'html.parser')

        # Find the table by ID
        table = soup.find('table', {'class': 'profile-table_calc'})

        if not table:
            return []

        # Find all rows (TR elements)
        rows = table.find_all('tr')

        # We need at least 2 rows (header + at least one data row)
        if len(rows) < 2:
            return []

        history_records = []

        # Process all data rows (skip header at index 0)
        for data_row in rows[1:]:
            # Get all cells (TD elements) in the data row
            cells = data_row.find_all('td')

            # We need at least 4 cells (Year-month + 3 ratings)
            if len(cells) < 4:
                continue

            try:
                # Extract Year-Month string (column 0)
                month_year_str = cells[0].get_text(strip=True)
                if not month_year_str:
                    continue

                # Extract ratings (columns 1, 3, 5)
                def extract_rating(cell) -> Optional[int]:
                    text = cell.get_text(strip=True)
                    if not text or text.lower() in ['not rated', 'unrated', '']:
                        return None
                    try:
                        rating = int(text)
                        # Validate rating is in reasonable range
                        if 0 <= rating <= 4000:
                            return rating
                    except ValueError:
                        pass
                    return None

                standard = extract_rating(cells[1])
                rapid = extract_rating(cells[3])
                blitz = extract_rating(cells[5])

                # Add record even if all ratings are None (month might be unrated)
                history_records.append({
                    'month_year_str': month_year_str,
                    'standard': standard,
                    'rapid': rapid,
                    'blitz': blitz
                })

            except (IndexError, ValueError):
                # Skip this row if extraction fails
                continue

        return history_records

    except Exception:
        return []


def _deduplicate_history_by_month(history_rows: List[Dict]) -> List[Dict]:
    """
    Deduplicate history rows by month, keeping the topmost (most recent) entry.

    When the same month appears multiple times, keeps the first occurrence
    (which appears at the top of the table and is most recent) and discards
    later occurrences.

    Args:
        history_rows: List of history row dicts from _extract_all_history_rows

    Returns:
        List of deduplicated history rows in original order

    Examples:
        >>> rows = [
        ...     {'month_year_str': '2025-Jun', 'standard': 1800, 'rapid': 1849, 'blitz': 1800},
        ...     {'month_year_str': '2025-May', 'standard': 1800, 'rapid': 1885, 'blitz': 1800},
        ...     {'month_year_str': '2025-Jun', 'standard': 1800, 'rapid': 1885, 'blitz': 1800},  # Duplicate
        ... ]
        >>> deduplicated = _deduplicate_history_by_month(rows)
        >>> len(deduplicated)
        2
        >>> deduplicated[0]['rapid']
        1849
    """
    seen_months = set()
    deduplicated = []

    for row in history_rows:
        month_year_str = row.get('month_year_str')

        if month_year_str not in seen_months:
            seen_months.add(month_year_str)
            deduplicated.append(row)

    return deduplicated


def _convert_raw_history_to_records(raw_history: List[Dict]) -> List[Dict]:
    """
    Convert raw history rows to final monthly records with parsed dates.

    Takes raw history from _extract_all_history_rows, deduplicates by month,
    and converts month/year strings to ISO 8601 dates (last day of month).

    Args:
        raw_history: List of raw history row dicts from _extract_all_history_rows

    Returns:
        List of final monthly record dicts with keys: date, standard, rapid, blitz
        Only includes records where month parsing succeeds (invalid months are skipped)

    Examples:
        >>> raw = [
        ...     {'month_year_str': '2025-Nov', 'standard': 1800, 'rapid': 1884, 'blitz': 1800},
        ...     {'month_year_str': '2025-Oct', 'standard': 1800, 'rapid': 1914, 'blitz': 1800},
        ... ]
        >>> records = _convert_raw_history_to_records(raw)
        >>> records[0]['date']
        datetime.date(2025, 11, 30)
    """
    # First deduplicate
    deduplicated = _deduplicate_history_by_month(raw_history)

    # Then convert each row
    final_records = []

    for row in deduplicated:
        month_year_str = row.get('month_year_str')

        # Parse month/year string to date
        month_date = _parse_month_year_string(month_year_str)

        # Skip if month parsing fails
        if month_date is None:
            continue

        # Build final record
        final_record = {
            'date': month_date,
            'standard': row.get('standard'),
            'rapid': row.get('rapid'),
            'blitz': row.get('blitz')
        }

        final_records.append(final_record)

    return final_records


def extract_rating_history(html: str) -> List[Dict]:
    """
    Extract complete rating history from FIDE player profile.

    Orchestrates the full history extraction pipeline:
    1. Extract all rows from the rating table
    2. Deduplicate by month (keeping topmost entry)
    3. Parse month/year strings to ISO 8601 dates
    4. Return final monthly records

    Args:
        html: HTML content from FIDE profile page
        
    Returns:
        List of monthly rating records with keys: date, standard, rapid, blitz
        Returns empty list if extraction fails or no data found

    Examples:
        >>> history = extract_rating_history(html)
        >>> len(history)
        7
        >>> history[0]['date']
        datetime.date(2025, 11, 30)
        >>> history[0]['rapid']
        1884
    """
    # Step 1: Extract all raw rows
    raw_history = _extract_all_history_rows(html)

    # Step 2-4: Convert to final records (deduplicates and parses dates)
    final_history = _convert_raw_history_to_records(raw_history)

    return final_history


def extract_player_name(html: str) -> Optional[str]:
    """
    Extract player name from FIDE profile HTML.
    
    Uses the documented selector from research.md: h1.player-title
    The player name is in the text content of the h1 element.
    
    Args:
        html: HTML content from FIDE profile page
        
    Returns:
        Player name as string, or None if not found
    """
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        player_title = soup.find('h1', class_='player-title')
        
        if player_title:
            name = player_title.get_text(strip=True)
            if name:
                return name
        
        # Fallback 1: Look for h1 tag without class check
        h1_tag = soup.find('h1')
        if h1_tag:
            name = h1_tag.get_text(strip=True)
            if name:
                return name
        
        # Fallback 2: Parse title tag
        if soup.title:
            title_text = soup.title.get_text(strip=True)
            # Remove common suffixes like " - FIDE Ratings" or " | FIDE"
            name = title_text.split(' - ')[0].split(' | ')[0].strip()
            if name:
                return name
        
        return None
    except Exception:
        return None


def load_player_data_from_csv(filepath: str) -> Dict[str, Dict[str, str]]:
    """
    Load player data from CSV file with FIDE IDs and optional emails.

    Parses a CSV file with headers "FIDE ID" and "email", validates each row,
    and returns a dictionary indexed by FIDE ID. Invalid entries are skipped
    with warnings logged to stderr.

    Args:
        filepath: Path to the CSV file (typically 'players.csv')

    Returns:
        Dictionary mapping FIDE ID to player data:
        {fide_id: {"email": "..."}, ...}
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If CSV headers are invalid or missing

    Side Effects:
        Logs warnings to stderr for invalid entries that are skipped
    """

    player_data = {}

    try:
        with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            # Validate headers
            if reader.fieldnames is None:
                raise ValueError(f"CSV file is empty: {filepath}")

            required_fields = {'FIDE ID', 'email'}
            if not required_fields.issubset(set(reader.fieldnames)):
                raise ValueError(
                    f"CSV file missing required headers. Expected: {required_fields}, "
                    f"Got: {set(reader.fieldnames)}"
                )

            # Process each row
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (skip header)
                fide_id = row.get('FIDE ID', '').strip() if row.get('FIDE ID') is not None else ''
                email = row.get('email', '').strip() if row.get('email') is not None else ''

                # Validate FIDE ID
                if not validate_fide_id(fide_id):
                    logger.warning(f"Line {row_num} - Invalid FIDE ID '{fide_id}' (skipped)")
                    continue

                # Validate email (empty is ok, but must be valid if provided)
                if not validate_email(email):
                    logger.warning(f"Line {row_num} - Invalid email '{email}' for FIDE ID {fide_id} (skipped)")
                    continue

                # Add to player data
                player_data[fide_id] = {"email": email}

    except FileNotFoundError:
        raise FileNotFoundError(f"Player data file not found: {filepath}")
    except PermissionError:
        raise PermissionError(f"Permission denied reading file: {filepath}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Unable to decode file {filepath} as UTF-8: {e}")

    return player_data


def fetch_fide_ids_from_api(api_endpoint: str, api_token: str) -> Optional[List[str]]:
    """
    Fetch FIDE IDs from external API endpoint.

    Sends a GET request to the configured API endpoint with token authentication.
    Parses the JSON response and extracts the fide_ids array as strings.
    Handles all errors gracefully - returns None if API is unavailable and logs details.

    Args:
        api_endpoint: Full URL to API endpoint (e.g., https://app.chesshub.cloud/api/fide-ids/)
        api_token: Authentication token for API (sent as Authorization: Token <token>)

    Returns:
        List of FIDE ID strings if successful, None if API unavailable/fails
    Side Effects:
        Logs all outcomes (success, errors, counts) using logging module
    """
    # Validate inputs
    if not api_endpoint or not api_endpoint.strip():
        logging.info("FIDE_IDS_API_ENDPOINT not configured")
        return None

    if not api_token or not api_token.strip():
        logging.info("API_TOKEN not configured for FIDE IDs API")
        return None

    try:
        # Prepare headers with token authentication
        headers = {
            "Authorization": f"Token {api_token}",
            "Accept": "application/json"
        }

        # Send GET request with 30 second timeout
        logging.info(f"Fetching FIDE IDs from API: {api_endpoint}")
        response = requests.get(api_endpoint, headers=headers, timeout=30)

        # Check HTTP status code
        if response.status_code == 401:
            logging.error("API authentication failed (401): Invalid or missing API token")
            return None
        elif response.status_code == 403:
            logging.error("API permission denied (403): Token does not have permission to access this endpoint")
            return None
        elif response.status_code == 404:
            logging.error(f"API endpoint not found (404): {api_endpoint}")
            return None
        elif response.status_code >= 500:
            logging.error(f"API server error ({response.status_code}): {response.text[:200]}")
            return None
        elif not response.ok:
            logging.error(f"API request failed with status {response.status_code}: {response.text[:200]}")
            return None

        # Parse JSON response
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError as e:
            logging.error(f"API response is not valid JSON: {e}")
            return None

        # Validate response structure
        if not isinstance(data, dict):
            logging.error(f"API response is not a JSON object: {type(data)}")
            return None

        if 'fide_ids' not in data:
            logging.error("API response missing 'fide_ids' field")
            return None

        fide_ids_data = data.get('fide_ids')
        if not isinstance(fide_ids_data, list):
            logging.error(f"API response 'fide_ids' is not an array: {type(fide_ids_data)}")
            return None

        # Validate that all IDs are strings
        fide_ids = []
        for fide_id in fide_ids_data:
            if isinstance(fide_id, str):
                fide_ids.append(fide_id)
            else:
                logging.warning(f"API response contains non-string FIDE ID: {fide_id} (type: {type(fide_id).__name__})")

        # Log success
        api_count = len(data.get('fide_ids', []))
        valid_count = len(fide_ids)
        logging.info(f"Successfully fetched {api_count} FIDE IDs from API ({valid_count} valid strings)")

        return fide_ids if fide_ids else None

    except requests.exceptions.Timeout:
        logging.error("API request timed out after 30 seconds")
        return None
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error to API endpoint: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching FIDE IDs from API: {e}")
        return None


def merge_player_ids(csv_ids: List[str], api_ids: List[str]) -> Tuple[List[str], List[str]]:
    """
    Merge FIDE IDs from CSV and API, with deduplication.

    Combines IDs from both sources using set operations to eliminate duplicates.
    Returns both the complete sorted list of unique IDs and the new IDs from API.

    Args:
        csv_ids: List of FIDE IDs from existing CSV file
        api_ids: List of FIDE IDs from API response

    Returns:
        Tuple of:
        - all_ids: Sorted list of all unique IDs (CSV union API)
        - new_ids: List of IDs only from API (API minus CSV)
    """
    csv_set = set(csv_ids) if csv_ids else set()
    api_set = set(api_ids) if api_ids else set()

    # Compute union and new IDs
    all_ids = sorted(list(csv_set | api_set))
    new_ids = sorted(list(api_set - csv_set))

    # Log merge summary
    csv_count = len(csv_set)
    api_count = len(api_set)
    total_count = len(all_ids)
    new_count = len(new_ids)

    logging.info(f"Merge summary: {csv_count} CSV IDs + {api_count} API IDs → {total_count} unique IDs, +{new_count} new")

    return all_ids, new_ids


def select_fide_ids_for_processing(
    mode: str,
    api_endpoint: str,
    api_token: str,
    csv_player_data: dict
) -> Tuple[List[str], List[str]]:
    """
    Select FIDE IDs for processing based on execution mode.

    In normal mode, processes all IDs from CSV (after merging with API).
    In quick mode, processes only new IDs returned by the API.

    Args:
        mode: Execution mode - 'normal' or 'quick'
        api_endpoint: Full URL to FIDE IDs API endpoint
        api_token: Authentication token for API
        csv_player_data: Dictionary of player data loaded from CSV

    Returns:
        Tuple of:
        - selected_ids: List of FIDE IDs to process
        - new_ids: List of new IDs to augment into the CSV

    Side Effects:
        - Logs mode selection and ID counts
        - Fetches from API if endpoint and token are configured
    """
    csv_ids = list(csv_player_data.keys()) if csv_player_data else []
    new_ids = []

    logging.info(f"Execution mode: {mode}")
    logging.info(f"Current CSV contains {len(csv_ids)} FIDE IDs")

    # Fetch API IDs if configured
    api_ids = None
    if api_endpoint and api_token:
        logging.info("Fetching FIDE IDs from API")
        api_ids = fetch_fide_ids_from_api(api_endpoint, api_token)
        if api_ids:
            # Compute new IDs (API minus CSV)
            csv_set = set(csv_ids)
            api_set = set(api_ids)
            new_ids = sorted(list(api_set - csv_set))
            logging.info(f"API returned {len(api_ids)} IDs, {len(new_ids)} are new")
        else:
            logging.warning("Failed to fetch FIDE IDs from API")
    else:
        logging.info("FIDE IDs API is not configured (optional feature)")

    # Select IDs based on mode
    if mode.lower() == 'quick':
        selected_ids = new_ids
        logging.info(f"Quick mode: selected {len(selected_ids)} new IDs for processing")
    else:  # normal mode
        # In normal mode, process all CSV IDs (which may have been augmented with new API IDs)
        if api_ids:
            # Merge CSV and API IDs
            all_ids, new_ids = merge_player_ids(csv_ids, api_ids)
            selected_ids = all_ids
        else:
            selected_ids = csv_ids
        logging.info(f"Normal mode: selected {len(selected_ids)} IDs for processing")

    return selected_ids, new_ids


def augment_players_file(csv_path: str, new_ids: List[str]) -> bool:
    """
    Append new FIDE IDs to existing CSV file.

    Reads existing player data and appends new rows for each new ID.
    Returns True if successful, False if any error occurred (with logging).

    Args:
        csv_path: Path to FIDE_PLAYERS_FILE CSV file
        new_ids: List of new IDs to append (from merge operation)

    Returns:
        True if successful, False if error occurred (logged)

    Side Effects:
        - Updates the CSV file with new rows
        - Logs all outcomes and errors
    """
    if not new_ids:
        logging.info("No new IDs to append to players file")
        return True

    try:
        # Read existing player data
        existing_players = {}
        try:
            existing_players = load_player_data_from_csv(csv_path)
        except FileNotFoundError:
            logging.info(f"Players file does not exist, will create: {csv_path}")

        # Merge in new IDs (skip if already exist)
        added_count = 0
        for new_id in new_ids:
            if new_id not in existing_players:
                existing_players[new_id] = {"email": ""}
                added_count += 1

        # Write updated file
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['FIDE ID', 'email']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write header
                writer.writeheader()

                # Write all player rows
                for fide_id, player_data in existing_players.items():
                    writer.writerow({'FIDE ID': fide_id, 'email': player_data.get('email', '')})

            logging.info(f"Updated players file: {csv_path} - added {added_count} new IDs")
            return True

        except IOError as e:
            logging.error(f"Error writing to players file {csv_path}: {e}")
            return False

    except Exception as e:
        logging.error(f"Unexpected error in augment_players_file: {e}")
        return False


def load_historical_ratings_by_player(filepath: str) -> Dict[str, List[Dict]]:
    """
    Load historical ratings from CSV file with monthly granularity.

    Reads the output CSV file (typically 'fide_ratings.csv') and creates a dictionary
    indexed by FIDE ID, with each entry containing ALL monthly rating records for that
    player. This is used for change detection to find new months.

    Args:
        filepath: Path to the historical ratings CSV file (typically 'fide_ratings.csv')

    Returns:
        Dictionary mapping FIDE ID to list of monthly rating records:
        {
            fide_id: [
                {"Date": "2025-11-30", "Player Name": "...", "Standard": ..., ...},
                {"Date": "2025-10-31", "Player Name": "...", "Standard": ..., ...},
                ...
            ],
            ...
        }
        Returns empty dict if file doesn't exist (first run)

    Side Effects:
        None - silently returns empty dict if file missing (expected on first run)
    """
    player_ratings = {}

    # Return empty dict if file doesn't exist (first run)
    if not os.path.exists(filepath):
        return player_ratings

    try:
        with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            # Validate headers
            if reader.fieldnames is None:
                return player_ratings

            required_fields = {'Date', 'FIDE ID', 'Player Name', 'Standard', 'Rapid', 'Blitz'}
            if not required_fields.issubset(set(reader.fieldnames)):
                # File exists but has wrong format, return empty
                return player_ratings

            # Read all records, grouping by FIDE ID
            for row in reader:
                fide_id = row.get('FIDE ID', '').strip()

                # Skip invalid FIDE IDs
                if not fide_id:
                    continue

                # Initialize list for this player if needed
                if fide_id not in player_ratings:
                    player_ratings[fide_id] = []

                # Add this month's record to the player's history
                month_record = {
                    "Date": row.get('Date', ''),
                    "Player Name": row.get('Player Name', ''),
                    "Standard": row.get('Standard', '') or None,
                    "Rapid": row.get('Rapid', '') or None,
                    "Blitz": row.get('Blitz', '') or None
                }

                player_ratings[fide_id].append(month_record)

    except (PermissionError, UnicodeDecodeError):
        # On read errors, silently return empty dict (same as file not found)
        return {}

    return player_ratings


def detect_new_months(
    fide_id: str,
    scraped_history: List[Dict],
    stored_history: Dict[str, List[Dict]]
) -> List[Dict]:
    """
    Detect new months in scraped history that don't exist in stored history.

    Compares complete scraped monthly history against stored monthly history to identify
    months that are new (exist in scraped but not in stored history). This is used for
    selective notifications - only notify when genuinely new months are found.

    Args:
        fide_id: Player's FIDE ID
        scraped_history: List of monthly records from extract_rating_history
                        Format: [{"date": date_obj, "standard": int, ...}, ...]
        stored_history: Dictionary indexed by FIDE ID with list of stored monthly records
                       (from load_historical_ratings_by_player)
                       Format: {fide_id: [{"Date": "2025-11-30", "Standard": "1800", ...}, ...], ...}

    Returns:
        List of new monthly records (format same as scraped_history records)
        Empty list if no new months detected

    Examples:
        # New month detected
        new_months = detect_new_months(
            "12345678",
            [{"date": date(2025, 11, 30), "standard": 1800, "rapid": 1884, "blitz": 1800}],
            {"12345678": [{"Date": "2025-10-31", "Standard": "1800", ...}]}
        )
        # Returns one new month record

        # No new months
        new_months = detect_new_months(
            "12345678",
            [{"date": date(2025, 11, 30), "standard": 1800, "rapid": 1884, "blitz": 1800}],
            {"12345678": [{"Date": "2025-11-30", "Standard": "1800", ...}]}
        )
        # Returns empty list
    """
    # Get stored month dates for this player
    stored_months = set()

    if fide_id in stored_history:
        for stored_record in stored_history[fide_id]:
            stored_date_str = stored_record.get("Date", "")
            if stored_date_str:
                stored_months.add(stored_date_str)

    # Find new months in scraped history
    new_months = []

    for scraped_record in scraped_history:
        scraped_date = scraped_record.get("date")
        if scraped_date is None:
            continue

        # Convert to ISO format for comparison
        scraped_date_str = scraped_date.isoformat() if isinstance(scraped_date, date) else str(scraped_date)

        # If this month is not in stored history, it's new
        if scraped_date_str not in stored_months:
            new_months.append(scraped_record)

    return new_months


def write_csv_output(filename: str, player_profiles: List[Dict]) -> None:
    """
    Write player profiles to CSV file with monthly granularity.

    Creates file with headers if it doesn't exist. For each player, writes one row per month
    from their rating_history. If a month already exists for a player, the existing row is
    replaced (UPDATE semantics).

    The Date column contains the last day of each month (e.g., 2025-11-30 for November 2025).

    Args:
        filename: Path to output CSV file
        player_profiles: List of dictionaries with keys: FIDE ID, Player Name, rating_history
                        where rating_history is a list of dicts with: date, Standard, Rapid, Blitz
    """
    fieldnames = ['Date', 'FIDE ID', 'Player Name', 'Standard', 'Rapid', 'Blitz']
    file_exists = os.path.exists(filename)

    # If file exists, read it and build a map of (FIDE ID, Date) -> row
    existing_rows_by_key = {}
    if file_exists:
        with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                fide_id = row.get('FIDE ID', '')
                date_str = row.get('Date', '')
                key = (fide_id, date_str)
                existing_rows_by_key[key] = row

    # Build new rows from profiles
    new_rows_by_key = {}

    for profile in player_profiles:
        fide_id = profile.get('FIDE ID', '')
        player_name = profile.get('Player Name', '')
        rating_history = profile.get('Rating History', [])

        # Write one row per month in history
        for month_record in rating_history:
            month_date = month_record.get('date')
            if month_date is None:
                continue

            date_str = month_date.isoformat() if isinstance(month_date, date) else str(month_date)

            key = (fide_id, date_str)

            # Convert None values to empty strings for CSV
            row = {
                'Date': date_str,
                'FIDE ID': fide_id,
                'Player Name': player_name,
                'Standard': month_record.get('standard', '') if month_record.get('standard') is not None else '',
                'Rapid': month_record.get('rapid', '') if month_record.get('rapid') is not None else '',
                'Blitz': month_record.get('blitz', '') if month_record.get('blitz') is not None else ''
            }

            new_rows_by_key[key] = row

    # Merge existing and new rows: new rows override existing ones
    merged_rows_by_key = {**existing_rows_by_key, **new_rows_by_key}

    # Write the file
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Write all merged rows (sorted for consistency)
        for key in sorted(merged_rows_by_key.keys()):
            writer.writerow(merged_rows_by_key[key])


def format_console_output(player_profiles: List[Dict]) -> str:
    """
    Format player profiles for console output in tabular format.

    Args:
        player_profiles: List of dictionaries with player data

    Returns:
        Formatted string for console display
    """
    if not player_profiles:
        return "No player data to display.\n"

    today = date.today().isoformat()

    # Header
    header = f"Date         FIDE ID       Player Name                              Standard  Rapid  Blitz"
    separator = "-" * len(header)

    lines = [header, separator]

    # Format each row
    for profile in player_profiles:
        date_str = today
        fide_id = profile.get('FIDE ID', '')
        player_name = profile.get('Player Name', '') or 'Unknown'
        standard = profile.get('Standard', '') if profile.get('Standard') is not None else 'Unrated'
        rapid = profile.get('Rapid', '') if profile.get('Rapid') is not None else 'Unrated'
        blitz = profile.get('Blitz', '') if profile.get('Blitz') is not None else 'Unrated'

        # Truncate long names
        if len(player_name) > 40:
            player_name = player_name[:37] + "..."

        # Format row with alignment
        row = f"{date_str:<12} {fide_id:<12} {player_name:<40} {str(standard):<9} {str(rapid):<6} {str(blitz)}"
        lines.append(row)

    return "\n".join(lines) + "\n"


def process_batch(fide_ids: List[str], historical_data: Dict[str, List[Dict]] = None) -> Tuple[List[Dict], List[str]]:
    """
    Process a batch of FIDE IDs and extract rating history with new month detection.

    Args:
        fide_ids: List of FIDE ID strings to process
        historical_data: Optional dictionary of historical ratings (for change detection).
                        If None, loaded from OUTPUT_FILENAME (fide_ratings.csv).
                        Format: {fide_id: [{"Date": "...", ...}, ...], ...}

    Returns:
        Tuple of (results, errors) where:
        - results: List of dictionaries with player data and rating history
        - errors: List of error messages

    Note:
        Each result dict includes:
        - 'rating_history': List of monthly rating records extracted from FIDE
        - 'new_months': List of months that are new (not in stored history)
    """
    results = []
    errors = []

    # Load historical data if not provided
    if historical_data is None:
        historical_data = load_historical_ratings_by_player(OUTPUT_FILENAME)

    for fide_id in fide_ids:
        # Validate FIDE ID format
        if not validate_fide_id(fide_id):
            errors.append(f"Invalid FIDE ID format: {fide_id} (skipped)")
            continue

        try:
            # Fetch profile
            html = fetch_fide_profile(fide_id)

            if html is None:
                errors.append(f"Player not found (FIDE ID: {fide_id}) (skipped)")
                continue

            # Extract player name
            player_name = extract_player_name(html) or ""

            # Extract complete rating history
            rating_history = extract_rating_history(html)

            # Check if we got at least one rating or player name
            if not rating_history and not player_name:
                errors.append(f"Unable to extract data from FIDE profile (FIDE ID: {fide_id}) (skipped)")
                continue

            # Detect new months in history
            new_months = detect_new_months(fide_id, rating_history, historical_data)

            # For current rating display, use the most recent month if available
            current_standard = None
            current_rapid = None
            current_blitz = None
            if rating_history:
                latest = rating_history[0]  # First item is most recent (newest month)
                current_standard = latest.get('standard')
                current_rapid = latest.get('rapid')
                current_blitz = latest.get('blitz')

            # Add to results
            results.append({
                'Date': date.today().isoformat(),
                'FIDE ID': fide_id,
                'Player Name': player_name,
                'Standard': current_standard,
                'Rapid': current_rapid,
                'Blitz': current_blitz,
                'Rating History': rating_history,
                'New Months': new_months
            })

        except ConnectionError as e:
            errors.append(f"Network error for FIDE ID {fide_id}: {e} (skipped)")
            continue
        except requests.Timeout:
            errors.append(f"Request timeout for FIDE ID {fide_id} (skipped)")
            continue
        except requests.HTTPError as e:
            errors.append(f"HTTP error for FIDE ID {fide_id}: {e} (skipped)")
            continue
        except Exception as e:
            errors.append(f"Unexpected error for FIDE ID {fide_id}: {e} (skipped)")
            continue

    return results, errors


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='FIDE Rating Scraper - Batch process chess player ratings from FIDE website',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Execution Modes:

  Normal Mode (default):
    Processes all FIDE IDs from players.csv file (including any new IDs from API).
    $ python fide_scraper.py

  Quick Mode (--quick):
    Processes only new FIDE IDs returned by the API (not in players.csv).
    Useful for incremental runs focused on recently added players.
    $ python fide_scraper.py --quick

Configuration:
  Reads FIDE IDs from the file specified in FIDE_PLAYERS_FILE environment variable
  (default: players.csv) and writes results to FIDE_OUTPUT_FILE (default: fide_ratings.csv).
  See .env.example for configuration options.
        """
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick mode: process only new FIDE IDs from API (skip existing players.csv IDs)'
    )

    args = parser.parse_args()
    execution_mode = 'quick' if args.quick else 'normal'

    # Batch processing mode
    try:
        start_time = datetime.now()
        logger.info(f"FIDE scraper started - mode: {execution_mode.upper()}, time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Load player data from CSV file (includes FIDE IDs and emails)
        logger.info(f"Loading player data from {FIDE_PLAYERS_FILE}")
        t0 = datetime.now()
        try:
            player_data = load_player_data_from_csv(FIDE_PLAYERS_FILE)
        except FileNotFoundError:
            # File doesn't exist yet; will be created if API adds IDs
            player_data = {}
        logger.info(f"Player data loaded: {len(player_data)} entries ({(datetime.now() - t0).total_seconds():.1f}s)")

        # Get API configuration
        api_endpoint = os.getenv('FIDE_IDS_API_ENDPOINT', '').strip()
        api_token = os.getenv('API_TOKEN', '').strip()

        # Select FIDE IDs based on execution mode
        logger.info("Selecting FIDE IDs for processing")
        t0 = datetime.now()
        fide_ids, new_ids = select_fide_ids_for_processing(
            execution_mode,
            api_endpoint,
            api_token,
            player_data
        )
        logger.info(f"FIDE ID selection done: {len(fide_ids)} selected, {len(new_ids)} new ({(datetime.now() - t0).total_seconds():.1f}s)")

        # Augment players file with new IDs if any were discovered
        if new_ids:
            success = augment_players_file(FIDE_PLAYERS_FILE, new_ids)
            if success:
                logging.info(f"Players file successfully augmented with {len(new_ids)} new FIDE IDs")
                # Reload player data after augmenting the file
                player_data = load_player_data_from_csv(FIDE_PLAYERS_FILE)
            else:
                logging.warning("Failed to augment players file; continuing with selected IDs")

        if not fide_ids:
            if execution_mode == 'quick':
                # In quick mode, no new IDs is valid (not an error)
                logger.info("Quick mode: no new FIDE IDs found from API")
                sys.exit(0)
            else:
                # In normal mode, empty list is an error
                logger.error("Player data file is empty or contains no valid players")
                sys.exit(2)

        logger.info(f"[{execution_mode.upper()}] Scraping FIDE ratings for {len(fide_ids)} players")

        # Process batch to fetch ratings
        t0 = datetime.now()
        results, errors = process_batch(fide_ids)
        logger.info(f"FIDE scraping done: {len(results)} succeeded, {len(errors)} failed ({(datetime.now() - t0).total_seconds():.1f}s)")

        # Write CSV output
        logger.info(f"Writing results to {OUTPUT_FILENAME}")
        t0 = datetime.now()
        write_csv_output(OUTPUT_FILENAME, results)
        logger.info(f"CSV output written ({(datetime.now() - t0).total_seconds():.1f}s)")

        # Send email notifications for players with rating changes
        logger.info("Sending email notifications...")
        t0 = datetime.now()
        email_sent, email_failed = send_batch_notifications(results, player_data)
        logger.info(f"Email notifications done: {email_sent} sent, {email_failed} failed ({(datetime.now() - t0).total_seconds():.1f}s)")

        # Post ratings updates to external API if configured
        logger.info("Posting rating updates to external API...")
        t0 = datetime.now()
        api_posted, api_failed = send_batch_api_updates(results)
        logger.info(f"API updates done: {api_posted} posted, {api_failed} failed ({(datetime.now() - t0).total_seconds():.1f}s)")

        # Display console output
        console_output = format_console_output(results)

        logger.debug("Latest FIDE Ratings: \n" + console_output)

        # Print summary
        success_count = len(results)
        error_count = len(errors)
        elapsed = (datetime.now() - start_time).total_seconds()

        logger.info(
            f"Run complete in {elapsed:.1f}s — "
            f"{success_count} players OK, {error_count} failed, "
            f"{email_sent} emails sent, {api_posted} API updates posted"
        )

        # Exit code: 0 if at least one success, 1 if all failed
        if success_count > 0:
            sys.exit(0)
        else:
            sys.exit(1)

    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        sys.exit(2)
    except ValueError as e:
        logger.error(f"Error: {e}")
        sys.exit(2)
    except PermissionError as e:
        logger.error(f"Error: {e}")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
