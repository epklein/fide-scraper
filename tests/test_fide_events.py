"""
Unit tests for fide_events.py (FIDE event history sync).
"""

import os
import sys
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fide_events
from fide_events import (
    EventsParseError, EventsRateLimited, FIDEEventsClient, RequestCapReached,
)
from events_api import EventsAPIError

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'fide_events')


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding='utf-8') as f:
        return f.read()


def _http(text, status=200):
    response = Mock()
    response.status_code = status
    response.text = text
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status}")
    return response


# --- Listing -----------------------------------------------------------------

class TestParsePeriodListing:
    def test_first_page(self):
        pairs, has_more = fide_events.parse_period_listing(fixture('a_calculations_page1.html'))
        assert pairs == [
            (date(2026, 8, 1), 'rapid'),
            (date(2026, 10, 1), 'blitz'),
            (date(2026, 11, 1), 'standard'),
            (date(2026, 11, 1), 'rapid'),
        ]
        assert has_more is True

    def test_more_periods(self):
        pairs, _ = fide_events.parse_period_listing(fixture('a_calculations_more.html'))
        assert pairs[0] == (date(2025, 4, 1), 'rapid')
        assert (date(2026, 6, 1), 'blitz') in pairs
        assert len(pairs) == 9

    def test_no_button(self):
        html = fixture('a_calculations_page1.html').replace('Check more periods', '')
        _, has_more = fide_events.parse_period_listing(html)
        assert has_more is False

    def test_no_view_links(self):
        assert fide_events.parse_period_listing('<table></table>') == ([], False)


class TestFetchPeriodListing:
    def _client(self):
        client = Mock()
        client.get.return_value = fixture('a_calculations_page1.html')
        client.post.return_value = fixture('a_calculations_more.html')
        return client

    def test_stored_period_on_first_page(self):
        client = self._client()
        pairs = fide_events.fetch_period_listing(client, '538026660', date(2026, 8, 1))
        client.post.assert_not_called()
        assert len(pairs) == 4
        client.get.assert_called_once_with(fide_events.LISTING_URL, {'event': '538026660'})

    def test_stored_period_older_than_first_page(self):
        client = self._client()
        pairs = fide_events.fetch_period_listing(client, '538026660', date(2025, 11, 1))
        client.post.assert_called_once_with(fide_events.LISTING_URL, {'action': '2', 'plr_id': '538026660'})
        assert len(pairs) == 13
        assert pairs == sorted(pairs, key=fide_events._pair_sort_key)

    def test_full_backfill(self):
        client = self._client()
        fide_events.fetch_period_listing(client, '538026660', None)
        client.post.assert_called_once()

    def test_no_button_no_second_call(self):
        client = self._client()
        client.get.return_value = fixture('a_calculations_page1.html').replace('Check more periods', '')
        fide_events.fetch_period_listing(client, '538026660', None)
        client.post.assert_not_called()


# --- Period events -----------------------------------------------------------

class TestParsePeriodEvents:
    def test_rated(self):
        events = fide_events.parse_period_events(fixture('indv_rapid_2025-11_rated.html'))
        assert events == [{
            'fide_event_code': '442504',
            'name': '2o Circuito de Xadrez Canoas Shopping Aberto Recreativo e Inclusivo Escolar Absoluto Quarta Etapa',
            'city': 'Canoas RS',
            'country': 'BRA',
            'start_date': date(2025, 10, 11),
            'end_date': date(2025, 10, 11),
            'games': 6,
            'rating_change': Decimal('52.00'),
        }]

    def test_unrated(self):
        [event] = fide_events.parse_period_events(fixture('indv_standard_2026-11_unrated.html'))
        assert event['fide_event_code'] == '500368'
        assert event['city'] == 'Porto Alegre RS'
        assert event['country'] == 'BRA'
        assert event['start_date'] == date(2026, 9, 23)
        assert event['end_date'] == date(2026, 10, 21)
        assert event['games'] == 3
        assert event['rating_change'] is None

    def test_several_events(self):
        events = fide_events.parse_period_events(fixture('indv_multiple_events.html'))
        assert [e['fide_event_code'] for e in events] == ['442504', '442600', '442700']

    def test_no_records(self):
        assert fide_events.parse_period_events(fixture('indv_no_records.html')) == []

    def test_unrecognized_markup(self):
        with pytest.raises(EventsParseError):
            fide_events.parse_period_events('<html><body>Something else</body></html>')

    def test_event_without_dates_skipped(self, caplog):
        html = fixture('indv_rapid_2025-11_rated.html').replace('2025-10-11', 'x')
        assert fide_events.parse_period_events(html) == []
        assert 'skipped' in caplog.text

    def test_location_without_country(self):
        assert fide_events._split_location('Somewhere') == ('Somewhere', '')

    def test_fetch_maps_time_control(self):
        client = Mock()
        client.get.return_value = fixture('indv_no_records.html')
        fide_events.fetch_period_events(client, '538026660', date(2026, 11, 1), 'blitz')
        client.get.assert_called_once_with(fide_events.PERIOD_URL, {
            'id_number': '538026660', 'rating_period': '2026-11-01', 't': 2,
        })


