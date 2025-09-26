"""Vistas para la aplicación de operaciones.

Este módulo contiene las vistas CRUD para el modelo TasaCambio.
"""

import pycountry
from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET
from forex_python.converter import CurrencyCodes

from .forms import DivisaForm, TasaCambioForm
from .models import Divisa, TasaCambio, TasaCambioHistorial
from .utils import get_flag_url_from_currency


def crear_divisa(request):
    """View para crear una nueva divisa.

    Argumento:
        request: La solicitud HTTP.
    Retorna:
        HttpResponse: el formulario de creación o la redirección después de guardar.

    """
    if request.method == "POST":
        form = DivisaForm(request.POST)
        if form.is_valid():
            divisa = form.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": "Divisa creada exitosamente",
                    "divisa": {
                        "pk": str(divisa.pk),
                        "codigo": divisa.codigo,
                        "nombre": divisa.nombre,
                        "simbolo": divisa.simbolo,
                        "estado": divisa.estado,
                    },
                },
                status=201,
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors}, status=400)
    form = DivisaForm()
    return render(request, "operaciones/divisa_list.html", {"form": form})


def obtener_divisas(request: HttpRequest) -> JsonResponse:
    """Obtiene las divisas disponibles en el sistema y las devuelve como un JSON.

    Esta vista utiliza la librería `pycountry` para obtener una lista de códigos
    ISO de divisas.

    Argumentos:
        request: La solicitud HTTP.

    Returns:
        JsonResponse: Una respuesta HTTP con una lista de diccionarios de divisas.

    """
    c = CurrencyCodes()
    data = []
    for currency in pycountry.currencies:
        codigo = getattr(currency, "alpha_3", None)
        if not codigo:
            continue
        nombre = getattr(currency, "name", "Desconocida")
        simbolo = c.get_symbol(codigo)
        data.append({"codigo": codigo, "nombre": nombre, "simbolo": simbolo})

    return JsonResponse(data, safe=False)


def edit_divisa(request, pk):
    """View para editar una divisa existente.

    Argumentos:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a editar.
    Retorna:
        HttpResponse: el formulario de edición o la redirección después de guardar.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    if request.method == "POST":
        divisa.nombre = request.POST.get("nombre")
        divisa.simbolo = request.POST.get("simbolo")
        divisa.estado = request.POST.get("estado")
        divisa.save()
        return redirect("operaciones:divisa_list")

    return redirect("operaciones:divisa_list")


def delete_divisa(request, pk):
    """View para eliminar una divisa específica.

    Argumento:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a eliminar.
    Retorna:
        HttpResponse: Redirige a la lista de divisas después de eliminar.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    if request.method == "POST":
        divisa.delete()
        return redirect("operaciones:divisa_list")
    return redirect("operaciones:divisa_detail", pk=pk)


def divisa_detail(request, pk):
    """View para mostrar los detalles de una divisa específica.

    Argumento:
        request: La solicitud HTTP.
        pk: El identificador de la divisa a mostrar.
    Retorna:
        HttpResponse: Renderiza el template divisa_detalle.html con el contexto de la divisa.

    """
    divisa = get_object_or_404(Divisa, pk=pk)
    return render(request, "divisa_detalle.html", {"divisa": divisa})


def divisa_listar(request: HttpRequest) -> object:
    """Muestra el listado de todas las divisas en el sistema.

    Argumentos:
        request: La solicitud HTTP.

    Retorna:
        HttpResponse: La página HTML con la lista de divisas.
    """
    divisas = Divisa.objects.all().order_by("codigo")
    print(f"DEBUG divisa_listar: Found {divisas.count()} currencies in database")
    for divisa in divisas:
        print(f"DEBUG: {divisa.pk} - {divisa.codigo} - {divisa.nombre}")
    return render(request, "divisa_list.html", {"object_list": divisas})


def tasa_cambio_listar(request: HttpRequest) -> object:
    """Renderiza la página de listado de tasas de cambio.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Renderiza el template tasa_cambio_list.html con el contexto de las tasas de cambio.

    """
    tasas = TasaCambio.objects.all().order_by("-fecha_actualizacion")
    return render(request, "tasa_cambio_list.html", {"tasas_de_cambio": tasas})


