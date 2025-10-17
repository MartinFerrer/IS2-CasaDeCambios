"""Vistas para transacciones de cambio de divisas.

Este módulo proporciona vistas para simular el cambio de divisas y para comprar y vender.
También incluye el CRUD de medios de pago para los clientes.
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Dict

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from apps.operaciones.models import Divisa, TasaCambio
from apps.operaciones.templatetags.custom_filters import strip_trailing_zeros
from apps.seguridad.decorators import client_required
from apps.usuarios.models import Cliente

from .models import BilleteraElectronica, CuentaBancaria, EntidadFinanciera, TarjetaCredito, Transaccion


def obtener_medio_financiero_por_identificador(identificador, cliente):
    """Obtiene el objeto de medio financiero basado en el identificador.
    
    Args:
        identificador: String como 'tarjeta_1', 'cuenta_2', 'billetera_3', etc.
        cliente: Objeto Cliente al que pertenece el medio
        
    Returns:
        Objeto del medio financiero (TarjetaCredito, CuentaBancaria, BilleteraElectronica) o None
        
    """
    if not identificador or identificador == "efectivo":
        return None

    try:
        # Separar tipo y ID del identificador
        partes = identificador.split('_')
        if len(partes) != 2:
            return None

        tipo_medio, id_medio = partes
        id_medio = int(id_medio)

        # Buscar según el tipo
        if tipo_medio == "tarjeta":
            return TarjetaCredito.objects.get(id=id_medio, cliente=cliente)
        elif tipo_medio == "cuenta":
            return CuentaBancaria.objects.get(id=id_medio, cliente=cliente)
        elif tipo_medio == "billetera":
            return BilleteraElectronica.objects.get(id=id_medio, cliente=cliente)

    except (ValueError, TarjetaCredito.DoesNotExist, CuentaBancaria.DoesNotExist, BilleteraElectronica.DoesNotExist):
        pass

    return None


def obtener_nombre_medio(medio_id, cliente):
    """Obtiene el nombre legible de un medio de pago/cobro con su alias real.

    :param medio_id: ID del medio de pago/cobro (ej: 'tarjeta_1', 'cuenta_2', 'efectivo')
    :param cliente: Instancia del cliente para buscar el medio
    :return: Nombre legible del medio con alias (ej: 'TC - Visa *1234')
    """
    if medio_id == "efectivo":
        return "Efectivo"
    elif medio_id == "stripe_new":
        return "Tarjeta Internacional (Stripe)"

    try:
        if medio_id.startswith("stripe_"):
            return "Tarjeta Internacional (Stripe) - Guardada"
        elif medio_id.startswith("tarjeta_"):
            medio_pk = medio_id.replace("tarjeta_", "")
            tarjeta = TarjetaCredito.objects.get(pk=medio_pk, cliente=cliente)
            return "TC - " + tarjeta.alias
        elif medio_id.startswith("cuenta_"):
            medio_pk = medio_id.replace("cuenta_", "")
            cuenta = CuentaBancaria.objects.get(pk=medio_pk, cliente=cliente)
            return "Cuenta - " + cuenta.alias
        elif medio_id.startswith("billetera_"):
            medio_pk = medio_id.replace("billetera_", "")
            billetera = BilleteraElectronica.objects.get(pk=medio_pk, cliente=cliente)
            return "Billetera - " + billetera.alias
    except Exception:
        # Si no se encuentra el medio, mostrar nombre genérico
        if medio_id.startswith("stripe_"):
            return "Tarjeta Internacional"
        elif medio_id.startswith("tarjeta_"):
            return "Tarjeta de Crédito"
        elif medio_id.startswith("cuenta_"):
            return "Cuenta Bancaria"
        elif medio_id.startswith("billetera_"):
            return "Billetera Electrónica"

    return "Método desconocido"


def _get_stripe_fixed_fee_pyg() -> Decimal:
    """Calcula la comisión fija de Stripe (0.30 USD) convertida a PYG usando la tasa vigente."""
    from django.conf import settings

    from apps.operaciones.models import TasaCambio

    try:
        # Obtener tasa USD/PYG vigente
        tasa_cambio = TasaCambio.objects.filter(
            divisa_origen__codigo="PYG", divisa_destino__codigo="USD", activo=True
        ).first()

        if tasa_cambio:
            # Convertir 0.30 USD a PYG
            tasa_venta = tasa_cambio.tasa_venta
            fee_pyg = settings.STRIPE_FIXED_FEE_USD * tasa_venta
            return fee_pyg
        else:
            # Fallback: usar tasa aproximada si no hay tasa activa
            return settings.STRIPE_FIXED_FEE_USD * Decimal("7000")  # ~7000 PYG/USD
    except Exception:
        # Fallback en caso de error
        return settings.STRIPE_FIXED_FEE_USD * Decimal("7000")


def _get_payment_commission(metodo_pago: str, cliente, tipo: str) -> Decimal:
    """Calcula la comisión del medio de pago."""
    from django.conf import settings

    # Stripe (tarjetas internacionales)
    if metodo_pago == "stripe_new" or metodo_pago.startswith("stripe_"):
        return settings.STRIPE_COMMISSION_RATE

    if metodo_pago.startswith("tarjeta_") and cliente:
        try:
            tarjeta_id = int(metodo_pago.split("_")[1])
            tarjeta = TarjetaCredito.objects.get(id=tarjeta_id, cliente=cliente)
            if tarjeta.entidad:
                return tarjeta.entidad.comision_compra if tipo == "compra" else tarjeta.entidad.comision_venta
            return Decimal("5.0")
        except (ValueError, TarjetaCredito.DoesNotExist):
            return Decimal("5.0")
    elif metodo_pago.startswith("cuenta_") and cliente:
        try:
            cuenta_id = int(metodo_pago.split("_")[1])
            cuenta = CuentaBancaria.objects.get(id=cuenta_id, cliente=cliente)
            if cuenta.entidad:
                return cuenta.entidad.comision_compra if tipo == "compra" else cuenta.entidad.comision_venta
            return Decimal("0.0")
        except (ValueError, CuentaBancaria.DoesNotExist):
            return Decimal("0.0")
    elif metodo_pago.startswith("billetera_") and cliente:
        try:
            billetera_id = int(metodo_pago.split("_")[1])
            billetera = BilleteraElectronica.objects.get(id=billetera_id, cliente=cliente)
            if billetera.entidad:
                return billetera.entidad.comision_compra if tipo == "compra" else billetera.entidad.comision_venta
            return Decimal("3.0")
        except (ValueError, BilleteraElectronica.DoesNotExist):
            return Decimal("3.0")
    else:
        comisiones_medios = {
            "efectivo": Decimal("0.0"),
            "cuenta": Decimal("0.0"),
            "tarjeta": Decimal("5.0"),
            "billetera": Decimal("3.0"),
            "stripe": settings.STRIPE_COMMISSION_RATE,
        }
        if metodo_pago.startswith("tarjeta"):
            return comisiones_medios["tarjeta"]
        elif metodo_pago.startswith("cuenta"):
            return comisiones_medios["cuenta"]
        elif metodo_pago.startswith("billetera"):
            return comisiones_medios["billetera"]
        elif metodo_pago.startswith("stripe"):
            return comisiones_medios["stripe"]
        return comisiones_medios["efectivo"]


def _get_collection_commission(metodo_cobro: str, cliente, tipo: str) -> Decimal:
    """Calcula la comisión del medio de cobro."""
    if metodo_cobro.startswith("tarjeta_") and cliente:
        try:
            tarjeta_id = int(metodo_cobro.split("_")[1])
            tarjeta = TarjetaCredito.objects.get(id=tarjeta_id, cliente=cliente)
            if tarjeta.entidad:
                return tarjeta.entidad.comision_compra if tipo == "compra" else tarjeta.entidad.comision_venta
            return Decimal("5.0")
        except (ValueError, TarjetaCredito.DoesNotExist):
            return Decimal("5.0")
    elif metodo_cobro.startswith("cuenta_") and cliente:
        try:
            cuenta_id = int(metodo_cobro.split("_")[1])
            cuenta = CuentaBancaria.objects.get(id=cuenta_id, cliente=cliente)
            if cuenta.entidad:
                return cuenta.entidad.comision_compra if tipo == "compra" else cuenta.entidad.comision_venta
            return Decimal("0.0")
        except (ValueError, CuentaBancaria.DoesNotExist):
            return Decimal("0.0")
    elif metodo_cobro.startswith("billetera_") and cliente:
        try:
            billetera_id = int(metodo_cobro.split("_")[1])
            billetera = BilleteraElectronica.objects.get(id=billetera_id, cliente=cliente)
            if billetera.entidad:
                return billetera.entidad.comision_compra if tipo == "compra" else billetera.entidad.comision_venta
            return Decimal("3.0")
        except (ValueError, BilleteraElectronica.DoesNotExist):
            return Decimal("3.0")
    else:
        comisiones_medios = {
            "efectivo": Decimal("0.0"),
            "cuenta": Decimal("0.0"),
            "tarjeta": Decimal("5.0"),
            "billetera": Decimal("3.0"),
        }
        if metodo_cobro.startswith("tarjeta"):
            return comisiones_medios["tarjeta"]
        elif metodo_cobro.startswith("cuenta"):
            return comisiones_medios["cuenta"]
        elif metodo_cobro.startswith("billetera"):
            return comisiones_medios["billetera"]
        return comisiones_medios["efectivo"]


def _compute_simulation(params: Dict, request) -> Dict:
    """Cálculo centralizado de la simulación.

    params: dict con keys: monto (float), divisa_seleccionada, tipo_operacion,
    metodo_pago, metodo_cobro
    request: HttpRequest que incluye el cliente en request.cliente (del middleware)

    Todas las transacciones son desde/hacia PYG:
    - Compra: cliente especifica monto de divisa extranjera que desea y se calcula el precio en PYG
    - Venta: cliente da divisa seleccionada y recibe PYG
    """
    monto = float(params.get("monto") or 0)
    divisa_seleccionada = params.get("divisa_seleccionada") or "USD"
    tipo = params.get("tipo_operacion") or "compra"
    metodo_pago = params.get("metodo_pago") or "efectivo"
    metodo_cobro = params.get("metodo_cobro") or "efectivo"

    # Obtener cliente del middleware para descuentos
    cliente = getattr(request, "cliente", None)

    # Determinar monedas origen y destino según tipo de operación
    moneda_origen = divisa_seleccionada
    moneda_destino = "PYG"

    # Buscar tasa de cambio activa (siempre con PYG como origen en la BD)
    tasa_cambio = None
    try:
        tasa_cambio = TasaCambio.objects.filter(
            divisa_origen__codigo="PYG", divisa_destino__codigo=divisa_seleccionada, activo=True
        ).first()
    except Exception:
        pass

    # Si no hay tasa de cambio, usar valores por defecto
    if not tasa_cambio:
        rates_to_pyg = {"USD": 7000.0, "EUR": 7600.0, "BRL": 1300.0}
        pb_dolar = Decimal(str(rates_to_pyg.get(divisa_seleccionada, 7000.0)))
        comision_com = Decimal("50.0")
        comision_vta = Decimal("75.0")
    else:
        pb_dolar = tasa_cambio.precio_base
        comision_com = tasa_cambio.comision_compra
        comision_vta = tasa_cambio.comision_venta

    # Obtener descuento por segmento del cliente
    pordes = Decimal("0.0")
    if cliente and cliente.tipo_cliente:
        pordes = cliente.tipo_cliente.descuento_sobre_comision

    # Obtener comisiones de medios
    comision_medio_pago_valor = _get_payment_commission(metodo_pago, cliente, tipo)
    comision_medio_cobro_valor = _get_collection_commission(metodo_cobro, cliente, tipo)

    # Comisión fija adicional para Stripe (solo para pagos)
    stripe_fixed_fee = Decimal("0.0")
    if metodo_pago == "stripe_new" or metodo_pago.startswith("stripe_"):
        stripe_fixed_fee = _get_stripe_fixed_fee_pyg()

    # Calcular según las fórmulas corregidas
    if tipo == "compra":
        # Para compra: el usuario especifica cuánta divisa extranjera desea
        # y calculamos cuántos guaraníes necesita
        comision_efectiva = comision_com - (comision_com * pordes / Decimal("100"))
        tc_efectiva = pb_dolar + comision_efectiva

        # monto = cantidad de divisa extranjera deseada
        # converted = cantidad de guaraníes necesarios (sin comisión de medio)
        converted = monto * float(tc_efectiva)
        comision_medio_pago = Decimal(str(converted)) * comision_medio_pago_valor / Decimal("100")

        # Para Stripe: agregar comisión fija además de la comisión porcentual
        total_comision_medio = comision_medio_pago + stripe_fixed_fee
        total = converted + float(total_comision_medio)  # Total en guaraníes a pagar

        comision_final = float(comision_efectiva)
        total_antes_comision_medio = converted
        tasa_display = float(tc_efectiva)
        comision_medio_cobro = Decimal("0.0")
    else:  # venta
        comision_efectiva = comision_vta - (comision_vta * pordes / Decimal("100"))
        tc_efectiva = pb_dolar - comision_efectiva
        converted = monto * float(tc_efectiva)
        comision_final = float(comision_efectiva)
        total_antes_comision_medio = converted
        comision_medio_pago = Decimal("0.0")
        comision_medio_cobro = Decimal(str(total_antes_comision_medio)) * comision_medio_cobro_valor / Decimal("100")
        total = total_antes_comision_medio - float(comision_medio_cobro)
        tasa_display = float(tc_efectiva)
        stripe_fixed_fee = Decimal("0.0")  # Para venta no se aplica Stripe

    # Determinar tipos de medios para display
    tipo_medio_pago = "efectivo"
    if metodo_pago.startswith("tarjeta"):
        tipo_medio_pago = "tarjeta"
    elif metodo_pago.startswith("cuenta"):
        tipo_medio_pago = "cuenta"
    elif metodo_pago.startswith("billetera"):
        tipo_medio_pago = "billetera"
    elif metodo_pago == "stripe_new" or metodo_pago.startswith("stripe_"):
        tipo_medio_pago = "stripe"

    tipo_medio_cobro = "efectivo"
    if metodo_cobro.startswith("tarjeta"):
        tipo_medio_cobro = "tarjeta"
    elif metodo_cobro.startswith("cuenta"):
        tipo_medio_cobro = "cuenta"
    elif metodo_cobro.startswith("billetera"):
        tipo_medio_cobro = "billetera"

    return {
        "monto_original": round(monto, 6),
        "moneda_origen": moneda_origen,
        "moneda_destino": moneda_destino,
        "tasa_cambio": tasa_display,
        "monto_convertido": round(converted, 6),
        "comision_base": round(float(comision_com if tipo == "compra" else comision_vta), 6),
        "descuento": round(float(pordes), 2),
        "comision_final": round(comision_final, 6),
        "comision_medio_pago_tipo": tipo_medio_pago,
        "comision_medio_pago_porcentaje": float(comision_medio_pago_valor),
        "comision_medio_pago_monto": round(float(comision_medio_pago), 6),
        "comision_medio_cobro_tipo": tipo_medio_cobro,
        "comision_medio_cobro_porcentaje": float(comision_medio_cobro_valor),
        "comision_medio_cobro_monto": round(float(comision_medio_cobro), 6),
        "total_antes_comision_medio": round(total_antes_comision_medio, 6),
        "total": round(total, 6),
        "tipo_operacion": tipo,
        "metodo_pago": metodo_pago,
        "metodo_cobro": metodo_cobro,
        # Campos específicos para Stripe
        "stripe_fixed_fee": round(float(stripe_fixed_fee), 6),
        "stripe_fixed_fee_usd": float(settings.STRIPE_FIXED_FEE_USD) if stripe_fixed_fee > 0 else 0.0,
    }


def simular_cambio_view(request: HttpRequest) -> HttpResponse:
    """Página para simular operaciones de cambio.

    Presenta una página donde el usuario puede simular una operación de compra/venta
    de divisas. El cliente se obtiene automáticamente del middleware.

    :param request: Objeto HttpRequest.
    :type request: django.http.HttpRequest
    :return: HttpResponse con el template "simular_cambio.html" y el contexto que
        incluye las divisas disponibles y el cliente asociado (si existe).
    :rtype: django.http.HttpResponse
    """
    from django.conf import settings

    divisas = Divisa.objects.filter(estado="activo").exclude(codigo="PYG")

    context = {
        "divisas": divisas,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        # El cliente se obtiene automáticamente del middleware en request.cliente
    }
    return render(request, "simular_cambio.html", context)


@require_GET
def api_simular_cambio(request: HttpRequest) -> JsonResponse:
    """Devuelva una simulación en JSON basada en parámetros GET.

    Parámetros esperados en la querystring (GET):
    - monto: cantidad numérica a convertir.
    - divisa_seleccionada: código de la divisa destino (ej. "USD").
    - tipo_operacion: "compra" o "venta".
    - metodo_pago: identificador del medio de pago (ej. "efectivo", "tarjeta_1").
    - metodo_cobro: identificador del medio de cobro.

    :param request: HttpRequest con la querystring de simulación.
    :type request: django.http.HttpRequest
    :return: JsonResponse con los detalles de la simulación (tasas, comisiones, totales).
    :rtype: django.http.JsonResponse
    """
    params = request.GET.dict()
    result = _compute_simulation(params, request)
    return JsonResponse(result)


@require_GET
def api_clientes_usuario(request: HttpRequest) -> JsonResponse:
    """Devuelve en JSON la lista de clientes asociados al usuario autenticado.

    Si el usuario no está autenticado retorna una lista vacía.

    :param request: HttpRequest del usuario que solicita la lista.
    :type request: django.http.HttpRequest
    :return: JsonResponse con clave "clientes" conteniendo una lista de objetos
        con campos: id, nombre, ruc.
    :rtype: django.http.JsonResponse
    """
    if not request.user.is_authenticated:
        return JsonResponse({"clientes": []})

    clientes = Cliente.objects.filter(usuarios=request.user).values("id", "nombre", "ruc")
    return JsonResponse({"clientes": list(clientes)})


@require_GET
def api_medios_pago_cliente(request: HttpRequest, cliente_id: int) -> JsonResponse:
    """Retorna en JSON los medios de pago y cobro habilitados para un cliente.

    El endpoint valida que el cliente exista y que el usuario tenga acceso. También
    adapta la respuesta según el parámetro GET ``tipo`` ("compra" o "venta").

    :param request: HttpRequest que puede contener el parámetro GET "tipo".
    :type request: django.http.HttpRequest
    :param cliente_id: ID del cliente cuyos medios se consultan.
    :type cliente_id: int
    :return: JsonResponse con estructura {"medios_pago": [...], "medios_cobro": [...]}.
    :rtype: django.http.JsonResponse
    """
    try:
        cliente = Cliente.objects.get(pk=cliente_id)

        # Verificar que el usuario tiene acceso a este cliente
        if request.user.is_authenticated and cliente not in Cliente.objects.filter(usuarios=request.user):
            return JsonResponse({"error": "No tienes acceso a este cliente"}, status=403)

        # Obtener tipo de operación del parámetro GET
        tipo_operacion = request.GET.get("tipo", "compra")

        medios_pago = []
        medios_cobro = []

        # Configurar medios de pago según tipo de operación
        if tipo_operacion == "venta":
            # Para venta: SOLO efectivo para pago
            medios_pago.append(
                {
                    "id": "efectivo",
                    "tipo": "efectivo",
                    "nombre": "Efectivo",
                    "descripcion": "Pago en efectivo",
                    "comision": 0,  # 0%
                }
            )
        else:
            # Para compra: todos los medios de pago disponibles
            # Agregar efectivo por defecto para pago
            medios_pago.append(
                {
                    "id": "efectivo",
                    "tipo": "efectivo",
                    "nombre": "Efectivo",
                    "descripcion": "Pago en efectivo",
                    "comision": 0,  # 0%
                }
            )

            # Agregar tarjetas de crédito habilitadas para pago
            for tarjeta in TarjetaCredito.objects.filter(cliente=cliente, habilitado_para_pago=True):
                # Obtener comisión de la entidad si existe
                comision = 5  # Comisión por defecto para tarjetas
                if tarjeta.entidad:
                    if tipo_operacion == "compra":
                        comision = float(tarjeta.entidad.comision_compra)
                    else:
                        comision = float(tarjeta.entidad.comision_venta)

                medios_pago.append(
                    {
                        "id": f"tarjeta_{tarjeta.id}",
                        "tipo": "tarjeta",
                        "nombre": f"TC - {tarjeta.generar_alias()}",
                        "descripcion": f"Tarjeta terminada en {tarjeta.numero_tarjeta[-4:]}",
                        "comision": comision,
                        "entidad": tarjeta.entidad.nombre if tarjeta.entidad else "Sin entidad",
                    }
                )

            # Agregar cuentas bancarias habilitadas para pago
            for cuenta in CuentaBancaria.objects.filter(cliente=cliente, habilitado_para_pago=True):
                # Obtener comisión de la entidad si existe
                comision = 0  # Comisión por defecto para cuentas
                if cuenta.entidad:
                    if tipo_operacion == "compra":
                        comision = float(cuenta.entidad.comision_compra)
                    else:
                        comision = float(cuenta.entidad.comision_venta)

                entidad_nombre = cuenta.entidad.nombre if cuenta.entidad else "Sin banco"

                medios_pago.append(
                    {
                        "id": f"cuenta_{cuenta.id}",
                        "tipo": "cuenta",
                        "nombre": f"Cuenta - {cuenta.generar_alias()}",
                        "descripcion": f"Cuenta {entidad_nombre} terminada en {cuenta.numero_cuenta[-4:]}",
                        "comision": comision,
                        "entidad": cuenta.entidad.nombre if cuenta.entidad else "Sin entidad",
                    }
                )

            # Agregar tarjetas extranjeras (Stripe) - solo para compra
            medios_pago.append(
                {
                    "id": "stripe_new",
                    "tipo": "stripe",
                    "nombre": "💳 Tarjeta Internacional (Stripe)",
                    "descripcion": "Nueva tarjeta internacional",
                    "comision": float(settings.STRIPE_COMMISSION_RATE),
                    "entidad": "Stripe",
                }
            )

            # Agregar billeteras electrónicas habilitadas para pago
            for billetera in BilleteraElectronica.objects.filter(cliente=cliente, habilitado_para_pago=True):
                # Obtener comisión de la entidad si existe
                comision = 3  # Comisión por defecto para billeteras
                if billetera.entidad:
                    if tipo_operacion == "compra":
                        comision = float(billetera.entidad.comision_compra)
                    else:
                        comision = float(billetera.entidad.comision_venta)

                entidad_nombre = billetera.entidad.nombre if billetera.entidad else "Sin proveedor"

                medios_pago.append(
                    {
                        "id": f"billetera_{billetera.id}",
                        "tipo": "billetera",
                        "nombre": f"Billetera - {billetera.generar_alias()}",
                        "descripcion": f"Billetera {entidad_nombre}",
                        "comision": comision,
                        "entidad": billetera.entidad.nombre if billetera.entidad else "Sin entidad",
                    }
                )

        # Configurar medios de cobro según tipo de operación
        # Agregar efectivo por defecto para cobro
        medios_cobro.append(
            {
                "id": "efectivo",
                "tipo": "efectivo",
                "nombre": "Efectivo",
                "descripcion": "Cobro en efectivo",
                "comision": 0,  # 0%
            }
        )

        # Para compra: solo efectivo para cobro
        # Para venta: agregar todos los medios habilitados para cobro
        if tipo_operacion == "venta":
            # Agregar tarjetas de crédito habilitadas para cobro
            for tarjeta in TarjetaCredito.objects.filter(cliente=cliente, habilitado_para_cobro=True):
                comision = 5  # Comisión por defecto para tarjetas
                if tarjeta.entidad:
                    comision = float(tarjeta.entidad.comision_venta)

                medios_cobro.append(
                    {
                        "id": f"tarjeta_{tarjeta.id}",
                        "tipo": "tarjeta",
                        "nombre": f"TC - {tarjeta.generar_alias()}",
                        "descripcion": f"Tarjeta terminada en {tarjeta.numero_tarjeta[-4:]}",
                        "comision": comision,
                        "entidad": tarjeta.entidad.nombre if tarjeta.entidad else "Sin entidad",
                    }
                )

            # Agregar cuentas bancarias habilitadas para cobro
            for cuenta in CuentaBancaria.objects.filter(cliente=cliente, habilitado_para_cobro=True):
                comision = 0  # Comisión por defecto para cuentas
                if cuenta.entidad:
                    comision = float(cuenta.entidad.comision_venta)

                entidad_nombre = cuenta.entidad.nombre if cuenta.entidad else "Sin banco"

                medios_cobro.append(
                    {
                        "id": f"cuenta_{cuenta.id}",
                        "tipo": "cuenta",
                        "nombre": f"Cuenta - {cuenta.generar_alias()}",
                        "descripcion": f"Cuenta {entidad_nombre} terminada en {cuenta.numero_cuenta[-4:]}",
                        "comision": comision,
                        "entidad": cuenta.entidad.nombre if cuenta.entidad else "Sin entidad",
                    }
                )

            # Agregar billeteras electrónicas habilitadas para cobro
            for billetera in BilleteraElectronica.objects.filter(cliente=cliente, habilitado_para_cobro=True):
                comision = 3  # Comisión por defecto para billeteras
                if billetera.entidad:
                    comision = float(billetera.entidad.comision_venta)

                entidad_nombre = billetera.entidad.nombre if billetera.entidad else "Sin proveedor"

                medios_cobro.append(
                    {
                        "id": f"billetera_{billetera.id}",
                        "tipo": "billetera",
                        "nombre": f"Billetera - {billetera.generar_alias()}",
                        "descripcion": f"Billetera {entidad_nombre}",
                        "comision": comision,
                        "entidad": billetera.entidad.nombre if billetera.entidad else "Sin entidad",
                    }
                )

        return JsonResponse({"medios_pago": medios_pago, "medios_cobro": medios_cobro})

    except Cliente.DoesNotExist:
        return JsonResponse({"error": "Cliente no encontrado"}, status=404)


@require_GET
def api_divisas_disponibles(request: HttpRequest) -> JsonResponse:
    """Devuelve las divisas destino disponibles según tasas activas.

    El servicio busca tasas de cambio activas con PYG como divisa origen y devuelve
    las divisas destino (excluye PYG) con su código, nombre y símbolo.

    :param request: HttpRequest (no requiere parámetros adicionales).
    :type request: django.http.HttpRequest
    :return: JsonResponse con clave "divisas" que contiene una lista de objetos
        {"codigo", "nombre", "simbolo"}.
    :rtype: django.http.JsonResponse
    """
    # Obtener todas las divisas destino que tienen tasas de cambio activas con PYG como origen
    divisas_destino = set()

    tasas_activas = TasaCambio.objects.filter(activo=True, divisa_origen__codigo="PYG").select_related("divisa_destino")

    for tasa in tasas_activas:
        if tasa.divisa_destino.codigo != "PYG":  # Excluir PYG de las opciones
            divisas_destino.add((tasa.divisa_destino.codigo, tasa.divisa_destino.nombre, tasa.divisa_destino.simbolo))

    # Convertir a lista de diccionarios
    destino_list = [{"codigo": cod, "nombre": nom, "simbolo": sim} for cod, nom, sim in divisas_destino]

    return JsonResponse({"divisas": destino_list})


def comprar_divisa_view(request):
    """Página para iniciar una operación de compra de divisas.

    Muestra las divisas disponibles (excluyendo PYG) y renderiza el template
    para que el usuario inicie la compra. El cliente asociado puede ser provisto
    por middleware (request.cliente) o por sesión.

    :param request: HttpRequest.
    :type request: django.http.HttpRequest
    :return: HttpResponse con el template "comprar_divisa.html" y contexto.
    :rtype: django.http.HttpResponse
    """
    # Obtener divisas disponibles (excluyendo PYG)
    divisas = Divisa.objects.filter(estado="activo").exclude(codigo="PYG")

    context = {
        "divisas": divisas,
        # request.cliente ya lo añade el middleware
    }
    return render(request, "comprar_divisa.html", context)


def vender_divisa_view(request: HttpRequest) -> HttpResponse:
    """Página para iniciar una operación de venta de divisas.

    Intenta obtener el cliente asociado desde la sesión o desde los clientes
    del usuario autenticado y renderiza el template de venta.

    :param request: HttpRequest.
    :type request: django.http.HttpRequest
    :return: HttpResponse con el template "vender_divisa.html" y el cliente asociado
        en el contexto (si existe).
    :rtype: django.http.HttpResponse
    """
    cliente_asociado = None
    if request.user.is_authenticated:
        cliente_id = request.session.get("cliente_id")
        if cliente_id:
            cliente_asociado = Cliente.objects.filter(id=cliente_id, usuarios=request.user).first()
        else:
            cliente_asociado = Cliente.objects.filter(usuarios=request.user).first()

    context = {"cliente_asociado": cliente_asociado}
    return render(request, "vender_divisa.html", context)


@login_required
def configuracion_medios_pago(request):
    """Redirige a la configuración de medios de pago del cliente activo en sesión.

    Si `request.cliente` está definido (ej. por middleware) redirige a la vista de
    configuración para ese cliente; si no, redirige a la lista de clientes/transacciones.

    :param request: HttpRequest del usuario.
    :type request: django.http.HttpRequest
    :return: HttpResponse redirigiendo a la página de configuración o lista.
    :rtype: django.http.HttpResponse
    """
    if request.cliente:
        return redirect("transacciones:medios_pago_cliente", cliente_id=request.cliente.id)
    else:
        return redirect("transacciones:lista")


@login_required
def medios_pago_cliente(request: HttpRequest, cliente_id: int) -> HttpResponse:
    """Muestra los medios de pago de un cliente concreto.

    Recupera tarjetas, cuentas y billeteras del cliente y renderiza la plantilla
    de configuración de medios de pago.

    :param request: HttpRequest del usuario autenticado.
    :type request: django.http.HttpRequest
    :param cliente_id: ID del cliente a mostrar.
    :type cliente_id: int
    :return: HttpResponse con la plantilla "transacciones/configuracion/medios_pago_cliente.html".
    :rtype: django.http.HttpResponse
    """
    cliente = get_object_or_404(Cliente, id=cliente_id, usuarios=request.user)

    tarjetas = cliente.tarjetacredito_set.all()
    cuentas = cliente.cuentabancaria_set.all()
    billeteras = cliente.billeteraelectronica_set.all()

    contexto = {
        "cliente": cliente,
        "tarjetas": tarjetas,
        "cuentas": cuentas,
        "billeteras": billeteras,
    }
    return render(request, "transacciones/configuracion/medios_pago_cliente.html", contexto)


@login_required
def crear_tarjeta(request: HttpRequest, cliente_id: int) -> HttpResponse:
    """Crear una nueva tarjeta de crédito para un cliente.

    Procesa el formulario POST para crear y asociar una tarjeta al cliente. Maneja
    validaciones y muestra mensajes al usuario en caso de error o éxito.

    :param request: HttpRequest que puede contener un POST con los datos de la tarjeta.
    :type request: django.http.HttpRequest
    :param cliente_id: ID del cliente al que se agregará la tarjeta.
    :type cliente_id: int
    :return: HttpResponse renderizando el formulario o redirigiendo a la lista de medios.
    :rtype: django.http.HttpResponse
    """
    cliente = get_object_or_404(Cliente, id=cliente_id, usuarios=request.user)

    if request.method == "POST":
        try:
            # Obtener la entidad seleccionada
            entidad_id = request.POST.get("entidad")
            entidad = None
            if entidad_id:
                entidad = EntidadFinanciera.objects.get(id=entidad_id, tipo="emisor_tarjeta", activo=True)

            tarjeta = TarjetaCredito.objects.create(
                cliente=cliente,
                numero_tarjeta=request.POST.get("numero_tarjeta", "").replace(" ", ""),
                nombre_titular=request.POST.get("nombre_titular"),
                fecha_expiracion=request.POST.get("fecha_expiracion"),
                cvv=request.POST.get("cvv"),
                entidad=entidad,
                alias=request.POST.get("alias", ""),
            )
            if not tarjeta.alias:
                tarjeta.alias = tarjeta.generar_alias()
            tarjeta.save()

            messages.success(request, "Tarjeta de crédito agregada exitosamente.")
            return redirect("transacciones:medios_pago_cliente", cliente_id=cliente.pk)

        except ValidationError as e:
            # Manejar errores de validación del modelo específicamente
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            else:
                messages.error(request, f"Error de validación: {e}")
        except Exception as e:
            messages.error(request, f"Error al crear tarjeta: {e!s}")

    # Obtener entidades emisoras de tarjetas activas
    entidades_tarjeta = EntidadFinanciera.objects.filter(tipo="emisor_tarjeta", activo=True).order_by("nombre")

    contexto = {
        "cliente": cliente,
        "entidades_tarjeta": entidades_tarjeta,
    }
    return render(request, "transacciones/configuracion/crear_tarjeta.html", contexto)


@login_required
def crear_cuenta_bancaria(request: HttpRequest, cliente_id: int) -> HttpResponse:
    """Agregar una cuenta bancaria a un cliente.

    Procesa el formulario para crear una nueva cuenta bancaria, asigna alias si
    es necesario y maneja errores de validación mostrando mensajes.

    :param request: HttpRequest con datos del formulario (POST) o GET para mostrar el form.
    :type request: django.http.HttpRequest
    :param cliente_id: ID del cliente destino.
    :type cliente_id: int
    :return: HttpResponse con el formulario o redirección tras creación.
    :rtype: django.http.HttpResponse
    """
    cliente = get_object_or_404(Cliente, id=cliente_id, usuarios=request.user)

    if request.method == "POST":
        try:
            # Obtener la entidad bancaria seleccionada
            entidad_id = request.POST.get("entidad")
            entidad = None
            if entidad_id:
                entidad = EntidadFinanciera.objects.get(id=entidad_id, tipo="banco", activo=True)

            cuenta = CuentaBancaria.objects.create(
                cliente=cliente,
                numero_cuenta=request.POST.get("numero_cuenta"),
                entidad=entidad,
                titular_cuenta=request.POST.get("titular_cuenta"),
                documento_titular=request.POST.get("documento_titular", ""),
                alias=request.POST.get("alias", ""),
                habilitado_para_pago=request.POST.get("habilitado_para_pago") == "on",
                habilitado_para_cobro=request.POST.get("habilitado_para_cobro") == "on",
            )
            if not cuenta.alias:
                cuenta.alias = cuenta.generar_alias()
            cuenta.save()
            messages.success(request, "Cuenta bancaria agregada exitosamente.")
            return redirect("transacciones:medios_pago_cliente", cliente_id=cliente.id)

        except ValidationError as e:
            # Manejar errores de validación del modelo específicamente
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        field_name = field.replace("_", " ").title() if field != "__all__" else "Error"
                        messages.error(request, f"{field_name}: {error}")
            else:
                messages.error(request, f"Error de validación: {e}")
        except Exception as e:
            messages.error(request, f"Error al crear cuenta bancaria: {e!s}")

    # Obtener entidades bancarias activas
    entidades_bancarias = EntidadFinanciera.objects.filter(tipo="banco", activo=True).order_by("nombre")

    contexto = {
        "cliente": cliente,
        "entidades_bancarias": entidades_bancarias,
    }
    return render(request, "transacciones/configuracion/crear_cuenta_bancaria.html", contexto)


@login_required
def crear_billetera(request: HttpRequest, cliente_id: int) -> HttpResponse:
    """Crear una billetera electrónica para un cliente.

    Procesa el POST del formulario para crear la billetera, manejar alias y
    habilitaciones para pago/cobro. Muestra mensajes de éxito o error.

    :param request: HttpRequest con datos del formulario.
    :type request: django.http.HttpRequest
    :param cliente_id: ID del cliente al que se asociará la billetera.
    :type cliente_id: int
    :return: HttpResponse renderizando el formulario o redirigiendo a la vista de medios.
    :rtype: django.http.HttpResponse
    """
    cliente = get_object_or_404(Cliente, id=cliente_id, usuarios=request.user)

    if request.method == "POST":
        try:
            # Obtener la entidad de billetera seleccionada
            entidad_id = request.POST.get("entidad")
            entidad = None
            if entidad_id:
                entidad = EntidadFinanciera.objects.get(id=entidad_id, tipo="proveedor_billetera", activo=True)

            billetera = BilleteraElectronica.objects.create(
                cliente=cliente,
                entidad=entidad,
                identificador=request.POST.get("identificador"),
                numero_telefono=request.POST.get("numero_telefono", ""),
                email_asociado=request.POST.get("email_asociado", ""),
                alias=request.POST.get("alias", ""),
                habilitado_para_pago=request.POST.get("habilitado_para_pago") == "on",
                habilitado_para_cobro=request.POST.get("habilitado_para_cobro") == "on",
            )
            if not billetera.alias:
                billetera.alias = billetera.generar_alias()
            billetera.save()
            messages.success(request, "Billetera electrónica agregada exitosamente.")
            return redirect("transacciones:medios_pago_cliente", cliente_id=cliente.id)

        except Exception as e:
            messages.error(request, f"Error al crear billetera: {e!s}")

    # Obtener entidades de billeteras activas
    entidades_billeteras = EntidadFinanciera.objects.filter(tipo="proveedor_billetera", activo=True).order_by("nombre")

    contexto = {
        "cliente": cliente,
        "entidades_billeteras": entidades_billeteras,
    }
    return render(request, "transacciones/configuracion/crear_billetera.html", contexto)


@login_required
def editar_tarjeta(request: HttpRequest, cliente_id: int, medio_id: int) -> HttpResponse:
    """Editar una tarjeta de crédito existente.

    Actualiza los campos de la tarjeta según el POST recibido y guarda los
    cambios. Maneja validaciones y muestra mensajes al usuario.

    :param request: HttpRequest con datos para actualizar la tarjeta.
    :type request: django.http.HttpRequest
    :param cliente_id: ID del cliente propietario (usado para validar pertenencia).
    :type cliente_id: int
    :param medio_id: ID de la tarjeta a editar.
    :type medio_id: int
    :return: HttpResponse renderizando el formulario de edición o redirigiendo.
    :rtype: django.http.HttpResponse
    """
    tarjeta = get_object_or_404(TarjetaCredito, id=medio_id, cliente__usuarios=request.user)

    if request.method == "POST":
        try:
            # Actualizar directamente el objeto existente
            tarjeta.numero_tarjeta = request.POST.get("numero_tarjeta", "").replace(" ", "")
            tarjeta.nombre_titular = request.POST.get("nombre_titular", "")
            tarjeta.cvv = request.POST.get("cvv", "")

            # Actualizar entidad
            entidad_id = request.POST.get("entidad")
            if entidad_id:
                tarjeta.entidad = EntidadFinanciera.objects.get(id=entidad_id, tipo="emisor_tarjeta", activo=True)
            else:
                tarjeta.entidad = None

            # Solo actualizar fecha si se proporciona
            fecha_expiracion = request.POST.get("fecha_expiracion")
            if fecha_expiracion:
                tarjeta.fecha_expiracion = datetime.strptime(fecha_expiracion, "%Y-%m-%d").date()

            tarjeta.alias = request.POST.get("alias", "")

            if not tarjeta.alias:
                tarjeta.alias = tarjeta.generar_alias()

            tarjeta.save()
            messages.success(request, "Tarjeta actualizada exitosamente.")
            return redirect("transacciones:medios_pago_cliente", cliente_id=tarjeta.cliente.id)

        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            else:
                messages.error(request, f"Error de validación: {e}")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error al editar tarjeta: {e!s}")

    # Obtener entidades emisoras de tarjetas activas
    entidades_tarjeta = EntidadFinanciera.objects.filter(tipo="emisor_tarjeta", activo=True).order_by("nombre")

    contexto = {
        "tarjeta": tarjeta,
        "cliente": tarjeta.cliente,
        "entidades_tarjeta": entidades_tarjeta,
    }
    return render(request, "transacciones/configuracion/editar_tarjeta.html", contexto)


@login_required
def editar_cuenta_bancaria(request: HttpRequest, cliente_id: int, medio_id: int) -> HttpResponse:
    """Editar una cuenta bancaria existente.

    Actualiza los datos de la cuenta y maneja la persistencia y errores de
    validación mostrando mensajes informativos.

    :param request: HttpRequest con datos de actualización.
    :type request: django.http.HttpRequest
    :param cliente_id: ID del cliente propietario.
    :type cliente_id: int
    :param medio_id: ID de la cuenta a editar.
    :type medio_id: int
    :return: HttpResponse con el formulario o redirección tras guardar.
    :rtype: django.http.HttpResponse
    """
    cuenta = get_object_or_404(CuentaBancaria, id=medio_id, cliente__usuarios=request.user)

    if request.method == "POST":
        try:
            # Actualizar directamente el objeto existente
            cuenta.numero_cuenta = request.POST.get("numero_cuenta", "")

            # Actualizar entidad bancaria
            entidad_id = request.POST.get("entidad")
            if entidad_id:
                cuenta.entidad = EntidadFinanciera.objects.get(id=entidad_id, tipo="banco", activo=True)
            else:
                cuenta.entidad = None

            cuenta.titular_cuenta = request.POST.get("titular_cuenta", "")
            cuenta.documento_titular = request.POST.get("documento_titular", "")
            cuenta.alias = request.POST.get("alias", "")

            cuenta.habilitado_para_pago = request.POST.get("habilitado_para_pago") == "on"
            cuenta.habilitado_para_cobro = request.POST.get("habilitado_para_cobro") == "on"

            if not cuenta.alias:
                cuenta.alias = cuenta.generar_alias()

            cuenta.save()
            messages.success(request, "Cuenta bancaria actualizada exitosamente.")
            return redirect("transacciones:medios_pago_cliente", cliente_id=cuenta.cliente.id)

        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            else:
                messages.error(request, f"Error de validación: {e}")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error al editar cuenta bancaria: {e!s}")

    # Obtener entidades bancarias activas
    entidades_bancarias = EntidadFinanciera.objects.filter(tipo="banco", activo=True).order_by("nombre")

    contexto = {
        "cuenta": cuenta,
        "cliente": cuenta.cliente,
        "entidades_bancarias": entidades_bancarias,
    }
    return render(request, "transacciones/configuracion/editar_cuenta_bancaria.html", contexto)


@login_required
def editar_billetera(request: HttpRequest, cliente_id: int, medio_id: int) -> HttpResponse:
    """Editar una billetera electrónica existente.

    Actualiza los campos de la billetera (identificador, contacto, alias y
    habilitaciones) y muestra mensajes de éxito o error.

    :param request: HttpRequest con los datos de la billetera.
    :type request: django.http.HttpRequest
    :param cliente_id: ID del cliente propietario.
    :type cliente_id: int
    :param medio_id: ID de la billetera a editar.
    :type medio_id: int
    :return: HttpResponse renderizando el formulario o redirigiendo tras guardado.
    :rtype: django.http.HttpResponse
    """
    billetera = get_object_or_404(BilleteraElectronica, id=medio_id, cliente__usuarios=request.user)

    if request.method == "POST":
        try:
            # Actualizar directamente el objeto existente
            # Actualizar entidad de billetera
            entidad_id = request.POST.get("entidad")
            if entidad_id:
                billetera.entidad = EntidadFinanciera.objects.get(
                    id=entidad_id, tipo="proveedor_billetera", activo=True
                )
            else:
                billetera.entidad = None

            billetera.identificador = request.POST.get("identificador", "")
            billetera.numero_telefono = request.POST.get("numero_telefono", "")
            billetera.email_asociado = request.POST.get("email_asociado", "")
            billetera.alias = request.POST.get("alias", "")

            # Actualizar campos de habilitación
            billetera.habilitado_para_pago = request.POST.get("habilitado_para_pago") == "on"
            billetera.habilitado_para_cobro = request.POST.get("habilitado_para_cobro") == "on"

            if not billetera.alias:
                billetera.alias = billetera.generar_alias()

            billetera.save()
            messages.success(request, "Billetera electrónica actualizada exitosamente.")
            return redirect("transacciones:medios_pago_cliente", cliente_id=billetera.cliente.id)

        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            else:
                messages.error(request, f"Error de validación: {e}")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error al editar billetera: {e!s}")

    # Obtener entidades de billeteras activas
    entidades_billeteras = EntidadFinanciera.objects.filter(tipo="proveedor_billetera", activo=True).order_by("nombre")

    contexto = {
        "billetera": billetera,
        "cliente": billetera.cliente,
        "entidades_billeteras": entidades_billeteras,
    }
    return render(request, "transacciones/configuracion/editar_billetera.html", contexto)


@login_required
def eliminar_medio_pago(request: HttpRequest, cliente_id: int, tipo: str, medio_id: int) -> HttpResponse:
    """Eliminar un medio de pago del cliente.

    Elimina físicamente la entidad correspondiente (tarjeta, cuenta o billetera)
    después de validar la pertenencia al usuario. Redirige a la lista de medios.

    :param request: HttpRequest del usuario que solicita la eliminación.
    :type request: django.http.HttpRequest
    :param cliente_id: ID del cliente propietario (informativo en la URL).
    :type cliente_id: int
    :param tipo: Tipo de medio: 'tarjeta', 'cuenta' o 'billetera'.
    :type tipo: str
    :param medio_id: ID del medio a eliminar.
    :type medio_id: int
    :return: HttpResponse redirigiendo a la vista de medios del cliente.
    :rtype: django.http.HttpResponse
    """
    if tipo == "tarjeta":
        medio = get_object_or_404(TarjetaCredito, id=medio_id, cliente__usuarios=request.user)
    elif tipo == "cuenta":
        medio = get_object_or_404(CuentaBancaria, id=medio_id, cliente__usuarios=request.user)
    elif tipo == "billetera":
        medio = get_object_or_404(BilleteraElectronica, id=medio_id, cliente__usuarios=request.user)
    else:
        messages.error(request, "Tipo de medio de pago inválido.")
        return redirect("transacciones:configuracion_medios_pago")

    # Eliminar directamente sin página de confirmación
    cliente_id = medio.cliente.id
    medio.delete()  # Eliminación física
    messages.success(request, f"{tipo.title()} eliminada exitosamente.")
    return redirect("transacciones:medios_pago_cliente", cliente_id=cliente_id)


@client_required
def vista_transacciones(request):
    """Lista las transacciones del cliente activo si existe.

    Muestra las transacciones asociadas al cliente activo desde el middleware.
    Si no hay cliente activo, muestra una lista vacía.

    :param request: HttpRequest que puede contener un cliente activo.
    :type request: django.http.HttpRequest
    :return: HttpResponse con el template "transacciones/lista_transacciones.html" y el contexto
        que incluye las transacciones y el cliente.
    :rtype: django.http.HttpResponse
    """
    # Obtener cliente activo del middleware
    cliente = getattr(request, "cliente", None)
    transacciones = []

    if cliente:
        # Obtener transacciones del cliente activo
        transacciones_raw = cliente.transacciones.all()

        # Procesar cada transacción para agregar nombres legibles de medios
        transacciones = []
        for transaccion in transacciones_raw:
            # Crear una copia de la transacción con campos adicionales para nombres legibles
            transaccion.nombre_medio_pago = obtener_nombre_medio(transaccion.medio_pago or "efectivo", cliente)
            transaccion.nombre_medio_cobro = obtener_nombre_medio(transaccion.medio_cobro or "efectivo", cliente)
            transacciones.append(transaccion)

    return render(
        request, "transacciones/lista_transacciones.html", {"transacciones": transacciones, "cliente": cliente}
    )


@client_required
def realizar_transaccion_view(request: HttpRequest) -> HttpResponse:
    """Página para realizar una transacción real de cambio de divisas.

    Presenta una interfaz similar a la simulación pero con capacidad de procesar
    la transacción real. El cliente se obtiene automáticamente del middleware.

    :param request: Objeto HttpRequest.
    :type request: django.http.HttpRequest
    :return: HttpResponse con el template "realizar_transaccion.html" y el contexto que
        incluye las divisas disponibles y el cliente asociado (si existe).
    :rtype: django.http.HttpResponse
    """
    divisas = Divisa.objects.filter(estado="activo").exclude(codigo="PYG")

    context = {
        "divisas": divisas,
        "STRIPE_PUBLISHABLE_KEY": settings.STRIPE_PUBLISHABLE_KEY,
        # El cliente se obtiene automáticamente del middleware en request.cliente
    }
    return render(request, "realizar_transaccion.html", context)


def _verificar_limites_transaccion(cliente, monto_pyg, fecha_transaccion=None):
    """Verifica si una transacción excede los límites diarios y mensuales configurados.

    Args:
        cliente: Instancia del cliente
        monto_pyg: Monto de la transacción en guaraníes (PYG)
        fecha_transaccion: Fecha de la transacción (usa datetime.date.today() si es None)

    Returns:
        dict: {'valid': bool, 'error_message': str, 'limits_info': dict}

    """
    from datetime import date

    from .models import LimiteTransacciones

    try:
        # Obtener límites actuales
        limite_config = LimiteTransacciones.get_limite_actual()

        # Si no hay límites configurados, permitir la transacción
        if not limite_config:
            return {"valid": True, "error_message": None, "limits_info": None}

        # Usar fecha actual si no se especifica
        if fecha_transaccion is None:
            fecha_transaccion = date.today()

        # Calcular inicio del mes
        inicio_mes = date(fecha_transaccion.year, fecha_transaccion.month, 1)

        # Obtener transacciones existentes del cliente (pendientes y completadas)
        transacciones_existentes = Transaccion.objects.filter(cliente=cliente, estado__in=["pendiente", "completada"])

        # Calcular montos acumulados del día (convertir a PYG)
        transacciones_dia = transacciones_existentes.filter(fecha_creacion__date=fecha_transaccion)

        monto_dia_pyg = Decimal("0")
        for trans in transacciones_dia:
            # Convertir monto a PYG según el tipo de operación
            if trans.tipo_operacion == "compra":
                # En compra, el cliente paga en PYG
                # Lo que cuenta para el límite es lo que paga en PYG
                monto_dia_pyg += trans.monto_origen
            else:  # venta
                # En venta, el cliente recibe PYG (monto_destino)
                # Lo que cuenta para el límite es lo que recibe en PYG
                monto_dia_pyg += trans.monto_destino

        # Calcular montos acumulados del mes
        transacciones_mes = transacciones_existentes.filter(
            fecha_creacion__date__gte=inicio_mes, fecha_creacion__date__lte=fecha_transaccion
        )

        monto_mes_pyg = Decimal("0")
        for trans in transacciones_mes:
            if trans.tipo_operacion == "compra":
                monto_mes_pyg += trans.monto_origen
            else:  # venta
                monto_mes_pyg += trans.monto_destino

        # Verificar límite diario
        nuevo_monto_dia = monto_dia_pyg + Decimal(str(monto_pyg))
        if nuevo_monto_dia > limite_config.limite_diario:
            return {
                "valid": False,
                "error_message": f"Límite diario excedido. "
                f"Límite: ₲{strip_trailing_zeros(limite_config.limite_diario, 0)}, "
                f"Usado hoy: ₲{strip_trailing_zeros(monto_dia_pyg, 0)}, "
                f"Nuevo total sería: ₲{strip_trailing_zeros(nuevo_monto_dia, 0)}",
                "limits_info": {
                    "limite_diario": float(limite_config.limite_diario),
                    "usado_dia": float(monto_dia_pyg),
                    "nuevo_total_dia": float(nuevo_monto_dia),
                },
            }

        # Verificar límite mensual
        nuevo_monto_mes = monto_mes_pyg + Decimal(str(monto_pyg))
        if nuevo_monto_mes > limite_config.limite_mensual:
            return {
                "valid": False,
                "error_message": f"Límite mensual excedido. "
                f"Límite: ₲{limite_config.limite_mensual:,.0f}, "
                f"Usado este mes: ₲{monto_mes_pyg:,.0f}, "
                f"Nuevo total sería: ₲{nuevo_monto_mes:,.0f}",
                "limits_info": {
                    "limite_mensual": float(limite_config.limite_mensual),
                    "usado_mes": float(monto_mes_pyg),
                    "nuevo_total_mes": float(nuevo_monto_mes),
                },
            }

        return {
            "valid": True,
            "error_message": None,
            "limits_info": {
                "limite_diario": float(limite_config.limite_diario),
                "limite_mensual": float(limite_config.limite_mensual),
                "usado_dia": float(monto_dia_pyg),
                "usado_mes": float(monto_mes_pyg),
                "disponible_dia": float(limite_config.limite_diario - monto_dia_pyg),
                "disponible_mes": float(limite_config.limite_mensual - monto_mes_pyg),
            },
        }

    except Exception:
        # En caso de error, registrar pero permitir la transacción para no bloquear el sistema
        return {"valid": True, "error_message": None, "limits_info": None}


@require_GET
@client_required
def api_crear_transaccion(request: HttpRequest) -> JsonResponse:
    """Crea una nueva transacción basada en parámetros de simulación.

    Parámetros esperados en la querystring (GET):
    - monto: cantidad numérica a convertir.
    - divisa_seleccionada: código de la divisa destino (ej. "USD").
    - tipo_operacion: "compra" o "venta".
    - metodo_pago: identificador del medio de pago (ej. "efectivo", "tarjeta_1").
    - metodo_cobro: identificador del medio de cobro.

    :param request: HttpRequest con la querystring de la transacción.
    :type request: django.http.HttpRequest
    :return: JsonResponse con los detalles de la nueva transacción creada.
    :rtype: django.http.JsonResponse
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Usuario no autenticado"}, status=401)

    cliente = getattr(request, "cliente", None)
    if not cliente:
        return JsonResponse({"error": "No hay cliente asociado"}, status=400)

    try:
        params = request.GET.dict()

        # Verificar si el usuario requiere MFA para transacciones ANTES de crear
        from apps.seguridad.models import PerfilMFA

        mfa_requerido = False
        try:
            perfil_mfa = PerfilMFA.objects.get(usuario=request.user)
            mfa_requerido = perfil_mfa.mfa_habilitado_transacciones
        except PerfilMFA.DoesNotExist:
            pass

        # Si se requiere MFA, verificar si ya fue validado para esta sesión
        if mfa_requerido:
            mfa_token = request.GET.get("mfa_token")
            if not mfa_token or not request.session.get(f"mfa_token_valido_{mfa_token}"):
                # Guardar los datos de la transacción en la sesión y requerir MFA
                request.session["datos_transaccion_mfa"] = params
                return JsonResponse(
                    {
                        "error": "MFA_REQUIRED",
                        "mensaje": "Se requiere verificación MFA para crear transacciones",
                        "redirect_url": reverse("seguridad:verificar_mfa_transaccion"),
                    },
                    status=400,
                )

        # Realizar la simulación para obtener los datos calculados
        simulation_data = _compute_simulation(params, request)

        # Validar datos requeridos
        monto_str = params.get("monto")
        if not monto_str:
            return JsonResponse({"error": "Monto es requerido"}, status=400)

        # Manejar tanto string como lista de strings (querystring puede devolver ambos)
        if isinstance(monto_str, list):
            monto_str = monto_str[0] if monto_str else ""

        try:
            monto = float(monto_str)
        except (ValueError, TypeError):
            return JsonResponse({"error": "Monto debe ser un número válido"}, status=400)

        divisa_seleccionada = params.get("divisa_seleccionada") or "USD"
        tipo_operacion = params.get("tipo_operacion") or "compra"

        if monto <= 0:
            return JsonResponse({"error": "Monto debe ser mayor a 0"}, status=400)

        # Obtener las divisas
        try:
            if tipo_operacion == "compra":
                divisa_origen = Divisa.objects.get(codigo="PYG")
                divisa_destino = Divisa.objects.get(codigo=divisa_seleccionada)
            else:  # venta
                divisa_origen = Divisa.objects.get(codigo=divisa_seleccionada)
                divisa_destino = Divisa.objects.get(codigo="PYG")
        except Divisa.DoesNotExist:
            return JsonResponse({"error": "Divisa no válida"}, status=400)

        # Crear la transacción
        from .models import Transaccion

        # Para compra: monto_origen es en PYG, monto_destino es en divisa extranjera
        # Para venta: monto_origen es en divisa extranjera, monto_destino es en PYG
        if tipo_operacion == "compra":
            monto_origen = Decimal(str(simulation_data["total"]))  # Total en PYG a pagar
            monto_destino = Decimal(str(simulation_data["monto_original"]))  # Divisa a recibir
        else:  # venta
            monto_origen = Decimal(str(simulation_data["monto_original"]))  # Divisa a entregar
            monto_destino = Decimal(str(simulation_data["total"]))  # PYG a recibir

        # Obtener y validar los medios de pago/cobro
        metodo_pago = params.get("metodo_pago", "efectivo")
        metodo_cobro = params.get("metodo_cobro", "efectivo")

        # Verificar límites de transacción antes de crear
        # Calcular el monto en PYG según el tipo de operación
        if tipo_operacion == "compra":
            monto_pyg_transaccion = monto_origen
        else:  # venta
            # En venta, el cliente recibe PYG (monto_destino)
            monto_pyg_transaccion = monto_destino

        # Validar límites
        limite_result = _verificar_limites_transaccion(cliente, monto_pyg_transaccion)
        if not limite_result["valid"]:
            return JsonResponse(
                {
                    "error": limite_result["error_message"],
                    "tipo_error": "limite_excedido",
                    "limits_info": limite_result["limits_info"],
                },
                status=400,
            )

        # Obtener la tasa de cambio actual para almacenar como tasa original
        tasa_actual = Decimal(str(simulation_data["tasa_cambio"]))

        transaccion = Transaccion.objects.create(
            cliente=cliente,
            usuario=request.user,
            tipo_operacion=tipo_operacion,
            estado="pendiente",
            divisa_origen=divisa_origen,
            divisa_destino=divisa_destino,
            tasa_aplicada=tasa_actual,
            tasa_original=tasa_actual,  # Almacenar la tasa original para verificar cambios posteriores
            monto_origen=monto_origen,
            monto_destino=monto_destino,
            medio_pago=metodo_pago,
            medio_cobro=metodo_cobro,
        )

        # Limpiar token MFA si se usó
        mfa_token = request.GET.get("mfa_token")
        if mfa_token and f"mfa_token_valido_{mfa_token}" in request.session:
            del request.session[f"mfa_token_valido_{mfa_token}"]

        return JsonResponse(
            {
                "success": True,
                "transaccion_id": str(transaccion.id_transaccion),
                "redirect_url": f"/transacciones/procesar/{transaccion.id_transaccion}/",
                "resumen": {
                    "id_transaccion": str(transaccion.id_transaccion),
                    "tipo_operacion": dict(transaccion.TIPOS_OPERACION).get(
                        transaccion.tipo_operacion, transaccion.tipo_operacion
                    ),
                    "cliente": transaccion.cliente.nombre,
                    "fecha_creacion": transaccion.fecha_creacion.strftime("%d/%m/%Y %H:%M"),
                    "divisa_origen": transaccion.divisa_origen.codigo,
                    "divisa_destino": transaccion.divisa_destino.codigo,
                    "monto_origen": float(transaccion.monto_origen),
                    "monto_destino": float(transaccion.monto_destino),
                    "tasa_aplicada": float(transaccion.tasa_aplicada),
                    "estado": dict(transaccion.ESTADOS_TRANSACCION).get(transaccion.estado, transaccion.estado),
                    "metodo_pago": params.get("metodo_pago", "efectivo"),
                    "metodo_cobro": params.get("metodo_cobro", "efectivo"),
                },
            }
        )

    except Exception as e:
        return JsonResponse({"error": f"Error al crear transacción: {e!s}"}, status=500)


