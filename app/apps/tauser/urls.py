from django.urls import path

from . import views

app_name = "tauser"

urlpatterns = [
    path("", views.ejemplo, name="ejemplo"),
]
