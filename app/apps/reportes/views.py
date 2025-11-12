"""Vistas para el módulo de reportes de Casa de Cambios.

Este módulo contiene las vistas y funciones para generar reportes y dashboards
financieros del sistema de casa de cambios.

Funcionalidades principales:
    - Dashboard interactivo de ganancias con gráficos y KPIs
    - Cálculo de ganancias por transacción basado en comisiones
    - Visualización temporal de fluctuaciones de ganancias
    - Comparación de ganancias por divisa y tipo de operación
    - Endpoint AJAX para actualización dinámica de datos

Dependencias:
    - Django 5.x
    - Plotly.js (para gráficos interactivos en frontend)
    - Modelos: Transaccion, TasaCambio, Divisa

Autor: Equipo IS2 - Casa de Cambios
Version: 1.0.0

"""

import json
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.safestring import mark_safe

from apps.operaciones.models import Divisa, TasaCambio
from apps.seguridad.decorators import permission_required
from apps.seguridad.permissions import PERM_VIEW_REPORTES
from apps.transacciones.models import Transaccion


def calcular_ganancia_transaccion(transaccion):
    """Calcula la ganancia de una transacción basada en la comisión aplicada.

    La ganancia se calcula multiplicando la comisión correspondiente (compra o venta)
    por la cantidad de divisa extranjera involucrada en la transacción.

    **IMPORTANTE**: Si la transacción ya tiene `ganancia_calculada` almacenada
    (histórico al momento de completar), usa ese valor. Esto evita recalcular
    con tasas actuales que pueden haber cambiado.

    Formula:
        - Casa VENDE (cliente compra): ganancia = comision_venta * cantidad_extranjera
        - Casa COMPRA (cliente vende): ganancia = comision_compra * cantidad_extranjera

    Args:
        transaccion (Transaccion): Objeto transacción con información completa de la operación.
            Debe contener divisa_origen, divisa_destino, monto_origen y monto_destino.

    Returns:
        Decimal: Ganancia en Guaraníes (PYG). Retorna 0 si no se puede calcular o si
            no existe una tasa de cambio activa.

    Raises:
        Exception: Captura cualquier excepción y retorna Decimal("0") para evitar fallos.

    Note:
        - **Prioridad 1**: Usa `ganancia_calculada` si existe (valor histórico guardado)
        - **Prioridad 2**: Calcula con `comision_aplicada` histórica si está disponible
        - **Prioridad 3**: Calcula con tasa activa actual (menos preciso para reportes históricos)
        - Siempre se busca la tasa de cambio activa desde PYG hacia la divisa extranjera.
        - Si no existe una tasa activa, retorna 0.

    Example:
        >>> transaccion = Transaccion.objects.get(pk="...")
        >>> ganancia = calcular_ganancia_transaccion(transaccion)
        >>> print(f"Ganancia: ₲{ganancia}")
        Ganancia: ₲5000.00

    """
    try:
        # PRIORIDAD 1: Si ya tiene ganancia calculada histórica, usarla
        if transaccion.ganancia_calculada is not None:
            return transaccion.ganancia_calculada

        # Identificar la divisa extranjera y su cantidad
        if transaccion.divisa_origen.codigo == "PYG":
            # Cliente COMPRA divisa extranjera (casa VENDE)
            divisa_extranjera = transaccion.divisa_destino
            cantidad_extranjera = transaccion.monto_destino
            tipo_comision = "venta"
        else:
            # Cliente VENDE divisa extranjera (casa COMPRA)
            divisa_extranjera = transaccion.divisa_origen
            cantidad_extranjera = transaccion.monto_origen
            tipo_comision = "compra"

        # PRIORIDAD 2: Si tiene comisión aplicada histórica, usarla
        if transaccion.comision_aplicada is not None:
            ganancia = transaccion.comision_aplicada * cantidad_extranjera
            return ganancia if ganancia > 0 else Decimal("0")

        # PRIORIDAD 3: Calcular con tasa activa actual (fallback)
        tasa = TasaCambio.objects.filter(
            divisa_origen__codigo="PYG", divisa_destino=divisa_extranjera, activo=True
        ).first()

        if tasa:
            # Ganancia = comision * cantidad de divisa extranjera
            if tipo_comision == "venta":
                ganancia = tasa.comision_venta * cantidad_extranjera
            else:
                ganancia = tasa.comision_compra * cantidad_extranjera

            return ganancia if ganancia > 0 else Decimal("0")

        return Decimal("0")
    except Exception:
        return Decimal("0")


