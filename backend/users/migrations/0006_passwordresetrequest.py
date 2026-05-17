import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_remove_registerrequest_token_hash_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PasswordResetRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dt_created', models.DateTimeField(auto_now_add=True)),
                ('dt_updated', models.DateTimeField(auto_now=True)),
                ('token', models.CharField(max_length=64)),
                ('status', models.CharField(
                    choices=[
                        ('wait', 'Ожидание'),
                        ('expired', 'Просрочено'),
                        ('complete', 'Завершено'),
                    ],
                    db_default='wait',
                    default='wait',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='password_reset_requests',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Пользователь',
                )),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
