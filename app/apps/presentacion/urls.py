from django.urls import path

from . import views

app_name = "presentacion"

urlpatterns = [
    path("", views.home, name="home"),
    path("cambiar-cliente/", views.cambiar_cliente, name="cambiar_cliente"),
]
