from django.contrib.auth.models import AbstractUser
from django.db import models

from common_utils.utils import generate_random_color


def get_user_avatar_filepath(instance: 'User', filename: str) -> str:
    return f'users/avatars/user_{instance.id}.webp'


class User(AbstractUser):
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

    def save(self, *args, **kwargs):
        if not self.color:
            self.color = generate_random_color()
        super().save(*args, **kwargs)
