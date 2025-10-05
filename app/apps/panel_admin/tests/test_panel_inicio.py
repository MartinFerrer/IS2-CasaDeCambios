"""Tests para la vista panel_inicio."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_panel_inicio_administrador_access(client_administrador):
    """Prueba que un administrador puede acceder al panel de inicio."""
    url = reverse("panel_inicio")
    response = client_administrador.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_panel_inicio_analista_access(client_analista):
    """Prueba que un analista cambiario puede acceder al panel de inicio."""
    url = reverse("panel_inicio")
    response = client_analista.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_panel_inicio_sin_rol_forbidden(client_sin_rol):
    """Prueba que un usuario sin rol NO puede acceder al panel de inicio."""
    url = reverse("panel_inicio")
    response = client_sin_rol.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_panel_inicio_anonymous_redirect(client):
    """Prueba que un usuario anónimo es redirigido al login."""
    url = reverse("panel_inicio")
    response = client.get(url)
    assert response.status_code == 302  # Redirect to login