@permission_required(PERM_VIEW_REPORTES)
def dashboard(request: HttpRequest) -> HttpResponse:
    """Vista principal del dashboard de ganancias y métricas financieras.

    Renderiza un dashboard interactivo con:
    - KPIs: ganancias totales, total de transacciones, ganancia promedio, tasa de crecimiento
    - Gráfico de líneas: evolución temporal de ganancias (separado por compra/venta)
    - Gráfico de barras: comparación de ganancias por divisa (agrupado compra vs venta)
    - Tabla: últimas 5 transacciones completadas con su ganancia calculada

    Args:
        request (HttpRequest): Objeto request de Django con parámetros GET opcionales:
            - start_date (str): Fecha inicio en formato YYYY-MM-DD (default: hace 30 días)
            - end_date (str): Fecha fin en formato YYYY-MM-DD (default: hoy)
            - currency (str): Código de divisa para filtrar o "all" (default: "all")

    Returns:
        HttpResponse: Página HTML renderizada con el dashboard y todos sus datos.

    Note:
        - El rango de fechas se limita automáticamente a máximo 1 año (365 días)
        - Solo se procesan transacciones con estado="completada"
        - Requiere permiso PERM_VIEW_REPORTES para acceder
        - Los datos se separan por tipo_operacion (compra/venta) para análisis comparativo

    Raises:
        PermissionDenied: Si el usuario no tiene el permiso PERM_VIEW_REPORTES

    Example:
        GET /reportes/dashboard/?start_date=2025-01-01&end_date=2025-12-31&currency=USD

    """
    # Obtener parámetros de filtro
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    currency = request.GET.get("currency", "all")

    # Fechas por defecto: últimos 30 días
    if not start_date or not end_date:
        end_datetime = timezone.now()
        start_datetime = end_datetime - timedelta(days=30)
    else:
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d")

    # Validar que el rango no exceda 1 año
    if (end_datetime - start_datetime).days > 365:
        end_datetime = start_datetime + timedelta(days=365)

    # Base query
    transactions = Transaccion.objects.filter(
        fecha_creacion__date__range=[start_datetime, end_datetime], estado="completada"
    ).select_related("divisa_origen", "divisa_destino")

    if currency != "all":
        transactions = transactions.filter(Q(divisa_origen__codigo=currency) | Q(divisa_destino__codigo=currency))

    # Calcular ganancias totales iterando sobre transacciones
    transactions_list = list(transactions)
    total_profits = Decimal("0")
    for trans in transactions_list:
        total_profits += calcular_ganancia_transaccion(trans)

    total_transactions = len(transactions_list)
    avg_profit = total_profits / total_transactions if total_transactions > 0 else Decimal("0")

    # Calcular tasa de crecimiento
    previous_start = start_datetime - timedelta(days=30)
    previous_transactions = list(
        Transaccion.objects.filter(
            fecha_creacion__date__range=[previous_start, start_datetime], estado="completada"
        ).select_related("divisa_origen", "divisa_destino")
    )

    if currency != "all":
        previous_transactions = [
            t
            for t in previous_transactions
            if t.divisa_origen.codigo == currency or t.divisa_destino.codigo == currency
        ]

    previous_profits = Decimal("0")
    for trans in previous_transactions:
        previous_profits += calcular_ganancia_transaccion(trans)

    growth_rate = ((total_profits - previous_profits) / previous_profits * 100) if previous_profits != 0 else 0

    # Datos para gráfico de ganancias por tiempo (línea) - separado por tipo
    daily_profits_compra = {}
    daily_profits_venta = {}
    all_dates = set()

    for trans in transactions_list:
        date = trans.fecha_creacion.date()
        all_dates.add(date)
        ganancia = calcular_ganancia_transaccion(trans)

        if trans.tipo_operacion == "compra":
            if date in daily_profits_compra:
                daily_profits_compra[date] += ganancia
            else:
                daily_profits_compra[date] = ganancia
        else:  # venta
            if date in daily_profits_venta:
                daily_profits_venta[date] += ganancia
            else:
                daily_profits_venta[date] = ganancia

    # Ordenar fechas y crear arrays para ambas series
    sorted_dates = sorted(all_dates)
    dates_labels = [date.strftime("%Y-%m-%d") for date in sorted_dates]
    profits_compra_data = [float(daily_profits_compra.get(date, Decimal("0"))) for date in sorted_dates]
    profits_venta_data = [float(daily_profits_venta.get(date, Decimal("0"))) for date in sorted_dates]

    # Datos para gráfico de ganancias por divisa (barras agrupadas: compra vs venta)
    currency_profits_compra = {}
    currency_profits_venta = {}
    all_currencies = set()

    for trans in transactions_list:
        # La divisa relevante es la extranjera (no PYG)
        if trans.divisa_origen.codigo == "PYG":
            divisa_codigo = trans.divisa_destino.codigo
        else:
            divisa_codigo = trans.divisa_origen.codigo

        all_currencies.add(divisa_codigo)
        ganancia = calcular_ganancia_transaccion(trans)

        # Separar por tipo de operación
        if trans.tipo_operacion == "compra":
            if divisa_codigo in currency_profits_compra:
                currency_profits_compra[divisa_codigo] += ganancia
            else:
                currency_profits_compra[divisa_codigo] = ganancia
        else:  # venta
            if divisa_codigo in currency_profits_venta:
                currency_profits_venta[divisa_codigo] += ganancia
            else:
                currency_profits_venta[divisa_codigo] = ganancia

    # Ordenar divisas por ganancia total (compra + venta)
    currency_totals = {}
    for currency in all_currencies:
        total = currency_profits_compra.get(currency, Decimal("0")) + currency_profits_venta.get(currency, Decimal("0"))
        currency_totals[currency] = total

    sorted_currencies = sorted(currency_totals.items(), key=lambda x: x[1], reverse=True)
    currency_labels = [codigo for codigo, _ in sorted_currencies]
    currency_compra_data = [float(currency_profits_compra.get(codigo, Decimal("0"))) for codigo in currency_labels]
    currency_venta_data = [float(currency_profits_venta.get(codigo, Decimal("0"))) for codigo in currency_labels]

    # Transacciones recientes con ganancia calculada (últimas 5)
    recent_transactions = transactions_list[:5] if len(transactions_list) >= 5 else transactions_list

    for transaction in recent_transactions:
        transaction.ganancia = calcular_ganancia_transaccion(transaction)

    # Obtener todas las divisas disponibles
    divisas_disponibles = Divisa.objects.all().order_by("codigo")

    context = {
        "start_date": start_datetime,
        "end_date": end_datetime,
        "selected_currency": currency,
        "total_profits": total_profits,
        "total_transactions": total_transactions,
        "avg_profit": avg_profit,
        "growth_rate": round(growth_rate, 2),
        "dates_labels": mark_safe(json.dumps(dates_labels)),
        "profits_compra_data": mark_safe(json.dumps(profits_compra_data)),
        "profits_venta_data": mark_safe(json.dumps(profits_venta_data)),
        "currency_labels": mark_safe(json.dumps(currency_labels)),
        "currency_compra_data": mark_safe(json.dumps(currency_compra_data)),
        "currency_venta_data": mark_safe(json.dumps(currency_venta_data)),
        "recent_transactions": recent_transactions,
        "divisas": divisas_disponibles,
    }

    return render(request, "reportes/dashboard.html", context)


