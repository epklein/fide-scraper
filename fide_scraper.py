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
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

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


def format_ratings_output(standard_rating: Optional[int], rapid_rating: Optional[int], blitz_rating: Optional[int] = None) -> str:
    """
    Format ratings for human-readable output.
    
    Args:
        standard_rating: Standard rating or None
        rapid_rating: Rapid rating or None
        blitz_rating: Blitz rating or None
        
    Returns:
        Formatted string for display
    """
    standard_str = str(standard_rating) if standard_rating is not None else "Unrated"
    rapid_str = str(rapid_rating) if rapid_rating is not None else "Unrated"
    blitz_str = str(blitz_rating) if blitz_rating is not None else "Unrated"
    
    return f"Standard: {standard_str}\nRapid: {rapid_str}\nBlitz: {blitz_str}"


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
    Returns a dictionary of only the changed ratings.

    Args:
        fide_id: Player's FIDE ID
        new_ratings: Latest ratings fetched (e.g., {"Standard": 2450, "Rapid": 2300, "Blitz": 2100})
        historical_data: Dictionary indexed by FIDE ID with latest record per player
                        (from load_historical_ratings_by_player)

    Returns:
        Dictionary of changed ratings: {rating_type: (old_value, new_value), ...}
        Empty dict {} if no changes detected or player is new (not in history)

    Examples:
        # Player with rating increase
        changes = detect_rating_changes(
            "12345678",
            {"Standard": 2450, "Rapid": 2300, "Blitz": 2100},
            {"12345678": {"Standard": "2440", "Rapid": "2300", "Blitz": "2100"}}
        )
        # Returns: {"Standard": (2440, 2450)}

        # New player (not in history)
        changes = detect_rating_changes(
            "99999999",
            {"Standard": 2450, "Rapid": 2300, "Blitz": 2100},
            {}
        )
        # Returns: {}
    """
    changes = {}

    # If player not in historical data, they're new - no changes to report
    if fide_id not in historical_data:
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


def compose_notification_email(
    player_name: str,
    fide_id: str,
    changes: Dict[str, Tuple[Optional[int], Optional[int]]],
    recipient_email: str,
    cc_email: Optional[str] = None
) -> Tuple[str, str]:
    """
    Compose a notification email about rating changes.

    Generates an email subject and body informing a player about their FIDE rating updates.
    The email includes their name, FIDE ID, and details of changed ratings.

    Args:
        player_name: Player's full name (e.g., "Alice Smith")
        fide_id: Player's FIDE ID (e.g., "12345678")
        changes: Dictionary of changed ratings {rating_type: (old_value, new_value), ...}
                Example: {"Standard": (2440, 2450), "Rapid": (2300, 2310)}
        recipient_email: Email address of the recipient (player)
        cc_email: Optional email address to CC (e.g., admin email). Not used in compose, for reference.

    Returns:
        Tuple of (subject, body) containing the email subject line and body content

    Examples:
        changes = {"Standard": (2440, 2450), "Rapid": (2300, 2310)}
        subject, body = compose_notification_email(
            "Alice Smith",
            "12345678",
            changes,
            "alice@example.com",
            "admin@example.com"
        )
        # subject: "Your FIDE Rating Update - Alice Smith"
        # body: Contains formatted rating changes with before/after values
    """
    # Compose subject
    subject = f"Your FIDE Rating Update - {player_name}"

    # Compose body
    lines = [
        "Dear " + player_name + ",",
        "",
        "Your FIDE ratings have been updated. Here are the changes:",
        ""
    ]

    # Add rating changes (sorted by rating type for consistency)
    for rating_type in sorted(changes.keys()):
        old_value, new_value = changes[rating_type]

        # Format old rating (handle None as "unrated")
        old_str = str(old_value) if old_value is not None else "unrated"
        # Format new rating (handle None as "unrated")
        new_str = str(new_value) if new_value is not None else "unrated"

        # Format the change line
        lines.append(f"{rating_type} Rating: {old_str} → {new_str}")

    # Add footer with FIDE profile URL
    lines.extend([
        "",
        "FIDE ID: " + fide_id,
        "Profile: " + construct_fide_url(fide_id),
        "",
        "Best regards,",
        "FIDE Rating Monitor",
        "Written by Eduardo Klein (https://eduklein.com.br/)"
    ])

    body = "\n".join(lines)

    return subject, body


def send_email_notification(
    recipient: str,
    cc: Optional[str],
    subject: str,
    body: str
) -> bool:
    """
    Send an email notification via SMTP.

    Sends an email with the given subject and body to the recipient, optionally CC'ing another address.
    Uses SMTP configuration from environment variables. All errors are logged and handled gracefully
    without raising exceptions.

    Args:
        recipient: Email address of the primary recipient (required)
        cc: Optional email address to CC on the message
        subject: Email subject line
        body: Email body content (plain text)

    Returns:
        True if email was sent successfully, False if any error occurred during sending

    Environment Variables (read from .env):
        SMTP_SERVER: SMTP server hostname (default: localhost)
        SMTP_PORT: SMTP server port (default: 587)
        SMTP_USERNAME: Optional username for SMTP authentication
        SMTP_PASSWORD: Optional password for SMTP authentication

    Examples:
        success = send_email_notification(
            "alice@example.com",
            "admin@example.com",
            "Your FIDE Rating Update - Alice Smith",
            "Dear Alice Smith,\nYour ratings have changed..."
        )
        if success:
            print("Email sent successfully")
        else:
            print("Failed to send email")
    """
    try:
        # Get SMTP configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME', '').strip() or None
        smtp_password = os.getenv('SMTP_PASSWORD', '').strip() or None

        # Validate recipient email
        if not recipient or not isinstance(recipient, str):
            logging.error(f"Invalid recipient email: {recipient}")
            return False

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_username if smtp_username else 'noreply@fide-monitor.local'
        msg['To'] = recipient

        # Add CC if provided
        if cc and isinstance(cc, str) and cc.strip():
            msg['Cc'] = cc.strip()

        # Attach plain text body
        msg.attach(MIMEText(body, 'plain'))

        # Build recipient list for sending (recipient + cc)
        recipient_list = [recipient]
        if cc and isinstance(cc, str) and cc.strip():
            recipient_list.append(cc.strip())

        # Connect to SMTP server and send
        try:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.starttls()

            # Authenticate if credentials provided
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)

            # Send email
            server.sendmail(
                msg['From'],
                recipient_list,
                msg.as_string()
            )

            server.quit()
            logging.info(f"Email sent successfully to {recipient}" + (f" (CC: {cc})" if cc else ""))
            return True

        except smtplib.SMTPAuthenticationError as e:
            logging.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logging.error(f"SMTP error occurred: {e}")
            return False
        except ConnectionError as e:
            logging.error(f"Connection error to SMTP server: {e}")
            return False
        except TimeoutError as e:
            logging.error(f"SMTP connection timeout: {e}")
            return False

    except (ValueError, TypeError) as e:
        logging.error(f"Invalid configuration or parameters: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error sending email: {e}")
        return False


def send_batch_notifications(
    results: List[Dict],
    player_data: Dict[str, Dict[str, str]],
    admin_cc_email: Optional[str] = None
) -> Tuple[int, int]:
    """
    Send email notifications to players with rating changes.

    Processes batch results and sends notification emails to players who:
    1. Have detected rating changes
    2. Have a valid email address configured
    3. Have not opted out (email field not empty)

    Args:
        results: List of player results from process_batch() with 'changes' key
        player_data: Dictionary of player data with emails {fide_id: {"email": "..."}, ...}
        admin_cc_email: Optional admin email to CC on all notifications (from ADMIN_CC_EMAIL env var)

    Returns:
        Tuple of (sent_count, failed_count) for logging and reporting

    Side Effects:
        Sends SMTP emails for players with changes. Logs all attempts. Continues on errors.
    """
    sent_count = 0
    failed_count = 0

    for result in results:
        fide_id = result.get('FIDE ID')
        player_name = result.get('Player Name', '')
        changes = result.get('changes', {})

        # Skip if no changes detected
        if not changes:
            continue

        # Get player email
        if fide_id not in player_data:
            continue

        player_email = player_data[fide_id].get('email', '').strip()

        # Skip if player has no email (opted out)
        if not player_email:
            continue

        try:
            # Compose email
            subject, body = compose_notification_email(
                player_name,
                fide_id,
                changes,
                player_email,
                admin_cc_email
            )

            # Send email
            success = send_email_notification(
                player_email,
                admin_cc_email,
                subject,
                body
            )

            if success:
                sent_count += 1
                print(f"✓ Email sent to {player_name} ({player_email})", file=sys.stderr)
            else:
                failed_count += 1
                print(f"✗ Failed to send email to {player_name} ({player_email})", file=sys.stderr)

        except Exception as e:
            failed_count += 1
            print(f"✗ Error sending email to {fide_id}: {e}", file=sys.stderr)

    return sent_count, failed_count


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


def get_fide_id_from_stdin() -> Optional[str]:
    """
    Get FIDE ID from standard input.
    
    Returns:
        FIDE ID string if provided, None otherwise
    """
    try:
        line = sys.stdin.readline().strip()
        return line if line else None
    except (EOFError, KeyboardInterrupt):
        return None


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='FIDE Rating Scraper - Retrieve chess player ratings from FIDE website',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Batch Processing Mode (default):
  Reads FIDE IDs from the file specified in FIDE_INPUT_FILE environment variable
  (default: fide_ids.txt) and writes results to FIDE_OUTPUT_FILE (default: fide_ratings.csv).

  Configure these paths by creating a .env file or setting environment variables.
  See .env.example for configuration options.

Single Player Mode:
  python fide_scraper.py <FIDE_ID>
  Retrieves rating for a single FIDE ID and prints to console.
        """
    )
    parser.add_argument(
        'fide_id',
        nargs='?',
        help='FIDE ID of the player to look up (for single player mode)'
    )

    args = parser.parse_args()

    # Batch processing mode (default)
    if not args.fide_id:
        try:
            # Load player data from CSV file (includes FIDE IDs and emails)
            player_data = load_player_data_from_csv(FIDE_PLAYERS_FILE)

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

            # Display console output
            console_output = format_console_output(results)

            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Latest FIDE Ratings:\n")

            print(console_output)
            print("")

            # Print errors to stderr
            if errors:
                for error in errors:
                    print(f"Error: {error}", file=sys.stderr)

            # Send email notifications for players with rating changes
            admin_cc_email = os.getenv('ADMIN_CC_EMAIL', '').strip() or None
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Sending email notifications...\n")
            email_sent, email_failed = send_batch_notifications(
                results,
                player_data,
                admin_cc_email
            )

            # Print summary
            success_count = len(results)
            error_count = len(errors)

            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Summary:")
            print(f"- Processed {success_count} IDs successfully, {error_count} errors")
            print(f"- Output written to: {OUTPUT_FILENAME}")
            if email_sent > 0 or email_failed > 0:
                print(f"- Email notifications: {email_sent} sent, {email_failed} failed")

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
    
    # Single FIDE ID mode (backward compatibility)
    fide_id = args.fide_id
    
    if not fide_id:
        # Try reading from stdin
        fide_id = get_fide_id_from_stdin()
    
    if not fide_id:
        print("Error: No FIDE ID provided. Usage: python fide_scraper.py <FIDE_ID> or python fide_scraper.py --file <FILE>", file=sys.stderr)
        sys.exit(2)
    
    # Validate FIDE ID
    if not validate_fide_id(fide_id):
        print(f"Error: Invalid FIDE ID format. Must be numeric (4-10 digits).", file=sys.stderr)
        sys.exit(2)
    
    # Fetch and parse ratings
    try:
        html = fetch_fide_profile(fide_id)
        
        if html is None:
            print(f"Error: Player not found (FIDE ID: {fide_id})", file=sys.stderr)
            sys.exit(1)
        
        standard_rating = extract_standard_rating(html)
        rapid_rating = extract_rapid_rating(html)
        blitz_rating = extract_blitz_rating(html)
        
        # Check if we got at least one rating
        if standard_rating is None and rapid_rating is None and blitz_rating is None:
            print(f"Error: Unable to extract ratings from FIDE profile (FIDE ID: {fide_id})", file=sys.stderr)
            sys.exit(1)
        
        # Output ratings
        output = format_ratings_output(standard_rating, rapid_rating, blitz_rating)
        print(output)
        sys.exit(0)
        
    except ConnectionError as e:
        print(f"Error: Unable to connect to FIDE website. Please check your internet connection.", file=sys.stderr)
        sys.exit(1)
    except requests.Timeout:
        print(f"Error: Request to FIDE website timed out.", file=sys.stderr)
        sys.exit(1)
    except requests.HTTPError as e:
        print(f"Error: Failed to retrieve ratings. {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: Unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
