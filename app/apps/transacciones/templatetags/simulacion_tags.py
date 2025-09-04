import json

from django import template

register = template.Library()


@register.simple_tag
def simulacion_config():
    """Return a JSON string with rates, commission rules and ISO decimals used by both backend and frontend.

    NOTE: These are defaults and the backend logic should use the same values or override them when available.
    """
    config = {
        "ratesToPYG": {"PYG": 1, "USD": 7000, "EUR": 7600, "BRL": 1300},
        "isoDecimals": {"PYG": 0, "USD": 2, "EUR": 2, "BRL": 2},
        "commissionPct": {"compra": 0.01, "venta": 0.015},
        "segmentoDiscount": {"VIP": 0.10, "Corporativo": 0.05, "Minorista": 0},
    }
    return json.dumps(config)
