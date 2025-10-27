from django.urls import path

from . import views
from .views import (
    cambiar_cliente,
    configurar_mfa,
    generar_qr_mfa,
    login_view,
    logout_view,
    obtener_clientes,
    registro_view,
    seleccionar_cliente,
    verificar_mfa_login,
)

app_name = "seguridad"

# URL patterns for the seguridad app
urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("registro/", registro_view, name="registro"),
    path("verificar/<int:uid>/<str:token>/", views.verificar_cuenta, name="verificar_cuenta"),
    path("cambiar-cliente/", cambiar_cliente, name="cambiar_cliente"),
    path("obtener-clientes/", obtener_clientes, name="obtener_clientes"),
    path("seleccionar-cliente/", seleccionar_cliente, name="seleccionar_cliente"),
    # MFA URLs
    path("mfa/login/", verificar_mfa_login, name="verificar_mfa_login"),
    path("mfa/configurar/", configurar_mfa, name="configurar_mfa"),
    path("mfa/qr/<int:perfil_id>/", generar_qr_mfa, name="generar_qr_mfa"),
    path("api/verificar-mfa-transaccion/", views.verificar_mfa_transaccion, name="verificar_mfa_transaccion"),
    # API MFA para flujo sin redirecciones
    path("api/check-mfa-required/", views.check_mfa_required, name="check_mfa_required"),
    path("api/verify-mfa-code/", views.verify_mfa_code, name="verify_mfa_code"),
]
