import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "global_exchange_django.settings")

app = Celery("global_exchange_django")
# Lee configuración desde settings.py con prefijo CELERY_*
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# (Opcional) ejemplo de schedule con Beat — puedes mover esto a settings.py si prefieres
app.conf.beat_schedule = {
    "notifs-diarias": {
        "task": "apps.usuarios.tasks.send_grouped_notifications",
        "schedule": 60 * 60 * 24,  # cada 24 horas (ajusta a crontab si quieres hora exacta)
        "args": ("diario",),
    },
    "notifs-semanales": {
        "task": "apps.usuarios.tasks.send_grouped_notifications",
        "schedule": 60 * 60 * 24 * 7,
        "args": ("semanal",),
    },
    "notifs-mensuales": {
        "task": "apps.usuarios.tasks.send_grouped_notifications",
        "schedule": 60 * 60 * 24 * 30,
        "args": ("mensual",),
    },
}