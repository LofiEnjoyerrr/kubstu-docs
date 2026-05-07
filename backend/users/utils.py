import secrets
import uuid

from django.contrib.auth import get_user_model
from django.utils.text import slugify

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