def tasa_cambio_crear(request: HttpRequest):
    """Crea una nueva tasa de cambio.

    Argumento:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Redirige al listado de tasas o renderiza el formulario de creación.

    """
    if request.method == "POST":
        form = TasaCambioForm(request.POST)
        if form.is_valid():
            nueva_tasa = form.save()
            # Guardar registro inicial en el historial
            TasaCambioHistorial.objects.create(
                tasa_cambio_original=nueva_tasa,
                divisa_origen=nueva_tasa.divisa_origen,
                divisa_destino=nueva_tasa.divisa_destino,
                precio_base=nueva_tasa.precio_base,
                comision_compra=nueva_tasa.comision_compra,
                comision_venta=nueva_tasa.comision_venta,
                activo=nueva_tasa.activo,
                motivo="Creación de Tasa",
                fecha_registro=timezone.now(),
            )
            return redirect("operaciones:tasa_cambio_listar")
    else:
        form = TasaCambioForm()
    return render(request, "tasa_cambio_form.html", {"form": form})


def tasa_cambio_editar(request: HttpRequest, pk: str) -> object:
    """Edita una tasa de cambio existente y guarda los cambios en el historial.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a editar.

    Retorna:
        HttpResponse: Redirige al listado de tasas o renderiza el formulario de edición.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)

    # Guardar valores originales para comparar
    valores_originales = {
        "precio_base": tasa.precio_base,
        "comision_compra": tasa.comision_compra,
        "comision_venta": tasa.comision_venta,
        "activo": tasa.activo,
    }

    if request.method == "POST":
        form = TasaCambioForm(request.POST, instance=tasa)
        if form.is_valid():
            # Verificar si hubo cambios reales
            cambios = []
            if tasa.precio_base != valores_originales["precio_base"]:
                cambios.append(f"Precio base: {valores_originales['precio_base']} → {tasa.precio_base}")
            if tasa.comision_compra != valores_originales["comision_compra"]:
                cambios.append(f"Comisión compra: {valores_originales['comision_compra']} → {tasa.comision_compra}")
            if tasa.comision_venta != valores_originales["comision_venta"]:
                cambios.append(f"Comisión venta: {valores_originales['comision_venta']} → {tasa.comision_venta}")
            if tasa.activo != valores_originales["activo"]:
                cambios.append(
                    f"Estado: {'Activo' if valores_originales['activo'] else 'Inactivo'} → {'Activo' if tasa.activo else 'Inactivo'}"
                )

            # Solo guardar en historial si hubo cambios
            if cambios:
                tasa_editada = form.save()
                # Actualizar fecha de modificación
                tasa_editada.fecha_actualizacion = timezone.now()
                tasa_editada.save()

                # Guardar en el historial con detalles de los cambios
                motivo_detallado = f"Edición de Tasa - Cambios: {'; '.join(cambios)}"
                TasaCambioHistorial.objects.create(
                    tasa_cambio_original=tasa_editada,
                    divisa_origen=tasa_editada.divisa_origen,
                    divisa_destino=tasa_editada.divisa_destino,
                    precio_base=tasa_editada.precio_base,
                    comision_compra=tasa_editada.comision_compra,
                    comision_venta=tasa_editada.comision_venta,
                    activo=tasa_editada.activo,
                    motivo=motivo_detallado,
                    fecha_registro=timezone.now(),
                )

            return redirect("operaciones:tasa_cambio_listar")
    else:
        form = TasaCambioForm(instance=tasa)
    return render(request, "tasa_cambio_form.html", {"form": form})


def tasa_cambio_desactivar(request: HttpRequest, pk: str) -> object:
    """Desactiva una tasa de cambio existente.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a desactivar.

    Retorna:
        HttpResponse: Redirige al listado de tasas.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST" and tasa.activo:  # Solo desactivar si está activa
        tasa.activo = False
        tasa.fecha_actualizacion = timezone.now()
        tasa.save()

        # Guardar en el historial
        TasaCambioHistorial.objects.create(
            tasa_cambio_original=tasa,
            divisa_origen=tasa.divisa_origen,
            divisa_destino=tasa.divisa_destino,
            precio_base=tasa.precio_base,
            comision_compra=tasa.comision_compra,
            comision_venta=tasa.comision_venta,
            activo=tasa.activo,
            motivo="Desactivación de Tasa",
            fecha_registro=timezone.now(),
        )
    return redirect("operaciones:tasa_cambio_listar")


