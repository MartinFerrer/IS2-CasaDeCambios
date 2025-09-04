"""Vistas para transacciones de cambio de divisas.

Este módulo proporciona vistas para simular el cambio de divisas y para comprar y vender.
"""

from typing import Dict

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


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
