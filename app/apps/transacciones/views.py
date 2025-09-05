"""Vistas para transacciones de cambio de divisas.

Este módulo proporciona vistas para simular el cambio de divisas y para comprar y vender.
También incluye el CRUD de medios de pago para los clientes.
"""

from datetime import datetime
from typing import Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from apps.usuarios.models import Cliente

from .models import BilleteraElectronica, CuentaBancaria, TarjetaCredito


def _compute_simulation(params: Dict, user) -> Dict:
    """Cálculo centralizado de la simulación.

    params: dict con keys: monto (float), moneda_origen, moneda_destino, tipo_operacion, metodo_pago, metodo_cobro
    user: request.user (puede ser AnonymousUser)
    Retorna diccionario con campos: monto_original, moneda_origen, moneda_destino, tasa_cambio, monto_convertido, descuento, comision_base, comision_final, total, tipo_operacion, metodo_pago, metodo_cobro
    """
    # Tasas de ejemplo relativas a PYG
    rates_to_pyg = {"PYG": 1.0, "USD": 7000.0, "EUR": 7600.0, "BRL": 1300.0}
    iso_decimals = {"PYG": 0, "USD": 2, "EUR": 2, "BRL": 2}

    monto = float(params.get("monto") or 0)
    origen = params.get("moneda_origen") or "PYG"
    destino = params.get("moneda_destino") or "USD"
    tipo = params.get("tipo_operacion") or "compra"
    metodo_pago = params.get("metodo_pago") or "efectivo"
    metodo_cobro = params.get("metodo_cobro") or "efectivo"

    # ratios
    rate = rates_to_pyg.get(origen, 1.0) / rates_to_pyg.get(destino, 1.0)
    converted = monto * rate

    # Comisiones
    commission_pct = {"compra": 0.01, "venta": 0.015}
    base_pct = commission_pct.get(tipo, 0.01)
    comision_base = converted * base_pct

    # Descuento por segmento
    segmento = getattr(user, "segmento", None) or "Minorista"
    segmento_discount = {"VIP": 0.10, "Corporativo": 0.05, "Minorista": 0.0}
    descuento_pct = segmento_discount.get(segmento, 0.0)
    comision_final = comision_base * (1 - descuento_pct)

    # Total a recibir por el cliente (se asume comision descontada del monto convertido)
    total = converted - comision_final

    return {
        "monto_original": round(monto, 6),
        "moneda_origen": origen,
        "moneda_destino": destino,
        "tasa_cambio": rate,
        "monto_convertido": round(converted, 6),
        "comision_base": round(comision_base, 6),
        "descuento": round(descuento_pct * 100, 2),
        "comision_final": round(comision_final, 6),
        "total": round(total, 6),
        "tipo_operacion": tipo,
        "metodo_pago": metodo_pago,
        "metodo_cobro": metodo_cobro,
        "iso_decimals": iso_decimals.get(destino, 2),
    }


def simular_cambio_view(request: HttpRequest) -> HttpResponse:
    """Página de simulación de cambio."""
    return render(request, "simular_cambio.html")


@require_GET
def api_simular_cambio(request: HttpRequest) -> JsonResponse:
    """Return JSON with a live simulation using querystring params.

    Example: /api/simular?monto=100&moneda_origen=PYG&moneda_destino=USD&tipo_operacion=compra
    """
    params = request.GET.dict()
    result = _compute_simulation(params, request.user)
    return JsonResponse(result)


def comprar_divisa_view(request: HttpRequest) -> HttpResponse:
    """Página para comprar divisas."""
    return render(request, "comprar_divisa.html")


