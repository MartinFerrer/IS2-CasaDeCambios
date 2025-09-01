# app/apps/transacciones/urls.py
"""Configuración de URLs para la aplicación presentacion.

Define plantillas de URL para la página principal y las vistas de cambio de divisas.
"""

from django.urls import path

from apps.presentacion.views import home

from . import views

urlpatterns = [
    path("", home, name="home"),
    # formato de las vistas para los botones de la pagina principal, pueden editar sin problema
    path("simular-cambio/", views.simular_cambio_view, name="simular_cambio"),
    path("comprar-divisa/", views.comprar_divisa_view, name="comprar_divisa"),
    path("vender-divisa/", views.vender_divisa_view, name="vender_divisa"),
]
