"""URLs para la aplicación tauser - Terminal de AutoServicio."""

from django.urls import path

from . import views

app_name = "tauser"

urlpatterns = [
    # Flujo tauser/Terminal de AutoServicio
    path("", views.bienvenida_atm, name="bienvenida"),
    path("mfa/", views.mfa_atm, name="mfa"),
    path("overview/", views.overview_operacion, name="overview_operacion"),
    path("cancelar/", views.cancelar_operacion, name="cancelar_operacion"),
    path("venta/", views.procesar_venta, name="procesar_venta"),
    path("venta/billetes/", views.procesar_billetes_venta, name="procesar_billetes_venta"),
    path("compra/", views.procesar_compra, name="procesar_compra"),
    # Nuevas URLs para manejo de cambio de cotización
    path("aceptar-cotizacion/", views.aceptar_nueva_cotizacion, name="aceptar_nueva_cotizacion"),
    path("cancelar-cotizacion/", views.cancelar_por_cotizacion, name="cancelar_por_cotizacion"),
]