# --- Client ------------------------------------------------------------------

class TestFIDEEventsClient:
    def test_ajax_header_and_pacing(self):
        client = FIDEEventsClient(delay_seconds=1.5, max_requests=10)
        with patch('fide_events.time.sleep') as sleep, \
                patch('fide_events.requests.request', return_value=_http('<html>ok</html>')) as request:
            client.get('https://x', {'a': 1})
            client.post('https://x', {'b': 2})
        assert sleep.call_count == 2
        sleep.assert_called_with(1.5)
        for call in request.call_args_list:
            assert call.kwargs['headers']['X-Requested-With'] == 'XMLHttpRequest'
        assert client.requests_used == 2

    @pytest.mark.parametrize('body', ['', '﻿', '﻿﻿\n'])
    def test_throttle(self, body):
        client = FIDEEventsClient(delay_seconds=0, max_requests=10)
        with patch('fide_events.time.sleep'), patch('fide_events.requests.request', return_value=_http(body)):
            with pytest.raises(EventsRateLimited):
                client.get('https://x', {})

    def test_cap(self):
        client = FIDEEventsClient(delay_seconds=0, max_requests=1)
        with patch('fide_events.time.sleep'), \
                patch('fide_events.requests.request', return_value=_http('ok')) as request:
            client.get('https://x', {})
            with pytest.raises(RequestCapReached):
                client.get('https://x', {})
        assert request.call_count == 1

    def test_http_error(self):
        client = FIDEEventsClient(delay_seconds=0, max_requests=10)
        with patch('fide_events.time.sleep'), patch('fide_events.requests.request', return_value=_http('x', 500)):
            with pytest.raises(requests.HTTPError):
                client.get('https://x', {})


# --- Selection and state -----------------------------------------------------

class TestSelection:
    LISTING = [
        (date(2026, 6, 1), 'rapid'),
        (date(2026, 8, 1), 'rapid'),
        (date(2026, 10, 1), 'blitz'),
        (date(2026, 11, 1), 'rapid'),
        (date(2026, 11, 1), 'standard'),
    ]

    def test_from_stored_period_inclusive_oldest_first(self):
        assert fide_events.pending_pairs(self.LISTING, date(2026, 8, 1)) == [
            (date(2026, 8, 1), 'rapid'),
            (date(2026, 10, 1), 'blitz'),
            (date(2026, 11, 1), 'standard'),
            (date(2026, 11, 1), 'rapid'),
        ]

    def test_no_stored_period(self):
        assert len(fide_events.pending_pairs(self.LISTING, None)) == 5

    def test_published_list(self):
        results = [
            {'Rating History': [{'date': date(2026, 11, 1)}, {'date': date(2026, 10, 1)}]},
            {'Rating History': [{'date': date(2026, 12, 1)}]},
            {'Rating History': []},
        ]
        assert fide_events.published_list(results) == date(2026, 12, 1)

    def test_published_list_none(self):
        assert fide_events.published_list([{'Rating History': []}]) is None
        assert fide_events.published_list([]) is None


class TestState:
    def test_round_trip(self, tmp_path):
        path = str(tmp_path / 'state.csv')
        fide_events.save_state(path, {'2': date(2026, 11, 1), '1': date(2026, 10, 1)})
        assert fide_events.load_state(path) == {'1': date(2026, 10, 1), '2': date(2026, 11, 1)}
        with open(path) as f:
            assert f.read().splitlines() == ['fide_id,checked_period', '1,2026-10-01', '2,2026-11-01']

    def test_missing_file(self, tmp_path):
        assert fide_events.load_state(str(tmp_path / 'missing.csv')) == {}

    def test_bad_rows_ignored(self, tmp_path):
        path = tmp_path / 'state.csv'
        path.write_text('fide_id,checked_period\n1,2026-10-01\n2,garbage\n')
        assert fide_events.load_state(str(path)) == {'1': date(2026, 10, 1)}

    def test_failed_write_leaves_no_partial_file(self, tmp_path):
        path = str(tmp_path / 'state.csv')
        fide_events.save_state(path, {'1': date(2026, 10, 1)})
        with patch('fide_events.os.replace', side_effect=OSError('disk full')):
            with pytest.raises(OSError):
                fide_events.save_state(path, {'1': date(2026, 11, 1)})
        assert fide_events.load_state(path) == {'1': date(2026, 10, 1)}
        assert os.listdir(tmp_path) == ['state.csv']


