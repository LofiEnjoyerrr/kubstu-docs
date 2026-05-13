from celery import Celery
from django.conf import settings

app = Celery(
    'KubSTU-Docs',
    include=['users.tasks'],
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.autodiscover_tasks()
