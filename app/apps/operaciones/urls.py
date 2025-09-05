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
    path("admin/tasas/<str:pk>/editar/", views.tasa_cambio_editar, name="tasa_cambio_editar"),
    path("admin/tasas/<str:pk>/desactivar/", views.tasa_cambio_desactivar, name="tasa_cambio_desactivar"),
    path("admin/tasas/<str:pk>/activar/", views.tasa_cambio_activar, name="tasa_cambio_activar"),
    # API endpoint para obtener tasas de cambio actuales
    path("api/tasas/", views.tasas_cambio_api, name="tasas_cambio_api"),
    # URLs para divisas
    path("divisa/", views.divisa_listar, name="divisa_list"),
    path("divisa/crear/", views.create_divisa, name="create_divisa"),
    path("divisa/detalles/<str:pk>/", views.divisa_detail, name="divisa_detail"),
    path("divisa/editar/<str:pk>/", views.edit_divisa, name="edit_divisa"),
    path("divisa/eliminar/<str:pk>/", views.delete_divisa, name="delete_divisa"),
    path("divisa/lista/<str:pk>/", views.divisa_listar, name="divisa_list"),
    path("tasas/api/", views.tasas_cambio_api, name="tasas_cambio_api"),
    path("tasas/historial/", views.historial_tasas_api, name="historial_tasas_api"),
]
