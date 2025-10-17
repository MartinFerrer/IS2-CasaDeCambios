from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("", views.ejemplo, name="ejemplo"),
    path("configuracion/", views.configuracion_usuario, name="configuracion_usuario"),
    path("notification/update/", views.actualizar_preferencia_notificacion, name="actualizar_preferencia_notificacion"),
    path("editar/", views.editar_perfil, name="editar_perfil"),
]
