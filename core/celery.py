import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("otp_auth")
# Все настройки Celery берутся из settings.py с префиксом CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