def tasa_cambio_activar(request: HttpRequest, pk: str) -> object:
    """Activa una tasa de cambio existente.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a activar.

    Retorna:
        HttpResponse: Redirige al listado de tasas.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST" and not tasa.activo:  # Solo activar si está inactiva
        tasa.activo = True
        tasa.fecha_actualizacion = timezone.now()
        tasa.save()

        # Guardar en el historial
        TasaCambioHistorial.objects.create(
            tasa_cambio_original=tasa,
            divisa_origen=tasa.divisa_origen,
            divisa_destino=tasa.divisa_destino,
            precio_base=tasa.precio_base,
            comision_compra=tasa.comision_compra,
            comision_venta=tasa.comision_venta,
            activo=tasa.activo,
            motivo="Activación de Tasa",
            fecha_registro=timezone.now(),
        )
    return redirect("operaciones:tasa_cambio_listar")


@require_GET
def tasas_cambio_api(request: HttpRequest) -> JsonResponse:
    """Devuelve las tasas de cambio actuales en formato JSON.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        JsonResponse: JSON con las tasas de cambio activas.

    """
    tasas = (
        TasaCambio.objects.filter(activo=True)
        .select_related("divisa_origen", "divisa_destino")
        .order_by("divisa_origen__codigo")
    )

    tasas_data = []
    for tasa in tasas:
        if tasa.divisa_origen.codigo == "PYG":
            precio_compra = float(tasa.precio_base) - float(tasa.comision_compra)
            precio_venta = float(tasa.precio_base) + float(tasa.comision_venta)
            divisa_mostrar = tasa.divisa_destino
        else:
            precio_compra = float(tasa.precio_base) - float(tasa.comision_compra)
            precio_venta = float(tasa.precio_base) + float(tasa.comision_venta)
            divisa_mostrar = tasa.divisa_origen

        # Obtener historial completo ordenado por fecha
        historial_queryset = (
            TasaCambioHistorial.objects.filter(tasa_cambio_original=tasa)
            .order_by("fecha_registro")  # Ordenar cronológicamente
            .values("fecha_registro", "precio_base", "comision_compra", "comision_venta", "motivo")
        )

        # Convertir el historial a lista y calcular precios
        historial_procesado = []
        for registro in historial_queryset:
            # Calcular precios de compra y venta para cada registro histórico
            if tasa.divisa_origen.codigo == "PYG":
                hist_compra = float(registro["precio_base"]) - float(registro["comision_compra"])
                hist_venta = float(registro["precio_base"]) + float(registro["comision_venta"])
            else:
                hist_compra = float(registro["precio_base"]) - float(registro["comision_compra"])
                hist_venta = float(registro["precio_base"]) + float(registro["comision_venta"])

            historial_procesado.append(
                {
                    "fecha_registro": registro["fecha_registro"],
                    "precio_base": registro["precio_base"],
                    "comision_compra": registro["comision_compra"],
                    "comision_venta": registro["comision_venta"],
                    "precio_compra_calculado": hist_compra,
                    "precio_venta_calculado": hist_venta,
                    "motivo": registro["motivo"],
                }
            )

        tasas_data.append(
            {
                "divisa": {
                    "codigo": divisa_mostrar.codigo,
                    "nombre": divisa_mostrar.nombre,
                    "simbolo": divisa_mostrar.simbolo,
                    "flag_url": get_flag_url_from_currency(divisa_mostrar.codigo),
                },
                "precio_compra": precio_compra,
                "precio_venta": precio_venta,
                "fecha_actualizacion": tasa.fecha_actualizacion.isoformat(),
                "historial": historial_procesado,  # Historial procesado con precios calculados
            }
        )

    return JsonResponse({"tasas": tasas_data, "total": len(tasas_data)})


@require_GET
def historial_tasas_api(request: HttpRequest) -> JsonResponse:
    """Devuelve el historial de tasas de cambio para el gráfico."""
    tasas = (
        TasaCambio.objects.filter(activo=True)
        .select_related("divisa_origen", "divisa_destino")
        .order_by("fecha_actualizacion")
    )

    historial = {}
    for tasa in tasas:
        # Determinar qué divisa mostrar
        if tasa.divisa_origen.codigo == "PYG":
            divisa = tasa.divisa_destino.codigo
        else:
            divisa = tasa.divisa_origen.codigo

        # Obtener historial de esta tasa
        registros_historial = (
            TasaCambioHistorial.objects.filter(tasa_cambio_original=tasa)
            .order_by("fecha_registro")
            .values("fecha_registro", "precio_base", "comision_compra", "comision_venta")
        )

        if registros_historial.exists():
            # Inicializar estructura si no existe
            if divisa not in historial:
                historial[divisa] = {"fechas": [], "compra": [], "venta": []}

            # Procesar cada registro del historial
            for registro in registros_historial:
                if tasa.divisa_origen.codigo == "PYG":
                    precio_compra = float(registro["precio_base"]) - float(registro["comision_compra"])
                    precio_venta = float(registro["precio_base"]) + float(registro["comision_venta"])
                else:
                    precio_compra = float(registro["precio_base"]) - float(registro["comision_compra"])
                    precio_venta = float(registro["precio_base"]) + float(registro["comision_venta"])

                historial[divisa]["fechas"].append(registro["fecha_registro"].isoformat())
                historial[divisa]["compra"].append(precio_compra)
                historial[divisa]["venta"].append(precio_venta)

    return JsonResponse({"historial": historial})


def tasa_cambio_historial_listar(request: HttpRequest) -> object:
    """Renderiza la página de listado del historial de tasas de cambio con filtros.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Renderiza el template tasa_cambio_historial_list.html con el contexto del historial filtrado.

    """
    from datetime import datetime

    historial = TasaCambioHistorial.objects.all().order_by("-fecha_registro")

    # Filtros
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    divisa = request.GET.get("divisa")
    motivo = request.GET.get("motivo")

    if fecha_inicio:
        historial = historial.filter(fecha_registro__gte=fecha_inicio)
    if fecha_fin:
        # Hacer que la fecha de fin sea inclusiva hasta el final del día
        try:
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
            fecha_fin_dt = fecha_fin_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            historial = historial.filter(fecha_registro__lte=fecha_fin_dt)
        except Exception:
            historial = historial.filter(fecha_registro__lte=fecha_fin)
    if divisa:
        historial = historial.filter(Q(divisa_origen__codigo=divisa) | Q(divisa_destino__codigo=divisa))
    if motivo:
        historial = historial.filter(motivo__icontains=motivo)

    # Obtener motivos únicos (sin duplicados)
    motivos_queryset = TasaCambioHistorial.objects.values_list("motivo", flat=True).distinct()
    motivos_unicos = sorted(set(motivos_queryset))

    context = {
        "historial": historial,
        "divisas": Divisa.objects.all(),  # Para el filtro de divisas
        "motivos": motivos_unicos,  # Motivos únicos para el filtro
    }

    return render(request, "tasa_cambio_historial_list.html", context)


# Vista mínima para crear tasa (solo para tests)
def crear_tasa_minimal(request):
    if request.method == "POST":
        form = TasaCambioForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("operaciones:tasa_cambio_listar")
        else:
            # Formulario con errores - devolver 200
            return render(request, "operaciones/crear_tasa.html", {"form": form})
    else:
        form = TasaCambioForm()
        return render(request, "operaciones/crear_tasa.html", {"form": form})


# Vista mínima para listar divisas (solo para tests)
def divisa_listar_minimal(request):
    divisas = Divisa.objects.all()
    return render(request, "operaciones/divisa_list.html", {"divisas": divisas})


# Vista mínima API para obtener divisas (solo para tests)
def obtener_divisas_minimal(request):
    divisas = Divisa.objects.all()
    data = []
    for divisa in divisas:
        data.append({"id": str(divisa.id), "codigo": divisa.codigo, "nombre": divisa.nombre, "simbolo": divisa.simbolo})
    return JsonResponse({"divisas": data})


# Vista mínima API para historial tasas (solo para tests)
def historial_tasas_api_minimal(request):
    """API endpoint para obtener historial de tasas de cambio de forma simplificada."""
    try:
        # Obtener las últimas 10 tasas de cambio
        tasas = TasaCambio.objects.select_related("divisa_origen", "divisa_destino").all()[:10]
        data = []

        for tasa in tasas:
            # Use pk instead of id in case there's a custom primary key
            tasa_id = getattr(tasa, "id", None) or tasa.pk

            data.append(
                {
                    "id": str(tasa_id),
                    "divisa_origen": tasa.divisa_origen.codigo,
                    "divisa_destino": tasa.divisa_destino.codigo,
                    "precio_base": float(tasa.precio_base),
                    "comision_compra": float(tasa.comision_compra),
                    "comision_venta": float(tasa.comision_venta),
                    "activo": tasa.activo,
                    # Usar fecha_actualizacion que sí existe en el modelo
                    "fecha": tasa.fecha_actualizacion.isoformat()
                    if tasa.fecha_actualizacion
                    else "2024-01-01T00:00:00",
                }
            )

        return JsonResponse({"historial": data}, status=200)

    except Exception as e:
        # Log del error para debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error en historial_tasas_api_minimal: {e!s}")

        return JsonResponse({"error": "Error interno del servidor"}, status=500)
