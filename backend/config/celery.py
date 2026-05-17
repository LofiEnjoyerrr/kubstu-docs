from celery import Celery
from celery.schedules import crontab
from django.conf import settings

app = Celery(
    'KubSTU-Docs',
    include=['users.tasks'],
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'expire-old-register-requests': {
        'task': 'users.tasks.expire_old_register_requests',
        'schedule': crontab(minute=0),
    },
    'expire-old-password-reset-requests': {
        'task': 'users.tasks.expire_old_password_reset_requests',
        'schedule': crontab(minute=0),
    },
}
