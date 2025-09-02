from django.urls import path

from . import views

# Este app_name debe coincidir con el namespace en tu archivo urls.py principal
app_name = "operaciones"

urlpatterns = [
    # URLs para el CRUD de Tasas de Cambio
    path("tasas-de-cambio/", views.tasa_cambio_listar, name="tasa_cambio_listar"),
    path("tasas-de-cambio/crear/", views.tasa_cambio_crear, name="tasa_cambio_crear"),
    path("tasas-de-cambio/<uuid:pk>/editar/", views.tasa_cambio_editar, name="tasa_cambio_editar"),
    path("tasas-de-cambio/<uuid:pk>/desactivar/", views.tasa_cambio_desactivar, name="tasa_cambio_desactivar"),
    path("tasas-de-cambio/<uuid:pk>/activar/", views.tasa_cambio_activar, name="tasa_cambio_activar"),
    # URL para la vista que muestra el listado de todas las divisa
    path("divisa/", views.divisa_listar, name="divisa_list"),
    # URL para la vista que crea una nueva divisa
    path("divisa/crear/", views.create_divisa, name="create_divisa"),
    # URL para la vista que muestra los detalles de una divisa específica
    path("divisa/detalles/<uuid:pk>/", views.divisa_detail, name="divisa_detail"),
    # Se agrega la URL para editar una divisa, que faltaba
    path("divisa/editar/<uuid:pk>/", views.edit_divisa, name="edit_divisa"),
    # URL para la vista que elimina una divisa específica
    path("divisa/eliminar/<uuid:pk>/", views.delete_divisa, name="delete_divisa"),
    # URL para la lista de dvisas
    path("divisa/lista/<uuid:pk>/", views.divisa_listar, name="divisa_list"),
]
