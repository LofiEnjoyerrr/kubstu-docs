import factory
from django.contrib.auth.hashers import make_password

from users.models import PasswordResetRequest, RegisterRequest, User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f'user_{n}')
    email = factory.LazyAttribute(lambda o: f'{o.username}@example.com')
    first_name = 'Test'
    last_name = 'User'
    password = factory.LazyFunction(lambda: make_password('correct-horse'))
    is_active = True


class RegisterRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RegisterRequest

    email = factory.Sequence(lambda n: f'pending_{n}@example.com')
    username = factory.Sequence(lambda n: f'pending_user_{n}')
    password = factory.LazyFunction(lambda: make_password('correct-horse'))
    ip = '127.0.0.1'
    # Tokens must be exactly EMAIL_VERIFY_TOKEN_LENGTH (64) chars and unique
    # across the test session — zero-pad the sequence number to 64 digits.
    token = factory.Sequence(lambda n: f'{n:064d}')


class PasswordResetRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PasswordResetRequest

    user = factory.SubFactory(UserFactory)
    # Same length / uniqueness requirement as the email-verify token.
    token = factory.Sequence(lambda n: f'{n:064d}')
