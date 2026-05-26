from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_passwordresetrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='FavoriteUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dt_created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('dt_updated', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_users', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favored_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['user__username', 'user__email'],
            },
        ),
        migrations.AddConstraint(
            model_name='favoriteuser',
            constraint=models.UniqueConstraint(fields=('owner', 'user'), name='unique_owner_favorite_user'),
        ),
    ]