# --- Orchestration -----------------------------------------------------------

PUBLISHED = date(2026, 11, 1)
EVENT = {
    'fide_event_code': '1', 'name': 'E', 'city': '', 'country': '',
    'start_date': date(2026, 1, 1), 'end_date': date(2026, 1, 1), 'games': 1, 'rating_change': None,
}


def _result(fide_id, name='Player'):
    return {'FIDE ID': fide_id, 'Player Name': name, 'Rating History': [{'date': PUBLISHED}]}


class FakeFIDE:
    """Stands in for fetch_period_listing / fetch_period_events and counts requests on the client."""

    def __init__(self, listings, failures=None):
        self.listings = listings
        self.failures = failures or {}
        self.fetched = []

    def listing(self, client, fide_id, stored):
        client._count()
        if ('listing', fide_id) in self.failures:
            raise self.failures[('listing', fide_id)]
        return self.listings[fide_id]

    def events(self, client, fide_id, period, time_control):
        client._count()
        key = (fide_id, period, time_control)
        if key in self.failures:
            raise self.failures[key]
        self.fetched.append(key)
        return [EVENT]


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv('FIDE_EVENTS_API_ENDPOINT', 'https://chesshub.cloud/api/fide-events/')
    monkeypatch.setenv('API_TOKEN', 'secret')
    return str(tmp_path / 'state.csv')


def _run(fake, fide_ids, results, state_path, latest=None, max_requests=100, post=None):
    def count(self):
        if self.requests_used >= self.max_requests:
            raise RequestCapReached()
        self.requests_used += 1

    post = post or Mock(return_value={'created': 1, 'updated': 0})
    with patch.object(FIDEEventsClient, '_count', count, create=True), \
            patch('fide_events.fetch_period_listing', side_effect=fake.listing), \
            patch('fide_events.fetch_period_events', side_effect=fake.events), \
            patch('fide_events.fetch_latest_periods', return_value=latest or {}) as latest_mock, \
            patch('fide_events.post_period_events', post):
        summary = fide_events.sync_events(fide_ids, results, 0, state_path=state_path, max_requests=max_requests)
    return summary, post, latest_mock


