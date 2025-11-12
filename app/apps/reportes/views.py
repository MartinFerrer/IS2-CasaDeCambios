"""Vistas para el módulo de reportes."""

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
from apps.seguridad.permissions import PERM_VIEW_TRANSACCION
from apps.transacciones.models import Transaccion


def calcular_ganancia_transaccion(transaccion):
    """Calcula la ganancia de una transacción basada en la comisión aplicada.

    La ganancia es simplemente: comision * cantidad de divisa extranjera

    Args:
        transaccion: Objeto Transaccion

    Returns:
        Decimal: Ganancia en PYG

    """
    try:
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

        # Buscar la tasa activa para obtener la comisión
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


@permission_required(PERM_VIEW_TRANSACCION)
def dashboard(request: HttpRequest) -> HttpResponse:
    """Vista principal del dashboard de ganancias.

    Muestra métricas, gráficos y transacciones recientes.
    Permite filtrar por rango de fechas (máximo 1 año) y divisa.
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


@permission_required(PERM_VIEW_TRANSACCION)
def dashboard_data(request: HttpRequest) -> JsonResponse:
    """Endpoint para actualizar los datos del dashboard vía AJAX.

    Retorna las ganancias calculadas según comisiones para
    actualizar dinámicamente los gráficos.
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
    """_summary_.

    Args:
        request (HttpRequest): _description_

    Returns:
        HttpResponse: _description_

    """
    return render(request, "base.html")
