"""Configuración de URLs para la aplicación operaciones.

Este módulo define los patrones de URL para operaciones relacionadas con tasas de cambio
y monedas (divisas), incluyendo operaciones CRUD para ambas.
"""

from django.urls import path

from . import views

# Este app_name debe coincidir con el namespace en tu archivo urls.py principal
app_name = "operaciones"

urlpatterns = [
    # URLs para el CRUD de Tasas de Cambio
    path("admin/tasas/", views.tasa_cambio_listar, name="tasa_cambio_listar"),
    path("admin/tasas/crear/", views.tasa_cambio_crear, name="tasa_cambio_crear"),
    path("admin/tasas/<uuid:pk>/editar/", views.tasa_cambio_editar, name="tasa_cambio_editar"),
    path("admin/tasas/<uuid:pk>/desactivar/", views.tasa_cambio_desactivar, name="tasa_cambio_desactivar"),
    path("admin/tasas/<uuid:pk>/activar/", views.tasa_cambio_activar, name="tasa_cambio_activar"),
    # URL para la vista que muestra el listado de todas las divisa
    path("admin/divisa/", views.divisa_listar, name="divisa_list"),
    # URL para la vista que crea una nueva divisa
    path("admin/divisa/crear/", views.crear_divisa, name="crear_divisa"),
    # Se agrega la URL para editar una divisa, que faltaba
    path("admin/divisa/editar/<str:pk>/", views.edit_divisa, name="edit_divisa"),
    # URL para la vista que elimina una divisa específica
    path("admin/divisa/delete/<str:pk>/", views.delete_divisa, name="delete_divisa"),
    # URL para obtener las divisas en formato JSON
    path("admin/divisas/api/", views.obtener_divisas, name="api_divisas"),
]
