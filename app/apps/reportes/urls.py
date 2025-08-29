from django.urls import path

from . import views

app_name = "apps.reportes"

urlpatterns = [
    path("", views.ejemplo, name="ejemplo"),
]
