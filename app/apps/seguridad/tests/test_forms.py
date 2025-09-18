"""Pruebas para el formulario de creación de usuarios personalizados en la aplicación seguridad.

Este módulo contiene pruebas para validar la funcionalidad del CustomUserCreationForm,
incluyendo la validación de datos del formulario y la coincidencia de contraseñas.
"""

import pytest
from apps.seguridad.forms import CustomUserCreationForm


@pytest.mark.django_db
def test_custom_user_creation_form_valid():
    """Prueba que el formulario de creación de usuario personalizado es válido con datos correctos."""
    form = CustomUserCreationForm(
        data={
            "nombre": "Test User",
            "email": "testform@example.com",
            "password1": "testpass123",
            "password2": "testpass123",
        }
    )
    assert form.is_valid()


@pytest.mark.django_db
def test_custom_user_creation_form_password_mismatch():
    """Prueba que el formulario es inválido si las contraseñas no coinciden."""
    form = CustomUserCreationForm(
        data={
            "nombre": "Test User",
            "email": "testform2@example.com",
            "password1": "testpass123",
            "password2": "wrongpass",
        }
    )
    assert not form.is_valid()
    assert "password2" in form.errors
