"""Módulo de pruebas para modelos de usuario.

Este módulo contiene pruebas para el modelo Usuario, incluyendo creación
y validación de restricciones como la unicidad del email.
"""

import pytest
from apps.usuarios.models import Usuario
from django.db import IntegrityError


@pytest.mark.django_db
def test_usuario_creation():
    """Prueba de creación de usuario.

    Verifica que un usuario se crea correctamente con los datos proporcionados.
    """
    user = Usuario.objects.create(nombre="Test User", email="testuser@example.com", password="testpass123")
    assert user.nombre == "Test User"
    assert user.email == "testuser@example.com"
    assert user.pk is not None


@pytest.mark.django_db
def test_usuario_unique_email():
    """Prueba de unicidad de email de usuario.

    Verifica que no se puedan crear dos usuarios con el mismo email.
    """
    Usuario.objects.create(nombre="User1", email="unique@example.com", password="pass1")
    with pytest.raises(IntegrityError):
        Usuario.objects.create(nombre="User2", email="unique@example.com", password="pass2")
