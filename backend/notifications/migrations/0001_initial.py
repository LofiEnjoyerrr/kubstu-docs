import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PushSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dt_created', models.DateTimeField(auto_now_add=True)),
                ('dt_updated', models.DateTimeField(auto_now=True)),
                ('endpoint', models.URLField(max_length=2048, unique=True, verbose_name='Endpoint push-сервиса')),
                ('p256dh', models.CharField(max_length=255, verbose_name='Публичный ключ клиента (p256dh)')),
                ('auth', models.CharField(max_length=255, verbose_name='Аутентификационный секрет')),
                ('user_agent', models.CharField(blank=True, db_default='', default='', max_length=512, verbose_name='User-Agent на момент подписки')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='push_subscriptions', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Push-подписка',
                'verbose_name_plural': 'Push-подписки',
            },
        ),
    ]
