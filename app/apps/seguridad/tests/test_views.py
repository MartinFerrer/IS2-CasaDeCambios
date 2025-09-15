"""Pruebas para las vistas de la aplicación de seguridad.

Este módulo contiene pruebas para las funcionalidades de registro, verificación,
login y logout de usuarios.
"""

import pytest
from apps.usuarios.models import Usuario
from django.core import mail
from django.urls import reverse


@pytest.mark.django_db
def test_registro_view_creates_inactive_user(client):
    """Prueba que la vista de registro crea un usuario inactivo."""
    url = reverse("seguridad:registro")
    data = {
        "nombre": "Nuevo Usuario",
        "email": "nuevo@ejemplo.com",
        "password1": "testpass123",
        "password2": "testpass123",
    }
    response = client.post(url, data)
    user = Usuario.objects.get(email="nuevo@ejemplo.com")
    assert user.activo is False
    assert response.status_code == 302
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_verificar_cuenta_activa_usuario(client, django_user_model):
    """Prueba que la vista de verificación activa al usuario."""
    user = django_user_model.objects.create(nombre="Verificar", email="verificar@ejemplo.com", activo=False)
    from django.contrib.auth.tokens import PasswordResetTokenGenerator

    token = PasswordResetTokenGenerator().make_token(user)
    url = reverse("seguridad:verificar_cuenta", kwargs={"uid": user.pk, "token": token})
    response = client.get(url)
    user.refresh_from_db()
    assert user.activo is True
    assert response.status_code == 302


@pytest.mark.django_db
def test_login_view(client, django_user_model):
    """Prueba que la vista de login autentica al usuario correctamente."""
    password = "testpass123"
    _user = django_user_model.objects.create_user(
        nombre="Login",
        email="login@ejemplo.com",
        password=password,
        activo=True,
    )
    url = reverse("seguridad:login")
    response = client.post(url, {"email": "login@ejemplo.com", "password": password})
    assert response.status_code == 302


@pytest.mark.django_db
def test_logout_view(client, django_user_model):
    """Prueba que la vista de logout cierra la sesión del usuario."""
    user = django_user_model.objects.create_user(
        nombre="Logout",
        email="logout@ejemplo.com",
        password="testpass123",
        activo=True,
    )
    client.force_login(user)
    url = reverse("seguridad:logout")
    response = client.get(url)
    assert response.status_code == 302