@permission_required(PERM_VIEW_REPORTES)
def dashboard_data(request: HttpRequest) -> JsonResponse:
    """Endpoint AJAX para actualizar dinámicamente los datos del dashboard.

    Retorna un JSON con todas las métricas y datos necesarios para actualizar
    los gráficos y KPIs del dashboard sin recargar la página completa.

    Args:
        request (HttpRequest): Objeto request de Django con parámetros GET requeridos:
            - start_date (str): Fecha inicio en formato YYYY-MM-DD (requerido)
            - end_date (str): Fecha fin en formato YYYY-MM-DD (requerido)
            - currency (str): Código de divisa para filtrar o "all" (opcional)

    Returns:
        JsonResponse: JSON con estructura:
            {
                "total_profits": float,
                "total_transactions": int,
                "avg_profit": float,
                "growth_rate": float,
                "dates_labels": list[str],
                "profits_compra_data": list[float],
                "profits_venta_data": list[float],
                "currency_labels": list[str],
                "currency_compra_data": list[float],
                "currency_venta_data": list[float],
                "recent_transactions": list[dict]
            }

        En caso de error:
            {"error": str} con status HTTP 400

    Raises:
        PermissionDenied: Si el usuario no tiene el permiso PERM_VIEW_REPORTES

    Note:
        - Valida que el rango de fechas no exceda 1 año (365 días)
        - Calcula tasa de crecimiento comparando con 30 días anteriores
        - Separa datos por tipo de operación (compra/venta) para gráficos agrupados

    Example:
        GET /reportes/dashboard/data/?start_date=2025-01-01&end_date=2025-12-31&currency=USD

        Response:
        {
            "total_profits": 1500000.50,
            "total_transactions": 92,
            "avg_profit": 16304.35,
            ...
        }

    """
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    currency = request.GET.get("currency")

    if not all([start_date, end_date]):
        return JsonResponse({"error": "Fechas requeridas"}, status=400)

    # Convertir fechas a datetime
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d")

    # Validar que el rango no exceda 1 año
    if (end_datetime - start_datetime).days > 365:
        return JsonResponse({"error": "El rango no puede exceder 1 año"}, status=400)

    # Base query
    transactions = Transaccion.objects.filter(
        fecha_creacion__date__range=[start_datetime, end_datetime], estado="completada"
    ).select_related("divisa_origen", "divisa_destino")

    if currency and currency != "all":
        transactions = transactions.filter(Q(divisa_origen__codigo=currency) | Q(divisa_destino__codigo=currency))

    # Calcular todas las métricas
    transactions_list = list(transactions)
    total_profits = Decimal("0")
    for trans in transactions_list:
        total_profits += calcular_ganancia_transaccion(trans)

    total_transactions = len(transactions_list)
    avg_profit = float(total_profits / total_transactions) if total_transactions > 0 else 0

    # Tasa de crecimiento
    previous_start = start_datetime - timedelta(days=30)
    previous_transactions = list(
        Transaccion.objects.filter(
            fecha_creacion__date__range=[previous_start, start_datetime], estado="completada"
        ).select_related("divisa_origen", "divisa_destino")
    )

    if currency and currency != "all":
        previous_transactions = [
            t
            for t in previous_transactions
            if t.divisa_origen.codigo == currency or t.divisa_destino.codigo == currency
        ]

    previous_profits = Decimal("0")
    for trans in previous_transactions:
        previous_profits += calcular_ganancia_transaccion(trans)

    growth_rate = ((total_profits - previous_profits) / previous_profits * 100) if previous_profits != 0 else 0

    # Datos para gráficos - separado por tipo
    daily_profits_compra = {}
    daily_profits_venta = {}
    all_dates = set()

    for trans in transactions_list:
        date = trans.fecha_creacion.date()
        all_dates.add(date)
        ganancia = calcular_ganancia_transaccion(trans)

        if trans.tipo_operacion == "compra":
            if date in daily_profits_compra:
                daily_profits_compra[date] += ganancia
            else:
                daily_profits_compra[date] = ganancia
        else:  # venta
            if date in daily_profits_venta:
                daily_profits_venta[date] += ganancia
            else:
                daily_profits_venta[date] = ganancia

    sorted_dates = sorted(all_dates)
    dates_labels = [date.strftime("%Y-%m-%d") for date in sorted_dates]
    profits_compra_data = [float(daily_profits_compra.get(date, Decimal("0"))) for date in sorted_dates]
    profits_venta_data = [float(daily_profits_venta.get(date, Decimal("0"))) for date in sorted_dates]

    # Datos para gráfico de ganancias por divisa (barras agrupadas: compra vs venta)
    currency_profits_compra = {}
    currency_profits_venta = {}
    all_currencies = set()

    for trans in transactions_list:
        # La divisa relevante es la extranjera (no PYG)
        if trans.divisa_origen.codigo == "PYG":
            divisa_codigo = trans.divisa_destino.codigo
        else:
            divisa_codigo = trans.divisa_origen.codigo

        all_currencies.add(divisa_codigo)
        ganancia = calcular_ganancia_transaccion(trans)

        # Separar por tipo de operación
        if trans.tipo_operacion == "compra":
            if divisa_codigo in currency_profits_compra:
                currency_profits_compra[divisa_codigo] += ganancia
            else:
                currency_profits_compra[divisa_codigo] = ganancia
        else:  # venta
            if divisa_codigo in currency_profits_venta:
                currency_profits_venta[divisa_codigo] += ganancia
            else:
                currency_profits_venta[divisa_codigo] = ganancia

    # Ordenar divisas por ganancia total (compra + venta)
    currency_totals = {}
    for currency in all_currencies:
        total = currency_profits_compra.get(currency, Decimal("0")) + currency_profits_venta.get(currency, Decimal("0"))
        currency_totals[currency] = total

    sorted_currencies = sorted(currency_totals.items(), key=lambda x: x[1], reverse=True)
    currency_labels = [codigo for codigo, _ in sorted_currencies]
    currency_compra_data = [float(currency_profits_compra.get(codigo, Decimal("0"))) for codigo in currency_labels]
    currency_venta_data = [float(currency_profits_venta.get(codigo, Decimal("0"))) for codigo in currency_labels]

    # Transacciones recientes (últimas 5)
    recent_transactions_list = transactions_list[:5] if len(transactions_list) >= 5 else transactions_list
    recent_transactions = [
        {
            "fecha": t.fecha_creacion.strftime("%d/%m/%Y %H:%M"),
            "tipo": t.tipo_operacion,
            "origen": f"{t.divisa_origen.codigo} {float(t.monto_origen):.2f}",
            "destino": f"{t.divisa_destino.codigo} {float(t.monto_destino):.2f}",
            "monto": float(t.monto_origen),
            "ganancia": float(calcular_ganancia_transaccion(t)),
        }
        for t in recent_transactions_list
    ]

    data = {
        "total_profits": float(total_profits),
        "total_transactions": total_transactions,
        "avg_profit": avg_profit,
        "growth_rate": round(float(growth_rate), 2),
        "dates_labels": dates_labels,
        "profits_compra_data": profits_compra_data,
        "profits_venta_data": profits_venta_data,
        "currency_labels": currency_labels,
        "currency_compra_data": currency_compra_data,
        "currency_venta_data": currency_venta_data,
        "recent_transactions": recent_transactions,
    }

    return JsonResponse(data)


def ejemplo(request: HttpRequest) -> HttpResponse:
    """Vista de ejemplo que renderiza la plantilla base.

    Esta es una vista de prueba/ejemplo que simplemente renderiza la plantilla
    base del sistema sin contenido adicional. Útil para testing o demostración.

    Args:
        request (HttpRequest): Objeto request de Django.

    Returns:
        HttpResponse: Página HTML renderizada desde la plantilla base.html

    Note:
        Esta vista probablemente será eliminada o reemplazada en producción.
        Se mantiene como referencia o para propósitos de desarrollo.

    """
    return render(request, "base.html")
