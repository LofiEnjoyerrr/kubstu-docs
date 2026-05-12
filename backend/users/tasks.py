from celery import shared_task
from django.core.mail import send_mail

from users.constants import EMAIL_VERIFY_MAIL_BODY, EMAIL_VERIFY_MAIL_TITLE


@shared_task
def send_email_verify(email: str, token: str) -> None:
    send_mail(
        EMAIL_VERIFY_MAIL_TITLE,
        EMAIL_VERIFY_MAIL_BODY.format(token),
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )
