import os
from datetime import timedelta
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('KubSTU-Docs', include=['users.tasks'])

# Read all CELERY_* keys from Django settings (namespace strips the prefix).
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'expire-old-register-requests': {
        'task': 'users.tasks.expire_old_register_requests',
        'schedule': timedelta(hours=1),
    },
    'expire-old-password-reset-requests': {
        'task': 'users.tasks.expire_old_password_reset_requests',
        'schedule': timedelta(hours=1),
    },
}
