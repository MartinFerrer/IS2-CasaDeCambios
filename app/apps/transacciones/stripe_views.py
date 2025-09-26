"""Vistas para integración con Stripe para pagos internacionales.

Este módulo maneja la creación de PaymentIntents de Stripe, procesamiento
de pagos con tarjetas internacionales y webhooks de Stripe.
"""

import json
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import StripePayment, Transaccion

# Configurar Stripe con la clave secreta
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
@require_POST
def create_stripe_payment_intent(request: HttpRequest) -> JsonResponse:
    """Crea un PaymentIntent de Stripe para una transacción de compra de divisa.

    Solo disponible para transacciones de tipo 'compra' donde el cliente
    paga en una moneda extranjera (como USD) para obtener divisas.

    Args:
        request: HttpRequest con datos JSON que incluye:
            - transaccion_id: ID de la transacción
            - currency: Moneda para el pago (USD, EUR, etc.)

    Returns:
        JsonResponse con client_secret para el frontend o error.

    """
    try:
        data = json.loads(request.body)
        transaccion_id = data.get("transaccion_id")
        currency = data.get("currency", "USD").upper()

        if not transaccion_id:
            return JsonResponse({"success": False, "error": "ID de transacción requerido"}, status=400)

        # Obtener la transacción
        cliente = getattr(request, "cliente", None)
        if not cliente:
            return JsonResponse({"success": False, "error": "No hay cliente asociado"}, status=400)

        transaccion = get_object_or_404(
            Transaccion,
            id_transaccion=transaccion_id,
            cliente=cliente,
            tipo_operacion="compra",  # Solo para compras
        )

        if transaccion.estado != "pendiente":
            return JsonResponse(
                {"success": False, "error": f"La transacción está en estado {transaccion.estado}"}, status=400
            )

        # Calcular el monto en la moneda solicitada
        # Para compras: el cliente paga el monto_origen (que está en PYG)
        # Necesitamos convertir a la moneda solicitada
        monto_pyg = transaccion.monto_origen

        # Aquí deberías implementar la conversión de PYG a la moneda solicitada
        # Por ahora, asumiremos una tasa fija de conversión
        # TODO: Implementar conversión real de tasas de cambio
        if currency == "USD":
            # Ejemplo: 1 USD = 7500 PYG (esto debería venir de tu API de tasas)
            monto_usd = monto_pyg / Decimal("7500")
            amount_cents = int(monto_usd * 100)  # Stripe usa centavos
        else:
            return JsonResponse({"success": False, "error": f"Moneda {currency} no soportada"}, status=400)

        # Crear o actualizar el registro de StripePayment
        stripe_payment, created = StripePayment.objects.get_or_create(
            cliente=cliente,
            defaults={
                "amount": monto_usd,
                "currency": currency,
                "status": "requires_payment_method",
                "metadata": json.dumps({"transaccion_id": str(transaccion_id), "tipo": "compra_divisa"}),
            },
        )

        # Crear PaymentIntent en Stripe
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata={
                    "transaccion_id": str(transaccion_id),
                    "cliente_id": str(cliente.id),
                    "tipo": "compra_divisa",
                },
                description=f"Compra de {transaccion.monto_destino} {transaccion.divisa_destino.codigo}",
            )

            # Actualizar el registro local
            stripe_payment.stripe_payment_intent_id = payment_intent.id
            stripe_payment.status = payment_intent.status
            stripe_payment.save()

            # Vincular la transacción con el pago Stripe
            if not transaccion.stripe_payment:
                transaccion.stripe_payment = stripe_payment
                transaccion.medio_pago = "stripe"
                transaccion.save()

            return JsonResponse(
                {
                    "success": True,
                    "client_secret": payment_intent.client_secret,
                    "amount": float(monto_usd),
                    "currency": currency,
                    "warning": "Stripe puede aplicar comisiones al pago",
                }
            )

        except stripe.error.StripeError as e:
            return JsonResponse({"success": False, "error": f"Error de Stripe: {e!s}"}, status=500)

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "Datos JSON inválidos"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Error interno: {e!s}"}, status=500)


