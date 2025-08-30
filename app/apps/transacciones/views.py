"""Vistas para transacciones de cambio de divisas.

Este módulo proporciona vistas para simular el cambio de divisas y para comprar y vender.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def simular_cambio_view(request: HttpRequest) -> HttpResponse:
    """Página de simulación de cambio."""
    return render(request, "transacciones/simular_cambio.html")


def comprar_divisa_view(request: HttpRequest) -> HttpResponse:
    """Página para comprar divisas."""
    return render(request, "transacciones/comprar_divisa.html")


def vender_divisa_view(request: HttpRequest) -> HttpResponse:
    """Página para vender divisas."""
    return render(request, "transacciones/vender_divisa.html")