def procesar_transaccion_view(request: HttpRequest, transaccion_id: str) -> HttpResponse:
    """Vista para procesar una transacción específica según su tipo y método de pago.

    Esta vista maneja tanto GET (mostrar detalles) como POST (confirmar transacción).

    :param request: HttpRequest del usuario.
    :type request: django.http.HttpRequest
    :param transaccion_id: UUID de la transacción a procesar.
    :type transaccion_id: str
    :return: HttpResponse con el template de procesamiento correspondiente.
    :rtype: django.http.HttpResponse
    """
    from .models import Transaccion

    try:
        transaccion = get_object_or_404(Transaccion, id_transaccion=transaccion_id, cliente__usuarios=request.user)

        # Si es POST, procesar la confirmación de la transacción
        if request.method == "POST":
            try:
                # Actualizar estado de la transacción
                transaccion.estado = "completada"
                transaccion.save()

                messages.success(request, "¡Transacción procesada exitosamente!")
                return redirect("transacciones:vista_transacciones")

            except Exception as e:
                messages.error(request, f"Error al procesar transacción: {e!s}")
                return redirect("transacciones:procesar_transaccion", transaccion_id=transaccion_id)

        # GET: mostrar detalles de la transacción
        # Usar los medios guardados en la transacción, con fallback a parámetros GET para compatibilidad
        metodo_pago = transaccion.medio_pago or request.GET.get("metodo_pago", "efectivo")
        metodo_cobro = transaccion.medio_cobro or request.GET.get("metodo_cobro", "efectivo")

        nombre_metodo_pago = obtener_nombre_medio(metodo_pago, transaccion.cliente)
        nombre_metodo_cobro = obtener_nombre_medio(metodo_cobro, transaccion.cliente)

        context = {
            "transaccion": transaccion,
            "metodo_pago": metodo_pago,
            "metodo_cobro": metodo_cobro,
            "nombre_metodo_pago": nombre_metodo_pago,
            "nombre_metodo_cobro": nombre_metodo_cobro,
        }

        return render(request, "procesar_transaccion.html", context)

    except Exception as e:
        messages.error(request, f"Error al procesar transacción: {e!s}")
        return redirect("transacciones:realizar_transaccion")


