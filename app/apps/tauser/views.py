"""Vistas para la aplicación tauser - Terminal de AutoServicio."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.transacciones.models import Transaccion


def ejemplo(request: HttpRequest) -> HttpResponse:
    """Vista de ejemplo.

    Args:
        request (HttpRequest): Solicitud HTTP.

    Returns:
        HttpResponse: Respuesta HTTP con template base.

    """
    return render(request, "base.html")


def bienvenida_atm(request: HttpRequest) -> HttpResponse:
    """Vista principal del ATM que solicita código de verificación.

    Args:
        request (HttpRequest): Solicitud HTTP.

    Returns:
        HttpResponse: Página de bienvenida del ATM.

    """
    if request.method == "POST":
        codigo_verificacion = request.POST.get("codigo_verificacion", "").strip().upper()

        if not codigo_verificacion:
            messages.error(request, "Por favor ingrese un código de verificación.")
            return render(request, "tauser/bienvenida.html")

        try:
            # Buscar transacción con código de verificación
            transaccion = Transaccion.objects.select_related(
                "cliente", "divisa_origen", "divisa_destino", "usuario"
            ).get(codigo_verificacion=codigo_verificacion, estado="pendiente")

            # Verificar que la transacción tenga un usuario responsable asignado
            if not transaccion.usuario:
                messages.error(request, "La transacción no tiene un operador asignado.")
                return render(request, "tauser/bienvenida.html")

            # Guardar ID de transacción en la sesión
            request.session["transaccion_atm_id"] = str(transaccion.id_transaccion)
            request.session["codigo_verificacion_validado"] = True

            # Redirigir al MFA
            return redirect("tauser:mfa")

        except Transaccion.DoesNotExist:
            messages.error(request, "Código de verificación no válido o transacción no encontrada.")
            return render(request, "tauser/bienvenida.html")
        except Exception:
            messages.error(request, "Error al procesar la solicitud. Intente nuevamente.")
            return render(request, "tauser/bienvenida.html")

    return render(request, "tauser/bienvenida.html")


def mfa_atm(request: HttpRequest) -> HttpResponse:
    """Vista para autenticación multi-factor.

    Args:
        request (HttpRequest): Solicitud HTTP.

    Returns:
        HttpResponse: Página de MFA.

    """
    # Verificar que existe una transacción ATM activa
    transaccion_id = request.session.get("transaccion_atm_id")
    codigo_validado = request.session.get("codigo_verificacion_validado", False)

    if not transaccion_id or not codigo_validado:
        messages.error(request, "Sesión no válida. Inicie nuevamente.")
        return redirect("tauser:bienvenida")

    try:
        transaccion = Transaccion.objects.select_related("cliente").get(
            id_transaccion=transaccion_id, estado="pendiente"
        )

    except Transaccion.DoesNotExist:
        messages.error(request, "Transacción no válida.")
        return redirect("tauser:bienvenida")

    if request.method == "POST":
        codigo_mfa = request.POST.get("codigo_mfa", "").strip()

        if not codigo_mfa:
            messages.error(request, "Por favor ingrese el código MFA.")
            return render(request, "tauser/mfa.html", {"sesion_atm": {"transaccion": transaccion}})

        # Verificar MFA con el sistema existente
        from apps.seguridad.models import PerfilMFA
        from apps.seguridad.utils import verificar_codigo_usuario

        try:
            perfil_mfa = PerfilMFA.objects.get(usuario=transaccion.usuario)
            if perfil_mfa.mfa_habilitado_transacciones and verificar_codigo_usuario(transaccion.usuario, codigo_mfa):
                request.session["mfa_completado"] = True
                return redirect("tauser:overview_operacion")
            # Si MFA está deshabilitado para transacciones, aceptar cualquier código de 4-6 dígitos
            elif perfil_mfa.mfa_habilitado_transacciones is False:
                if len(codigo_mfa) >= 4:
                    request.session["mfa_completado"] = True
                    return redirect("tauser:overview_operacion")
            else:
                messages.error(request, "Código MFA no válido.")
        except PerfilMFA.DoesNotExist:
            # Si no tiene MFA configurado, aceptar cualquier código de 4-6 dígitos
            if len(codigo_mfa) >= 4:
                request.session["mfa_completado"] = True
                return redirect("tauser:overview_operacion")
            else:
                messages.error(request, "Código MFA no válido.")

    return render(request, "tauser/mfa.html", {"sesion_atm": {"transaccion": transaccion}})


def overview_operacion(request: HttpRequest) -> HttpResponse:
    """Vista que muestra el resumen de la operación.

    Args:
        request (HttpRequest): Solicitud HTTP.

    Returns:
        HttpResponse: Página de overview de la operación.

    """
    # Verificar sesión ATM activa
    transaccion_id = request.session.get("transaccion_atm_id")
    codigo_validado = request.session.get("codigo_verificacion_validado", False)
    mfa_completado = request.session.get("mfa_completado", False)

    if not transaccion_id or not codigo_validado or not mfa_completado:
        messages.error(request, "Sesión no válida. Inicie nuevamente.")
        return redirect("tauser:bienvenida")

    try:
        transaccion = Transaccion.objects.select_related("cliente", "divisa_origen", "divisa_destino").get(
            id_transaccion=transaccion_id, estado="pendiente"
        )

    except Transaccion.DoesNotExist:
        messages.error(request, "Transacción no válida.")
        return redirect("tauser:bienvenida")

    context = {
        "transaccion": transaccion,
    }

    return render(request, "tauser/overview_operacion.html", context)


@require_http_methods(["POST"])
def cancelar_operacion(request: HttpRequest) -> HttpResponse:
    """Vuelve a la página de bienvenida sin cancelar la transacción.

    Args:
        request (HttpRequest): Solicitud HTTP.

    Returns:
        HttpResponse: Redirección a la página de bienvenida.

    """
    # Limpiar sesión ATM sin modificar la transacción
    session_keys = ["transaccion_atm_id", "codigo_verificacion_validado", "mfa_completado"]
    for key in session_keys:
        if key in request.session:
            del request.session[key]

    messages.info(request, "Sesión finalizada. Puede iniciar una nueva operación.")
    return redirect("tauser:bienvenida")


def procesar_venta(request: HttpRequest) -> HttpResponse:
    """Procesa el pago con billetes para operaciones de venta.

    Verifica cambios en la cotización antes de proceder con la venta.

    Args:
        request (HttpRequest): Solicitud HTTP.

    Returns:
        HttpResponse: Vista de procesamiento de venta o redirección por cambio de cotización.

    """
    # Validar sesión ATM
    transaccion_id = request.session.get("transaccion_atm_id")
    if not transaccion_id:
        messages.error(request, "Sesión no válida. Vuelva a iniciar la operación.")
        return redirect("tauser:bienvenida")

    try:
        transaccion = Transaccion.objects.get(id_transaccion=transaccion_id)

        # Verificar que sea una operación de venta
        if transaccion.tipo_operacion != "venta":
            messages.error(request, "Esta operación no es de venta.")
            return redirect("tauser:bienvenida")
        if transaccion.estado != "pendiente":
            messages.error(request, "La transacción ya ha sido procesada o cancelada.")
            return redirect("tauser:bienvenida")

        # Verificar cambios en la cotización
        resultado_verificacion = transaccion.verificar_cambio_cotizacion()

        if resultado_verificacion.get("cambio_detectado", False):
            context = {
                "transaccion": transaccion,
                "cambio_cotizacion": True,
                "resultado_verificacion": resultado_verificacion,
            }
            return render(request, "tauser/overview_operacion.html", context)

        # Si no hay cambios, proceder normalmente
        context = {"transaccion": transaccion}
        return render(request, "tauser/procesar_venta.html", context)

    except Transaccion.DoesNotExist:
        messages.error(request, "Transacción no encontrada.")
        return redirect("tauser:bienvenida")
    except Exception as e:
        messages.error(request, f"Error inesperado: {e!s}")
        return redirect("tauser:bienvenida")


def procesar_compra(request: HttpRequest) -> HttpResponse:
    """Procesa el retiro de billetes para operaciones de compra.

    Args:
        request (HttpRequest): Solicitud HTTP.

    Returns:
        HttpResponse: Vista de procesamiento de compra.

    """
    from django.core.exceptions import ValidationError

    from apps.stock.models import MovimientoStock
    from apps.stock.services import confirmar_movimiento

    # Validar sesión ATM
    transaccion_id = request.session.get("transaccion_atm_id")
    if not transaccion_id:
        messages.error(request, "Sesión no válida. Vuelva a iniciar la operación.")
        return redirect("tauser:bienvenida")

    transaccion = None
    try:
        transaccion = Transaccion.objects.get(id_transaccion=transaccion_id)

        # Verificar que sea una operación de compra
        if transaccion.tipo_operacion != "compra":
            messages.error(request, "Esta operación no es de compra.")
            return redirect("tauser:bienvenida")

        # Buscar el movimiento de stock pendiente asociado a esta transacción
        movimiento_stock = MovimientoStock.objects.filter(transaccion=transaccion, estado="pendiente").first()

        if not movimiento_stock:
            messages.error(request, "No se encontró movimiento de stock pendiente para esta transacción.")
            return redirect("tauser:bienvenida")

        # Confirmar el movimiento en el servicio (solo necesita el ID)
        confirmar_movimiento(movimiento_stock.pk)

        # NO se genera factura en COMPRA (retiro de efectivo)
        # La factura ya fue generada cuando el cliente pagó con tarjeta/transferencia/stripe

        # Limpiar sesión ATM
        session_keys = ["transaccion_atm_id", "codigo_verificacion_validado", "mfa_completado"]
        for key in session_keys:
            if key in request.session:
                del request.session[key]

        # Renderizar página de confirmación
        context = {
            "transaccion": transaccion,
            "success": True,
        }
        return render(request, "tauser/transaccion_completada.html", context)

    except Transaccion.DoesNotExist:
        messages.error(request, "Transacción no encontrada.")
        return redirect("tauser:bienvenida")
    except ValidationError as e:
        messages.error(request, f"Error al procesar la transacción: {e!s}")
        context = {"transaccion": transaccion, "success": False, "error": str(e)}
        return render(request, "tauser/transaccion_completada.html", context)
    except Exception as e:
        messages.error(request, f"Error inesperado: {e!s}")
        return redirect("tauser:bienvenida")


@require_http_methods(["POST"])
def procesar_billetes_venta(request: HttpRequest) -> HttpResponse:
    """Procesa los billetes depositados por el cliente para operaciones de venta.

    Valida que el monto total de los billetes coincida exactamente con el monto
    requerido y ejecuta el servicio depositar_divisas.

    Args:
        request (HttpRequest): Solicitud HTTP con datos de denominaciones.

    Returns:
        HttpResponse: Página de transacción completada o error.

    """
    import json
    from decimal import Decimal

    from django.core.exceptions import ValidationError
    from django.utils import timezone

    from apps.stock.services import depositar_divisas

    # Validar sesión ATM
    transaccion_id = request.session.get("transaccion_atm_id")
    if not transaccion_id:
        messages.error(request, "Sesión no válida. Vuelva a iniciar la operación.")
        return redirect("tauser:bienvenida")

    transaccion = None
    try:
        transaccion = Transaccion.objects.get(id_transaccion=transaccion_id)
        if transaccion.estado != "pendiente":
            messages.error(request, "La transacción ya ha sido procesada.")
            return redirect("tauser:bienvenida")
        # Verificar que sea una operación de venta
        if transaccion.tipo_operacion != "venta":
            messages.error(request, "Esta operación no es de venta.")
            return redirect("tauser:bienvenida")

        # Obtener denominaciones del formulario
        denominaciones_json = request.POST.get("denominaciones_json", "[]")
        try:
            denominaciones = json.loads(denominaciones_json)
        except json.JSONDecodeError:
            messages.error(request, "Error en el formato de datos de denominaciones.")
            return redirect("tauser:procesar_venta")

        if not denominaciones:
            messages.error(request, "Debe ingresar al menos una denominación de billetes.")
            return redirect("tauser:procesar_venta")

        # Calcular monto total de billetes depositados
        monto_total = Decimal("0.00")
        for item in denominaciones:
            denominacion = Decimal(str(item["denominacion"]))
            cantidad = int(item["cantidad"])
            monto_total += denominacion * cantidad

        # Verificar que el monto coincida exactamente
        monto_requerido = transaccion.monto_origen
        if abs(monto_total - monto_requerido) >= Decimal("0.01"):
            messages.error(
                request,
                f"El monto depositado ({monto_total}) no coincide con el monto requerido ({monto_requerido}). "
                f"Diferencia: {monto_total - monto_requerido}",
            )
            return redirect("tauser:procesar_venta")

        # Ejecutar servicio de depositar_divisas
        # Necesitamos el tauser_id (debe estar en la transacción o sesión)
        from apps.tauser.models import Tauser

        # Obtener el tauser asociado con la transacción
        try:
            id_tauser = (
                Transaccion.objects.filter(id_transaccion=transaccion_id).values_list("tauser__id", flat=True).first()
            )
            tauser = Tauser.objects.filter(id=id_tauser).first()
            if not tauser:
                raise ValueError("Tauser asociado no encontrado")
        except Exception:
            raise ValueError("Error al obtener tauser para el depósito")

        try:
            depositar_divisas(
                tauser_id=tauser.pk,
                divisa_id=transaccion.divisa_origen.codigo,
                denominaciones_cantidades=denominaciones,
                transaccion=transaccion,
                panel_admin=False,
            )
        except Exception as e:
            messages.error(request, f"Error al depositar divisas: {e!s}")
            context = {"transaccion": transaccion, "success": False, "error": str(e)}
            return render(request, "tauser/transaccion_completada.html", context)

        # Actualizar estado de la transacción
        transaccion.estado = "completada"
        transaccion.fecha_pago = timezone.now()
        transaccion.fecha_completada = timezone.now()
        transaccion.save()

        # Generar factura electrónica SOLO en VENTA con efectivo (pago en TAUSER)
        # En VENTA el cliente deposita efectivo = está pagando, por lo tanto se genera factura
        try:
            from apps.transacciones.facturacion import procesar_facturacion_post_pago

            exito, mensaje = procesar_facturacion_post_pago(transaccion)
            if exito:
                print(f"✓ Factura generada para VENTA en efectivo: {mensaje}")
            else:
                print(f"✗ Error generando factura para VENTA en efectivo: {mensaje}")
        except Exception as e:
            # No fallar si la facturación falla
            print(f"✗ Excepción generando factura para transacción TAUSER {transaccion.id_transaccion}: {e}")

        # Limpiar sesión ATM
        session_keys = ["transaccion_atm_id", "codigo_verificacion_validado", "mfa_completado"]
        for key in session_keys:
            if key in request.session:
                del request.session[key]

        # Obtener medio de cobro para mostrar en la confirmación
        from apps.transacciones.views import obtener_medio_financiero_por_identificador

        medio_cobro = obtener_medio_financiero_por_identificador(transaccion.medio_cobro, transaccion.cliente)

        # Renderizar página de confirmación con mensaje específico
        context = {
            "transaccion": transaccion,
            "success": True,
            "mensaje_personalizado": "En breve se realizará su transferencia en su medio de cobro.",
            "medio_cobro": medio_cobro,
        }
        return render(request, "tauser/transaccion_completada.html", context)

    except Transaccion.DoesNotExist:
        messages.error(request, "Transacción no encontrada.")
        return redirect("tauser:bienvenida")
    except ValidationError as e:
        messages.error(request, f"Error de validación: {e!s}")
        if transaccion:
            context = {"transaccion": transaccion, "success": False, "error": str(e)}
            return render(request, "tauser/transaccion_completada.html", context)
        return redirect("tauser:bienvenida")
    except Exception as e:
        messages.error(request, f"Error inesperado: {e!s}")
        if transaccion:
            context = {"transaccion": transaccion, "success": False, "error": str(e)}
            return render(request, "tauser/transaccion_completada.html", context)
        return redirect("tauser:bienvenida")


@require_http_methods(["POST"])
def aceptar_nueva_cotizacion(request: HttpRequest) -> HttpResponse:
    """Acepta la nueva cotización y continúa con la operación.

    Args:
        request (HttpRequest): Solicitud HTTP.

    Returns:
        HttpResponse: Redirección a procesar_venta o error.

    """
    # Validar sesión ATM
    transaccion_id = request.session.get("transaccion_atm_id")
    if not transaccion_id:
        messages.error(request, "Sesión no válida. Vuelva a iniciar la operación.")
        return redirect("tauser:bienvenida")

    try:
        transaccion = Transaccion.objects.get(id_transaccion=transaccion_id)

        # Aceptar la nueva cotización
        transaccion.aceptar_nueva_cotizacion()

        messages.success(request, "Nueva cotización aceptada. Puede continuar con la operación.")

        # Redirigir a overview_operacion para continuar normalmente
        return redirect("tauser:overview_operacion")

    except Transaccion.DoesNotExist:
        messages.error(request, "Transacción no encontrada.")
        return redirect("tauser:bienvenida")
    except Exception as e:
        messages.error(request, f"Error al aceptar la cotización: {e!s}")
        return redirect("tauser:overview_operacion")


@require_http_methods(["POST"])
def cancelar_por_cotizacion(request: HttpRequest) -> HttpResponse:
    """Cancela la transacción por no aceptar la nueva cotización.

    Args:
        request (HttpRequest): Solicitud HTTP.

    Returns:
        HttpResponse: Redirección a bienvenida con transacción cancelada.

    """
    # Validar sesión ATM
    transaccion_id = request.session.get("transaccion_atm_id")
    if not transaccion_id:
        messages.error(request, "Sesión no válida. Vuelva a iniciar la operación.")
        return redirect("tauser:bienvenida")

    try:
        transaccion = Transaccion.objects.get(id_transaccion=transaccion_id)

        # Cancelar por cotización usando el método del modelo
        transaccion.cancelar_por_cotizacion("Transacción cancelada por el cliente debido a cambio de cotización")

        # Limpiar sesión ATM
        session_keys = ["transaccion_atm_id", "codigo_verificacion_validado", "mfa_completado"]
        for key in session_keys:
            if key in request.session:
                del request.session[key]

        messages.info(request, "Transacción cancelada por cambio de cotización.")
        return redirect("tauser:bienvenida")

    except Transaccion.DoesNotExist:
        messages.error(request, "Transacción no encontrada.")
        return redirect("tauser:bienvenida")
    except Exception as e:
        messages.error(request, f"Error al cancelar la transacción: {e!s}")
        return redirect("tauser:bienvenida")
