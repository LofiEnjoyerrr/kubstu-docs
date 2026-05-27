from django.db import models

from common_utils.orm.mixins import AutoDateMixin
from docs.models import Document
from users.models import User


class PushSubscription(AutoDateMixin):
    """
    One Web Push subscription belonging to a user. A single user can have
    many subscriptions (one per browser / device they've opted-in from), so
    the unique key is the ``endpoint`` URL — that's what the browser uses
    to identify the subscription on its side too.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='push_subscriptions',
        verbose_name='Пользователь',
    )

    endpoint = models.URLField(
        max_length=2048,
        unique=True,
        verbose_name='Endpoint push-сервиса',
    )
    p256dh = models.CharField(
        max_length=255,
        verbose_name='Публичный ключ клиента (p256dh)',
    )
    auth = models.CharField(
        max_length=255,
        verbose_name='Аутентификационный секрет',
    )

    user_agent = models.CharField(
        max_length=512,
        blank=True,
        default='',
        db_default='',
        verbose_name='User-Agent на момент подписки',
    )

    class Meta:
        verbose_name = 'Push-подписка'
        verbose_name_plural = 'Push-подписки'

    def __str__(self) -> str:
        return f'{self.user_id} → {self.endpoint[:60]}'


class UserNotificationSettings(AutoDateMixin):
    """Owner-wide notification preferences."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name='Пользователь',
    )
    edit_notifications_enabled = models.BooleanField(
        default=True,
        db_default=True,
        verbose_name='Уведомления о редактировании документов',
    )

    class Meta:
        verbose_name = 'Настройки уведомлений пользователя'
        verbose_name_plural = 'Настройки уведомлений пользователей'

    def __str__(self) -> str:
        return f'Настройки уведомлений {self.user}'


class DocumentNotificationSettings(AutoDateMixin):
    """Per-document notification preferences for document owners."""

    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name='Документ',
    )
    edit_notifications_enabled = models.BooleanField(
        default=True,
        db_default=True,
        verbose_name='Уведомления о редактировании документа',
    )
    use_global_default = models.BooleanField(
        default=True,
        db_default=True,
        verbose_name='Использовать глобальную настройку',
    )

    class Meta:
        verbose_name = 'Настройки уведомлений документа'
        verbose_name_plural = 'Настройки уведомлений документов'

    def __str__(self) -> str:
        return f'Настройки уведомлений документа {self.document_id}'
