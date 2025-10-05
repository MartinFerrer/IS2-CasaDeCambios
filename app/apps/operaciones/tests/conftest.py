"""Configuración común para tests de operaciones."""

import pytest
from apps.usuarios.models import Usuario
from django.contrib.auth.models import Group


@pytest.fixture
def grupo_administrador():
    """Fixture para crear el grupo Administrador."""
    return Group.objects.get_or_create(name="Administrador")[0]


@pytest.fixture
def grupo_analista():
    """Fixture para crear el grupo Analista Cambiario."""
    return Group.objects.get_or_create(name="Analista Cambiario")[0]


@pytest.fixture
def usuario_administrador(grupo_administrador):
    """Fixture para crear un usuario con rol Administrador."""
    usuario = Usuario.objects.create(
        email="admin@example.com", nombre="Admin User", password="adminpass123", activo=True
    )
    usuario.groups.add(grupo_administrador)
    return usuario


@pytest.fixture
def usuario_analista(grupo_analista):
    """Fixture para crear un usuario con rol Analista Cambiario."""
    usuario = Usuario.objects.create(
        email="analista@example.com", nombre="Analista User", password="analistapass123", activo=True
    )
    usuario.groups.add(grupo_analista)
    return usuario


@pytest.fixture
def usuario_sin_rol():
    """Fixture para crear un usuario sin rol específico."""
    return Usuario.objects.create(
        email="usuario@example.com", nombre="Usuario Normal", password="userpass123", activo=True
    )


@pytest.fixture
def client_administrador(client, usuario_administrador):
    """Fixture para un client autenticado como administrador."""
    client.force_login(usuario_administrador)
    return client


@pytest.fixture
def client_analista(client, usuario_analista):
    """Fixture para un client autenticado como analista."""
    client.force_login(usuario_analista)
    return client


@pytest.fixture
def client_sin_rol(client, usuario_sin_rol):
    """Fixture para un client autenticado sin rol específico."""
    client.force_login(usuario_sin_rol)
    return client