@login_required
@require_GET
def stripe_payment_status(request: HttpRequest, payment_intent_id: str) -> JsonResponse:
    """Verifica el estado de un PaymentIntent de Stripe.

    Args:
        request: HttpRequest
        payment_intent_id: ID del PaymentIntent de Stripe

    Returns:
        JsonResponse con el estado del pago.

    """
    try:
        cliente = getattr(request, "cliente", None)
        if not cliente:
            return JsonResponse({"success": False, "error": "No hay cliente asociado"}, status=400)

        # Verificar que el pago pertenece al cliente
        stripe_payment = get_object_or_404(StripePayment, stripe_payment_intent_id=payment_intent_id, cliente=cliente)

        # Consultar el estado actual en Stripe
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # Actualizar el estado local
            stripe_payment.status = payment_intent.status
            stripe_payment.save()

            # Si el pago fue exitoso, actualizar la transacción
            if payment_intent.status == "succeeded":
                transaccion = Transaccion.objects.filter(stripe_payment=stripe_payment).first()

                if transaccion and transaccion.estado == "pendiente":
                    transaccion.estado = "completada"
                    transaccion.save()

            return JsonResponse(
                {
                    "success": True,
                    "status": payment_intent.status,
                    "amount_received": payment_intent.amount_received,
                    "currency": payment_intent.currency,
                }
            )

        except stripe.error.StripeError as e:
            return JsonResponse({"success": False, "error": f"Error de Stripe: {e!s}"}, status=500)

    except Exception as e:
        return JsonResponse({"success": False, "error": f"Error interno: {e!s}"}, status=500)


