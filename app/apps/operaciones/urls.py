"""Configuración de URLs para la aplicación operaciones.
Este módulo define los patrones de URL para operaciones relacionadas con tasas de cambio
y monedas (divisas), incluyendo operaciones CRUD para ambas.
"""

from django.urls import path

from . import views

# Este app_name debe coincidir con el namespace en tu archivo urls.py principal
app_name = "operaciones"

urlpatterns = [
    path("admin/tasas/historial/", views.tasa_cambio_historial_listar, name="tasa_cambio_historial_listar"),
    path("admin/tasas/historial/", views.historial_tasas_api, name="historial_tasas_api"),
]
