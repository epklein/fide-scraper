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
from email_notifier import send_batch_notifications
from ratings_api import send_batch_api_updates

# Load environment variables from .env file
load_dotenv()

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


def construct_fide_url(fide_id: str) -> str:
    """
    Construct FIDE profile URL from FIDE ID.
    
    Args:
        fide_id: Validated FIDE ID
        
    Returns:
        URL string for the FIDE profile page
    """
    return f"https://ratings.fide.com/profile/{fide_id}"


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


def _extract_rating_by_selector(html: str, selector: str) -> Optional[int]:
    """
    Extract rating from FIDE profile HTML using a CSS selector.
    
    Shared implementation for extracting ratings from FIDE profile pages.
    The rating value is in the first <p> tag within the selected div.
    
    Args:
        html: HTML content from FIDE profile page
        selector: CSS selector for the rating div (e.g., 'div.profile-standart')
        
    Returns:
        Rating as integer, or None if not found/unrated
    """
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        rating_div = soup.select_one(selector)
        
        if rating_div:
            # Get the first <p> tag which contains the rating
            p_tag = rating_div.find('p')
            if p_tag:
                rating_text = p_tag.get_text(strip=True)
                
                # Check if it says "Not rated"
                if rating_text.lower() in ['not rated', 'unrated']:
                    return None
                
                # Extract numeric rating
                rating = _extract_rating_from_text(rating_text)
                if rating is not None:
                    return rating
        
        return None
    except Exception:
        return None


def extract_standard_rating(html: str) -> Optional[int]:
    """
    Extract standard rating from FIDE profile HTML.
    
    Uses the documented selector from research.md: div.profile-standart
    The rating value is in the first <p> tag within this div.
    
    Args:
        html: HTML content from FIDE profile page
        
    Returns:
        Standard rating as integer, or None if not found/unrated
    """
    # Note: FIDE website uses "standart" (typo) instead of "standard"
    return _extract_rating_by_selector(html, 'div.profile-standart')


def extract_rapid_rating(html: str) -> Optional[int]:
    """
    Extract rapid rating from FIDE profile HTML.
    
    Uses the documented selector from research.md: div.profile-rapid
    The rating value is in the first <p> tag within this div.
    
    Args:
        html: HTML content from FIDE profile page
        
    Returns:
        Rapid rating as integer, or None if not found/unrated
    """
    return _extract_rating_by_selector(html, 'div.profile-rapid')


def extract_blitz_rating(html: str) -> Optional[int]:
    """
    Extract blitz rating from FIDE profile HTML.
    
    Uses the documented selector from research.md: div.profile-blitz
    The rating value is in the first <p> tag within this div.
    
    Args:
        html: HTML content from FIDE profile page
        
    Returns:
        Blitz rating as integer, or None if not found/unrated
    """
    return _extract_rating_by_selector(html, 'div.profile-blitz')


