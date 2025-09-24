"""Configuración de URLs para la aplicación panel_admin.

Define rutas para la gestión de usuarios, roles, clientes y operaciones de asociación.
"""

from django.urls import path

from apps.panel_admin import views

urlpatterns = [
    path("", views.panel_inicio, name="panel_inicio"),
    path("configuracion/", views.configuracion, name="configuracion"),
    path("configuracion/guardar_comisiones", views.guardar_comisiones, name="guardar_comisiones"),
    path("usuarios/", views.usuario_list, name="usuario_listar"),
    path("usuarios/crear/", views.usuario_create, name="usuario_crear"),
    path("usuarios/<int:pk>/editar/", views.usuario_edit, name="usuario_editar"),
    path("usuarios/<int:pk>/eliminar/", views.usuario_delete, name="usuario_eliminar"),
    path("roles/", views.rol_list, name="rol_listar"),
    path("clientes/", views.cliente_list, name="cliente_listar"),
    path("clientes/crear/", views.cliente_create, name="cliente_crear"),
    path("clientes/<int:pk>/editar/", views.cliente_edit, name="cliente_editar"),
    path("clientes/<int:pk>/eliminar/", views.cliente_delete, name="cliente_eliminar"),
    path("asociar/", views.asociar_cliente_usuario_form, name="asociar_cliente_usuario_form"),
    path("asociar/<int:usuario_id>/", views.asociar_cliente_usuario_post, name="asociar_cliente_usuario_post"),
    path("desasociar/<int:usuario_id>/", views.desasociar_cliente_usuario, name="desasociar_cliente_usuario"),
    # URL para la vista que muestra el listado de todas las divisa
    path("divisa/", views.divisa_listar, name="divisa_list"),
    # URL para la vista que crea una nueva divisa
    path("divisa/crear/", views.crear_divisa, name="crear_divisa"),
    # Se agrega la URL para editar una divisa, que faltaba
    path("divisa/editar/<str:pk>/", views.edit_divisa, name="edit_divisa"),
    # URL para la vista que elimina una divisa específica
    path("divisa/delete/<str:pk>/", views.delete_divisa, name="delete_divisa"),
    path("divisa/<str:pk>/", views.divisa_detail, name="divisa_detail"),
    # URL para obtener las divisas en formato JSON
    path("divisas/api/", views.obtener_divisas, name="api_divisas"),
]
