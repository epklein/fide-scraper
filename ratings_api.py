"""
External ratings API integration module for FIDE Rating Scraper.

Handles communication with external APIs for posting and retrieving rating data.
"""

import os
import sys
import logging
import requests
from typing import Optional, Dict, Tuple, List


def _load_api_config() -> Optional[Dict[str, str]]:
    """
    Load API configuration from environment variables.

    Returns:
        dict with 'endpoint' and 'token' keys if both are configured, None otherwise

    Side Effects:
        Logs warning if one but not both environment variables are set

    Environment variables:
        - FIDE_RATINGS_API_ENDPOINT: Full URL to API endpoint (e.g., https://eduklein.cloud/api/fide-ratings/)
        - API_TOKEN: Authentication token for the API
    """
    endpoint = os.getenv('FIDE_RATINGS_API_ENDPOINT', '').strip()
    token = os.getenv('API_TOKEN', '').strip()

    # Both must be set
    if not endpoint and not token:
        # Neither set - silent (optional feature)
        return None

    if endpoint and not token:
        logging.warning("FIDE_RATINGS_API_ENDPOINT is set but API_TOKEN is missing - API posting disabled")
        return None

    if token and not endpoint:
        logging.warning("API_TOKEN is set but FIDE_RATINGS_API_ENDPOINT is missing - API posting disabled")
        return None

    return {'endpoint': endpoint, 'token': token}


def _post_rating_to_api(
    profile: Dict,
    api_endpoint: str,
    api_token: str,
    timeout: int = 5,
    max_retries: int = 1
) -> bool:
    """
    POST a player rating update to external API.

    Args:
        profile: dict with keys {
            'Date', 'FIDE ID', 'Player Name',
            'Standard', 'Rapid', 'Blitz'
        }
        api_endpoint: Full URL to POST endpoint
        api_token: Bearer token for Authorization header
        timeout: Request timeout in seconds (default 5)
        max_retries: Number of retries on failure (default 1)

    Returns:
        bool: True if successful (200 OK), False if failed after retries

    Side Effects:
        - Logs success to logging.info()
        - Logs errors to logging.error() with full context
        - Does NOT raise exceptions on API failures

    Handles:
        - requests.Timeout: logged as error, retries once, returns False
        - requests.ConnectionError: logged as error, retries once, returns False
        - requests.HTTPError: logged with status code, returns False
        - Unexpected response format: logged as error, returns False
    """
    fide_id = profile.get('fide_id', 'unknown')

    # Transform profile dict to API request format
    rating_update = {
        'date': profile.get('date'),
        'fide_id': profile.get('fide_id'),
        'player_name': profile.get('player_name'),
        'standard_rating': profile.get('standard_rating'),
        'rapid_rating': profile.get('rapid_rating'),
        'blitz_rating': profile.get('blitz_rating')
    }

    headers = {
        'Authorization': f'Token {api_token}',
        'Content-Type': 'application/json'
    }

    attempt = 0
    while attempt <= max_retries:
        try:
            response = requests.post(
                api_endpoint,
                json=rating_update,
                headers=headers,
                timeout=timeout
            )

            # Check for success
            if response.status_code == 200:
                logging.info(f"API request successful for FIDE ID {fide_id}: {response.status_code} OK")
                return True
            else:
                # HTTP error (4xx, 5xx, etc.)
                try:
                    error_msg = response.json().get('error', 'Unknown error')
                except:
                    error_msg = response.text[:200]  # Truncate if too long

                logging.error(f"API returned {response.status_code} for FIDE ID {fide_id}: {error_msg}")

                # Don't retry 4xx errors (client error)
                if response.status_code >= 400 and response.status_code < 500:
                    return False

                # Retry on 5xx
                if attempt < max_retries and response.status_code >= 500:
                    attempt += 1
                    continue

                return False

        except requests.Timeout:
            logging.error(f"API request timeout for FIDE ID {fide_id} after {timeout} seconds (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                attempt += 1
                continue
            return False

        except requests.ConnectionError as e:
            logging.error(f"Failed to connect to API for FIDE ID {fide_id}: {str(e)} (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                attempt += 1
                continue
            return False

        except Exception as e:
            logging.error(f"Unexpected error posting to API for FIDE ID {fide_id}: {str(e)}")
            return False

    return False


def send_batch_api_updates(
    results: List[Dict]
) -> Tuple[int, int]:
    """
    Send rating updates to external API for profiles with new rating history months.

    Processes batch results and sends API updates for players who have detected
    new months in their rating history. Only profiles with new_months are posted to the API.

    Args:
        results: List of player results from process_batch() with 'new_months' key

    Returns:
        Tuple of (posted_count, failed_count) for logging and reporting

    Side Effects:
        Posts HTTP requests to external API for profiles with new months.
        Logs all attempts. Continues on errors.
    """
    # Load API configuration from environment variables
    api_config = _load_api_config()

    if not api_config:
        # API not configured, return early with no updates
        return 0, 0

    posted_count = 0
    failed_count = 0

    for profile in results:
        # Skip if no new months detected
        new_months = profile.get('New Months', [])
        if not new_months:
            continue

        fide_id = profile.get('FIDE ID', 'unknown')
        player_name = profile.get('Player Name', '')

        try:
            # Post each new month to API
            for month_record in new_months:
                # Build API payload for this month
                api_payload = {
                    'date': month_record.get('date').isoformat() if hasattr(month_record.get('date'), 'isoformat') else str(month_record.get('date')),
                    'fide_id': fide_id,
                    'player_name': player_name,
                    'standard_rating': month_record.get('standard'),
                    'rapid_rating': month_record.get('rapid'),
                    'blitz_rating': month_record.get('blitz')
                }

                # Post to API
                success = _post_rating_to_api(
                    api_payload,
                    api_config['endpoint'],
                    api_config['token']
                )

                if success:
                    posted_count += 1
                else:
                    failed_count += 1

            print(f"✓ API updates posted for {player_name} ({fide_id}) - {len(new_months)} months", file=sys.stderr)
        except Exception as e:
            failed_count += len(new_months)
            print(f"✗ Error posting API update for {fide_id}: {e}", file=sys.stderr)

    return posted_count, failed_count
