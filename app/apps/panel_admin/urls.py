"""Configuración de URLs para la aplicación panel_admin.

Define rutas para la gestión de usuarios, roles, clientes y operaciones de asociación.
"""

from django.urls import path

from apps.panel_admin import views

urlpatterns = [
    path("", views.panel_inicio, name="panel_inicio"),
    path("configuracion/", views.configuracion, name="configuracion"),
    path("configuracion/guardar_comisiones", views.guardar_comisiones, name="guardar_comisiones"),
    path("configuracion/guardar_limites", views.guardar_limites, name="guardar_limites"),
    path("configuracion/entidades/crear/", views.entidad_create, name="entidad_crear"),
    path("configuracion/entidades/<int:pk>/editar/", views.entidad_edit, name="entidad_editar"),
    path("configuracion/entidades/<int:pk>/eliminar/", views.entidad_delete, name="entidad_eliminar"),
    path("usuarios/", views.usuario_list, name="usuario_listar"),
    path("usuarios/crear/", views.usuario_create, name="usuario_crear"),
    path("usuarios/<int:pk>/editar/", views.usuario_edit, name="usuario_editar"),
    path("usuarios/<int:pk>/eliminar/", views.usuario_delete, name="usuario_eliminar"),
    path("roles/", views.rol_list, name="rol_listar"),
    path("roles/<int:rol_id>/asignar_permiso/", views.rol_asignar_permiso, name="rol_asignar_permiso"),
    path(
        "roles/<int:rol_id>/desasignar_permiso/<int:permiso_id>/",
        views.rol_desasignar_permiso,
        name="rol_desasignar_permiso",
    ),
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
    # URLs para el CRUD de Tasas de Cambio
    path("tasas/", views.tasa_cambio_listar, name="tasa_cambio_listar"),
    path("tasas/crear/", views.tasa_cambio_crear, name="tasa_cambio_crear"),
    path("tasas/<str:pk>/editar/", views.tasa_cambio_editar, name="tasa_cambio_editar"),
    path("tasas/<str:pk>/desactivar/", views.tasa_cambio_desactivar, name="tasa_cambio_desactivar"),
    path("tasas/<str:pk>/activar/", views.tasa_cambio_activar, name="tasa_cambio_activar"),
    # URLs para historial de tasas de cambio
    path("tasas/historial/", views.tasa_cambio_historial_listar, name="tasa_cambio_historial_listar"),
    # URLs para el CRUD de Tauser
    path("tauser/", views.tauser_list, name="tauser_listar"),
    path("tauser/crear/", views.tauser_create, name="tauser_crear"),
    path("tauser/<int:pk>/editar/", views.tauser_edit, name="tauser_editar"),
    path("tauser/<int:pk>/eliminar/", views.tauser_delete, name="tauser_eliminar"),
    # URLs para operaciones de stock
    path("tauser/depositar/", views.tauser_depositar, name="tauser_depositar"),
    path("tauser/extraer/", views.tauser_extraer, name="tauser_extraer"),
    # URLs para historial de movimientos de stock
    path("movimientos/", views.movimientos_stock_listar, name="movimientos_stock_listar"),

]
