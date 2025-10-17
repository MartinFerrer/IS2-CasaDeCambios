from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.operaciones.models import TasaCambioHistorial

from .models import PreferenciaNotificacion

logger = logging.getLogger(__name__)


def ventana_para_frecuencia(freq_key: str) -> timedelta:
    if freq_key == "diario":
        # return timedelta(days=1) valor default
        return timedelta(seconds=5)  # para pruebas y mostrar rapidamente durante la presentacion
    if freq_key == "semanal":
        return timedelta(weeks=1)
    return timedelta(days=30)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_single_notification(self, preferencia_id: int, subject: str, text_body: str, html_body: str):
    """Envía un correo ya compuesto para una preferencia dada.
    Actualiza preferencia.ultimo_envio si el envío fue exitoso.
    """
    try:
        pref = PreferenciaNotificacion.objects.select_related("cliente").get(pk=preferencia_id)
    except PreferenciaNotificacion.DoesNotExist:
        logger.warning("PreferenciaNotificacion %s no encontrada", preferencia_id)
        return

    email_to = getattr(pref.cliente, "email", None)
    if not email_to:
        logger.info("Cliente %s no tiene email, omitiendo notificación", pref.cliente)
        return

    msg = EmailMultiAlternatives(subject, text_body, getattr(settings, "DEFAULT_FROM_EMAIL", None), [email_to])
    if html_body:
        msg.attach_alternative(html_body, "text/html")

    try:
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Error enviando email a %s: %s", email_to, exc)
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Máximo reintentos alcanzado para preferencia %s", preferencia_id)
        return

    # actualizar ultimo_envio tras envío exitoso
    try:
        with transaction.atomic():
            pref.ultimo_envio = timezone.now()
            pref.save(update_fields=["ultimo_envio"])
    except Exception:
        logger.exception("Error actualizando ultimo_envio para preferencia %s", preferencia_id)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def send_grouped_notifications(self, frecuencia: str):
    """Tarea que agrupa cambios y delega el envío por cliente.
    - Busca PreferenciaNotificacion habilitadas con la frecuencia dada.
    - Para cada preferencia arma el resumen (text/html) y encola send_single_notification.
    """
    ahora = timezone.now()
    ventana = ventana_para_frecuencia(frecuencia)

    prefs_qs = PreferenciaNotificacion.objects.filter(habilitado=True, frecuencia=frecuencia).select_related("cliente")
    for pref in prefs_qs.iterator():
        try:
            last = pref.ultimo_envio or (ahora - ventana)
            cambios_qs = (
                TasaCambioHistorial.objects.select_related("divisa_origen", "divisa_destino")
                .filter(fecha_registro__gt=last)
                .order_by("fecha_registro")
            )

            # Si tu historial no guarda relación con cliente, filtra según las tasas relevantes
            # ejemplo: .filter(tasa__cliente=pref.cliente)  <-- adaptar según tu modelo
            cambios = list(cambios_qs)
            if not cambios:
                continue

            context = {
                "cliente": pref.cliente,
                "changes": cambios,
                "since": last,
                "until": ahora,
                "frecuencia": frecuencia,
            }
            subject = f"Resumen de cambios en tasas ({frecuencia.capitalize()})"
            text_body = render_to_string("emails/tasa_cambios_summary.txt", context)
            html_body = render_to_string("emails/tasa_cambios_summary.html", context)

            # Encolar envío por cliente: pasamos preferencia.id para que la tarea actualice ultimo_envio
            send_single_notification.delay(pref.id, subject, text_body, html_body)

        except Exception as exc:
            logger.exception("Error procesando preferencia %s: %s", getattr(pref, "id", "n/a"), exc)
            # continuar con la siguiente preferencia
            continue
