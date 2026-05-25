from unittest.mock import MagicMock

import pytest

from notifications.models import PushSubscription
from notifications.serializers import (
    PushSubscriptionSerializer,
    PushUnsubscribeSerializer,
)
from notifications.tests.factories import PushSubscriptionFactory
from users.tests.factories import UserFactory


def _make_request(user, user_agent: str = 'pytest-ua'):
    request = MagicMock()
    request.user = user
    request.META = {'HTTP_USER_AGENT': user_agent}
    return request


@pytest.mark.django_db
def test_subscribe_serializer_creates_subscription_with_user_agent():
    user = UserFactory()
    request = _make_request(user, user_agent='Mozilla/5.0')

    serializer = PushSubscriptionSerializer(
        data={
            'endpoint': 'https://push.example.com/sub/abc',
            'keys': {'p256dh': 'pk', 'auth': 'auth-secret'},
        },
        context={'request': request},
    )
    assert serializer.is_valid(), serializer.errors
    serializer.save()

    sub = PushSubscription.objects.get(endpoint='https://push.example.com/sub/abc')
    assert sub.user == user
    assert sub.p256dh == 'pk'
    assert sub.auth == 'auth-secret'
    assert sub.user_agent == 'Mozilla/5.0'


@pytest.mark.django_db
def test_subscribe_serializer_upserts_on_endpoint_collision():
    """
    Re-subscribing with the same endpoint (e.g. browser reused the same
    PushSubscription) must overwrite the row, not raise UniqueViolation.
    """
    first_user = UserFactory()
    PushSubscriptionFactory(
        user=first_user,
        endpoint='https://push.example.com/sub/abc',
        p256dh='old',
        auth='old',
    )

    second_user = UserFactory()
    request = _make_request(second_user)
    serializer = PushSubscriptionSerializer(
        data={
            'endpoint': 'https://push.example.com/sub/abc',
            'keys': {'p256dh': 'new', 'auth': 'new'},
        },
        context={'request': request},
    )
    assert serializer.is_valid(), serializer.errors
    serializer.save()

    sub = PushSubscription.objects.get(endpoint='https://push.example.com/sub/abc')
    assert sub.user == second_user
    assert sub.p256dh == 'new'


def test_subscribe_serializer_rejects_missing_keys():
    serializer = PushSubscriptionSerializer(
        data={
            'endpoint': 'https://push.example.com/sub/abc',
            'keys': {'p256dh': 'pk'},  # missing auth
        },
        context={'request': _make_request(MagicMock())},
    )
    assert not serializer.is_valid()
    assert 'keys' in serializer.errors


def test_unsubscribe_serializer_validates_endpoint_url():
    serializer = PushUnsubscribeSerializer(data={'endpoint': 'not-a-url'})
    assert not serializer.is_valid()
