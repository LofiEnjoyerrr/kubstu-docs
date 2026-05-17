from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0003_document_is_public'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='version',
            field=models.PositiveIntegerField(db_default=0, default=0, verbose_name='Версия'),
        ),
    ]
