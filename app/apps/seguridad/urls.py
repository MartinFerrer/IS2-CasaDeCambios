from django.urls import path

from . import views

app_name = "seguridad"

urlpatterns = [
    #path("", views.ejemplo, name="ejemplo"),
    #path("registro/", views.registro, name="registro"),
    path("login/", views.login_view, name="login"),
    #path("logout/", views.logout_view, name="logout"),
]
