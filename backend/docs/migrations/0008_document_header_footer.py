from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0007_document_page_layout'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='page_height',
            field=models.PositiveIntegerField(
                db_default=1056, default=1056,
                verbose_name='Высота страницы (px)',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='header_content',
            field=models.TextField(
                blank=True, db_default='', default='',
                verbose_name='Колонтитул сверху (JSON)',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='footer_content',
            field=models.TextField(
                blank=True, db_default='', default='',
                verbose_name='Колонтитул снизу (JSON)',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='show_page_numbers',
            field=models.BooleanField(
                db_default=False, default=False,
                verbose_name='Показывать номера страниц',
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='page_number_start',
            field=models.PositiveIntegerField(
                db_default=1, default=1,
                verbose_name='Начальный номер страницы',
            ),
        ),
    ]
