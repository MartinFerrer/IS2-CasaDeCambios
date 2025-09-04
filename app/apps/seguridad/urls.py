from django.urls import path

from . import views
from .views import login_view, logout_view, registro_view

app_name = "seguridad"

# URL patterns for the seguridad app
urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("registro/", registro_view, name="registro"),
    path("verificar/<int:uid>/<str:token>/", views.verificar_cuenta, name="verificar_cuenta"),
]
