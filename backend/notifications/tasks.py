"""
Celery tasks for sending Web Push notifications.

Triggers (from ``realtime.consumers.DocumentConsumer``) call
:func:`notify_document_edit` with a short delay. The WebSocket consumer
decides when an editing session should notify; this task only fans the
push out to every subscription the owner has registered. Dead
subscriptions (HTTP 410 from the push service) are pruned on the way out.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from pywebpush import WebPushException, webpush

from notifications.models import (
    DocumentNotificationSettings,
    PushSubscription,
    UserNotificationSettings,
)

logger = logging.getLogger(__name__)


def _vapid_claims() -> dict[str, str]:
    """The ``sub`` claim must be a mailto:/https: URI identifying the sender."""
    sub = getattr(settings, 'VAPID_CLAIM_SUB', '') or 'mailto:admin@example.com'
    return {'sub': sub}


def edit_notifications_enabled(owner_id: int, doc_id: int) -> bool:
    """Return whether edit notifications are enabled for this owner/document."""
    document_settings = DocumentNotificationSettings.objects.filter(document_id=doc_id).first()
    if document_settings and not document_settings.use_global_default:
        return document_settings.edit_notifications_enabled

    user_settings = UserNotificationSettings.objects.filter(user_id=owner_id).first()
    if user_settings:
        return user_settings.edit_notifications_enabled
    return True


@shared_task(name='notifications.notify_document_edit')
def notify_document_edit(
    *,
    owner_id: int,
    doc_id: int,
    editor_id: int,
    editor_username: str,
    doc_title: str,
) -> str:
    """
    Push "user X started editing your document" to ``owner_id``.

    Returns a short status string for observability — ``'disabled'``,
    ``'no-subscriptions'``, or ``'sent:N'`` where N is the count of
    subscriptions the push reached.
    """
    if owner_id == editor_id:
        return 'self-edit'

    if not edit_notifications_enabled(owner_id, doc_id):
        return 'disabled'

    private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    if not private_key:
        logger.warning('VAPID_PRIVATE_KEY is not configured; skipping push')
        return 'no-vapid-key'

    subs = list(PushSubscription.objects.filter(user_id=owner_id))
    if not subs:
        return 'no-subscriptions'

    payload = json.dumps({
        'title': 'KubSTU Docs',
        'body': f'{editor_username} начал(а) изменять документ «{doc_title}»',
        'doc_id': doc_id,
        'tag': f'doc-{doc_id}-edit',
    })

    sent = 0
    expired_ids: list[int] = []
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=_vapid_claims(),
                ttl=60 * 60,  # 1 hour delivery window
            )
            sent += 1
        except WebPushException as exc:
            response = getattr(exc, 'response', None)
            status_code = getattr(response, 'status_code', None)
            if status_code in (404, 410):
                # Endpoint is permanently gone — drop the subscription.
                expired_ids.append(sub.id)
            else:
                logger.warning(
                    'webpush failed for subscription %s: status=%s exc=%s',
                    sub.id, status_code, exc,
                )
        except Exception:  # noqa: BLE001
            logger.exception('webpush crashed for subscription %s', sub.id)

    if expired_ids:
        PushSubscription.objects.filter(pk__in=expired_ids).delete()

    return f'sent:{sent}'


def enqueue_edit_notification(
    *,
    owner_id: int,
    doc_id: int,
    editor_id: int,
    editor_username: str,
    doc_title: str,
) -> Any:
    """
    Thin wrapper used from the WebSocket consumer. Centralized so the
    consumer doesn't need to import Celery internals or know the task name.
    """
    return notify_document_edit.delay(
        owner_id=owner_id,
        doc_id=doc_id,
        editor_id=editor_id,
        editor_username=editor_username,
        doc_title=doc_title,
    )
