import re

from common_utils.utils import generate_random_color

HEX_PATTERN = re.compile(r'^#[0-9a-f]{6}$')


def test_generate_random_color_format():
    for _ in range(50):
        color = generate_random_color()
        assert HEX_PATTERN.fullmatch(color), color


def test_generate_random_color_distribution():
    """Sanity check: not all colors are the same (1-in-16M collision is fine)."""
    samples = {generate_random_color() for _ in range(20)}
    assert len(samples) > 1
