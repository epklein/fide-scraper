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

# Load environment variables from .env file
load_dotenv()

# Constants and environment-based configuration
OUTPUT_FILENAME = os.getenv('FIDE_OUTPUT_FILE', 'fide_ratings.csv')
INPUT_FILENAME = os.getenv('FIDE_INPUT_FILE', 'fide_ids.txt')


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


def read_fide_ids_from_file(filepath: str) -> List[str]:
    """
    Read FIDE IDs from a text file, one per line.
    
    Args:
        filepath: Path to the input file
        
    Returns:
        List of FIDE ID strings (with empty lines skipped and whitespace stripped)
        
    Raises:
        FileNotFoundError: If file doesn't exist
        PermissionError: If file cannot be read
    """
    fide_ids = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    fide_ids.append(line)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {filepath}")
    except PermissionError:
        raise PermissionError(f"Permission denied: {filepath}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Unable to decode file {filepath}: {e}")
    
    return fide_ids


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


def process_batch(fide_ids: List[str]) -> Tuple[List[Dict], List[str]]:
    """
    Process a batch of FIDE IDs and extract player information.
    
    Args:
        fide_ids: List of FIDE ID strings to process
        
    Returns:
        Tuple of (results, errors) where:
        - results: List of dictionaries with player data
        - errors: List of error messages
    """
    results = []
    errors = []
    
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
            
            # Add to results
            results.append({
                'FIDE ID': fide_id,
                'Player Name': player_name,
                'Standard': standard_rating,
                'Rapid': rapid_rating,
                'Blitz': blitz_rating
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
            # Read FIDE IDs from configured input file
            fide_ids = read_fide_ids_from_file(INPUT_FILENAME)

            if not fide_ids:
                print("Error: Input file is empty or contains no valid FIDE IDs.", file=sys.stderr)
                sys.exit(2)

            print(f"Processing FIDE IDs from file: {INPUT_FILENAME}\n")

            # Process batch
            results, errors = process_batch(fide_ids)

            # Write CSV output
            write_csv_output(OUTPUT_FILENAME, results)

            # Display console output
            console_output = format_console_output(results)
            print(console_output)

            # Print errors to stderr
            if errors:
                for error in errors:
                    print(f"Error: {error}", file=sys.stderr)

            # Print summary
            success_count = len(results)
            error_count = len(errors)
            print(f"Output written to: {OUTPUT_FILENAME}")
            print(f"Processed {success_count} IDs successfully, {error_count} errors")

            # Exit code: 0 if at least one success, 1 if all failed
            if success_count > 0:
                sys.exit(0)
            else:
                sys.exit(1)

        except FileNotFoundError as e:
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
