import pytest

from users.constants import EMAIL_VERIFY_TOKEN_LENGTH, PASSWORD_RESET_TOKEN_LENGTH
from users.constants.email_verify import EMAIL_VERIFY_TOKEN_ALPHABET
from users.constants.password_reset import PASSWORD_RESET_TOKEN_ALPHABET
from users.tests.factories import UserFactory
from users.utils import (
    generate_email_verify_token,
    generate_password_reset_token,
    generate_username,
)


@pytest.mark.django_db
def test_generate_username_uses_local_part_of_email():
    # Django's slugify strips dots, so "john.doe" → "johndoe".
    username = generate_username('john.doe@example.com')
    assert username.startswith('johndoe_')


@pytest.mark.django_db
def test_generate_username_falls_back_to_user_for_unsluggable_emails():
    username = generate_username('@@@@@@example.com')
    # slugify strips the local part to empty, falls back to "user".
    assert username.startswith('user_')


@pytest.mark.django_db
def test_generate_username_avoids_existing_username():
    UserFactory(username='alice_42')
    name = generate_username('alice@example.com')
    assert name != 'alice_42'
    assert name.startswith('alice_')


def test_generate_email_verify_token_length_and_alphabet():
    token = generate_email_verify_token()
    assert len(token) == EMAIL_VERIFY_TOKEN_LENGTH
    assert set(token).issubset(set(EMAIL_VERIFY_TOKEN_ALPHABET))


def test_generate_password_reset_token_length_and_alphabet():
    token = generate_password_reset_token()
    assert len(token) == PASSWORD_RESET_TOKEN_LENGTH
    assert set(token).issubset(set(PASSWORD_RESET_TOKEN_ALPHABET))


def test_tokens_are_not_constant():
    tokens = {generate_email_verify_token() for _ in range(10)}
    assert len(tokens) > 1
