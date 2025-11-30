"""Vistas para el módulo de reportes de Casa de Cambios.

Este módulo contiene vistas de ejemplo para el sistema de casa de cambios.

Autor: Equipo IS2 - Casa de Cambios
Version: 1.0.0

"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


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
