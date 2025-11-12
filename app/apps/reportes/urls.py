from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/data/", views.dashboard_data, name="dashboard_data"),
    path("ejemplo/", views.ejemplo, name="ejemplo"),
]
