"""Vistas para la aplicación de operaciones.

Este módulo contiene las vistas CRUD para el modelo TasaCambio.
"""

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from .models import TasaCambio, TasaCambioHistorial
from .utils import get_flag_url_from_currency


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
        # Calcular precio de compra y venta desde la perspectiva de la casa de cambio
        # Casa COMPRA divisa del cliente (cliente VENDE): precio_base - comision_compra
        # Casa VENDE divisa al cliente (cliente COMPRA): precio_base + comision_venta
        if tasa.divisa_origen.codigo == "PYG":
            # Tasa almacenada como PYG -> Divisa extranjera
            precio_compra = float(tasa.precio_base) - float(tasa.comision_compra)  # Casa compra divisa
            precio_venta = float(tasa.precio_base) + float(tasa.comision_venta)  # Casa vende divisa
            divisa_mostrar = tasa.divisa_destino
        else:
            # Si la divisa destino es PYG (caso raro, pero por compatibilidad)
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
            # Casa COMPRA (cliente vende) = base - comision_compra
            # Casa VENDE (cliente compra) = base + comision_venta
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
