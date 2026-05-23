"""
Celery tasks for sending Web Push notifications.

Triggers (from ``realtime.consumers.DocumentConsumer``) call
:func:`notify_document_edit` with a short delay — the task applies a
per-(owner, doc, editor) throttle backed by Redis cache and, if not
throttled, fans the push out to every subscription the owner has
registered. Dead subscriptions (HTTP 410 from the push service) are
pruned on the way out.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from pywebpush import WebPushException, webpush

from notifications.models import PushSubscription

logger = logging.getLogger(__name__)


# 15-minute freeze between pushes to the same owner for the same
# (document, editor) pair. The user explicitly asked for this — without
# it a typing session would flood notifications.
EDIT_NOTIFICATION_THROTTLE_SECONDS = 15 * 60


def _throttle_key(owner_id: int, doc_id: int, editor_id: int) -> str:
    return f'push:edit-throttle:{owner_id}:{doc_id}:{editor_id}'


def _vapid_claims() -> dict[str, str]:
    """The ``sub`` claim must be a mailto:/https: URI identifying the sender."""
    sub = getattr(settings, 'VAPID_CLAIM_SUB', '') or 'mailto:admin@example.com'
    return {'sub': sub}


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

    Returns a short status string for observability — ``'throttled'``,
    ``'no-subscriptions'``, or ``'sent:N'`` where N is the count of
    subscriptions the push reached.
    """
    if owner_id == editor_id:
        return 'self-edit'

    private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    if not private_key:
        logger.warning('VAPID_PRIVATE_KEY is not configured; skipping push')
        return 'no-vapid-key'

    key = _throttle_key(owner_id, doc_id, editor_id)
    # ``cache.add`` is atomic: it succeeds only if the key is absent,
    # which is exactly the "first edit in the window wins" semantics we
    # want. Subsequent edits within 15 min return False and short-circuit.
    if not cache.add(key, '1', timeout=EDIT_NOTIFICATION_THROTTLE_SECONDS):
        return 'throttled'

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