def vender_divisa_view(request: HttpRequest) -> HttpResponse:
    """Página para vender divisas."""
    return render(request, "vender_divisa.html")

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
            tarjeta = TarjetaCredito.objects.create(
                cliente=cliente,
                numero_tarjeta=request.POST.get("numero_tarjeta"),
                nombre_titular=request.POST.get("nombre_titular"),
                fecha_expiracion=request.POST.get("fecha_expiracion"),
                cvv=request.POST.get("cvv"),
                alias=request.POST.get("alias", ""),
            )
            if not tarjeta.alias:
                tarjeta.alias = tarjeta.generar_alias()
            tarjeta.save()

            messages.success(request, "Tarjeta de crédito agregada exitosamente.")
            return redirect("medios_pago_cliente", cliente_id=cliente.pk)

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

    contexto = {"cliente": cliente}
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
            cuenta = CuentaBancaria.objects.create(
                cliente=cliente,
                numero_cuenta=request.POST.get("numero_cuenta"),
                banco=request.POST.get("banco"),
                titular_cuenta=request.POST.get("titular_cuenta"),
                documento_titular=request.POST.get("documento_titular", ""),
                alias=request.POST.get("alias", ""),
            )
            if not cuenta.alias:
                cuenta.alias = cuenta.generar_alias()
            cuenta.save()
            messages.success(request, "Cuenta bancaria agregada exitosamente.")
            return redirect("medios_pago_cliente", cliente_id=cliente.id)

        except ValidationError as e:
            # Manejar errores de validación del modelo específicamente
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        field_name = field.replace('_', ' ').title() if field != '__all__' else 'Error'
                        messages.error(request, f"{field_name}: {error}")
            else:
                messages.error(request, f"Error de validación: {e}")
        except Exception as e:
            messages.error(request, f"Error al crear cuenta bancaria: {e!s}")

    contexto = {"cliente": cliente}
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
            billetera = BilleteraElectronica.objects.create(
                cliente=cliente,
                proveedor=request.POST.get("proveedor"),
                identificador=request.POST.get("identificador"),
                numero_telefono=request.POST.get("numero_telefono", ""),
                email_asociado=request.POST.get("email_asociado", ""),
                alias=request.POST.get("alias", ""),
            )
            if not billetera.alias:
                billetera.alias = billetera.generar_alias()
            billetera.save()
            messages.success(request, "Billetera electrónica agregada exitosamente.")
            return redirect("medios_pago_cliente", cliente_id=cliente.id)

        except Exception as e:
            messages.error(request, f"Error al crear billetera: {e!s}")

    contexto = {
        "cliente": cliente,
        "proveedores": BilleteraElectronica.PROVEEDORES,
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

            # Solo actualizar fecha si se proporciona
            fecha_expiracion = request.POST.get("fecha_expiracion")
            if fecha_expiracion:
                tarjeta.fecha_expiracion = datetime.strptime(fecha_expiracion, "%Y-%m-%d").date()

            tarjeta.alias = request.POST.get("alias", "")

            if not tarjeta.alias:
                tarjeta.alias = tarjeta.generar_alias()

            tarjeta.save()
            messages.success(request, "Tarjeta actualizada exitosamente.")
            return redirect("medios_pago_cliente", cliente_id=tarjeta.cliente.id)

        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            else:
                messages.error(request, f"Error de validación: {e}")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error al editar tarjeta: {e!s}")

    contexto = {"tarjeta": tarjeta, "cliente": tarjeta.cliente}
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
            cuenta.banco = request.POST.get("banco", "")
            cuenta.titular_cuenta = request.POST.get("titular_cuenta", "")
            cuenta.documento_titular = request.POST.get("documento_titular", "")
            cuenta.alias = request.POST.get("alias", "")

            if not cuenta.alias:
                cuenta.alias = cuenta.generar_alias()

            cuenta.save()
            messages.success(request, "Cuenta bancaria actualizada exitosamente.")
            return redirect("medios_pago_cliente", cliente_id=cuenta.cliente.id)

        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            else:
                messages.error(request, f"Error de validación: {e}")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error al editar cuenta bancaria: {e!s}")

    contexto = {"cuenta": cuenta, "cliente": cuenta.cliente}
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
            billetera.proveedor = request.POST.get("proveedor", "")
            billetera.identificador = request.POST.get("identificador", "")
            billetera.numero_telefono = request.POST.get("numero_telefono", "")
            billetera.email_asociado = request.POST.get("email_asociado", "")
            billetera.alias = request.POST.get("alias", "")

            if not billetera.alias:
                billetera.alias = billetera.generar_alias()

            billetera.save()
            messages.success(request, "Billetera electrónica actualizada exitosamente.")
            return redirect("medios_pago_cliente", cliente_id=billetera.cliente.id)

        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            else:
                messages.error(request, f"Error de validación: {e}")
        except (ValueError, TypeError) as e:
            messages.error(request, f"Error al editar billetera: {e!s}")

    contexto = {
        "billetera": billetera,
        "cliente": billetera.cliente,
        "proveedores": BilleteraElectronica.PROVEEDORES,
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
        return redirect("configuracion_medios_pago")

    if request.method == "POST":
        cliente_id = medio.cliente.id
        medio.delete()  # Eliminación física
        messages.success(request, f"{tipo.title()} eliminada exitosamente.")
        return redirect("medios_pago_cliente", cliente_id=cliente_id)

    contexto = {
        "medio": medio,
        "tipo": tipo,
        "cliente": medio.cliente,
    }
    return render(request, "transacciones/configuracion/confirmar_eliminar.html", contexto)