def _extract_rating_from_text(text: str) -> Optional[int]:
    """
    Extract numeric rating from text string.
    
    Args:
        text: Text that may contain a rating
        
    Returns:
        Rating as integer, or None if not found
    """
    import re
    # Look for 3-4 digit numbers (typical rating range)
    match = re.search(r'\b(\d{3,4})\b', text)
    if match:
        rating = int(match.group(1))
        # Validate rating is in reasonable range
        if 0 <= rating <= 3000:
            return rating
    return None


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
    import logging

    # Set up logging for warnings
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)

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
                    print(
                        f"Warning: Line {row_num} - Invalid FIDE ID '{fide_id}' (skipped)",
                        file=sys.stderr
                    )
                    continue

                # Validate email (empty is ok, but must be valid if provided)
                if not validate_email(email):
                    print(
                        f"Warning: Line {row_num} - Invalid email '{email}' for FIDE ID {fide_id} (skipped)",
                        file=sys.stderr
                    )
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
        api_endpoint: Full URL to API endpoint (e.g., https://eduklein.cloud/api/fide-ids/)
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


def load_historical_ratings_by_player(filepath: str) -> Dict[str, Dict[str, any]]:
    """
    Load historical ratings from CSV file and index by FIDE ID.

    Reads the output CSV file (typically 'fide_ratings.csv') and creates a dictionary
    indexed by FIDE ID, with each entry containing the most recent rating record
    for that player. This is used for change detection.

    Args:
        filepath: Path to the historical ratings CSV file (typically 'fide_ratings.csv')

    Returns:
        Dictionary mapping FIDE ID to latest player rating record:
        {fide_id: {"Date": "...", "Player Name": "...", "Standard": ..., ...}, ...}
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

            # Read all records, keeping only the latest for each FIDE ID
            for row in reader:
                fide_id = row.get('FIDE ID', '').strip()

                # Skip invalid FIDE IDs
                if not fide_id:
                    continue

                # Always keep the latest record (CSV is appended, so last one is latest)
                player_ratings[fide_id] = {
                    "Date": row.get('Date', ''),
                    "Player Name": row.get('Player Name', ''),
                    "Standard": row.get('Standard', '') or None,
                    "Rapid": row.get('Rapid', '') or None,
                    "Blitz": row.get('Blitz', '') or None
                }

    except (PermissionError, UnicodeDecodeError):
        # On read errors, silently return empty dict (same as file not found)
        return {}

    return player_ratings


def detect_rating_changes(
    fide_id: str,
    new_ratings: Dict[str, Optional[int]],
    historical_data: Dict[str, Dict]
) -> Dict[str, Tuple[Optional[int], Optional[int]]]:
    """
    Detect which player ratings have changed between runs.

    Compares current ratings against the most recent historical record for a player.
    Returns a dictionary of only the changed ratings. For new players (not in history),
    all scraped ratings are notified as changes.

    Args:
        fide_id: Player's FIDE ID
        new_ratings: Latest ratings fetched (e.g., {"Standard": 2450, "Rapid": 2300, "Blitz": 2100})
        historical_data: Dictionary indexed by FIDE ID with latest record per player
                        (from load_historical_ratings_by_player)

    Returns:
        Dictionary of changed ratings: {rating_type: (old_value, new_value), ...}
        For new players, all ratings are returned as changes with None as old_value.

    Examples:
        # Player with rating increase
        changes = detect_rating_changes(
            "12345678",
            {"Standard": 2450, "Rapid": 2300, "Blitz": 2100},
            {"12345678": {"Standard": "2440", "Rapid": "2300", "Blitz": "2100"}}
        )
        # Returns: {"Standard": (2440, 2450)}

        # New player (not in history) - all ratings are changes
        changes = detect_rating_changes(
            "99999999",
            {"Standard": 2450, "Rapid": 2300, "Blitz": 2100},
            {}
        )
        # Returns: {"Standard": (None, 2450), "Rapid": (None, 2300), "Blitz": (None, 2100)}
    """
    changes = {}

    # If player not in historical data, they're new - report all ratings as changes
    if fide_id not in historical_data:
        for rating_type in ["Standard", "Rapid", "Blitz"]:
            new_rating = new_ratings.get(rating_type)
            if new_rating is not None:
                changes[rating_type] = (None, new_rating)
        return changes

    historical_record = historical_data[fide_id]

    # Check each rating type
    for rating_type in ["Standard", "Rapid", "Blitz"]:
        new_rating = new_ratings.get(rating_type)

        # Get historical rating, converting empty string to None
        historical_rating_str = historical_record.get(rating_type)
        historical_rating = None
        if historical_rating_str and isinstance(historical_rating_str, str) and historical_rating_str.strip():
            try:
                historical_rating = int(historical_rating_str)
            except (ValueError, TypeError):
                historical_rating = None

        # Compare ratings (considering None as unrated)
        if new_rating != historical_rating:
            changes[rating_type] = (historical_rating, new_rating)

    return changes


def write_csv_output(filename: str, player_profiles: List[Dict]) -> None:
    """
    Write player profiles to CSV file, replacing same-day entries and preserving older entries.

    Creates file with headers if it doesn't exist. If file exists, removes any entries from today
    and appends new entries. This ensures that running the script multiple times on the same day
    replaces previous data while preserving history from previous dates.

    Each entry includes the current date as the first column.

    Args:
        filename: Path to output CSV file
        player_profiles: List of dictionaries with keys: FIDE ID, Player Name, Standard, Rapid, Blitz
    """
    fieldnames = ['Date', 'FIDE ID', 'Player Name', 'Standard', 'Rapid', 'Blitz']
    today = date.today().isoformat()
    file_exists = os.path.exists(filename)

    # If file exists, read it and filter out today's entries
    existing_rows = []
    if file_exists:
        with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Keep entries from previous dates, exclude today's entries
                if row.get('Date') != today:
                    existing_rows.append(row)

    # Write the file with preserved older entries and new entries for today
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Write preserved older entries
        for row in existing_rows:
            writer.writerow(row)

        # Write new entries for today
        for profile in player_profiles:
            # Convert None values to empty strings for CSV
            row = {
                'Date': today,
                'FIDE ID': profile.get('FIDE ID', ''),
                'Player Name': profile.get('Player Name', ''),
                'Standard': profile.get('Standard', '') if profile.get('Standard') is not None else '',
                'Rapid': profile.get('Rapid', '') if profile.get('Rapid') is not None else '',
                'Blitz': profile.get('Blitz', '') if profile.get('Blitz') is not None else ''
            }
            writer.writerow(row)


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
    header = f"Date         FIDE ID      Player Name                              Standard  Rapid  Blitz"
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


def process_batch(fide_ids: List[str], historical_data: Dict[str, Dict] = None) -> Tuple[List[Dict], List[str]]:
    """
    Process a batch of FIDE IDs and extract player information with change detection.

    Args:
        fide_ids: List of FIDE ID strings to process
        historical_data: Optional dictionary of historical ratings (for change detection).
                        If None, loaded from OUTPUT_FILENAME (fide_ratings.csv).
                        Format: {fide_id: {Date, Player Name, Standard, Rapid, Blitz}, ...}

    Returns:
        Tuple of (results, errors) where:
        - results: List of dictionaries with player data and detected changes
        - errors: List of error messages

    Note:
        Each result dict includes a 'changes' key with detected rating changes:
        {'changes': {'Standard': (old, new), ...}} for changed players,
        {'changes': {}} for unchanged players or new players.
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

            # Extract ratings
            standard_rating = extract_standard_rating(html)
            rapid_rating = extract_rapid_rating(html)
            blitz_rating = extract_blitz_rating(html)

            # Check if we got at least one rating or player name
            if standard_rating is None and rapid_rating is None and blitz_rating is None and not player_name:
                errors.append(f"Unable to extract data from FIDE profile (FIDE ID: {fide_id}) (skipped)")
                continue

            # Detect rating changes
            new_ratings = {
                'Standard': standard_rating,
                'Rapid': rapid_rating,
                'Blitz': blitz_rating
            }
            changes = detect_rating_changes(fide_id, new_ratings, historical_data)

            # Add to results
            results.append({
                'Date': date.today().isoformat(),
                'FIDE ID': fide_id,
                'Player Name': player_name,
                'Standard': standard_rating,
                'Rapid': rapid_rating,
                'Blitz': blitz_rating,
                'changes': changes
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
Batch Processing Mode:
  Reads FIDE IDs from the file specified in FIDE_PLAYERS_FILE environment variable
  (default: players.csv) and writes results to FIDE_OUTPUT_FILE (default: fide_ratings.csv).

  Configure these paths by creating a .env file or setting environment variables.
  See .env.example for configuration options.
        """
    )

    # Batch processing mode
    try:
        # Load player data from CSV file (includes FIDE IDs and emails)
        try:
            player_data = load_player_data_from_csv(FIDE_PLAYERS_FILE)
        except FileNotFoundError:
            # File doesn't exist yet; will be created if API adds IDs
            player_data = {}

        # Augment players file with FIDE IDs from API if configured
        api_endpoint = os.getenv('FIDE_IDS_API_ENDPOINT', '').strip()
        api_token = os.getenv('API_TOKEN', '').strip()

        if api_endpoint and api_token:
            logging.info("FIDE IDs API is configured, attempting to fetch and augment players file")
            api_ids = fetch_fide_ids_from_api(api_endpoint, api_token)
            if api_ids:
                csv_ids = list(player_data.keys())
                all_ids, new_ids = merge_player_ids(csv_ids, api_ids)
                success = augment_players_file(FIDE_PLAYERS_FILE, new_ids)
                if success:
                    logging.info(f"Players file successfully augmented with {len(new_ids)} new FIDE IDs from API")
                    # Reload player data after augmenting the file
                    player_data = load_player_data_from_csv(FIDE_PLAYERS_FILE)
                else:
                    logging.warning("Failed to augment players file; continuing with existing file")
            else:
                logging.warning("Failed to fetch FIDE IDs from API; continuing with existing players file")
        else:
            logging.info("FIDE IDs API is not configured (optional feature)")

        if not player_data:
            print("Error: Player data file is empty or contains no valid players.", file=sys.stderr)
            sys.exit(2)

        # Extract FIDE IDs from the loaded player data
        fide_ids = list(player_data.keys())

        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Processing {len(fide_ids)} players from file: {FIDE_PLAYERS_FILE}\n")

        # Process batch to fetch ratings
        results, errors = process_batch(fide_ids)

        # Write CSV output
        write_csv_output(OUTPUT_FILENAME, results)


        # Send email notifications for players with rating changes
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Sending email notifications...")
        email_sent, email_failed = send_batch_notifications(results, player_data)
        print("\n")

        # Post ratings updates to external API if configured
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Posting rating updates to external API...")
        api_posted, api_failed = send_batch_api_updates(results)
        print("\n")

        # Display console output
        console_output = format_console_output(results)

        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Latest FIDE Ratings:\n")

        print(console_output)
        print("\n")

        # Print summary
        success_count = len(results)
        error_count = len(errors)

        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Summary:")
        print(f"- Processed {success_count} IDs successfully, {error_count} errors")
        print(f"- Output written to: {OUTPUT_FILENAME}")
        if email_sent > 0 or email_failed > 0:
            print(f"- Email notifications: {email_sent} sent, {email_failed} failed")
        if api_posted > 0 or api_failed > 0:
            print(f"- API updates: {api_posted} posted, {api_failed} failed")

        # Exit code: 0 if at least one success, 1 if all failed
        if success_count > 0:
            sys.exit(0)
        else:
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except PermissionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: Unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
