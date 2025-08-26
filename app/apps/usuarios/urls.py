from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.ejemplo, name="ejemplo"),
]
