from django.urls import path

from . import views
from .views import cambiar_cliente, login_view, logout_view, obtener_clientes, registro_view, seleccionar_cliente

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
]
