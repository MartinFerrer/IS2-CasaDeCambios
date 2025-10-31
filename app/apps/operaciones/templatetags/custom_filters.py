# apps/operaciones/templatetags/custom_filters.py
"""Filtros de plantilla personalizados para el módulo de operaciones.

Este módulo proporciona filtros de plantilla de Django para formatear y mostrar
valores numéricos en plantillas, específicamente para operaciones de cambio de divisas.

Filtros incluidos:
- strip_trailing_zeros: elimina los ceros finales de números decimales
"""


from django import template
from django.utils.formats import number_format

register = template.Library()


@register.filter(name="strip_trailing_zeros")
def strip_trailing_zeros(value, decimal_pos=-99):
    """Formatea el número con separadores de miles y hasta `decimal_pos` decimales,
    pero elimina ceros innecesarios al final.

    """
    if(decimal_pos == -99):
        s = number_format(value, use_l10n=True)
    else:
        s = number_format(value, decimal_pos=decimal_pos, use_l10n=True)
    if ',' in s:  # quitar ceros extra
        s = s.rstrip('0').rstrip(',')
    return s
