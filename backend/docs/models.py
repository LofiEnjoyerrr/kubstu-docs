from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import UniqueConstraint

from common_utils.orm.mixins import AutoDateMixin
from users.models import User


class Document(AutoDateMixin):
    title = models.CharField(max_length=255, verbose_name='Заголовок документа')
    content = models.TextField(blank=True, default='', db_default='', verbose_name='Текст документа')

    is_public = models.BooleanField(
        default=False,
        db_default=False,
        verbose_name='Публичный',
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Владелец документа',
    )

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'

    def __str__(self):
        return self.title


class DocumentAccess(AutoDateMixin):
    ROLE_CHOICES = [
        ('viewer', 'Наблюдатель'),
        ('editor', 'Редактор'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accesses', verbose_name='Пользователь')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='accesses', verbose_name='Документ')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='Роль доступа')

    class Meta:
        verbose_name = 'Доступ к документу'
        verbose_name_plural = 'Доступы к документам'

        constraints = [
            UniqueConstraint(fields=['user', 'document'], name='unique_user_document'),
        ]
