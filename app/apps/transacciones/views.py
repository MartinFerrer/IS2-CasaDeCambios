"""Vistas para transacciones de cambio de divisas.

Este módulo proporciona vistas para simular el cambio de divisas y para comprar y vender.
También incluye el CRUD de medios de pago para los clientes.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict

from apps.operaciones.models import Divisa, TasaCambio
from apps.usuarios.models import Cliente
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .models import BilleteraElectronica, CuentaBancaria, EntidadFinanciera, TarjetaCredito


def _compute_simulation(params: Dict, user, cliente_id=None) -> Dict:
    """Cálculo centralizado de la simulación.

    params: dict con keys: monto (float), divisa_seleccionada, tipo_operacion,
    metodo_pago, metodo_cobro
    user: request.user (puede ser AnonymousUser)
    cliente_id: ID del cliente seleccionado para la simulación

    Todas las transacciones son desde/hacia PYG:
    - Compra: cliente da PYG y recibe divisa seleccionada
    - Venta: cliente da divisa seleccionada y recibe PYG
    """
    monto = float(params.get("monto") or 0)
    divisa_seleccionada = params.get("divisa_seleccionada") or "USD"
    tipo = params.get("tipo_operacion") or "compra"
    metodo_pago = params.get("metodo_pago") or "efectivo"
    metodo_cobro = params.get("metodo_cobro") or "efectivo"

    # Obtener cliente seleccionado para descuentos
    cliente = None
    if cliente_id:
        try:
            cliente = Cliente.objects.get(pk=cliente_id)
        except Cliente.DoesNotExist:
            pass

    # Determinar monedas origen y destino según tipo de operación
    if tipo == "compra":
        moneda_origen = "PYG"
        moneda_destino = divisa_seleccionada
    else:  # venta
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
        # Tasas de ejemplo relativas a PYG
        rates_to_pyg = {"USD": 7000.0, "EUR": 7600.0, "BRL": 1300.0}
        pb_dolar = Decimal(str(rates_to_pyg.get(divisa_seleccionada, 7000.0)))
        comision_com = Decimal("50.0")  # Comisión de compra por defecto
        comision_vta = Decimal("75.0")  # Comisión de venta por defecto
    else:
        pb_dolar = tasa_cambio.valor
        comision_com = tasa_cambio.comision_compra
        comision_vta = tasa_cambio.comision_venta

    # Obtener descuento por segmento del cliente
    pordes = Decimal("0.0")
    if cliente and cliente.tipo_cliente:
        pordes = cliente.tipo_cliente.descuento_sobre_comision

    # Obtener comisión del medio de pago específico si es aplicable
    comision_medio_pago_valor = Decimal("0.0")
    # Obtener comisión del medio de cobro específico si es aplicable
    comision_medio_cobro_valor = Decimal("0.0")

    # Procesar medio de pago
    if metodo_pago.startswith("tarjeta_") and cliente:
        try:
            tarjeta_id = int(metodo_pago.split("_")[1])
            tarjeta = TarjetaCredito.objects.get(id=tarjeta_id, cliente=cliente)
            if tarjeta.entidad:
                if tipo == "compra":
                    comision_medio_pago_valor = tarjeta.entidad.comision_compra
                else:
                    comision_medio_pago_valor = tarjeta.entidad.comision_venta
            else:
                comision_medio_pago_valor = Decimal("5.0")  # Comisión por defecto
        except (ValueError, TarjetaCredito.DoesNotExist):
            comision_medio_pago_valor = Decimal("5.0")  # Comisión por defecto

    elif metodo_pago.startswith("cuenta_") and cliente:
        try:
            cuenta_id = int(metodo_pago.split("_")[1])
            cuenta = CuentaBancaria.objects.get(id=cuenta_id, cliente=cliente)
            if cuenta.entidad:
                if tipo == "compra":
                    comision_medio_pago_valor = cuenta.entidad.comision_compra
                else:
                    comision_medio_pago_valor = cuenta.entidad.comision_venta
            else:
                comision_medio_pago_valor = Decimal("0.0")  # Comisión por defecto
        except (ValueError, CuentaBancaria.DoesNotExist):
            comision_medio_pago_valor = Decimal("0.0")  # Comisión por defecto

    elif metodo_pago.startswith("billetera_") and cliente:
        try:
            billetera_id = int(metodo_pago.split("_")[1])
            billetera = BilleteraElectronica.objects.get(id=billetera_id, cliente=cliente)
            if billetera.entidad:
                if tipo == "compra":
                    comision_medio_pago_valor = billetera.entidad.comision_compra
                else:
                    comision_medio_pago_valor = billetera.entidad.comision_venta
            else:
                comision_medio_pago_valor = Decimal("3.0")  # Comisión por defecto
        except (ValueError, BilleteraElectronica.DoesNotExist):
            comision_medio_pago_valor = Decimal("3.0")  # Comisión por defecto
    else:
        # Para efectivo o medios genéricos, usar comisiones por defecto
        comisiones_medios = {
            "efectivo": Decimal("0.0"),  # 0%
            "cuenta": Decimal("0.0"),  # 0%
            "tarjeta": Decimal("5.0"),  # 5%
            "billetera": Decimal("3.0"),  # 3%
        }

        # Determinar tipo de medio de pago para comisión
        if metodo_pago.startswith("tarjeta"):
            comision_medio_pago_valor = comisiones_medios["tarjeta"]
        elif metodo_pago.startswith("cuenta"):
            comision_medio_pago_valor = comisiones_medios["cuenta"]
        elif metodo_pago.startswith("billetera"):
            comision_medio_pago_valor = comisiones_medios["billetera"]
        else:
            comision_medio_pago_valor = comisiones_medios["efectivo"]

    # Procesar medio de cobro
    if metodo_cobro.startswith("tarjeta_") and cliente:
        try:
            tarjeta_id = int(metodo_cobro.split("_")[1])
            tarjeta = TarjetaCredito.objects.get(id=tarjeta_id, cliente=cliente)
            if tarjeta.entidad:
                if tipo == "compra":
                    comision_medio_cobro_valor = tarjeta.entidad.comision_compra
                else:
                    comision_medio_cobro_valor = tarjeta.entidad.comision_venta
            else:
                comision_medio_cobro_valor = Decimal("5.0")  # Comisión por defecto
        except (ValueError, TarjetaCredito.DoesNotExist):
            comision_medio_cobro_valor = Decimal("5.0")  # Comisión por defecto

    elif metodo_cobro.startswith("cuenta_") and cliente:
        try:
            cuenta_id = int(metodo_cobro.split("_")[1])
            cuenta = CuentaBancaria.objects.get(id=cuenta_id, cliente=cliente)
            if cuenta.entidad:
                if tipo == "compra":
                    comision_medio_cobro_valor = cuenta.entidad.comision_compra
                else:
                    comision_medio_cobro_valor = cuenta.entidad.comision_venta
            else:
                comision_medio_cobro_valor = Decimal("0.0")  # Comisión por defecto
        except (ValueError, CuentaBancaria.DoesNotExist):
            comision_medio_cobro_valor = Decimal("0.0")  # Comisión por defecto

    elif metodo_cobro.startswith("billetera_") and cliente:
        try:
            billetera_id = int(metodo_cobro.split("_")[1])
            billetera = BilleteraElectronica.objects.get(id=billetera_id, cliente=cliente)
            if billetera.entidad:
                if tipo == "compra":
                    comision_medio_cobro_valor = billetera.entidad.comision_compra
                else:
                    comision_medio_cobro_valor = billetera.entidad.comision_venta
            else:
                comision_medio_cobro_valor = Decimal("3.0")  # Comisión por defecto
        except (ValueError, BilleteraElectronica.DoesNotExist):
            comision_medio_cobro_valor = Decimal("3.0")  # Comisión por defecto
    else:
        # Para efectivo o medios genéricos, usar comisiones por defecto
        comisiones_medios = {
            "efectivo": Decimal("0.0"),  # 0%
            "cuenta": Decimal("0.0"),  # 0%
            "tarjeta": Decimal("5.0"),  # 5%
            "billetera": Decimal("3.0"),  # 3%
        }

        # Determinar tipo de medio de cobro para comisión
        if metodo_cobro.startswith("tarjeta"):
            comision_medio_cobro_valor = comisiones_medios["tarjeta"]
        elif metodo_cobro.startswith("cuenta"):
            comision_medio_cobro_valor = comisiones_medios["cuenta"]
        elif metodo_cobro.startswith("billetera"):
            comision_medio_cobro_valor = comisiones_medios["billetera"]
        else:
            comision_medio_cobro_valor = comisiones_medios["efectivo"]

    # Calcular según las fórmulas corregidas
    if tipo == "compra":
        # Cliente da PYG y recibe divisa
        # Precio final compra = precio base + (comisión compra - (comisión compra * descuento por segmento))
        comision_efectiva = comision_com - (comision_com * pordes / Decimal("100"))
        tc_efectiva = pb_dolar + comision_efectiva

        # Aplicar comisión del medio de pago al monto que se paga en PYG
        comision_medio_pago = Decimal(str(monto)) * comision_medio_pago_valor / Decimal("100")
        monto_efectivo_para_cambio = monto - float(comision_medio_pago)

        # Calcular divisa que se recibe con el monto efectivo (después de comisión del medio)
        converted = monto_efectivo_para_cambio / float(tc_efectiva)  # Monto en divisa destino
        comision_final = float(comision_efectiva)
        total_antes_comision_medio = monto / float(tc_efectiva)  # Para mostrar diferencia
        total = converted
        tasa_display = float(tc_efectiva)

        # Para compra, no se aplica comisión de cobro (se cobra en efectivo)
        comision_medio_cobro = Decimal("0.0")
    else:  # venta
        # Cliente da divisa y recibe PYG
        # Precio final venta = precio base - (comisión venta - (comisión venta * descuento por segmento))
        comision_efectiva = comision_vta - (comision_vta * pordes / Decimal("100"))
        tc_efectiva = pb_dolar - comision_efectiva
        converted = monto * float(tc_efectiva)  # Monto en PYG antes de comisión medio
        comision_final = float(comision_efectiva)
        total_antes_comision_medio = converted

        # Para venta, NO aplicar comisión del medio de pago (cliente da divisa en efectivo)
        comision_medio_pago = Decimal("0.0")

        # Aplicar comisión del medio de cobro al recibir PYG
        comision_medio_cobro = Decimal(str(total_antes_comision_medio)) * comision_medio_cobro_valor / Decimal("100")
        total = total_antes_comision_medio - float(comision_medio_cobro)
        tasa_display = float(tc_efectiva)

    # Determinar tipo de medio de pago para display
    tipo_medio_pago = "efectivo"
    if metodo_pago.startswith("tarjeta"):
        tipo_medio_pago = "tarjeta"
    elif metodo_pago.startswith("cuenta"):
        tipo_medio_pago = "cuenta"
    elif metodo_pago.startswith("billetera"):
        tipo_medio_pago = "billetera"

    # Determinar tipo de medio de cobro para display
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
    }


def simular_cambio_view(request: HttpRequest) -> HttpResponse:
    """Página de simulación de cambio con cliente seleccionado en sesión."""
    cliente_asociado = None
    if request.user.is_authenticated:
        cliente_id = request.session.get("cliente_id")
        if cliente_id:
            cliente_asociado = Cliente.objects.filter(id=cliente_id, usuarios=request.user).first()
        else:
            # fallback al primer cliente del usuario
            cliente_asociado = Cliente.objects.filter(usuarios=request.user).first()

    divisas = Divisa.objects.filter(estado="activo").exclude(codigo="PYG")

    context = {
        "cliente_asociado": cliente_asociado,
        "divisas": divisas,
    }
    return render(request, "simular_cambio.html", context)


@require_GET
def api_simular_cambio(request: HttpRequest) -> JsonResponse:
    """Return JSON with a live simulation using querystring params.

    Example: /api/simular?monto=100&moneda_origen=PYG&moneda_destino=USD&tipo_operacion=compra
    """
    params = request.GET.dict()
    cliente_id = params.get("cliente_id")
    result = _compute_simulation(params, request.user, cliente_id)
    return JsonResponse(result)


@require_GET
def api_clientes_usuario(request: HttpRequest) -> JsonResponse:
    """Retorna los clientes asociados al usuario autenticado."""
    if not request.user.is_authenticated:
        return JsonResponse({"clientes": []})

    clientes = Cliente.objects.filter(usuarios=request.user).values("id", "nombre", "ruc")
    return JsonResponse({"clientes": list(clientes)})


@require_GET
def api_medios_pago_cliente(request: HttpRequest, cliente_id: int) -> JsonResponse:
    """Retorna los medios de pago asociados a un cliente.

    Filtra las opciones según el tipo de operación:
    - Compra: todos los medios de pago disponibles, solo efectivo para cobro
    - Venta: solo efectivo para pago y cobro
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
    """Retorna las divisas disponibles basadas en las tasas de cambio activas.

    Solo retorna divisas_destino ya que todas las transacciones son desde/hacia PYG.
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
    """Página para comprar divisas con cliente asociado automáticamente."""
    # Obtener divisas disponibles (excluyendo PYG)
    divisas = Divisa.objects.filter(estado="activo").exclude(codigo="PYG")

    context = {
        "divisas": divisas,
        # request.cliente ya lo añade el middleware
    }
    return render(request, "comprar_divisa.html", context)


def vender_divisa_view(request: HttpRequest) -> HttpResponse:
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
def configuracion_medios_pago(request: HttpRequest) -> HttpResponse:
    """Muestra lista de clientes asociados al usuario en sesión.

    Args:
        request: HttpRequest object.

    Returns:
        HttpResponse: Rendered lista_clientes.html template.

    """
    # Obtener clientes asociados al usuario actual
    clientes = request.user.clientes.all()

    contexto = {
        "clientes": clientes,
    }
    return render(request, "transacciones/configuracion/lista_clientes.html", contexto)


@login_required
def medios_pago_cliente(request: HttpRequest, cliente_id: int) -> HttpResponse:
    """Muestra todos los medios de pago registrados (tarjetas, cuentas, billeteras).

    Args:
        request: HttpRequest object.
        cliente_id: ID del cliente a mostrar.

    Returns:
        HttpResponse: Rendered medios_pago_cliente.html template.

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
    """Procesa el formulario para agregar una nueva tarjeta de crédito a un cliente.

    Args:
        request: HttpRequest object.
        cliente_id: ID del cliente al que se agregará la tarjeta.

    Returns:
        HttpResponse: Rendered crear_tarjeta.html template o redirect.

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
                numero_tarjeta=request.POST.get("numero_tarjeta"),
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
    """Procesa el formulario para agregar una nueva cuenta bancaria a un cliente.

    Args:
        request: HttpRequest object.
        cliente_id: ID del cliente al que se agregará la cuenta.

    Returns:
        HttpResponse: Rendered crear_cuenta_bancaria.html template o redirect.

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
    """Procesa el formulario para agregar una nueva billetera electrónica a un cliente.

    Args:
        request: HttpRequest object.
        cliente_id: ID del cliente al que se agregará la billetera.

    Returns:
        HttpResponse: Rendered crear_billetera.html template o redirect.

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
    """Edita una tarjeta de crédito existente.

    Args:
        request: HttpRequest object.
        cliente_id: ID del cliente propietario de la tarjeta.
        medio_id: ID de la tarjeta a editar.

    Returns:
        HttpResponse: Rendered editar_tarjeta.html template o redirect.

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
    """Edita una cuenta bancaria existente.

    Args:
        request: HttpRequest object.
        cliente_id: ID del cliente propietario de la cuenta.
        medio_id: ID de la cuenta a editar.

    Returns:
        HttpResponse: Rendered editar_cuenta_bancaria.html template o redirect.

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
    """Edita una billetera electrónica existente.

    Args:
        request: HttpRequest object.
        cliente_id: ID del cliente propietario de la billetera.
        medio_id: ID de la billetera a editar.

    Returns:
        HttpResponse: Rendered editar_billetera.html template o redirect.

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
    """Elimina un medio de pago específico.

    Args:
        request: HttpRequest object.
        cliente_id: ID del cliente propietario del medio de pago.
        tipo: Tipo de medio de pago ('tarjeta', 'cuenta', 'billetera').
        medio_id: ID del medio de pago a eliminar.

    Returns:
        HttpResponse: Rendered confirmar_eliminar.html template o redirect.

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


@login_required
def vista_transacciones(request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        messages.warning(request, "Primero selecciona un cliente.")
        return redirect("presentacion:home")  # si no eligió cliente

    # Obtener cliente y verificar que pertenece al usuario
    cliente = get_object_or_404(Cliente, id=cliente_id, usuarios=request.user)

    # Obtener transacciones del cliente
    transacciones = cliente.transacciones.all()  # asegurarse de que existe related_name

    return render(request, "transacciones/lista.html", {"transacciones": transacciones, "cliente": cliente})
