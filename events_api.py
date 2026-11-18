"""
FIDE events API integration module for FIDE Rating Scraper.

Talks to the chess-wizard FIDE events endpoints:
- GET  /api/fide-events/latest-periods/  -> {fide_id: "YYYY-MM-01"}
- POST /api/fide-events/                 -> one player, one rating period, one time control
"""

import os
import logging
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class EventsAPIError(Exception):
    """Raised when a call to the Chess Hub FIDE events API fails."""


def load_events_api_config() -> Optional[Dict[str, str]]:
    """
    Load the FIDE events API configuration from environment variables.

    Returns:
        dict with 'endpoint', 'latest_periods_url' and 'token', or None when the
        sync is disabled (endpoint unset, or set without API_TOKEN).

    Environment variables:
        - FIDE_EVENTS_API_ENDPOINT: e.g. https://chesshub.cloud/api/fide-events/
        - API_TOKEN: Authentication token shared with the other APIs
    """
    endpoint = os.getenv('FIDE_EVENTS_API_ENDPOINT', '').strip()
    token = os.getenv('API_TOKEN', '').strip()

    if not endpoint:
        return None

    if not token:
        logger.warning("FIDE_EVENTS_API_ENDPOINT is set but API_TOKEN is missing - events posting disabled")
        return None

    base = endpoint if endpoint.endswith('/') else endpoint + '/'
    return {
        'endpoint': endpoint,
        'latest_periods_url': base + 'latest-periods/',
        'token': token,
    }


def _headers(token: str) -> Dict[str, str]:
    return {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}


def fetch_latest_periods(config: Dict[str, str], timeout: int = 15) -> Dict[str, date]:
    """
    Read the latest stored rating period of every FIDE player with events.

    Returns:
        {fide_id: date} - players missing from the map have no stored period

    Raises:
        EventsAPIError: On network errors, non-2xx responses or an invalid body
    """
    url = config['latest_periods_url']
    try:
        response = requests.get(url, headers=_headers(config['token']), timeout=timeout)
    except requests.RequestException as e:
        raise EventsAPIError(f"latest-periods request failed: {e}") from e

    if not 200 <= response.status_code < 300:
        raise EventsAPIError(
            f"latest-periods returned {response.status_code}: {(response.text or '')[:200]}"
        )

    try:
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("body is not an object")
        return {str(fide_id): date.fromisoformat(value) for fide_id, value in body.items()}
    except (ValueError, TypeError) as e:
        raise EventsAPIError(f"latest-periods returned an invalid body: {e}") from e


def _format_rating_change(value) -> Optional[str]:
    """Format a rating change as a two-decimal string ("-9.60"), or None."""
    if value is None:
        return None
    return str(Decimal(value).quantize(Decimal('0.01')))


def build_period_payload(
    fide_id: str,
    player_name: str,
    rating_period: date,
    time_control: str,
    events: List[Dict],
) -> Dict:
    """Build the POST /api/fide-events/ body for one period and time control."""
    return {
        'fide_id': fide_id,
        'player_name': player_name,
        'rating_period': rating_period.isoformat(),
        'time_control': time_control,
        'events': [
            {
                'fide_event_code': event['fide_event_code'],
                'name': event['name'],
                'city': event.get('city') or '',
                'country': event.get('country') or '',
                'start_date': event['start_date'].isoformat(),
                'end_date': event['end_date'].isoformat(),
                'games': event.get('games'),
                'rating_change': _format_rating_change(event.get('rating_change')),
            }
            for event in events
        ],
    }


def post_period_events(
    config: Dict[str, str],
    fide_id: str,
    player_name: str,
    rating_period: date,
    time_control: str,
    events: List[Dict],
    timeout: int = 15,
) -> Dict[str, int]:
    """
    POST one player's events of one rating period and time control.

    Returns:
        {'created': n, 'updated': n} as reported by Chess Hub (0 when absent)

    Raises:
        EventsAPIError: On network errors or any non-2xx response
    """
    payload = build_period_payload(fide_id, player_name, rating_period, time_control, events)
    try:
        response = requests.post(
            config['endpoint'], json=payload, headers=_headers(config['token']), timeout=timeout
        )
    except requests.RequestException as e:
        raise EventsAPIError(f"events POST failed for FIDE ID {fide_id}: {e}") from e

    if not 200 <= response.status_code < 300:
        raise EventsAPIError(
            f"events POST returned {response.status_code} for FIDE ID {fide_id} "
            f"({rating_period.isoformat()} {time_control}): {(response.text or '')[:200]}"
        )

    try:
        body = response.json()
    except ValueError:
        body = {}
    return {
        'created': int(body.get('created') or 0),
        'updated': int(body.get('updated') or 0),
    }
