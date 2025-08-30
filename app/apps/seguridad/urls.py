from django.urls import path
from .views import login_view, logout_view, registro_view

app_name = "seguridad"

# URL patterns for the seguridad app
urlpatterns = [
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("registro/", registro_view, name="registro"),
]
