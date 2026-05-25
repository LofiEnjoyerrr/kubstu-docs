import pytest

from users.services import validate_credentials
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_validate_credentials_username_returns_true_when_free():
    assert validate_credentials('username', 'nobody') is True


@pytest.mark.django_db
def test_validate_credentials_username_returns_false_when_taken():
    UserFactory(username='taken')
    assert validate_credentials('username', 'taken') is False


@pytest.mark.django_db
def test_validate_credentials_email_returns_true_when_free():
    assert validate_credentials('email', 'free@example.com') is True


@pytest.mark.django_db
def test_validate_credentials_email_returns_false_when_taken():
    UserFactory(email='taken@example.com')
    assert validate_credentials('email', 'taken@example.com') is False
