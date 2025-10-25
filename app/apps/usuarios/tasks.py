from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .models import Cliente


def enviar_notificacion_cambio_cotizacion(cliente_id, datos_cambio_cotizacion):
    """Envía notificación por email al cliente sobre cambios en la cotización de divisas

    Args:
        cliente_id: ID del cliente a notificar
        datos_cambio_cotizacion: Diccionario con información del cambio de cotización

    """
    try:
        cliente = Cliente.objects.get(id=cliente_id)

        asunto = "Actualización de Cotización - Global Exchange Services"

        contexto = {
            "nombre_cliente": cliente.nombre,
            "divisa_origen": datos_cambio_cotizacion["divisa_origen"],
            "divisa_destino": datos_cambio_cotizacion["divisa_destino"],
            "cotizacion_anterior": datos_cambio_cotizacion.get("cotizacion_anterior"),
            "cotizacion_nueva": datos_cambio_cotizacion.get("cotizacion_nueva"),
            "tasa_compra_anterior": datos_cambio_cotizacion.get("tasa_compra_anterior"),
            "tasa_compra_nueva": datos_cambio_cotizacion.get("tasa_compra_nueva"),
            "tasa_venta_anterior": datos_cambio_cotizacion.get("tasa_venta_anterior"),
            "tasa_venta_nueva": datos_cambio_cotizacion.get("tasa_venta_nueva"),
            "fecha_actualizacion": datos_cambio_cotizacion.get("fecha_actualizacion"),
            "variacion_porcentaje": datos_cambio_cotizacion.get("variacion_porcentaje"),
        }

        mensaje_html = render_to_string("usuarios/emails/notificacion_cambio_cotizacion.html", contexto)
        mensaje_plano = strip_tags(mensaje_html)

        send_mail(
            subject=asunto,
            message=mensaje_plano,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[cliente.email],
            html_message=mensaje_html,
            fail_silently=False,
        )

        return f"Notificación enviada a {cliente.email}"

    except Cliente.DoesNotExist:
        return f"Cliente con ID {cliente_id} no encontrado"
    except Exception as error:
        return f"Error enviando notificación: {error!s}"
