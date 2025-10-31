"""Tests para las vistas de operaciones con control de acceso por roles."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_divisa_list_administrador_access(client_administrador):
    """Prueba que un administrador puede acceder a la lista de divisas."""
    url = reverse("divisa_list")
    response = client_administrador.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_divisa_list_analista_access(client_analista):
    """Prueba que un analista cambiario puede acceder a la lista de divisas."""
    url = reverse("divisa_list")
    response = client_analista.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_divisa_list_sin_rol_forbidden(client_sin_rol):
    """Prueba que un usuario sin rol NO puede acceder a la lista de divisas."""
    url = reverse("divisa_list")
    response = client_sin_rol.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_tasa_cambio_list_administrador_access(client_administrador):
    """Prueba que un administrador puede acceder a la lista de tasas de cambio."""
    url = reverse("tasa_cambio_listar")
    response = client_administrador.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_tasa_cambio_list_analista_access(client_analista):
    """Prueba que un analista cambiario puede acceder a la lista de tasas de cambio."""
    url = reverse("tasa_cambio_listar")
    response = client_analista.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_tasa_cambio_list_sin_rol_forbidden(client_sin_rol):
    """Prueba que un usuario sin rol NO puede acceder a la lista de tasas de cambio."""
    url = reverse("tasa_cambio_listar")
    response = client_sin_rol.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_historial_tasas_administrador_access(client_administrador):
    """Prueba que un administrador puede acceder al historial de tasas."""
    url = reverse("tasa_cambio_historial_listar")
    response = client_administrador.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_historial_tasas_analista_access(client_analista):
    """Prueba que un analista cambiario puede acceder al historial de tasas."""
    url = reverse("tasa_cambio_historial_listar")
    response = client_analista.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_historial_tasas_sin_rol_forbidden(client_sin_rol):
    """Prueba que un usuario sin rol NO puede acceder al historial de tasas."""
    url = reverse("tasa_cambio_historial_listar")
    response = client_sin_rol.get(url)
    assert response.status_code == 403