@login_required
def api_cancelar_transaccion(request: HttpRequest, transaccion_id: str) -> JsonResponse:
    """Cancel an existing transaction.

    Args:
        request: HttpRequest object
        transaccion_id: UUID de la transacción a cancelar

    Returns:
        JsonResponse con el resultado de la operación

    """
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Método no permitido"}, status=405)

    try:
        # Obtener la transacción
        transaccion = get_object_or_404(Transaccion, id_transaccion=transaccion_id)

        # Verificar que el usuario tiene un cliente activo
        if not request.cliente:
            return JsonResponse({"success": False, "message": "No tienes un cliente asociado"}, status=403)

        # Verificar que la transacción pertenece al cliente actual
        if transaccion.cliente != request.cliente:
            return JsonResponse(
                {"success": False, "message": "No tienes permisos para cancelar esta transacción"}, status=403
            )

        # Verificar que la transacción puede ser cancelada
        if transaccion.estado == "cancelada":
            return JsonResponse({"success": False, "message": "La transacción ya está cancelada"}, status=400)

        if transaccion.estado == "completada":
            return JsonResponse(
                {"success": False, "message": "No se puede cancelar una transacción completada"}, status=400
            )

        # Cancelar la transacción
        transaccion.estado = "cancelada"
        transaccion.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Transacción cancelada exitosamente",
                "transaccion_id": str(transaccion.id_transaccion),
            }
        )

    except Transaccion.DoesNotExist:
        return JsonResponse({"success": False, "message": "Transacción no encontrada"}, status=404)
    except Exception:
        return JsonResponse({"success": False, "message": "Error interno del servidor"}, status=500)


