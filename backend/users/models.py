from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from common_utils.orm.mixins import AutoDateMixin
from common_utils.utils import generate_random_color
from users.tasks import send_email_verify


def get_user_avatar_filepath(instance: 'User', filename: str) -> str:
    return f'users/avatars/user_{instance.id}.webp'


class User(AbstractUser, AutoDateMixin):
    email = models.EmailField(unique=True)

    avatar = models.ImageField(
        max_length=120,
        upload_to=get_user_avatar_filepath,
        blank=True,
        default='',
        db_default='',
        verbose_name='Аватар',
    )

    color = models.CharField(
        max_length=7,
        blank=True,
        default=generate_random_color,
        db_default='#000000',
        verbose_name='Цвет пользователя',
    )


class RegisterRequest(AutoDateMixin):
    class RegisterRequestStatus(models.TextChoices):
        WAIT = 'wait', 'Ожидание'
        EXPIRED = 'expired', 'Просрочено'
        COMPLETE = 'complete', 'Завершено'

    email = models.EmailField()
    username = models.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    password = models.CharField(max_length=128)

    ip = models.GenericIPAddressField()

    status = models.CharField(
        choices=RegisterRequestStatus,
        default=RegisterRequestStatus.WAIT,
        db_default=RegisterRequestStatus.WAIT,
    )

    token_hash = models.CharField(max_length=128)

    def send_email_verify(self):
        send_email_verify.delay(self.email, self.token_hash)
