from django.db import migrations, models


def clear_default_status(apps, schema_editor):
    Document = apps.get_model('docs', 'Document')
    Document.objects.filter(status_text='В работе', status_color='#2563eb').update(status_text='')


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0009_document_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='status_text',
            field=models.CharField(
                blank=True,
                db_default='',
                default='',
                max_length=30,
                verbose_name='РЎС‚Р°С‚СѓСЃ РґРѕРєСѓРјРµРЅС‚Р°',
            ),
        ),
        migrations.RunPython(clear_default_status, migrations.RunPython.noop),
    ]
