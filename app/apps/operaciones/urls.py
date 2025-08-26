from django.urls import path

from . import views

app_name = "operaciones"

urlpatterns = [
    path("", views.ejemplo, name="ejemplo"),
]
