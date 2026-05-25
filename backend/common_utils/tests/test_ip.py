from unittest.mock import MagicMock

import pytest

from common_utils.ip import get_client_ip


def _make_request(meta: dict) -> MagicMock:
    request = MagicMock()
    request.META = meta
    return request


def test_get_client_ip_returns_remote_addr_when_no_xff():
    request = _make_request({'REMOTE_ADDR': '10.0.0.1'})
    assert get_client_ip(request) == '10.0.0.1'


def test_get_client_ip_prefers_x_forwarded_for():
    request = _make_request({
        'HTTP_X_FORWARDED_FOR': '203.0.113.5',
        'REMOTE_ADDR': '10.0.0.1',
    })
    assert get_client_ip(request) == '203.0.113.5'


def test_get_client_ip_takes_first_when_xff_is_chain():
    request = _make_request({
        'HTTP_X_FORWARDED_FOR': '203.0.113.5, 198.51.100.10, 10.0.0.1',
        'REMOTE_ADDR': '10.0.0.1',
    })
    assert get_client_ip(request) == '203.0.113.5'


def test_get_client_ip_strips_whitespace_around_xff_value():
    request = _make_request({
        'HTTP_X_FORWARDED_FOR': '   203.0.113.5  ,  198.51.100.10',
    })
    assert get_client_ip(request) == '203.0.113.5'


def test_get_client_ip_returns_none_when_no_data():
    request = _make_request({})
    assert get_client_ip(request) is None
