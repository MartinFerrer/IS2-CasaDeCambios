# apps/operaciones/templatetags/custom_filters.py
"""Filtros de plantilla personalizados para el módulo de operaciones.

Este módulo proporciona filtros de plantilla de Django para formatear y mostrar
valores numéricos en plantillas, específicamente para operaciones de cambio de divisas.

Filtros incluidos:
- strip_trailing_zeros: elimina los ceros finales de números decimales
"""

from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def strip_trailing_zeros(value):
    """Elimina los ceros a la derecha de un número Decimal.

    Args:
        value (Decimal): El valor decimal a formatear.
    Retorna:
        str: El valor como cadena sin ceros a la derecha.
        Ejemplo: 100.00 -> 100, 150.50 -> 150.5

    """
    if isinstance(value, (Decimal, float)):
        # Convierte el valor a una cadena y elimina los ceros finales y el punto decimal
        # si es el último carácter.
        s = f"{value:f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
    return value
