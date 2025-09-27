"""Tests unitarios para las views de roles en panel_admin/views.py."""

import pytest
from apps.usuarios.models import Usuario
from django.contrib.auth.models import Group
from django.urls import reverse


@pytest.mark.django_db
def test_rol_list_view(client):
    """Verifica que la vista de lista de roles responde correctamente y contiene los grupos."""
    # Crear grupo y usuario administrador
    admin_group, _ = Group.objects.get_or_create(name="Administrador")
    Group.objects.get_or_create(name="Rol1")

    # Crear usuario administrador
    admin_user = Usuario.objects.create_user(email="admin@test.com", nombre="Admin User", password="testpass123")
    admin_user.groups.add(admin_group)

    # Autenticar usuario
    client.force_login(admin_user)

    url = reverse("rol_listar")
    response = client.get(url)
    assert response.status_code == 200
    assert "grupos" in response.context
    assert response.context["grupos"].count() >= 2  # Administrador + Rol1
