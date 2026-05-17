from datetime import datetime, timedelta

from celery import shared_task
from django.core.mail import send_mail

from users.constants import (
    EMAIL_VERIFY_MAIL_BODY,
    EMAIL_VERIFY_MAIL_TITLE,
    EMAIL_VERIFY_REQUEST_LIFETIME,
    PASSWORD_RESET_MAIL_BODY,
    PASSWORD_RESET_MAIL_TITLE,
    PASSWORD_RESET_REQUEST_LIFETIME,
)


@shared_task
def send_email_verify(email: str, token: str) -> None:
    send_mail(
        EMAIL_VERIFY_MAIL_TITLE,
        EMAIL_VERIFY_MAIL_BODY.format(token),
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )


@shared_task
def send_password_reset_email(email: str, token: str) -> None:
    send_mail(
        PASSWORD_RESET_MAIL_TITLE,
        PASSWORD_RESET_MAIL_BODY.format(token, PASSWORD_RESET_REQUEST_LIFETIME),
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )


@shared_task
def expire_old_register_requests() -> int:
    from users.models import RegisterRequest

    threshold = datetime.now() - timedelta(minutes=EMAIL_VERIFY_REQUEST_LIFETIME)
    updated = RegisterRequest.objects.filter(
        status=RegisterRequest.RegisterRequestStatus.WAIT,
        dt_created__lt=threshold,
    ).update(status=RegisterRequest.RegisterRequestStatus.EXPIRED)

    return updated


@shared_task
def expire_old_password_reset_requests() -> int:
    from users.models import PasswordResetRequest

    threshold = datetime.now() - timedelta(minutes=PASSWORD_RESET_REQUEST_LIFETIME)
    updated = PasswordResetRequest.objects.filter(
        status=PasswordResetRequest.PasswordResetRequestStatus.WAIT,
        dt_created__lt=threshold,
    ).update(status=PasswordResetRequest.PasswordResetRequestStatus.EXPIRED)

    return updated
