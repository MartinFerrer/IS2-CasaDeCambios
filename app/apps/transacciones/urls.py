# app/apps/transacciones/urls.py
"""Configuración de URLs para la aplicación transacciones.

Define plantillas de URL para transacciones y configuración de medios de pago.
"""

from django.urls import path

from . import views

app_name = "transacciones"

urlpatterns = [
    # URLs para transacciones
    path("simular-cambio/", views.simular_cambio_view, name="simular_cambio"),
    path("api/simular", views.api_simular_cambio, name="api_simular_cambio"),
    path("api/clientes", views.api_clientes_usuario, name="api_clientes_usuario"),
    path("api/cliente/<int:cliente_id>/medios-pago", views.api_medios_pago_cliente, name="api_medios_pago_cliente"),
    path("api/divisas", views.api_divisas_disponibles, name="api_divisas_disponibles"),
    path("comprar-divisa/", views.comprar_divisa_view, name="comprar_divisa"),
    path("vender-divisa/", views.vender_divisa_view, name="vender_divisa"),
    # URLs para configuración de medios de pago
    path("configuracion/", views.configuracion_medios_pago, name="configuracion_medios_pago"),
    path("configuracion/cliente/<int:cliente_id>/", views.medios_pago_cliente, name="medios_pago_cliente"),
    # URLs para crear medios de pago
    path("configuracion/cliente/<int:cliente_id>/tarjeta/crear/", views.crear_tarjeta, name="crear_tarjeta"),
    path(
        "configuracion/cliente/<int:cliente_id>/cuenta/crear/",
        views.crear_cuenta_bancaria,
        name="crear_cuenta_bancaria",
    ),
    path("configuracion/cliente/<int:cliente_id>/billetera/crear/", views.crear_billetera, name="crear_billetera"),
    # URLs para editar medios de pago
    path(
        "configuracion/cliente/<int:cliente_id>/tarjeta/<int:medio_id>/editar/",
        views.editar_tarjeta,
        name="editar_tarjeta",
    ),
    path(
        "configuracion/cliente/<int:cliente_id>/cuenta/<int:medio_id>/editar/",
        views.editar_cuenta_bancaria,
        name="editar_cuenta_bancaria",
    ),
    path(
        "configuracion/cliente/<int:cliente_id>/billetera/<int:medio_id>/editar/",
        views.editar_billetera,
        name="editar_billetera",
    ),
    # URL para eliminar medios de pago
    path(
        "configuracion/cliente/<int:cliente_id>/<str:tipo>/<int:medio_id>/eliminar/",
        views.eliminar_medio_pago,
        name="eliminar_medio_pago",
    ),
    # URLs para realizar transacciones reales
    path("realizar-transaccion/", views.realizar_transaccion_view, name="realizar_transaccion"),
    path("api/crear-transaccion", views.api_crear_transaccion, name="api_crear_transaccion"),
    path(
        "api/cancelar-transaccion/<str:transaccion_id>/",
        views.api_cancelar_transaccion,
        name="api_cancelar_transaccion",
    ),
    path("api/procesar-pago-bancario/", views.api_procesar_pago_bancario, name="api_procesar_pago_bancario"),
    path("popup-banco/<str:transaccion_id>/", views.popup_banco_simulado, name="popup_banco_simulado"),
    path(
        "popup-tauser-retiro/<str:transaccion_id>/", views.popup_codigo_tauser_retiro, name="popup_codigo_tauser_retiro"
    ),
    path("procesar/<str:transaccion_id>/", views.procesar_transaccion_view, name="procesar_transaccion"),
    # URLs para verificación y cancelación por cotización
    path(
        "api/verificar-cotizacion/<str:transaccion_id>/",
        views.api_verificar_cotizacion,
        name="api_verificar_cotizacion",
    ),
    path("api/verificar-disponibilidad-tauser/<str:transaccion_id>/",
        views.api_verificar_stock_tauser,
        name="api_verificar_stock_tauser"
    ),
    path(
        "api/cancelar-por-cotizacion/<str:transaccion_id>/",
        views.api_cancelar_por_cotizacion,
        name="api_cancelar_por_cotizacion",
    ),
    path(
        "api/aceptar-nueva-cotizacion/<str:transaccion_id>/",
        views.api_aceptar_nueva_cotizacion,
        name="api_aceptar_nueva_cotizacion",
    ),

    path("api/historial/<str:transaccion_id>/", views.api_historial_transaccion, name="api_historial_transaccion"),
    # URLs para Stripe
    path("api/stripe/create-payment-intent/", views.create_stripe_payment_intent, name="stripe_create_payment_intent"),
    path("api/stripe/confirm-payment/", views.confirm_stripe_payment, name="stripe_confirm_payment"),
    path("stripe/webhook/", views.stripe_webhook_handler, name="stripe_webhook"),
    path("", views.vista_transacciones, name="lista"),
]
