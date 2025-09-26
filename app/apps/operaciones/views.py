"""Vistas para la aplicación de operaciones.

Este módulo contiene las vistas CRUD para el modelo TasaCambio.
"""

from django.db.models import Q
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import Divisa, TasaCambio, TasaCambioHistorial


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
