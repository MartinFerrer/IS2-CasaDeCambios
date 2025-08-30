"""Configuración de URLs para la aplicación presentacion.

Define los patrones de URL para las vistas relacionadas con transacciones.
"""

from django.urls import path

from . import views

app_name = "transacciones"

urlpatterns = [
    path("", views.home, name="home"),
]
