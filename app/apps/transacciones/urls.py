# app/apps/transacciones/urls.py
"""Configuración de URLs para la aplicación transacciones.

Define plantillas de URL para transacciones y configuración de medios de pago.
"""

from django.urls import path

from apps.presentacion.views import home

from . import views

urlpatterns = [
    path("", home, name="home"),
    # URLs para transacciones
    path("simular-cambio/", views.simular_cambio_view, name="simular_cambio"),
    path("comprar-divisa/", views.comprar_divisa_view, name="comprar_divisa"),
    path("vender-divisa/", views.vender_divisa_view, name="vender_divisa"),
    # URLs para configuración de medios de pago
    path("configuracion/", views.configuracion_medios_pago, name="configuracion_medios_pago"),
    path("configuracion/cliente/<int:cliente_id>/", views.medios_pago_cliente, name="medios_pago_cliente"),
    # URLs para crear medios de pago
    path("configuracion/cliente/<int:cliente_id>/tarjeta/crear/", views.crear_tarjeta, name="crear_tarjeta"),
    path("configuracion/cliente/<int:cliente_id>/cuenta/crear/", views.crear_cuenta_bancaria, name="crear_cuenta_bancaria"),
    path("configuracion/cliente/<int:cliente_id>/billetera/crear/", views.crear_billetera, name="crear_billetera"),
    # URLs para editar medios de pago
    path("configuracion/cliente/<int:cliente_id>/tarjeta/<int:medio_id>/editar/", views.editar_tarjeta, name="editar_tarjeta"),
    path("configuracion/cliente/<int:cliente_id>/cuenta/<int:medio_id>/editar/", views.editar_cuenta_bancaria, name="editar_cuenta_bancaria"),
    path("configuracion/cliente/<int:cliente_id>/billetera/<int:medio_id>/editar/", views.editar_billetera, name="editar_billetera"),
    # URL para eliminar medios de pago
    path("configuracion/cliente/<int:cliente_id>/<str:tipo>/<int:medio_id>/eliminar/", views.eliminar_medio_pago, name="eliminar_medio_pago"),
]
