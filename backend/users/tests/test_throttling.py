import pytest

from users.throttling import ExtendedRateThrottle


@pytest.mark.parametrize(
    'rate,expected',
    [
        ('5/15m', (5, 15 * 60)),
        ('20/1d', (20, 86400)),
        ('10/2h', (10, 2 * 3600)),
        ('100/30s', (100, 30)),
    ],
)
def test_parse_rate_supports_multi_digit_multipliers(rate, expected):
    throttle = ExtendedRateThrottle()
    assert throttle.parse_rate(rate) == expected


def test_parse_rate_rejects_unknown_period_unit():
    throttle = ExtendedRateThrottle()
    with pytest.raises(KeyError):
        throttle.parse_rate('5/15x')
