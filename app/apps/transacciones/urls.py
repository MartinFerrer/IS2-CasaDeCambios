from django.urls import path

from . import views

app_name = "transacciones"

urlpatterns = [
    path("", views.ejemplo, name="ejemplo"),
]
