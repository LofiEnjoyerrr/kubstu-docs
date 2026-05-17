from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0002_alter_document_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='is_public',
            field=models.BooleanField(db_default=False, default=False, verbose_name='Публичный'),
        ),
    ]
