"""Tests unitarios para las views de roles en panel_admin/views.py."""

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse


@pytest.mark.django_db
def test_rol_list_view(client):
    """Verifica que la vista de lista de roles responde correctamente y contiene los grupos."""
    Group.objects.create(name="Rol1")
    url = reverse("rol_listar")
    response = client.get(url)
    assert response.status_code == 200
    assert "grupos" in response.context
    assert response.context["grupos"].count() >= 1