class TestSyncEvents:
    def test_disabled(self, monkeypatch):
        monkeypatch.delenv('FIDE_EVENTS_API_ENDPOINT', raising=False)
        with patch('fide_events.fetch_latest_periods') as latest:
            assert fide_events.sync_events(['1'], [_result('1')], 0) is None
        latest.assert_not_called()

    def test_already_checked_makes_no_request(self, env):
        fide_events.save_state(env, {'1': PUBLISHED})
        fake = FakeFIDE({'1': [(date(2026, 11, 1), 'rapid')]})
        summary, post, _ = _run(fake, ['1'], [_result('1')], env)
        assert summary['due'] == 0
        assert summary['requests'] == 0
        post.assert_not_called()

    def test_full_backfill_oldest_first(self, env):
        listing = [(date(2025, 4, 1), 'rapid'), (date(2026, 11, 1), 'standard'), (date(2026, 11, 1), 'rapid')]
        fake = FakeFIDE({'1': listing})
        summary, post, latest = _run(fake, ['1'], [_result('1', 'Klein, Eduardo Pavinato')], env)
        latest.assert_called_once()
        assert fake.fetched == [('1',) + pair for pair in listing]
        assert [c.args[3:5] for c in post.call_args_list] == listing
        assert post.call_args_list[0].args[2] == 'Klein, Eduardo Pavinato'
        assert fide_events.load_state(env) == {'1': PUBLISHED}
        assert summary['completed'] == 1
        assert summary['periods_posted'] == 3
        assert summary['created'] == 3
        assert summary['requests'] == 4
        assert summary['stop_reason'] == 'completed'

    def test_resume_from_stored_period(self, env):
        listing = [(date(2025, 4, 1), 'rapid'), (date(2025, 11, 1), 'rapid'), (date(2026, 11, 1), 'rapid')]
        fake = FakeFIDE({'1': listing})
        _run(fake, ['1'], [_result('1')], env, latest={'1': date(2025, 11, 1)})
        assert fake.fetched == [('1', date(2025, 11, 1), 'rapid'), ('1', date(2026, 11, 1), 'rapid')]

    def test_throttle_stops_the_sync(self, env):
        fake = FakeFIDE(
            {'1': [(date(2026, 11, 1), 'rapid')], '2': [(date(2026, 11, 1), 'rapid')], '3': []},
            failures={('2', date(2026, 11, 1), 'rapid'): EventsRateLimited()},
        )
        summary, _, _ = _run(fake, ['1', '2', '3'], [_result('1'), _result('2'), _result('3')], env)
        assert summary['stop_reason'] == 'throttled'
        assert fide_events.load_state(env) == {'1': PUBLISHED}
        assert summary['requests'] == 4  # 3 is never listed

    def test_timeout_continues_with_next_player(self, env):
        fake = FakeFIDE({'1': [], '2': []}, failures={('listing', '1'): requests.Timeout()})
        summary, _, _ = _run(fake, ['1', '2'], [_result('1'), _result('2')], env)
        assert fide_events.load_state(env) == {'2': PUBLISHED}
        assert summary['failed'] == 1
        assert summary['completed'] == 1

    def test_rejected_post_stops_the_player(self, env):
        listing = [(date(2026, 10, 1), 'rapid'), (date(2026, 11, 1), 'rapid')]
        fake = FakeFIDE({'1': listing})
        post = Mock(side_effect=EventsAPIError('400'))
        summary, _, _ = _run(fake, ['1'], [_result('1')], env, post=post)
        assert fake.fetched == [('1', date(2026, 10, 1), 'rapid')]
        assert fide_events.load_state(env) == {}
        assert summary['failed'] == 1

    def test_cap_reached_mid_player(self, env):
        listing = [(date(2026, m, 1), 'rapid') for m in range(1, 12)]
        fake = FakeFIDE({'1': listing})
        summary, post, _ = _run(fake, ['1'], [_result('1')], env, max_requests=5)
        assert summary['stop_reason'] == 'cap'
        assert summary['requests'] == 5
        assert post.call_count == 4  # listing + 4 periods
        assert fide_events.load_state(env) == {}

    def test_latest_periods_unavailable(self, env):
        fake = FakeFIDE({'1': []})
        with patch('fide_events.fetch_latest_periods', side_effect=EventsAPIError('500')), \
                patch('fide_events.fetch_period_listing', side_effect=fake.listing) as listing:
            summary = fide_events.sync_events(['1'], [_result('1')], 0, state_path=env)
        listing.assert_not_called()
        assert summary['stop_reason'] == 'skipped'
        assert not os.path.exists(env)

    def test_no_published_list(self, env):
        with patch('fide_events.fetch_latest_periods') as latest:
            summary = fide_events.sync_events(['1'], [{'FIDE ID': '1', 'Rating History': []}], 0, state_path=env)
        latest.assert_not_called()
        assert summary['stop_reason'] == 'skipped'

    def test_only_selected_ids(self, env):
        fake = FakeFIDE({'1503014': [], '538026660': []})
        _, _, _ = _run(fake, ['1503014'], [_result('1503014'), _result('538026660')], env)
        assert fide_events.load_state(env) == {'1503014': PUBLISHED}

    def test_player_without_profile_result_skipped(self, env):
        fake = FakeFIDE({'1': []})
        summary, _, _ = _run(fake, ['1', '2'], [_result('1')], env)
        assert summary['due'] == 1

    def test_new_list_makes_player_due_and_keeps_other_rows(self, env):
        fide_events.save_state(env, {'1': date(2026, 10, 1), '9': date(2026, 10, 1)})
        fake = FakeFIDE({'1': []})
        summary, _, _ = _run(fake, ['1'], [_result('1')], env)
        assert summary['due'] == 1
        assert fide_events.load_state(env) == {'1': PUBLISHED, '9': date(2026, 10, 1)}

    def test_empty_period_not_posted(self, env):
        fake = FakeFIDE({'1': [(date(2026, 11, 1), 'rapid')]})
        fake.events = lambda client, *args: (client._count(), [])[1]
        summary, post, _ = _run(fake, ['1'], [_result('1')], env)
        post.assert_not_called()
        assert fide_events.load_state(env) == {'1': PUBLISHED}

    def test_summary_logged(self, env, caplog):
        caplog.set_level('INFO')
        fake = FakeFIDE({'1': []})
        _run(fake, ['1'], [_result('1')], env)
        assert 'FIDE events sync: stop=completed' in caplog.text


# --- Integration in fide_scraper.main ---------------------------------------

