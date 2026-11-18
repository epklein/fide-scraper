"""
FIDE event history sync.

Reads the events a player took part in from the AJAX endpoints behind the
FIDE profile's Calculations tab and sends them to Chess Hub, one rating period
and time control at a time (see events_api.py).

FIDE has no bulk endpoint, so the sync is incremental:
- Chess Hub's latest stored period per player (GET latest-periods/) bounds what
  is fetched: every listed period from that one on, oldest first.
- A local state file records the newest FIDE list each player was checked
  for, so a player is checked once per monthly list, not on every cron run.
"""

import csv
import logging
import os
import re
import tempfile
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

from events_api import EventsAPIError, fetch_latest_periods, load_events_api_config, post_period_events

logger = logging.getLogger(__name__)

FIDE_BASE_URL = 'https://ratings.fide.com'
LISTING_URL = FIDE_BASE_URL + '/a_calculations.phtml'
PERIOD_URL = FIDE_BASE_URL + '/a_indv_calculation.php'

# FIDE's rating type codes (`rating=` in the listing, `t=` in the period call)
TIME_CONTROL_BY_CODE = {0: 'standard', 1: 'rapid', 2: 'blitz'}
CODE_BY_TIME_CONTROL = {tc: code for code, tc in TIME_CONTROL_BY_CODE.items()}

DEFAULT_STATE_FILE = 'fide_events_state.csv'
DEFAULT_MAX_REQUESTS = 300

# Chess Hub field limits, so an overlong value never turns into a permanent 400
NAME_MAX_LENGTH = 255
CITY_MAX_LENGTH = 100

_VIEW_LINK_RE = re.compile(
    r'calculations\.phtml\?id_number=\d+&(?:amp;)?period=(\d{4}-\d{2}-\d{2})&(?:amp;)?rating=([012])'
)
_EVENT_LINK_RE = re.compile(r'report\.phtml\?event=(\d+)')
_COUNTRY_RE = re.compile(r'[A-Z]{3}')

Pair = Tuple[date, str]


class EventsRateLimited(Exception):
    """FIDE answered with its empty throttle body."""


class RequestCapReached(Exception):
    """The per-run FIDE request budget is used up."""


class EventsParseError(Exception):
    """A FIDE response did not have the expected markup."""


def _is_throttle_body(text: str) -> bool:
    """FIDE throttles with HTTP 200 and an empty or BOM-only body (as fide_scraper does)."""
    return not text.replace('﻿', '').strip()


