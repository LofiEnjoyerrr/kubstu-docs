import secrets
import uuid
from random import choice
from string import ascii_letters

from django.contrib.auth import get_user_model
from django.utils.text import slugify

from users.constants import EMAIL_VERIFY_TOKEN_LENGTH

User = get_user_model()

_MAX_USERNAME_GENERATE_ATTEMPTS = 10

def generate_username(email: str) -> str:
    base = slugify(email.split('@')[0]).replace('-', '_')

    if not base:
        base = 'user'

    for _ in range(_MAX_USERNAME_GENERATE_ATTEMPTS):
        suffix = secrets.randbelow(100000)

        username = f'{base}_{suffix}'

        if not User.objects.filter(username=username).exists():
            return username

    return f'{base}_{uuid.uuid4()}'


def generate_email_verify_token() -> str:
    return ''.join([choice(ascii_letters) for _ in range(EMAIL_VERIFY_TOKEN_LENGTH)])
