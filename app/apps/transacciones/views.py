"""Vistas para transacciones de cambio de divisas.

Este módulo proporciona vistas para simular el cambio de divisas y para comprar y vender.
También incluye el CRUD de medios de pago para los clientes.
"""

from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.usuarios.models import Cliente

from .models import BilleteraElectronica, CuentaBancaria, TarjetaCredito


def simular_cambio_view(request: HttpRequest) -> HttpResponse:
    """Página de simulación de cambio."""
    return render(request, "transacciones/simular_cambio.html")


def comprar_divisa_view(request: HttpRequest) -> HttpResponse:
    """Página para comprar divisas."""
    return render(request, "transacciones/comprar_divisa.html")


def vender_divisa_view(request: HttpRequest) -> HttpResponse:
    """Página para vender divisas."""
    return render(request, "transacciones/vender_divisa.html")

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

    # Obtener todos los medios de pago del cliente (ahora eliminamos físicamente)
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
                ruc_titular=request.POST.get("ruc_titular", ""),
                alias=request.POST.get("alias", ""),
            )
            if not cuenta.alias:
                cuenta.alias = cuenta.generar_alias()
            cuenta.save()
            messages.success(request, "Cuenta bancaria agregada exitosamente.")
            return redirect("medios_pago_cliente", cliente_id=cliente.id)

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
            cuenta.ruc_titular = request.POST.get("ruc_titular", "")
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
