"""
Tests for the push-notification fan-out task.

``webpush`` (the call into pywebpush) is patched in every test — we don't
want the suite making real HTTPS calls.
"""

import pytest
from django.test import override_settings
from pywebpush import WebPushException

from notifications.models import PushSubscription
from notifications.tasks import notify_document_edit
from notifications.tests.factories import (
    DocumentNotificationSettingsFactory,
    PushSubscriptionFactory,
    UserNotificationSettingsFactory,
)
from users.tests.factories import UserFactory


def _call(owner, editor, doc_id=1, title='Doc'):
    return notify_document_edit(
        owner_id=owner.id,
        doc_id=doc_id,
        editor_id=editor.id,
        editor_username=editor.username,
        doc_title=title,
    )


@pytest.mark.django_db
def test_self_edit_short_circuits(mocker):
    user = UserFactory()
    webpush = mocker.patch('notifications.tasks.webpush')

    result = _call(owner=user, editor=user)

    assert result == 'self-edit'
    webpush.assert_not_called()


@pytest.mark.django_db
@override_settings(VAPID_PRIVATE_KEY='')
def test_missing_vapid_key_skips_send(mocker):
    owner = UserFactory()
    editor = UserFactory()
    webpush = mocker.patch('notifications.tasks.webpush')

    result = _call(owner=owner, editor=editor)

    assert result == 'no-vapid-key'
    webpush.assert_not_called()


@pytest.mark.django_db
def test_no_subscriptions_returns_explicit_status(mocker):
    owner = UserFactory()
    editor = UserFactory()
    webpush = mocker.patch('notifications.tasks.webpush')

    result = _call(owner=owner, editor=editor)

    assert result == 'no-subscriptions'
    webpush.assert_not_called()


@pytest.mark.django_db
def test_task_does_not_throttle_repeat_calls(mocker):
    owner = UserFactory()
    editor = UserFactory()
    PushSubscriptionFactory(user=owner)
    webpush = mocker.patch('notifications.tasks.webpush')

    first = _call(owner=owner, editor=editor)
    second = _call(owner=owner, editor=editor)

    assert first == 'sent:1'
    assert second == 'sent:1'
    assert webpush.call_count == 2


@pytest.mark.django_db
def test_global_disabled_setting_skips_send(mocker):
    owner = UserFactory()
    editor = UserFactory()
    PushSubscriptionFactory(user=owner)
    UserNotificationSettingsFactory(user=owner, edit_notifications_enabled=False)
    webpush = mocker.patch('notifications.tasks.webpush')

    result = _call(owner=owner, editor=editor)

    assert result == 'disabled'
    webpush.assert_not_called()


@pytest.mark.django_db
def test_document_enabled_setting_overrides_global_disabled(mocker):
    owner = UserFactory()
    editor = UserFactory()
    PushSubscriptionFactory(user=owner)
    UserNotificationSettingsFactory(user=owner, edit_notifications_enabled=False)
    settings = DocumentNotificationSettingsFactory(
        document__owner=owner,
        edit_notifications_enabled=True,
        use_global_default=False,
    )
    webpush = mocker.patch('notifications.tasks.webpush')

    result = _call(owner=owner, editor=editor, doc_id=settings.document_id)

    assert result == 'sent:1'
    webpush.assert_called_once()


@pytest.mark.django_db
def test_document_default_follows_global_disabled(mocker):
    owner = UserFactory()
    editor = UserFactory()
    PushSubscriptionFactory(user=owner)
    UserNotificationSettingsFactory(user=owner, edit_notifications_enabled=False)
    settings = DocumentNotificationSettingsFactory(
        document__owner=owner,
        edit_notifications_enabled=True,
        use_global_default=True,
    )
    webpush = mocker.patch('notifications.tasks.webpush')

    result = _call(owner=owner, editor=editor, doc_id=settings.document_id)

    assert result == 'disabled'
    webpush.assert_not_called()


@pytest.mark.django_db
def test_document_disabled_setting_skips_send(mocker):
    owner = UserFactory()
    editor = UserFactory()
    PushSubscriptionFactory(user=owner)
    settings = DocumentNotificationSettingsFactory(
        document__owner=owner,
        edit_notifications_enabled=False,
    )
    webpush = mocker.patch('notifications.tasks.webpush')

    result = _call(owner=owner, editor=editor, doc_id=settings.document_id)

    assert result == 'disabled'
    webpush.assert_not_called()


@pytest.mark.django_db
def test_successful_send_counts_subscriptions(mocker):
    owner = UserFactory()
    editor = UserFactory()
    PushSubscriptionFactory(user=owner)
    PushSubscriptionFactory(user=owner)
    PushSubscriptionFactory(user=owner)
    webpush = mocker.patch('notifications.tasks.webpush')

    result = _call(owner=owner, editor=editor)

    assert result == 'sent:3'
    assert webpush.call_count == 3


def _expired_webpush_exception() -> WebPushException:
    """Build a 410 WebPushException — pywebpush's shape is awkward to fake."""

    class _Resp:
        status_code = 410
        text = 'gone'

    exc = WebPushException('endpoint expired', response=_Resp())
    return exc


@pytest.mark.django_db
def test_expired_410_subscriptions_are_pruned(mocker):
    owner = UserFactory()
    editor = UserFactory()
    alive = PushSubscriptionFactory(user=owner)
    dead = PushSubscriptionFactory(user=owner)

    # First sub succeeds, second sub returns 410 -> should be deleted.
    mocker.patch(
        'notifications.tasks.webpush',
        side_effect=[None, _expired_webpush_exception()],
    )

    result = _call(owner=owner, editor=editor)

    assert result == 'sent:1'
    assert PushSubscription.objects.filter(pk=alive.pk).exists()
    assert not PushSubscription.objects.filter(pk=dead.pk).exists()


@pytest.mark.django_db
def test_other_webpush_failures_do_not_drop_subscription(mocker):
    """500 / network errors are logged but the sub row must stay."""
    owner = UserFactory()
    editor = UserFactory()
    sub = PushSubscriptionFactory(user=owner)

    class _Resp:
        status_code = 500
        text = 'oops'

    mocker.patch(
        'notifications.tasks.webpush',
        side_effect=WebPushException('boom', response=_Resp()),
    )

    result = _call(owner=owner, editor=editor)

    # No push reached the user, but the subscription stays for next time.
    assert result == 'sent:0'
    assert PushSubscription.objects.filter(pk=sub.pk).exists()
