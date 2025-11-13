#!/usr/bin/env python3
"""
FIDE Rating Scraper

A simple script to retrieve chess player ratings from the FIDE website.
"""

import sys
import requests
from bs4 import BeautifulSoup
from typing import Optional, Tuple


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
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Use documented selector from research.md
        # Note: FIDE website uses "standart" (typo) instead of "standard"
        rating_div = soup.select_one('div.profile-standart')
        
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
    if not html:
        return None
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Use documented selector from research.md
        rating_div = soup.select_one('div.profile-rapid')
        
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


def _find_rating_in_text(text: str, keywords: list) -> Optional[int]:
    """
    Find rating near specific keywords in text.
    
    Args:
        text: Full page text
        keywords: List of keywords to search for
        
    Returns:
        Rating as integer, or None if not found
    """
    import re
    for keyword in keywords:
        # Look for keyword followed by a number
        pattern = rf'{keyword}.*?(\d{{3,4}})'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rating = int(match.group(1))
            if 0 <= rating <= 3000:
                return rating
    return None


def format_ratings_output(standard_rating: Optional[int], rapid_rating: Optional[int]) -> str:
    """
    Format ratings for human-readable output.
    
    Args:
        standard_rating: Standard rating or None
        rapid_rating: Rapid rating or None
        
    Returns:
        Formatted string for display
    """
    standard_str = str(standard_rating) if standard_rating is not None else "Unrated"
    rapid_str = str(rapid_rating) if rapid_rating is not None else "Unrated"
    
    return f"Standard: {standard_str}\nRapid: {rapid_str}"


def get_fide_id_from_args() -> Optional[str]:
    """
    Get FIDE ID from command-line arguments.
    
    Returns:
        FIDE ID string if provided, None otherwise
    """
    if len(sys.argv) > 1:
        return sys.argv[1]
    return None


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
    # Get FIDE ID from command line or stdin
    fide_id = get_fide_id_from_args()
    
    if not fide_id:
        # Try reading from stdin
        fide_id = get_fide_id_from_stdin()
    
    if not fide_id:
        print("Error: No FIDE ID provided. Usage: python fide_scraper.py <FIDE_ID>", file=sys.stderr)
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
        
        # Check if we got at least one rating
        if standard_rating is None and rapid_rating is None:
            print(f"Error: Unable to extract ratings from FIDE profile (FIDE ID: {fide_id})", file=sys.stderr)
            sys.exit(1)
        
        # Output ratings
        output = format_ratings_output(standard_rating, rapid_rating)
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
