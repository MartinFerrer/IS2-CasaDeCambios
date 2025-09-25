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


def _get_payment_commission(metodo_pago: str, cliente, tipo: str) -> Decimal:
    """Calcula la comisión del medio de pago."""
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
        }
        if metodo_pago.startswith("tarjeta"):
            return comisiones_medios["tarjeta"]
        elif metodo_pago.startswith("cuenta"):
            return comisiones_medios["cuenta"]
        elif metodo_pago.startswith("billetera"):
            return comisiones_medios["billetera"]
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
        total = converted + float(comision_medio_pago)  # Total en guaraníes a pagar

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

    # Determinar tipos de medios para display
    tipo_medio_pago = "efectivo"
    if metodo_pago.startswith("tarjeta"):
        tipo_medio_pago = "tarjeta"
    elif metodo_pago.startswith("cuenta"):
        tipo_medio_pago = "cuenta"
    elif metodo_pago.startswith("billetera"):
        tipo_medio_pago = "billetera"

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
    """Página para simular operaciones de cambio.

    Presenta una página donde el usuario puede simular una operación de compra/venta
    de divisas. El cliente se obtiene automáticamente del middleware.

    :param request: Objeto HttpRequest.
    :type request: django.http.HttpRequest
    :return: HttpResponse con el template "simular_cambio.html" y el contexto que
        incluye las divisas disponibles y el cliente asociado (si existe).
    :rtype: django.http.HttpResponse
    """
    divisas = Divisa.objects.filter(estado="activo").exclude(codigo="PYG")

    context = {
        "divisas": divisas,
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
        transacciones = cliente.transacciones.all()

    return render(
        request, "transacciones/lista_transacciones.html", {"transacciones": transacciones, "cliente": cliente}
    )


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
        # El cliente se obtiene automáticamente del middleware en request.cliente
    }
    return render(request, "realizar_transaccion.html", context)


@require_GET
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
                divisa_origen = Divisa.objects.get(codigo=divisa_seleccionada)
                divisa_destino = Divisa.objects.get(codigo="PYG")
            else:  # venta
                divisa_origen = Divisa.objects.get(codigo=divisa_seleccionada)
                divisa_destino = Divisa.objects.get(codigo="PYG")
        except Divisa.DoesNotExist:
            return JsonResponse({"error": "Divisa no válida"}, status=400)

        # Crear la transacción
        from .models import Transaccion

        transaccion = Transaccion.objects.create(
            cliente=cliente,
            usuario=request.user,  # Usuario es el modelo de autenticación personalizado
            tipo_operacion=tipo_operacion,
            estado="pendiente",
            divisa_origen=divisa_origen,
            divisa_destino=divisa_destino,
            tasa_aplicada=Decimal(str(simulation_data["tasa_cambio"])),
            monto_origen=Decimal(str(simulation_data["monto_original"])),
            monto_destino=Decimal(str(simulation_data["total"])),
        )

        return JsonResponse(
            {
                "success": True,
                "transaccion_id": str(transaccion.id_transaccion),
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

    Esta vista redirige al flujo de procesamiento adecuado según el tipo de operación
    y los métodos de pago/cobro seleccionados.

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

        # Obtener parámetros de la transacción desde la sesión o query params
        metodo_pago = request.GET.get("metodo_pago", "efectivo")
        metodo_cobro = request.GET.get("metodo_cobro", "efectivo")

        context = {
            "transaccion": transaccion,
            "metodo_pago": metodo_pago,
            "metodo_cobro": metodo_cobro,
        }

        # Por ahora, renderizar una vista genérica de procesamiento
        # En el futuro, se puede añadir lógica para redirigir a vistas específicas
        # según el tipo de operación y métodos de pago/cobro
        return render(request, "procesar_transaccion.html", context)

    except Exception as e:
        messages.error(request, f"Error al procesar transacción: {e!s}")
        return redirect("transacciones:realizar_transaccion")
