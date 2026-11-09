from smtplib import SMTPException

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task(autoretry_for=(SMTPException, OSError), retry_backoff=True, max_retries=3, ignore_result=True)
def send_code_email(email, code):
    """Письмо с кодом. Ретраи с бэкоффом, если SMTP временно недоступен."""
    minutes = settings.OTP_CODE_TTL // 60
    send_mail(
        subject=f"Код для входа: {code}",
        message=f"Ваш код для входа: {code}\n\nКод действует {minutes} мин. "
                f"Если вы не запрашивали код — просто проигнорируйте письмо.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