@require_POST
def api_procesar_pago_bancario(request: HttpRequest) -> JsonResponse:
    """Procesa la respuesta del componente bancario simulado.

    Recibe la respuesta del gateway de pagos externo simulado y actualiza
    el estado de la transacción según el resultado (éxito o error).

    Args:
        request: HttpRequest con datos JSON del resultado del pago

    Returns:
        JsonResponse con el resultado del procesamiento

    """
    import json
    from datetime import datetime

    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "Usuario no autenticado"}, status=401)

    try:
        # Parsear datos JSON
        data = json.loads(request.body)
        transaccion_id = data.get("transaccion_id")
        exito = data.get("exito", False)
        mensaje_error = data.get("mensaje_error")

        if not transaccion_id:
            return JsonResponse({"success": False, "message": "ID de transacción requerido"}, status=400)

        # Obtener la transacción
        cliente = getattr(request, "cliente", None)
        if not cliente:
            return JsonResponse({"success": False, "message": "No hay cliente asociado"}, status=400)

        transaccion = get_object_or_404(Transaccion, id_transaccion=transaccion_id, cliente=cliente)

        # Verificar que la transacción esté en estado pendiente
        if transaccion.estado != "pendiente":
            return JsonResponse(
                {
                    "success": False,
                    "message": f"La transacción está en estado '{transaccion.estado}' y no puede ser procesada",
                },
                status=400,
            )

        # Procesar según el resultado del banco
        if exito:
            # Pago exitoso
            transaccion.estado = "completada"
            transaccion.fecha_pago = datetime.now()
            mensaje_log = "Pago procesado exitosamente"

        else:
            # Pago fallido
            transaccion.estado = "pendiente"

        # Guardar cambios
        transaccion.save()

        return JsonResponse(
            {
                "success": True,
                "message": "Resultado del pago procesado correctamente",
                "transaccion": {
                    "id": str(transaccion.id_transaccion),
                    "estado": transaccion.estado,
                    "fecha_pago": transaccion.fecha_pago.isoformat() if transaccion.fecha_pago else None,
                },
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Datos JSON inválidos"}, status=400)
    except Transaccion.DoesNotExist:
        return JsonResponse({"success": False, "message": "Transacción no encontrada"}, status=404)
    except Exception:
        return JsonResponse({"success": False, "message": "Error interno del servidor"}, status=500)


@login_required
def popup_banco_simulado(request: HttpRequest, transaccion_id: str) -> HttpResponse:
    """Vista para la ventana emergente del banco simulado.

    Renderiza la interfaz de simulación bancaria en una ventana emergente
    separada para procesar el pago de una transacción.

    Args:
        request: HttpRequest de la solicitud
        transaccion_id: ID único de la transacción a procesar

    Returns:
        HttpResponse con la página de simulación bancaria

    """
    try:
        # Obtener cliente asociado al usuario
        cliente = getattr(request, "cliente", None)
        if not cliente:
            # Crear una transacción dummy para mostrar error
            context = {
                "error": "No hay cliente asociado al usuario",
                "transaccion": None,
                "cliente": None,
            }
            return render(request, "popup_banco_simulado.html", context)

        # Obtener la transacción
        try:
            transaccion = get_object_or_404(Transaccion, id_transaccion=transaccion_id, cliente=cliente)
        except Transaccion.DoesNotExist:
            context = {
                "error": "Transacción no encontrada",
                "transaccion": None,
                "cliente": cliente,
            }
            return render(request, "popup_banco_simulado.html", context)

        # Verificar que la transacción esté en estado pendiente
        if transaccion.estado != "pendiente":
            context = {
                "error": f"La transacción está en estado '{transaccion.estado}' y no puede ser procesada",
                "transaccion": transaccion,
                "cliente": cliente,
            }
            return render(request, "popup_banco_simulado.html", context)

        # Determinar el tipo de procesamiento según el medio de pago
        medio_pago = transaccion.medio_pago or ""
        medio_cobro = transaccion.medio_cobro or ""

        # Si es efectivo, generar código TAUSER para PAGAR
        if medio_pago.lower() == "efectivo":
            # Generar código único para TAUSER
            import random
            import string

            codigo_tauser = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

            context = {
                "transaccion": transaccion,
                "cliente": cliente,
                "es_efectivo": True,
                "codigo_tauser": codigo_tauser,
                "tipo_operacion": "pagar",  # Para pagar dinero
            }

            return render(request, "popup_codigo_tauser.html", context)

        # Para tarjetas y cuentas bancarias, usar el popup bancario primero

        # Obtener los medios financieros reales basados en los identificadores
        medio_pago_obj = None
        medio_cobro_obj = None

        if medio_pago and medio_pago != "efectivo":
            medio_pago_obj = obtener_medio_financiero_por_identificador(medio_pago, cliente)

        if medio_cobro and medio_cobro != "efectivo":
            medio_cobro_obj = obtener_medio_financiero_por_identificador(medio_cobro, cliente)

        context = {
            "transaccion": transaccion,
            "cliente": cliente,
            "es_efectivo": False,
            "medio_pago_obj": medio_pago_obj,
            "medio_cobro_obj": medio_cobro_obj,
        }

        return render(request, "popup_banco_simulado.html", context)

    except Exception:
        context = {
            "error": "Error interno del servidor",
            "transaccion": None,
            "cliente": None,
        }
        return render(request, "popup_banco_simulado.html", context)


@login_required
def popup_codigo_tauser_retiro(request: HttpRequest, transaccion_id: str) -> HttpResponse:
    """Vista para generar código TAUSER de retiro después del pago bancario.

    Esta función se llama después de que se complete exitosamente un pago
    por tarjeta o cuenta bancaria, para generar el código que permite
    retirar el dinero en efectivo en un TAUSER.

    Args:
        request: HttpRequest de la solicitud
        transaccion_id: ID único de la transacción ya pagada

    Returns:
        HttpResponse con la página del código TAUSER para retiro

    """
    try:
        # Obtener cliente asociado al usuario
        cliente = getattr(request, "cliente", None)
        if not cliente:
            context = {
                "error": "No hay cliente asociado al usuario",
                "transaccion": None,
                "cliente": None,
            }
            return render(request, "popup_codigo_tauser.html", context)

        # Obtener la transacción
        try:
            transaccion = get_object_or_404(Transaccion, id_transaccion=transaccion_id, cliente=cliente)
        except Transaccion.DoesNotExist:
            context = {
                "error": "Transacción no encontrada",
                "transaccion": None,
                "cliente": cliente,
            }
            return render(request, "popup_codigo_tauser.html", context)

        # Verificar que la transacción esté completada
        if transaccion.estado != "completada":
            context = {
                "error": "La transacción debe estar completada para generar código de retiro",
                "transaccion": transaccion,
                "cliente": cliente,
            }
            return render(request, "popup_codigo_tauser.html", context)

        # Generar código único para TAUSER (retiro)
        import random
        import string

        codigo_tauser = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

        context = {
            "transaccion": transaccion,
            "cliente": cliente,
            "es_efectivo": False,
            "codigo_tauser": codigo_tauser,
            "tipo_operacion": "retirar",  # Para retirar dinero
        }

        return render(request, "popup_codigo_tauser.html", context)

    except Exception:
        context = {
            "error": "Error interno del servidor",
            "transaccion": None,
            "cliente": None,
        }
        return render(request, "popup_codigo_tauser.html", context)


@require_GET
def api_verificar_cotizacion(request: HttpRequest, transaccion_id: str) -> JsonResponse:
    """Verificasi la cotización de una transacción ha cambiado significativamente.

    Args:
        request: HttpRequest object
        transaccion_id: UUID de la transacción a verificar

    Returns:
        JsonResponse con información del cambio de cotización

    """
    try:
        transaccion = get_object_or_404(Transaccion, id_transaccion=transaccion_id)

        # Solo verificar transacciones pendientes
        if transaccion.estado != "pendiente":
            return JsonResponse({"success": False, "message": "La transacción no está en estado pendiente"}, status=400)

        # Verificar cambio de cotización
        resultado = transaccion.verificar_cambio_cotizacion()

        if "error" in resultado:
            return JsonResponse(
                {"success": False, "message": f"Error al verificar cotización: {resultado['error']}"}, status=500
            )

        # Si hay cambio significativo, actualizar el campo de notificación
        if resultado.get("cambio_detectado"):
            transaccion.cambio_cotizacion_notificado = True
            transaccion.save(update_fields=["tasa_actual", "cambio_cotizacion_notificado"])

        return JsonResponse(
            {
                "success": True,
                "cambio_detectado": resultado.get("cambio_detectado", False),
                "tasa_original": float(resultado.get("tasa_original", 0)),
                "tasa_actual": float(resultado.get("tasa_actual", 0)),
                "porcentaje_cambio": float(resultado.get("porcentaje_cambio", 0)),
                "cambio_absoluto": float(resultado.get("cambio_absoluto", 0)),
                "umbral_superado": resultado.get("umbral_superado", False),
                "transaccion": {
                    "id": str(transaccion.id_transaccion),
                    "estado": transaccion.estado,
                    "monto_origen": float(transaccion.monto_origen),
                    "monto_destino": float(transaccion.monto_destino),
                    "divisa_origen": transaccion.divisa_origen.codigo,
                    "divisa_destino": transaccion.divisa_destino.codigo,
                },
            }
        )

    except Transaccion.DoesNotExist:
        return JsonResponse({"success": False, "message": "Transacción no encontrada"}, status=404)
    except Exception:
        return JsonResponse({"success": False, "message": "Error interno del servidor"}, status=500)


@require_POST
def api_cancelar_por_cotizacion(request: HttpRequest, transaccion_id: str) -> JsonResponse:
    """Cancela una transacción por cambio de cotización.

    Args:
        request: HttpRequest object
        transaccion_id: UUID de la transacción a cancelar

    Returns:
        JsonResponse confirmando la cancelación

    """
    try:
        transaccion = get_object_or_404(Transaccion, id_transaccion=transaccion_id)

        # Solo cancelar transacciones pendientes
        if transaccion.estado != "pendiente":
            return JsonResponse(
                {"success": False, "message": "Solo se pueden cancelar transacciones pendientes"}, status=400
            )

        # Obtener motivo opcional del request
        import json

        try:
            data = json.loads(request.body)
            motivo_custom = data.get("motivo", "")
        except (json.JSONDecodeError, AttributeError):
            motivo_custom = ""

        # Cancelar la transacción
        motivo = motivo_custom or "Cancelada por el cliente debido a cambio de cotización"
        transaccion.cancelar_por_cotizacion(motivo)

        return JsonResponse(
            {
                "success": True,
                "message": "Transacción cancelada exitosamente",
                "transaccion": {
                    "id": str(transaccion.id_transaccion),
                    "estado": transaccion.estado,
                    "motivo_cancelacion": transaccion.motivo_cancelacion,
                },
            }
        )

    except Transaccion.DoesNotExist:
        return JsonResponse({"success": False, "message": "Transacción no encontrada"}, status=404)
    except Exception:
        return JsonResponse({"success": False, "message": "Error interno del servidor"}, status=500)


@require_POST
def api_aceptar_nueva_cotizacion(request: HttpRequest, transaccion_id: str) -> JsonResponse:
    """Acepta la nueva cotización y continuar con la transacción.

    Args:
        request: HttpRequest object
        transaccion_id: UUID de la transacción

    Returns:
        JsonResponse confirmando la aceptación

    """
    try:
        transaccion = get_object_or_404(Transaccion, id_transaccion=transaccion_id)

        # Solo procesar transacciones pendientes
        if transaccion.estado != "pendiente":
            return JsonResponse(
                {"success": False, "message": "Solo se pueden actualizar transacciones pendientes"}, status=400
            )

        # Verificar que hay una nueva cotización disponible
        if not transaccion.tasa_actual:
            resultado = transaccion.verificar_cambio_cotizacion()
            if "error" in resultado:
                return JsonResponse(
                    {"success": False, "message": f"Error al obtener nueva cotización: {resultado['error']}"},
                    status=500,
                )

        # Aceptar la nueva cotización
        transaccion.aceptar_nueva_cotizacion()

        return JsonResponse(
            {
                "success": True,
                "message": "Nueva cotización aceptada exitosamente",
                "transaccion": {
                    "id": str(transaccion.id_transaccion),
                    "estado": transaccion.estado,
                    "tasa_aplicada": float(transaccion.tasa_aplicada),
                    "monto_origen": float(transaccion.monto_origen),
                    "monto_destino": float(transaccion.monto_destino),
                    "divisa_origen": transaccion.divisa_origen.codigo,
                    "divisa_destino": transaccion.divisa_destino.codigo,
                },
            }
        )

    except Transaccion.DoesNotExist:
        return JsonResponse({"success": False, "message": "Transacción no encontrada"}, status=404)
    except Exception:
        return JsonResponse({"success": False, "message": "Error interno del servidor"}, status=500)


# =================
# VISTAS DE STRIPE
# =================


@require_POST
def create_stripe_payment_intent(request: HttpRequest) -> JsonResponse:
    """Crear un Payment Intent de Stripe para procesar el pago.

    Esta vista crea un Payment Intent en Stripe para una transacción específica,
    aplicando la comisión configurada.

    Args:
        request: HttpRequest con datos JSON de la transacción

    Returns:
        JsonResponse con el client_secret del Payment Intent o error

    """
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Usuario no autenticado"}, status=401)

    cliente = getattr(request, "cliente", None)
    if not cliente:
        return JsonResponse({"error": "No hay cliente asociado"}, status=400)

    try:
        # Parsear datos JSON
        data = json.loads(request.body)
        transaccion_id = data.get("transaccion_id")

        if not transaccion_id:
            return JsonResponse({"error": "ID de transacción requerido"}, status=400)

        # Obtener la transacción
        transaccion = get_object_or_404(Transaccion, id_transaccion=transaccion_id, cliente=cliente)

        # Verificar que la transacción esté pendiente
        if transaccion.estado != "pendiente":
            return JsonResponse(
                {"error": f"La transacción está en estado '{transaccion.estado}' y no puede ser procesada"}, status=400
            )

        # Verificar que sea un pago con Stripe
        if not (transaccion.medio_pago == "stripe_new" or transaccion.medio_pago.startswith("stripe_")):
            return JsonResponse({"error": "Esta transacción no es para pago con Stripe"}, status=400)

        # Calcular el monto a cobrar en centavos
        # Para compra: el cliente paga en PYG (monto_origen)
        # Para venta: esto no debería usar Stripe, pero por seguridad verificamos
        if transaccion.tipo_operacion != "compra":
            return JsonResponse({"error": "Stripe solo se usa para operaciones de compra"}, status=400)

        # Convertir PYG a USD para Stripe (aproximadamente 1 USD = 7000 PYG)
        # Stripe requiere montos en centavos de USD
        monto_pyg = float(transaccion.monto_origen)
        monto_usd = monto_pyg / 7000.0  # Conversión aproximada
        monto_centavos = int(monto_usd * 100)  # Convertir a centavos

        # Monto mínimo de Stripe: 50 centavos USD
        if monto_centavos < 50:
            return JsonResponse({"error": "El monto es demasiado pequeño para procesar con Stripe"}, status=400)

        # Crear el Payment Intent
        intent = stripe.PaymentIntent.create(
            amount=monto_centavos,
            currency="usd",
            metadata={
                "transaccion_id": str(transaccion.id_transaccion),
                "cliente_id": str(cliente.id),
                "usuario_id": str(request.user.id),
                "tipo_operacion": transaccion.tipo_operacion,
                "monto_pyg": str(monto_pyg),
            },
            description=f"Compra de {transaccion.divisa_destino.codigo} - Global Exchange",
        )

        # Crear registro de pago Stripe
        from .models import StripePayment

        stripe_payment = StripePayment.objects.create(
            cliente=cliente,
            stripe_payment_intent_id=intent.id,
            amount=Decimal(str(monto_usd)),  # Monto en USD, no centavos
            currency="USD",
            status="requires_payment_method",
            metadata=intent.metadata,
        )

        # Actualizar la transacción con el stripe_payment
        transaccion.stripe_payment = stripe_payment
        transaccion.save()

        return JsonResponse(
            {
                "success": True,
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
                "amount_usd": monto_usd,
                "amount_cents": monto_centavos,
                "stripe_payment_id": stripe_payment.id,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Datos JSON inválidos"}, status=400)
    except stripe.error.StripeError as e:
        print(f"Error de Stripe: {e}")
        return JsonResponse({"error": f"Error de Stripe: {e!s}"}, status=400)
    except Exception as e:
        print(f"Error al crear Payment Intent: {e}")
        return JsonResponse({"error": "Error interno del servidor"}, status=500)


@require_POST
def confirm_stripe_payment(request: HttpRequest) -> JsonResponse:
    """Confirmar el pago de Stripe y actualizar la transacción.

    Esta vista se llama después de que el cliente complete el pago
    en el frontend para confirmar el estado y actualizar la transacción.

    Args:
        request: HttpRequest con datos del Payment Intent

    Returns:
        JsonResponse con el resultado de la confirmación

    """
    import json

    import stripe
    from django.conf import settings

    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Usuario no autenticado"}, status=401)

    cliente = getattr(request, "cliente", None)
    if not cliente:
        return JsonResponse({"error": "No hay cliente asociado"}, status=400)

    try:
        # Parsear datos JSON
        data = json.loads(request.body)
        payment_intent_id = data.get("payment_intent_id")

        if not payment_intent_id:
            return JsonResponse({"error": "ID del Payment Intent requerido"}, status=400)

        # Obtener el Payment Intent de Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)

        # Buscar el registro de pago en la base de datos
        from .models import StripePayment

        stripe_payment = get_object_or_404(StripePayment, stripe_payment_intent_id=payment_intent_id)

        # Buscar la transacción asociada a este StripePayment
        from .models import Transaccion

        transaccion = get_object_or_404(Transaccion, stripe_payment=stripe_payment)

        # Verificar que la transacción pertenece al cliente
        if transaccion.cliente != cliente:
            return JsonResponse({"error": "No tienes permiso para confirmar este pago"}, status=403)

        # Actualizar el estado del pago según Stripe
        stripe_payment.status = intent.status

        if intent.status == "succeeded":
            # Pago exitoso
            transaccion.estado = "completada"
            mensaje = "Pago procesado exitosamente con Stripe"

        elif intent.status in ["requires_payment_method", "requires_confirmation"]:
            # Pago requiere acción adicional
            transaccion.estado = "pendiente"
            mensaje = "El pago requiere confirmación adicional"

        else:
            # Pago fallido o cancelado
            transaccion.estado = "pendiente"
            mensaje = f"Pago no completado. Estado: {intent.status}"

        # Guardar cambios
        stripe_payment.save()
        transaccion.save()

        return JsonResponse(
            {
                "success": True,
                "message": mensaje,
                "payment_status": intent.status,
                "transaccion_status": transaccion.estado,
                "transaccion_id": str(transaccion.id_transaccion),
                "payment_intent_id": payment_intent_id,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Datos JSON inválidos"}, status=400)
    except stripe.error.StripeError as e:
        print(f"Error de Stripe: {e}")
        return JsonResponse({"error": f"Error de Stripe: {e!s}"}, status=400)
    except Exception as e:
        print(f"Error al confirmar pago Stripe: {e}")
        return JsonResponse({"error": "Error interno del servidor"}, status=500)


@require_POST
def stripe_webhook_handler(request: HttpRequest) -> HttpResponse:
    """Webhook handler para eventos de Stripe.

    Maneja eventos enviados por Stripe para mantener sincronizado
    el estado de los pagos.

    Args:
        request: HttpRequest con el evento de Stripe

    Returns:
        HttpResponse con código 200 si se procesó exitosamente

    """
    import stripe
    from django.conf import settings
    from django.http import HttpResponse

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Obtener la clave del webhook endpoint (configurar en settings)
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    try:
        # Verificar la firma del webhook si está configurada
        if endpoint_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            # En desarrollo, parsear directamente sin verificar firma
            import json

            event = json.loads(payload)

        # Manejar el evento
        if event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            _handle_payment_intent_succeeded(payment_intent)

        elif event["type"] == "payment_intent.payment_failed":
            payment_intent = event["data"]["object"]
            _handle_payment_intent_failed(payment_intent)

        elif event["type"] == "payment_intent.canceled":
            payment_intent = event["data"]["object"]
            _handle_payment_intent_canceled(payment_intent)

        else:
            pass  # Evento no manejado

        return HttpResponse(status=200)

    except ValueError as e:
        print(f"Payload inválido del webhook: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        print(f"Firma inválida del webhook: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        print(f"Error en webhook Stripe: {e}")
        return HttpResponse(status=500)


def _handle_payment_intent_succeeded(payment_intent):
    """Manejar evento de pago exitoso."""
    try:
        from .models import StripePayment

        stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent["id"])
        stripe_payment.status = "succeeded"
        stripe_payment.paid = True
        stripe_payment.stripe_charge_id = payment_intent.get("latest_charge")
        stripe_payment.save()

        # Actualizar transacción
        transaccion = stripe_payment.transaccion
        transaccion.estado = "completada"
        transaccion.save()

    except StripePayment.DoesNotExist:
        print(f"StripePayment no encontrado para Payment Intent: {payment_intent['id']}")
    except Exception as e:
        print(f"Error manejando payment_intent.succeeded: {e}")


def _handle_payment_intent_failed(payment_intent):
    """Manejar evento de pago fallido."""
    try:
        from .models import StripePayment

        stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent["id"])
        stripe_payment.status = "failed"
        stripe_payment.paid = False
        stripe_payment.save()

        # La transacción permanece en pendiente para permitir reintentos

    except StripePayment.DoesNotExist:
        pass  # StripePayment no encontrado
    except Exception as e:
        print(f"Error manejando payment_intent.failed: {e}")


def _handle_payment_intent_canceled(payment_intent):
    """Manejar evento de pago cancelado."""
    try:
        from .models import StripePayment

        stripe_payment = StripePayment.objects.get(stripe_payment_intent_id=payment_intent["id"])
        stripe_payment.status = "canceled"
        stripe_payment.paid = False
        stripe_payment.save()

        # Cancelar la transacción también
        transaccion = stripe_payment.transaccion
        transaccion.estado = "cancelada"
        transaccion.motivo_cancelacion = "Pago cancelado en Stripe"
        transaccion.save()

    except StripePayment.DoesNotExist:
        pass  # StripePayment no encontrado
    except Exception as e:
        print(f"Error manejando payment_intent.canceled: {e}")
