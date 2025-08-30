from django.urls import path

from . import views

app_name = "transacciones"

urlpatterns = [
    path("", views.home, name="home"),
]