@csrf_exempt
@require_POST
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    """Endpoint para recibir webhooks de Stripe.

    Maneja eventos como payment_intent.succeeded, payment_intent.payment_failed, etc.

    Args:
        request: HttpRequest con el payload del webhook

    Returns:
        HttpResponse indicando si el webhook fue procesado correctamente.

    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # Manejar el evento
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        _handle_successful_payment(payment_intent)

    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        _handle_failed_payment(payment_intent)

    elif event["type"] == "payment_intent.requires_action":
        payment_intent = event["data"]["object"]
        _handle_requires_action(payment_intent)

    elif event["type"] == "payment_intent.canceled":
        payment_intent = event["data"]["object"]
        _handle_canceled_payment(payment_intent)

    # Eventos de Charge (más definitivos para contabilidad)
    elif event["type"] == "charge.succeeded":
        charge = event["data"]["object"]
        _handle_charge_succeeded(charge)

    elif event["type"] == "charge.failed":
        charge = event["data"]["object"]
        _handle_charge_failed(charge)

    # Eventos críticos de disputas/chargebacks
    elif event["type"] == "charge.dispute.created":
        dispute = event["data"]["object"]
        _handle_dispute_created(dispute)

    elif event["type"] == "charge.dispute.updated":
        dispute = event["data"]["object"]
        _handle_dispute_updated(dispute)

    # Eventos de reembolsos
    elif event["type"] == "charge.refunded":
        charge = event["data"]["object"]
        _handle_refund(charge)

    return HttpResponse(status=200)


def _handle_successful_payment(payment_intent):
    """Maneja un pago exitoso de Stripe.

    Args:
        payment_intent: Objeto PaymentIntent de Stripe

    """
    try:
        stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent["id"])

        # Actualizar el estado del pago
        stripe_payment.status = "succeeded"
        stripe_payment.save()

        # Actualizar la transacción asociada
        transaccion = Transaccion.objects.filter(stripe_payment=stripe_payment).first()

        if transaccion:
            transaccion.estado = "completada"
            transaccion.fecha_pago = stripe_payment.updated_at
            transaccion.save()

    except StripePayment.DoesNotExist:
        # Log del error - pago no encontrado en nuestra base de datos
        pass


def _handle_failed_payment(payment_intent):
    """Maneja un pago fallido de Stripe.

    Args:
        payment_intent: Objeto PaymentIntent de Stripe

    """
    try:
        stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent["id"])

        # Actualizar el estado del pago
        stripe_payment.status = "payment_failed"
        stripe_payment.save()

        # La transacción permanece en estado 'pendiente' para reintento

    except StripePayment.DoesNotExist:
        # Log del error - pago no encontrado en nuestra base de datos
        pass


def _handle_canceled_payment(payment_intent):
    """Maneja un pago cancelado de Stripe.

    Args:
        payment_intent: Objeto PaymentIntent de Stripe

    """
    try:
        stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent["id"])

        # Actualizar el estado del pago
        stripe_payment.status = "canceled"
        stripe_payment.save()

        # Actualizar la transacción asociada
        transaccion = Transaccion.objects.filter(stripe_payment=stripe_payment).first()

        if transaccion:
            transaccion.estado = "cancelada"
            transaccion.save()

    except StripePayment.DoesNotExist:
        # Log del error - pago no encontrado en nuestra base de datos
        pass


def _handle_requires_action(payment_intent):
    """Maneja pagos que requieren acción adicional (3D Secure, SCA).

    Args:
        payment_intent: Objeto PaymentIntent de Stripe

    """
    try:
        stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent["id"])
        stripe_payment.status = "requires_action"
        stripe_payment.save()

        # La transacción permanece pendiente hasta que se complete la autenticación

    except StripePayment.DoesNotExist:
        pass


def _handle_charge_succeeded(charge):
    """Maneja confirmación final de cargo exitoso.

    Args:
        charge: Objeto Charge de Stripe

    """
    try:
        # Buscar por payment_intent_id en el charge
        payment_intent_id = charge.get("payment_intent")
        if payment_intent_id:
            stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent_id)

            # Marcar como definitivamente exitoso
            stripe_payment.status = "charge_succeeded"
            stripe_payment.save()

            # Confirmar transacción como completada
            transaccion = Transaccion.objects.filter(stripe_payment=stripe_payment).first()
            if transaccion and transaccion.estado != "completada":
                transaccion.estado = "completada"
                transaccion.fecha_pago = stripe_payment.updated_at
                transaccion.save()

    except StripePayment.DoesNotExist:
        pass


def _handle_charge_failed(charge):
    """Maneja fallos en el cargo final.

    Args:
        charge: Objeto Charge de Stripe

    """
    try:
        payment_intent_id = charge.get("payment_intent")
        if payment_intent_id:
            stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent_id)
            stripe_payment.status = "charge_failed"
            stripe_payment.save()

    except StripePayment.DoesNotExist:
        pass


def _handle_dispute_created(dispute):
    """Maneja creación de disputas/chargebacks - CRÍTICO para casa de cambio.

    Args:
        dispute: Objeto Dispute de Stripe

    """
    try:
        charge_id = dispute.get("charge")
        if charge_id:
            # Buscar el pago asociado y marcar como disputado
            stripe_payment = StripePayment.objects.filter(
                stripe_payment_intent_id__in=stripe.Charge.retrieve(charge_id).payment_intent
            ).first()

            if stripe_payment:
                stripe_payment.status = "disputed"
                stripe_payment.save()

                # Marcar transacción como disputada - IMPORTANTE PARA CONTABILIDAD
                transaccion = Transaccion.objects.filter(stripe_payment=stripe_payment).first()
                if transaccion:
                    transaccion.estado = "disputada"
                    transaccion.save()

                # TODO: Notificar administradores inmediatamente
                # TODO: Congelar fondos relacionados si es necesario

    except Exception:
        # Log crítico - disputas deben ser manejadas sin fallos
        pass


def _handle_dispute_updated(dispute):
    """Maneja actualizaciones de disputas (resolución, escalamiento).

    Args:
        dispute: Objeto Dispute de Stripe

    """
    try:
        # Actualizar estado según resultado de la disputa
        charge_id = dispute.get("charge")
        dispute_status = dispute.get("status")

        if charge_id:
            stripe_payment = StripePayment.objects.filter(
                stripe_payment_intent_id__in=stripe.Charge.retrieve(charge_id).payment_intent
            ).first()

            if stripe_payment:
                if dispute_status == "won":
                    stripe_payment.status = "dispute_won"
                    # Reactivar transacción
                    transaccion = Transaccion.objects.filter(stripe_payment=stripe_payment).first()
                    if transaccion:
                        transaccion.estado = "completada"
                        transaccion.save()

                elif dispute_status == "lost":
                    stripe_payment.status = "dispute_lost"
                    # Mantener transacción como disputada

                stripe_payment.save()

    except Exception:
        pass


def _handle_refund(charge):
    """Maneja reembolsos de pagos.

    Args:
        charge: Objeto Charge de Stripe

    """
    try:
        payment_intent_id = charge.get("payment_intent")
        if payment_intent_id:
            stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent_id)
            stripe_payment.status = "refunded"
            stripe_payment.save()

            # Marcar transacción como reembolsada
            transaccion = Transaccion.objects.filter(stripe_payment=stripe_payment).first()
            if transaccion:
                transaccion.estado = "reembolsada"
                transaccion.save()

    except StripePayment.DoesNotExist:
        pass
