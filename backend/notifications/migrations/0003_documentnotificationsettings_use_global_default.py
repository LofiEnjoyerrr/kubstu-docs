from django.db import migrations, models


def mark_explicit_disabled_documents(apps, schema_editor):
    DocumentNotificationSettings = apps.get_model('notifications', 'DocumentNotificationSettings')
    DocumentNotificationSettings.objects.filter(
        edit_notifications_enabled=False,
    ).update(use_global_default=False)


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_notification_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentnotificationsettings',
            name='use_global_default',
            field=models.BooleanField(
                db_default=True,
                default=True,
                verbose_name='Использовать глобальную настройку',
            ),
        ),
        migrations.RunPython(mark_explicit_disabled_documents, migrations.RunPython.noop),
    ]