class TestMainIntegration:
    def _run_main(self, sync_side_effect=None):
        import fide_scraper
        calls = []
        result = _result('538026660')

        def record(name, value=None):
            def fn(*args, **kwargs):
                calls.append(name)
                if isinstance(sync_side_effect, Exception) and name == 'sync':
                    raise sync_side_effect
                return value
            return fn

        with patch('sys.argv', ['fide_scraper.py']), \
                patch('fide_scraper.load_player_data_from_csv', return_value={'538026660': {}}), \
                patch('fide_scraper.select_fide_ids_for_processing', return_value=(['538026660'], [])), \
                patch('fide_scraper.process_batch', return_value=([result], [])), \
                patch('fide_scraper.write_csv_output', side_effect=record('csv')), \
                patch('fide_scraper.send_batch_notifications', side_effect=record('email', (0, 0))), \
                patch('fide_scraper.send_batch_api_updates', side_effect=record('ratings_api', (1, 0))), \
                patch('fide_scraper.sync_events', side_effect=record('sync')) as sync:
            with pytest.raises(SystemExit) as exit_info:
                fide_scraper.main()
        return calls, exit_info.value.code, sync

    def test_events_after_ratings(self):
        calls, code, sync = self._run_main()
        assert calls == ['csv', 'email', 'ratings_api', 'sync']
        assert code == 0
        args = sync.call_args.args
        assert args[0] == ['538026660']
        assert args[1][0]['FIDE ID'] == '538026660'

    def test_sync_exception_keeps_exit_code(self):
        calls, code, _ = self._run_main(sync_side_effect=RuntimeError('boom'))
        assert calls[-1] == 'sync'
        assert code == 0


# --- Old FIDE data -------------------------------------------------------------

class TestOldPeriods:
    def test_invalid_data_is_an_empty_period(self):
        assert fide_events.parse_period_events(fixture('indv_invalid_data.html')) == []

    def test_zero_end_date_becomes_start(self):
        events = fide_events.parse_period_events(fixture('indv_standard_2001-07_zero_end_dates.html'))
        assert events
        first = events[0]
        assert first['fide_event_code'] == '19212'
        assert first['start_date'] == date(2001, 2, 9)
        assert first['end_date'] == date(2001, 2, 9)

    def test_century_end_date_moved_forward(self):
        events = fide_events.parse_period_events(fixture('indv_standard_2002-04_century_end_dates.html'))
        assert events[0]['fide_event_code'] == '21236'
        assert events[0]['start_date'] == date(2001, 12, 17)
        assert events[0]['end_date'] == date(2001, 12, 23)
        assert all(e['end_date'] >= e['start_date'] for e in events)

    @pytest.mark.parametrize('start, end, expected', [
        (date(2001, 2, 9), None, (date(2001, 2, 9), date(2001, 2, 9))),
        (None, date(2001, 2, 9), (date(2001, 2, 9), date(2001, 2, 9))),
        (None, None, None),
        (date(2001, 12, 17), date(1901, 12, 23), (date(2001, 12, 17), date(2001, 12, 23))),
        (date(2001, 12, 17), date(2001, 12, 1), (date(2001, 12, 17), date(2001, 12, 17))),
        (date(2001, 12, 17), date(1850, 1, 1), (date(2001, 12, 17), date(2001, 12, 17))),
        (date(2004, 2, 20), date(1904, 2, 29), (date(2004, 2, 20), date(2004, 2, 29))),
        (date(2001, 1, 1), date(2000, 2, 29), (date(2001, 1, 1), date(2001, 1, 1))),
        (date(2025, 10, 11), date(2025, 10, 12), (date(2025, 10, 11), date(2025, 10, 12))),
    ])
    def test_event_dates(self, start, end, expected):
        assert fide_events._event_dates(start, end) == expected


class TestSyncLogging:
    def test_start_and_player_lines(self, env, caplog):
        caplog.set_level('INFO')
        fake = FakeFIDE({'1': [(date(2026, 11, 1), 'rapid')]})
        _run(fake, ['1', '2'], [_result('1')], env, latest={'1': date(2026, 11, 1)})
        assert 'FIDE events sync started: 1 of 2 players due for the 2026-11 list' in caplog.text
        assert 'FIDE events [1/1] FIDE ID 1: 1 pending since 2026-11, 1 posted, 1 created' in caplog.text

    def test_failure_names_the_period(self, env, caplog):
        fake = FakeFIDE({'1': [(date(2001, 10, 1), 'standard')]},
                        failures={('1', date(2001, 10, 1), 'standard'): EventsParseError('boom')})
        _run(fake, ['1'], [_result('1')], env)
        assert 'FIDE ID 1 (2001-10 standard): boom' in caplog.text
