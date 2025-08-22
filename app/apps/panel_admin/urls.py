from django.urls import path
from . import views

urlpatterns = [
    path("", views.panel_inicio, name="panel_inicio"),
    path("usuarios/", views.usuario_list, name="usuario_listar"),
    path("usuarios/crear/", views.usuario_create, name="usuario_crear"),
    path("usuarios/<int:pk>/editar/", views.usuario_edit, name="usuario_editar"),
    path("usuarios/<int:pk>/eliminar/", views.usuario_delete, name="usuario_eliminar"),
    path("roles/", views.rol_list, name="rol_listar"),
    path("roles/crear/", views.rol_create, name="rol_crear"),
    path("roles/<int:pk>/editar/", views.rol_edit, name="rol_editar"),
    path("roles/<int:pk>/eliminar/", views.rol_delete, name="rol_eliminar"),
]