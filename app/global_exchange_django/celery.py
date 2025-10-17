import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "global_exchange_django.settings")

app = Celery("global_exchange_django")
# Lee configuración desde settings.py con prefijo CELERY_*
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