class FIDEEventsClient:
    """Paced FIDE requests with the AJAX header and a per-run request budget."""

    def __init__(self, delay_seconds: float, max_requests: int, timeout: int = 15):
        self.delay_seconds = delay_seconds
        self.max_requests = max_requests
        self.timeout = timeout
        self.requests_used = 0

    def _request(self, method: str, url: str, **kwargs) -> str:
        if self.requests_used >= self.max_requests:
            raise RequestCapReached(f"FIDE event request cap of {self.max_requests} reached")
        time.sleep(self.delay_seconds)
        self.requests_used += 1
        response = requests.request(
            method, url,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        if _is_throttle_body(response.text):
            raise EventsRateLimited(f"FIDE returned an empty response for {url} (rate limited)")
        return response.text

    def get(self, url: str, params: Dict) -> str:
        return self._request('GET', url, params=params)

    def post(self, url: str, data: Dict) -> str:
        return self._request('POST', url, data=data)


# --- Parsing -----------------------------------------------------------------

def _pair_sort_key(pair: Pair):
    period, time_control = pair
    return period, CODE_BY_TIME_CONTROL[time_control]


def parse_period_listing(html: str) -> Tuple[List[Pair], bool]:
    """
    Parse a Calculations listing (first page or the `action=2` response).

    Returns:
        (pairs, has_more): the (period, time control) pairs with a View link,
        sorted oldest first, and whether the "Check more periods" button is shown
    """
    pairs = {
        (date.fromisoformat(period), TIME_CONTROL_BY_CODE[int(code)])
        for period, code in _VIEW_LINK_RE.findall(html)
    }
    return sorted(pairs, key=_pair_sort_key), 'Check more periods' in html


def _cell_texts(row) -> List[str]:
    return [cell.get_text(strip=True) for cell in row.find_all('td')]


def _parse_summary(table) -> Tuple[Optional[int], Optional[Decimal]]:
    """Read games (`n`) and rating change (`K*chg`) from a calc_table's summary row, by header label."""
    rows = table.find_all('tr')
    if len(rows) < 2:
        raise EventsParseError("calc_table has no summary row")
    header, summary = _cell_texts(rows[0]), _cell_texts(rows[1])

    def value(label: str) -> Optional[str]:
        if label not in header:
            return None
        index = header.index(label)
        return summary[index] if index < len(summary) and summary[index] else None

    games_text = value('n')
    change_text = value('K*chg')
    try:
        games = int(games_text) if games_text is not None else None
        rating_change = Decimal(change_text) if change_text is not None else None
    except (ValueError, InvalidOperation) as e:
        raise EventsParseError(f"invalid summary values: {e}") from e
    return games, rating_change


def _split_location(location: str) -> Tuple[str, str]:
    """'Canoas RS BRA' -> ('Canoas RS', 'BRA'); the country is the last token when it is a 3-letter code."""
    tokens = location.split()
    if tokens and _COUNTRY_RE.fullmatch(tokens[-1]):
        return ' '.join(tokens[:-1]), tokens[-1]
    return ' '.join(tokens), ''


def _parse_fide_date(text: str) -> Optional[date]:
    """'2001-02-09' -> date; FIDE's '0000-00-00' or anything invalid -> None."""
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


def _event_dates(start: Optional[date], end: Optional[date]) -> Optional[Tuple[date, date]]:
    """
    Repair the dates FIDE has for old events, so Chess Hub accepts them (end >= start).

    - A missing end ('0000-00-00') becomes the start, and a missing start the end.
    - An end a century before the start (FIDE has 2001-12-17 .. 1901-12-23 for
      events up to ~2006) is moved forward 100 years when that lands within a
      year of the start; any other end before the start becomes the start.

    Returns None when neither date is valid.
    """
    if start is None and end is None:
        return None
    if start is None:
        return end, end
    if end is None:
        return start, start
    if end < start:
        try:
            shifted = end.replace(year=end.year + 100)
        except ValueError:  # Feb 29 in a non-leap target year
            shifted = None
        if shifted is not None and start <= shifted <= start + timedelta(days=366):
            return start, shifted
        return start, start
    return start, end


def parse_period_events(html: str) -> List[Dict]:
    """
    Parse the events of one rating period and time control (a_indv_calculation.php).

    Returns:
        One dict per event, in page order, with fide_event_code, name, city,
        country, start_date, end_date, games and rating_change (None when the
        player was unrated in that list). [] for "No records found." and for
        FIDE's "Invalid data" (old periods listed without calculation details).

    Raises:
        EventsParseError: When the response has neither events nor one of those messages
    """
    soup = BeautifulSoup(html, 'html.parser')
    links = soup.find_all('a', href=_EVENT_LINK_RE)
    if not links:
        if 'No records' in html or 'Invalid data' in html:
            return []
        raise EventsParseError("no event found in the period response")

    events = []
    for link in links:
        code = _EVENT_LINK_RE.search(link['href']).group(1)
        name = ' '.join(link.get_text(' ').split())
        block = link.find_parent('div', class_='default_div_full')
        line = block.find('div', class_='rtng_line02') if block else None
        table = block.find_next('table', class_='calc_table') if block else None
        if line is None or table is None:
            raise EventsParseError(f"event {code} has no location line or calc_table")

        date_spans = line.find_all('span', class_='dates_span')
        raw_dates = [span.get_text(strip=True) for span in date_spans]
        dates = _event_dates(*(_parse_fide_date(text) for text in raw_dates)) if len(raw_dates) == 2 else None
        if dates is None:
            logger.warning(f"FIDE event {code} ({name}) has no valid start and end dates {raw_dates} - skipped")
            continue
        start_date, end_date = dates
        if [start_date.isoformat(), end_date.isoformat()] != raw_dates:
            logger.debug(f"FIDE event {code} ({name}): dates {raw_dates} repaired to {start_date} .. {end_date}")
        for span in date_spans:
            span.extract()
        city, country = _split_location(line.get_text(' '))

        games, rating_change = _parse_summary(table)
        events.append({
            'fide_event_code': code,
            'name': name[:NAME_MAX_LENGTH],
            'city': city[:CITY_MAX_LENGTH],
            'country': country,
            'start_date': start_date,
            'end_date': end_date,
            'games': games,
            'rating_change': rating_change,
        })
    return events


# --- Fetching ----------------------------------------------------------------

def fetch_period_listing(client: FIDEEventsClient, fide_id: str, stored_period: Optional[date]) -> List[Pair]:
    """
    List a player's (period, time control) pairs, oldest first.

    The older periods (`action=2`) are requested only when the first page has
    the "Check more periods" button and the stored period is missing or older
    than the first page's oldest period: older rows exist only there.
    """
    pairs, has_more = parse_period_listing(client.get(LISTING_URL, {'event': fide_id}))
    first_page_oldest = pairs[0][0] if pairs else None
    if has_more and (stored_period is None or first_page_oldest is None or stored_period < first_page_oldest):
        more, _ = parse_period_listing(client.post(LISTING_URL, {'action': '2', 'plr_id': fide_id}))
        pairs = sorted(set(pairs) | set(more), key=_pair_sort_key)
    return pairs


def fetch_period_events(client: FIDEEventsClient, fide_id: str, period: date, time_control: str) -> List[Dict]:
    """Fetch and parse one player's events of one rating period and time control."""
    html = client.get(PERIOD_URL, {
        'id_number': fide_id,
        'rating_period': period.isoformat(),
        't': CODE_BY_TIME_CONTROL[time_control],
    })
    return parse_period_events(html)


# --- Selection and state -----------------------------------------------------

def pending_pairs(listing: Iterable[Pair], stored_period: Optional[date]) -> List[Pair]:
    """Pairs at or after the stored period (all of them when there is none), oldest first."""
    pairs = [pair for pair in listing if stored_period is None or pair[0] >= stored_period]
    return sorted(pairs, key=_pair_sort_key)


def published_list(results: List[Dict]) -> Optional[date]:
    """The newest FIDE list month in this run's rating histories, or None."""
    months = [
        record['date']
        for result in results
        for record in (result.get('Rating History') or [])
        if record.get('date')
    ]
    return max(months) if months else None


def load_state(path: str) -> Dict[str, date]:
    """Read {fide_id: checked_period}. A missing or unreadable file is empty."""
    state = {}
    try:
        with open(path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                try:
                    state[row['fide_id'].strip()] = date.fromisoformat(row['checked_period'].strip())
                except (KeyError, AttributeError, ValueError):
                    continue
    except FileNotFoundError:
        return {}
    except (OSError, csv.Error) as e:
        logger.warning(f"Unable to read FIDE events state file {path}: {e} - treating it as empty")
        return {}
    return state


def save_state(path: str, state: Dict[str, date]) -> None:
    """Write the state through a temp file in the same directory and an atomic rename."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(prefix='.fide_events_state.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['fide_id', 'checked_period'])
            for fide_id in sorted(state):
                writer.writerow([fide_id, state[fide_id].isoformat()])
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _max_requests_from_env() -> int:
    raw = os.getenv('FIDE_EVENTS_MAX_REQUESTS', '').strip()
    if not raw:
        return DEFAULT_MAX_REQUESTS
    try:
        return max(0, int(raw))
    except ValueError:
        logger.warning(f"Invalid FIDE_EVENTS_MAX_REQUESTS={raw!r} - using {DEFAULT_MAX_REQUESTS}")
        return DEFAULT_MAX_REQUESTS


# --- Orchestration -----------------------------------------------------------

def _log_summary(summary: Dict) -> None:
    logger.info(
        "FIDE events sync: stop={stop_reason}, due={due}, completed={completed}, failed={failed}, "
        "periods_posted={periods_posted}, events_created={created}, events_updated={updated}, "
        "fide_requests={requests}".format(**summary)
    )


def sync_events(
    fide_ids: List[str],
    results: List[Dict],
    delay_seconds: float,
    state_path: Optional[str] = None,
    max_requests: Optional[int] = None,
) -> Optional[Dict]:
    """
    Send the FIDE events of the run's players to Chess Hub, incrementally.

    Args:
        fide_ids: IDs selected for this run, in order
        results: This run's rating results (for the published list and player names)
        delay_seconds: Wait before every FIDE request (REQUEST_DELAY_SECONDS)
        state_path: Local checked-list file (default: FIDE_EVENTS_STATE_FILE)
        max_requests: Per-run FIDE request cap (default: FIDE_EVENTS_MAX_REQUESTS)

    Returns:
        The summary dict, or None when the sync is not configured
    """
    config = load_events_api_config()
    if config is None:
        logger.debug("FIDE events sync disabled (FIDE_EVENTS_API_ENDPOINT not configured)")
        return None

    if state_path is None:
        state_path = os.getenv('FIDE_EVENTS_STATE_FILE', '').strip() or DEFAULT_STATE_FILE
    if max_requests is None:
        max_requests = _max_requests_from_env()

    client = FIDEEventsClient(delay_seconds, max_requests)
    summary = {
        'stop_reason': 'completed', 'due': 0, 'completed': 0, 'failed': 0,
        'periods_posted': 0, 'created': 0, 'updated': 0, 'requests': 0,
    }

    published = published_list(results)
    if published is None:
        logger.info("FIDE events sync skipped: no rating history parsed in this run")
        summary['stop_reason'] = 'skipped'
        _log_summary(summary)
        return summary

    try:
        latest_periods = fetch_latest_periods(config)
    except EventsAPIError as e:
        logger.warning(f"FIDE events sync skipped: {e}")
        summary['stop_reason'] = 'skipped'
        _log_summary(summary)
        return summary

    state = load_state(state_path)
    names = {result.get('FIDE ID'): result.get('Player Name') or '' for result in results}

    due_ids = []
    for fide_id in fide_ids:
        checked = state.get(fide_id)
        if checked is not None and checked >= published:
            continue
        if fide_id not in names:
            logger.debug(f"FIDE events: no profile result for FIDE ID {fide_id} in this run - skipped")
            continue
        due_ids.append(fide_id)

    logger.info(
        f"FIDE events sync started: {len(due_ids)} of {len(fide_ids)} players due for the "
        f"{published.strftime('%Y-%m')} list, {len(latest_periods)} with stored events in Chess Hub, "
        f"cap {max_requests} FIDE requests"
    )

    for position, fide_id in enumerate(due_ids, start=1):
        summary['due'] += 1
        stored = latest_periods.get(fide_id)
        requests_before = client.requests_used
        player = {'periods': 0, 'created': 0, 'updated': 0}
        where = 'listing'
        try:
            listing = fetch_period_listing(client, fide_id, stored)
            pending = pending_pairs(listing, stored)
            for period, time_control in pending:
                where = f"{period.strftime('%Y-%m')} {time_control}"
                events = fetch_period_events(client, fide_id, period, time_control)
                if events:
                    counts = post_period_events(
                        config, fide_id, names[fide_id], period, time_control, events)
                    player['periods'] += 1
                    player['created'] += counts['created']
                    player['updated'] += counts['updated']
            state[fide_id] = published
            save_state(state_path, state)
            summary['completed'] += 1
            logger.info(
                f"FIDE events [{position}/{len(due_ids)}] FIDE ID {fide_id}: "
                f"{len(pending)} pending since {stored.strftime('%Y-%m') if stored else 'start'}, "
                f"{player['periods']} posted, {player['created']} created, {player['updated']} updated, "
                f"{client.requests_used - requests_before} requests"
            )
        except EventsRateLimited as e:
            logger.warning(f"FIDE events: throttled at FIDE ID {fide_id} ({where}): {e} - stopping the sync")
            summary['failed'] += 1
            summary['stop_reason'] = 'throttled'
            break
        except RequestCapReached:
            logger.info(
                f"FIDE events: request cap of {max_requests} reached at FIDE ID {fide_id} ({where}) - "
                f"stopping the sync, {len(due_ids) - position + 1} players left for the next run"
            )
            summary['stop_reason'] = 'cap'
            break
        except (requests.RequestException, EventsParseError, EventsAPIError) as e:
            logger.warning(f"FIDE events: sync failed for FIDE ID {fide_id} ({where}): {e}")
            summary['failed'] += 1
        except Exception as e:
            logger.error(f"FIDE events: unexpected error for FIDE ID {fide_id} ({where}): {e}")
            summary['failed'] += 1
        finally:
            summary['periods_posted'] += player['periods']
            summary['created'] += player['created']
            summary['updated'] += player['updated']

    summary['requests'] = client.requests_used
    _log_summary(summary)
    return summary
