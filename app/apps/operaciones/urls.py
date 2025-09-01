from django.urls import path

from . import views

app_name = "operaciones"

urlpatterns = [
    # URLs para el CRUD de Tasas de Cambio
    path("tasas-de-cambio/", views.tasa_cambio_listar, name="tasa_cambio_listar"),
    path("tasas-de-cambio/crear/", views.tasa_cambio_crear, name="tasa_cambio_crear"),
    path("tasas-de-cambio/<uuid:pk>/editar/", views.tasa_cambio_editar, name="tasa_cambio_editar"),
    path("tasas-de-cambio/<uuid:pk>/desactivar/", views.tasa_cambio_desactivar, name="tasa_cambio_desactivar"),
    path("tasas-de-cambio/<uuid:pk>/activar/", views.tasa_cambio_activar, name="tasa_cambio_activar"),
]
