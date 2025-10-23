"""Vistas para el módulo de reportes."""

from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone

from apps.operaciones.models import Divisa
from apps.seguridad.decorators import permission_required
from apps.seguridad.permissions import PERM_VIEW_TRANSACCION
from apps.transacciones.models import Transaccion


@permission_required(PERM_VIEW_TRANSACCION)
def dashboard(request: HttpRequest) -> HttpResponse:
    """Vista principal del dashboard de ganancias."""
    # Obtener parámetros de filtro
    start_date = request.GET.get("start_date", (timezone.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
    end_date = request.GET.get("end_date", timezone.now().strftime("%Y-%m-%d"))
    currency = request.GET.get("currency", "all")

    # Convertir fechas a datetime
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d")

    # Base query
    transactions = Transaccion.objects.filter(
        fecha_creacion__date__range=[start_datetime, end_datetime], estado="completado"
    )

    if currency != "all":
        transactions = transactions.filter(Q(divisa_origen__codigo=currency) | Q(divisa_destino__codigo=currency))

    # Calcular métricas generales
    total_profits = transactions.aggregate(
        total=Sum(ExpressionWrapper(F("monto_destino") - F("monto_origen"), output_field=DecimalField()))
    )["total"] or Decimal("0")

    total_transactions = transactions.count()
    avg_profit = total_profits / total_transactions if total_transactions > 0 else Decimal("0")

    # Calcular tasa de crecimiento
    previous_start = start_datetime - timedelta(days=30)
    previous_transactions = Transaccion.objects.filter(
        fecha_creacion__date__range=[previous_start, start_datetime], estado="completado"
    )

    if currency != "all":
        previous_transactions = previous_transactions.filter(
            Q(divisa_origen__codigo=currency) | Q(divisa_destino__codigo=currency)
        )

    previous_profits = previous_transactions.aggregate(
        total=Sum(ExpressionWrapper(F("monto_destino") - F("monto_origen"), output_field=DecimalField()))
    )["total"] or Decimal("0")

    growth_rate = ((total_profits - previous_profits) / previous_profits * 100) if previous_profits != 0 else 0

    # Calcular tasa de conversión (transacciones completadas / total)
    total_attempted = Transaccion.objects.filter(fecha_creacion__date__range=[start_datetime, end_datetime]).count()
    conversion_rate = (total_transactions / total_attempted * 100) if total_attempted > 0 else 0

    # Datos para gráfico de ganancias por tiempo
    daily_profits = (
        transactions.annotate(date=TruncDate("fecha_creacion"))
        .values("date")
        .annotate(profit=Sum(ExpressionWrapper(F("monto_destino") - F("monto_origen"), output_field=DecimalField())))
        .order_by("date")
    )

    dates_labels = [profit["date"].strftime("%Y-%m-%d") for profit in daily_profits]
    profits_data = [float(profit["profit"]) for profit in daily_profits]

    # Datos para gráfico de ganancias por divisa
    currency_profits = (
        transactions.values("divisa_destino__codigo")
        .annotate(profit=Sum(ExpressionWrapper(F("monto_destino") - F("monto_origen"), output_field=DecimalField())))
        .order_by("-profit")
    )

    currency_labels = [profit["divisa_destino__codigo"] for profit in currency_profits]
    currency_data = [float(profit["profit"]) for profit in currency_profits]

    # Transacciones recientes
    recent_transactions = transactions.order_by("-fecha_creacion")[:10]

    for transaction in recent_transactions:
        transaction.ganancia = transaction.monto_destino - transaction.monto_origen

    context = {
        "start_date": start_datetime,
        "end_date": end_datetime,
        "selected_currency": currency,
        "total_profits": total_profits,
        "total_transactions": total_transactions,
        "avg_profit": avg_profit,
        "growth_rate": round(growth_rate, 2),
        "conversion_rate": round(conversion_rate, 2),
        "dates_labels": dates_labels,
        "profits_data": profits_data,
        "currency_labels": currency_labels,
        "currency_data": currency_data,
        "recent_transactions": recent_transactions,
        "divisas": Divisa.objects.filter(estado="activo"),
    }

    return render(request, "reportes/dashboard.html", context)


@permission_required(PERM_VIEW_TRANSACCION)
def dashboard_data(request: HttpRequest) -> JsonResponse:
    """Endpoint para actualizar los datos del dashboard vía AJAX."""
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    currency = request.GET.get("currency")

    if not all([start_date, end_date]):
        return JsonResponse({"error": "Fechas requeridas"}, status=400)

    # Convertir fechas a datetime
    start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_datetime = datetime.strptime(end_date, "%Y-%m-%d")

    # Base query
    transactions = Transaccion.objects.filter(
        fecha_creacion__date__range=[start_datetime, end_datetime], estado="completado"
    )

    if currency != "all":
        transactions = transactions.filter(Q(divisa_origen__codigo=currency) | Q(divisa_destino__codigo=currency))

    # Calcular todas las métricas
    total_profits = float(
        transactions.aggregate(
            total=Sum(ExpressionWrapper(F("monto_destino") - F("monto_origen"), output_field=DecimalField()))
        )["total"]
        or 0
    )

    total_transactions = transactions.count()
    avg_profit = total_profits / total_transactions if total_transactions > 0 else 0

    # Tasa de crecimiento
    previous_start = start_datetime - timedelta(days=30)
    previous_transactions = Transaccion.objects.filter(
        fecha_creacion__date__range=[previous_start, start_datetime], estado="completado"
    )

    if currency != "all":
        previous_transactions = previous_transactions.filter(
            Q(divisa_origen__codigo=currency) | Q(divisa_destino__codigo=currency)
        )

    previous_profits = float(
        previous_transactions.aggregate(
            total=Sum(ExpressionWrapper(F("monto_destino") - F("monto_origen"), output_field=DecimalField()))
        )["total"]
        or 0
    )

    growth_rate = ((total_profits - previous_profits) / previous_profits * 100) if previous_profits != 0 else 0

    # Tasa de conversión
    total_attempted = Transaccion.objects.filter(fecha_creacion__date__range=[start_datetime, end_datetime]).count()
    conversion_rate = (total_transactions / total_attempted * 100) if total_attempted > 0 else 0

    # Datos de gráficos
    daily_profits = (
        transactions.annotate(date=TruncDate("fecha_creacion"))
        .values("date")
        .annotate(profit=Sum(ExpressionWrapper(F("monto_destino") - F("monto_origen"), output_field=DecimalField())))
        .order_by("date")
    )

    currency_profits = (
        transactions.values("divisa_destino__codigo")
        .annotate(profit=Sum(ExpressionWrapper(F("monto_destino") - F("monto_origen"), output_field=DecimalField())))
        .order_by("-profit")
    )

    # Transacciones recientes
    recent_transactions = [
        {
            "fecha": t.fecha_creacion.strftime("%d/%m/%Y %H:%M"),
            "tipo": t.tipo_operacion,
            "origen": f"{t.divisa_origen.codigo} {float(t.monto_origen):.2f}",
            "destino": f"{t.divisa_destino.codigo} {float(t.monto_destino):.2f}",
            "monto": float(t.monto_origen),
            "ganancia": float(t.monto_destino - t.monto_origen),
        }
        for t in transactions.order_by("-fecha_creacion")[:10]
    ]

    data = {
        "total_profits": total_profits,
        "total_transactions": total_transactions,
        "avg_profit": avg_profit,
        "growth_rate": round(growth_rate, 2),
        "conversion_rate": round(conversion_rate, 2),
        "dates_labels": [p["date"].strftime("%Y-%m-%d") for p in daily_profits],
        "profits_data": [float(p["profit"]) for p in daily_profits],
        "currency_labels": [p["divisa_destino__codigo"] for p in currency_profits],
        "currency_data": [float(p["profit"]) for p in currency_profits],
        "recent_transactions": recent_transactions,
    }

    return JsonResponse(data)
