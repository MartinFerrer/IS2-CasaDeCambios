from django.urls import path

from . import views

# Este app_name debe coincidir con el namespace en tu archivo urls.py principal
app_name = "operaciones"

urlpatterns = [
    # URL para la vista que muestra el listado de todas las monedas
    path("monedas/", views.moneda_listar, name="moneda_list"),
    # URL para la vista que crea una nueva moneda
    path("monedas/crear/", views.create_moneda, name="create_moneda"),
    # URL para la vista que muestra los detalles de una moneda específica
    path("monedas/detalles/<int:pk>/", views.moneda_detail, name="moneda_detail"),
    # Se agrega la URL para editar una moneda, que faltaba
    path("monedas/editar/<int:pk>/", views.edit_moneda, name="edit_moneda"),
    # URL para la vista que elimina una moneda específica
    path("monedas/eliminar/<int:pk>/", views.delete_moneda, name="delete_moneda"),
]
