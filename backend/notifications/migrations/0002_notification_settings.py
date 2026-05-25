import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0008_document_header_footer'),
        ('notifications', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentNotificationSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dt_created', models.DateTimeField(auto_now_add=True)),
                ('dt_updated', models.DateTimeField(auto_now=True)),
                ('edit_notifications_enabled', models.BooleanField(db_default=True, default=True, verbose_name='Уведомления о редактировании документа')),
                ('document', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_settings', to='docs.document', verbose_name='Документ')),
            ],
            options={
                'verbose_name': 'Настройки уведомлений документа',
                'verbose_name_plural': 'Настройки уведомлений документов',
            },
        ),
        migrations.CreateModel(
            name='UserNotificationSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dt_created', models.DateTimeField(auto_now_add=True)),
                ('dt_updated', models.DateTimeField(auto_now=True)),
                ('edit_notifications_enabled', models.BooleanField(db_default=True, default=True, verbose_name='Уведомления о редактировании документов')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_settings', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Настройки уведомлений пользователя',
                'verbose_name_plural': 'Настройки уведомлений пользователей',
            },
        ),
    ]
