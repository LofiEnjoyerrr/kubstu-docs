from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0006_alter_comment_author_alter_comment_document'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='page_width',
            field=models.PositiveIntegerField(db_default=816, default=816, verbose_name='Ширина страницы (px)'),
        ),
        migrations.AddField(
            model_name='document',
            name='margin_top',
            field=models.PositiveIntegerField(db_default=96, default=96, verbose_name='Верхний отступ (px)'),
        ),
        migrations.AddField(
            model_name='document',
            name='margin_right',
            field=models.PositiveIntegerField(db_default=96, default=96, verbose_name='Правый отступ (px)'),
        ),
        migrations.AddField(
            model_name='document',
            name='margin_bottom',
            field=models.PositiveIntegerField(db_default=96, default=96, verbose_name='Нижний отступ (px)'),
        ),
        migrations.AddField(
            model_name='document',
            name='margin_left',
            field=models.PositiveIntegerField(db_default=96, default=96, verbose_name='Левый отступ (px)'),
        ),
    ]
