"""Vistas para la aplicación de operaciones.

Este módulo contiene las vistas CRUD para el modelo TasaCambio.
"""

from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .forms import TasaCambioForm
from .models import Divisa, TasaCambio, TasaCambioHistorial
from .utils import get_flag_url_from_currency


def tasa_cambio_listar(request: HttpRequest) -> object:
    """Renderiza la página de listado de tasas de cambio.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Renderiza el template tasa_cambio_list.html con el contexto de las tasas de cambio.

    """
    tasas = TasaCambio.objects.all().order_by("-fecha_actualizacion")
    return render(request, "tasa_cambio_list.html", {"tasas_de_cambio": tasas})


def tasa_cambio_crear(request: HttpRequest) -> object:
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
            # Guardar en el historial
            TasaCambioHistorial.objects.create(
                tasa_cambio_original=nueva_tasa,
                divisa_origen=nueva_tasa.divisa_origen,
                divisa_destino=nueva_tasa.divisa_destino,
                precio_base=nueva_tasa.precio_base,
                comision_compra=nueva_tasa.comision_compra,
                comision_venta=nueva_tasa.comision_venta,
                activo=nueva_tasa.activo,
                motivo="Creación de Tasa",
            )
            return redirect("operaciones:tasa_cambio_listar")
    else:
        form = TasaCambioForm()
    return render(request, "tasa_cambio_form.html", {"form": form})


def tasa_cambio_editar(request: HttpRequest, pk: str) -> object:
    """Edita una tasa de cambio existente.

    Argumento:
        request: Objeto HttpRequest.
        pk: str, el identificador único (UUID) de la tasa de cambio a editar.

    Retorna:
        HttpResponse: Redirige al listado de tasas o renderiza el formulario de edición.

    """
    tasa = get_object_or_404(TasaCambio, pk=pk)
    if request.method == "POST":
        form = TasaCambioForm(request.POST, instance=tasa)
        if form.is_valid():
            tasa_editada = form.save()
            # Guardar en el historial
            TasaCambioHistorial.objects.create(
                tasa_cambio_original=tasa_editada,
                divisa_origen=tasa_editada.divisa_origen,
                divisa_destino=tasa_editada.divisa_destino,
                precio_base=tasa_editada.precio_base,
                comision_compra=tasa_editada.comision_compra,
                comision_venta=tasa_editada.comision_venta,
                activo=tasa_editada.activo,
                motivo="Edición de Tasa",
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
    if request.method == "POST":
        tasa.activo = False
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
        )
        return redirect("operaciones:tasa_cambio_listar")
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
    if request.method == "POST":
        tasa.activo = True
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
        )
        return redirect("operaciones:tasa_cambio_listar")
    return redirect("operaciones:tasa_cambio_listar")


#########################################################################################################
@require_GET
def tasas_cambio_api(request: HttpRequest) -> JsonResponse:
    """Devuelve las tasas de cambio actuales en formato JSON.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        JsonResponse: JSON con las tasas de cambio activas.

    """
    # Obtener solo las tasas activas, ordenadas por divisa origen
    tasas = (
        TasaCambio.objects.filter(activo=True)
        .select_related("divisa_origen", "divisa_destino")
        .order_by("divisa_origen__codigo")
    )

    tasas_data = []
    for tasa in tasas:
        # Calcular precio de compra y venta
        if tasa.divisa_origen.codigo == "PYG":
            # Si la divisa origen es PYG, entonces vendemos la divisa destino
            precio_compra = float(tasa.precio_base) - float(tasa.comision_compra)
            precio_venta = float(tasa.precio_base) + float(tasa.comision_venta)
            divisa_mostrar = tasa.divisa_destino
        else:
            # Si la divisa destino es PYG, entonces compramos la divisa origen
            precio_compra = float(tasa.precio_base) - float(tasa.comision_compra)
            precio_venta = float(tasa.precio_base) + float(tasa.comision_venta)
            divisa_mostrar = tasa.divisa_origen

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
            precio_compra = float(tasa.precio_base) + float(tasa.comision_compra)
            precio_venta = float(tasa.precio_base) - float(tasa.comision_venta)
        else:
            divisa = tasa.divisa_origen.codigo
            precio_compra = float(tasa.precio_base) - float(tasa.comision_compra)
            precio_venta = float(tasa.precio_base) + float(tasa.comision_venta)

        # Inicializar estructura si no existe
        if divisa not in historial:
            historial[divisa] = {"fechas": [], "compra": [], "venta": []}

        # Agregar datos
        historial[divisa]["fechas"].append(tasa.fecha_actualizacion.isoformat())
        historial[divisa]["compra"].append(precio_compra)
        historial[divisa]["venta"].append(precio_venta)

    return JsonResponse({"historial": historial})


##########################################################################################################


def tasa_cambio_historial_listar(request: HttpRequest) -> object:
    """Renderiza la página de listado del historial de tasas de cambio con filtros.

    Args:
        request: Objeto HttpRequest.

    Retorna:
        HttpResponse: Renderiza el template tasa_cambio_historial_list.html con el contexto del historial filtrado.

    """
    from datetime import datetime

    historial = TasaCambioHistorial.objects.all()

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
