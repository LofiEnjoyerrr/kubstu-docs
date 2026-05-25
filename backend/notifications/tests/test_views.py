import pytest
from django.test import override_settings
from django.urls import reverse

from notifications.models import (
    DocumentNotificationSettings,
    PushSubscription,
    UserNotificationSettings,
)
from notifications.tests.factories import PushSubscriptionFactory


@pytest.mark.django_db
@override_settings(VAPID_PUBLIC_KEY='my-public-key')
def test_vapid_public_key_endpoint_returns_configured_key(api_client):
    response = api_client.get(reverse('push-vapid-public-key'))
    assert response.status_code == 200
    assert response.data == {'public_key': 'my-public-key'}


@pytest.mark.django_db
def test_subscribe_requires_auth(api_client):
    response = api_client.post(
        reverse('push-subscribe'),
        {
            'endpoint': 'https://push.example.com/sub/x',
            'keys': {'p256dh': 'pk', 'auth': 'auth'},
        },
        format='json',
    )
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_subscribe_creates_subscription(auth_client, user):
    response = auth_client.post(
        reverse('push-subscribe'),
        {
            'endpoint': 'https://push.example.com/sub/x',
            'keys': {'p256dh': 'pk', 'auth': 'auth'},
        },
        format='json',
    )
    assert response.status_code == 201
    assert PushSubscription.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_subscribe_rejects_bad_payload(auth_client):
    response = auth_client.post(
        reverse('push-subscribe'),
        {'endpoint': 'https://push.example.com/sub/x', 'keys': {}},
        format='json',
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_unsubscribe_removes_subscription(auth_client, user):
    sub = PushSubscriptionFactory(user=user)
    response = auth_client.post(
        reverse('push-unsubscribe'),
        {'endpoint': sub.endpoint},
        format='json',
    )
    assert response.status_code == 204
    assert not PushSubscription.objects.filter(pk=sub.pk).exists()


@pytest.mark.django_db
def test_unsubscribe_does_not_touch_other_users_subscriptions(auth_client, other_user):
    sub = PushSubscriptionFactory(user=other_user)
    response = auth_client.post(
        reverse('push-unsubscribe'),
        {'endpoint': sub.endpoint},
        format='json',
    )
    assert response.status_code == 204
    # ``user`` had no matching subscription, but ``other_user``'s row survives.
    assert PushSubscription.objects.filter(pk=sub.pk).exists()


@pytest.mark.django_db
def test_unsubscribe_requires_auth(api_client):
    response = api_client.post(
        reverse('push-unsubscribe'),
        {'endpoint': 'https://push.example.com/sub/x'},
        format='json',
    )
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_get_global_notification_preferences_defaults_to_enabled(auth_client, user):
    response = auth_client.get(reverse('notification-preferences'))

    assert response.status_code == 200
    assert response.data == {'edit_notifications_enabled': True}
    assert UserNotificationSettings.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_patch_global_notification_preferences(auth_client, user):
    response = auth_client.patch(
        reverse('notification-preferences'),
        {'edit_notifications_enabled': False},
        format='json',
    )

    assert response.status_code == 200
    assert response.data == {'edit_notifications_enabled': False}
    assert not user.notification_settings.edit_notifications_enabled


@pytest.mark.django_db
def test_get_document_notification_preferences_defaults_to_enabled(auth_client, document):
    response = auth_client.get(reverse('document-notification-preferences', args=[document.pk]))

    assert response.status_code == 200
    assert response.data == {
        'document_id': document.pk,
        'edit_notifications_enabled': True,
    }
    assert DocumentNotificationSettings.objects.filter(document=document).exists()


@pytest.mark.django_db
def test_patch_document_notification_preferences(auth_client, document):
    response = auth_client.patch(
        reverse('document-notification-preferences', args=[document.pk]),
        {'edit_notifications_enabled': False},
        format='json',
    )

    assert response.status_code == 200
    assert response.data == {
        'document_id': document.pk,
        'edit_notifications_enabled': False,
    }
    assert not document.notification_settings.edit_notifications_enabled


@pytest.mark.django_db
def test_non_owner_cannot_access_document_notification_preferences(
    other_auth_client,
    document,
):
    response = other_auth_client.get(
        reverse('document-notification-preferences', args=[document.pk]),
    )

    assert response.status_code == 404
