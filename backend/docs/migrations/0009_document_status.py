from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0008_document_header_footer'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='status_text',
            field=models.CharField(
                blank=True,
                db_default='',
                default='',
                max_length=30,
                verbose_name='Статус документа',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='status_color',
            field=models.CharField(
                db_default='#2563eb',
                default='#2563eb',
                max_length=7,
                verbose_name='Цвет статуса',
            ),
        ),
    ]
