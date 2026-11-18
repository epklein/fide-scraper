"""
Unit tests for events_api.py (Chess Hub FIDE events endpoints).
"""

import os
import sys
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import events_api
from events_api import EventsAPIError


CONFIG = {
    'endpoint': 'https://chesshub.cloud/api/fide-events/',
    'latest_periods_url': 'https://chesshub.cloud/api/fide-events/latest-periods/',
    'token': 'secret',
}

EVENT = {
    'fide_event_code': '442504',
    'name': 'Torneio',
    'city': 'Canoas RS',
    'country': 'BRA',
    'start_date': date(2025, 10, 11),
    'end_date': date(2025, 10, 11),
    'games': 6,
    'rating_change': Decimal('52.00'),
}


def _response(status, body=None, text=''):
    response = Mock()
    response.status_code = status
    response.text = text
    if isinstance(body, Exception):
        response.json.side_effect = body
    else:
        response.json.return_value = body
    return response


class TestLoadConfig:
    def test_enabled(self, monkeypatch):
        monkeypatch.setenv('FIDE_EVENTS_API_ENDPOINT', 'https://chesshub.cloud/api/fide-events/')
        monkeypatch.setenv('API_TOKEN', 'secret')
        assert events_api.load_events_api_config() == CONFIG

    def test_latest_periods_url_without_trailing_slash(self, monkeypatch):
        monkeypatch.setenv('FIDE_EVENTS_API_ENDPOINT', 'https://chesshub.cloud/api/fide-events')
        monkeypatch.setenv('API_TOKEN', 'secret')
        config = events_api.load_events_api_config()
        assert config['endpoint'] == 'https://chesshub.cloud/api/fide-events'
        assert config['latest_periods_url'] == 'https://chesshub.cloud/api/fide-events/latest-periods/'

    def test_endpoint_unset(self, monkeypatch):
        monkeypatch.delenv('FIDE_EVENTS_API_ENDPOINT', raising=False)
        monkeypatch.setenv('API_TOKEN', 'secret')
        assert events_api.load_events_api_config() is None

    def test_endpoint_without_token_warns(self, monkeypatch, caplog):
        monkeypatch.setenv('FIDE_EVENTS_API_ENDPOINT', 'https://chesshub.cloud/api/fide-events/')
        monkeypatch.setenv('API_TOKEN', '')
        assert events_api.load_events_api_config() is None
        assert 'events posting disabled' in caplog.text


class TestFetchLatestPeriods:
    def test_success(self):
        with patch('events_api.requests.get', return_value=_response(200, {'538026660': '2026-11-01'})) as get:
            assert events_api.fetch_latest_periods(CONFIG) == {'538026660': date(2026, 11, 1)}
        args, kwargs = get.call_args
        assert args[0] == CONFIG['latest_periods_url']
        assert kwargs['headers']['Authorization'] == 'Token secret'

    def test_empty(self):
        with patch('events_api.requests.get', return_value=_response(200, {})):
            assert events_api.fetch_latest_periods(CONFIG) == {}

    @pytest.mark.parametrize('status', [401, 500])
    def test_http_error(self, status):
        with patch('events_api.requests.get', return_value=_response(status, text='nope')):
            with pytest.raises(EventsAPIError):
                events_api.fetch_latest_periods(CONFIG)

    def test_timeout(self):
        with patch('events_api.requests.get', side_effect=requests.Timeout()):
            with pytest.raises(EventsAPIError):
                events_api.fetch_latest_periods(CONFIG)

    def test_invalid_json(self):
        with patch('events_api.requests.get', return_value=_response(200, ValueError('bad'))):
            with pytest.raises(EventsAPIError):
                events_api.fetch_latest_periods(CONFIG)

    def test_invalid_date(self):
        with patch('events_api.requests.get', return_value=_response(200, {'1': 'nope'})):
            with pytest.raises(EventsAPIError):
                events_api.fetch_latest_periods(CONFIG)


class TestPostPeriodEvents:
    def test_payload_shape(self):
        payload = events_api.build_period_payload(
            '538026660', 'Klein, Eduardo Pavinato', date(2025, 11, 1), 'rapid', [EVENT])
        assert payload == {
            'fide_id': '538026660',
            'player_name': 'Klein, Eduardo Pavinato',
            'rating_period': '2025-11-01',
            'time_control': 'rapid',
            'events': [{
                'fide_event_code': '442504',
                'name': 'Torneio',
                'city': 'Canoas RS',
                'country': 'BRA',
                'start_date': '2025-10-11',
                'end_date': '2025-10-11',
                'games': 6,
                'rating_change': '52.00',
            }],
        }

    def test_null_rating_change(self):
        payload = events_api.build_period_payload(
            '1', 'X', date(2026, 11, 1), 'standard', [{**EVENT, 'rating_change': None}])
        assert payload['events'][0]['rating_change'] is None

    def test_success(self):
        with patch('events_api.requests.post',
                   return_value=_response(200, {'fide_id': '1', 'created': 1, 'updated': 2})) as post:
            counts = events_api.post_period_events(CONFIG, '1', 'X', date(2025, 11, 1), 'rapid', [EVENT])
        assert counts == {'created': 1, 'updated': 2}
        args, kwargs = post.call_args
        assert args[0] == CONFIG['endpoint']
        assert kwargs['headers']['Authorization'] == 'Token secret'
        assert kwargs['json']['rating_period'] == '2025-11-01'

    @pytest.mark.parametrize('status', [400, 401, 500])
    def test_http_error(self, status):
        with patch('events_api.requests.post', return_value=_response(status, text='bad')):
            with pytest.raises(EventsAPIError):
                events_api.post_period_events(CONFIG, '1', 'X', date(2025, 11, 1), 'rapid', [EVENT])

    def test_timeout(self):
        with patch('events_api.requests.post', side_effect=requests.Timeout()):
            with pytest.raises(EventsAPIError):
                events_api.post_period_events(CONFIG, '1', 'X', date(2025, 11, 1), 'rapid', [EVENT])
