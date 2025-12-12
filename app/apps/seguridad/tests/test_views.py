"""Pruebas para las vistas de la aplicación de seguridad.

Este módulo contiene pruebas para las funcionalidades de registro, verificación,
login y logout de usuarios.
"""

import pytest
from django.core import mail
from django.urls import reverse

from apps.usuarios.models import Usuario


@pytest.mark.django_db
def test_registro_view_creates_inactive_user(client, monkeypatch):
    """Prueba que la vista de registro crea un usuario inactivo y llama a send_mail."""
    url = reverse("seguridad:registro")
    data = {
        "nombre": "Nuevo Usuario",
        "email": "nuevo@ejemplo.com",
        "password1": "testpass123",
        "password2": "testpass123",
    }

    called = {"count": 0, "args": None, "kwargs": None}

    import django.core.mail as django_mail

    real_send_mail = django_mail.send_mail

    def fake_send_mail(*args, **kwargs):
        called["count"] += 1
        called["args"] = args
        called["kwargs"] = kwargs
        # Call the real send_mail so the test mail.outbox is populated
        return real_send_mail(*args, **kwargs)

    monkeypatch.setattr("apps.seguridad.views.send_mail", fake_send_mail)

    response = client.post(url, data)
    user = Usuario.objects.get(email="nuevo@ejemplo.com")
    assert user.activo is False
    assert response.status_code == 302
    # Verificar que la función send_mail fue llamada exactamente una vez
    assert called["count"] == 1
    # También verificar que se haya colocado un correo en outbox por compatibilidad
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


# Tests para vistas MFA
@pytest.mark.django_db
def test_configurar_mfa_view_get(client, django_user_model):
    """Prueba la vista de configuración MFA con GET."""
    user = django_user_model.objects.create_user(
        nombre="MFA Config",
        email="mfaconfig@ejemplo.com",
        password="testpass123",
        activo=True,
    )
    client.force_login(user)

    from apps.seguridad.models import PerfilMFA

    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    url = reverse("seguridad:configurar_mfa")
    response = client.get(url)

    assert response.status_code == 200
    assert "form" in response.context
    assert "perfil_mfa" in response.context


@pytest.mark.django_db
def test_configurar_mfa_view_post_valid(client, django_user_model):
    """Prueba la configuración MFA con datos válidos."""
    user = django_user_model.objects.create_user(
        nombre="MFA Valid",
        email="mfavalid@ejemplo.com",
        password="testpass123",
        activo=True,
    )
    client.force_login(user)

    from apps.seguridad.models import PerfilMFA

    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    url = reverse("seguridad:configurar_mfa")
    data = {
        "mfa_habilitado_login": False,
        "mfa_habilitado_transacciones": True,
    }
    response = client.post(url, data)

    assert response.status_code == 302  # Redirect after success
    perfil_mfa.refresh_from_db()
    assert perfil_mfa.mfa_habilitado_transacciones is True


@pytest.mark.django_db
def test_generar_qr_mfa_view(client, django_user_model):
    """Prueba la vista de generación de código QR MFA."""
    user = django_user_model.objects.create_user(
        nombre="QR MFA",
        email="qrmfa@ejemplo.com",
        password="testpass123",
        activo=True,
    )
    client.force_login(user)

    from apps.seguridad.models import PerfilMFA

    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    url = reverse("seguridad:generar_qr_mfa", kwargs={"perfil_id": perfil_mfa.pk})
    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"


@pytest.mark.django_db
def test_generar_qr_mfa_view_not_owner(client, django_user_model):
    """Prueba que no se puede acceder al QR de otro usuario."""
    user1 = django_user_model.objects.create_user(
        nombre="User 1",
        email="user1@ejemplo.com",
        password="testpass123",
        activo=True,
    )
    user2 = django_user_model.objects.create_user(
        nombre="User 2",
        email="user2@ejemplo.com",
        password="testpass123",
        activo=True,
    )

    from apps.seguridad.models import PerfilMFA

    perfil_mfa_user2 = PerfilMFA.objects.create(usuario=user2)

    client.force_login(user1)
    url = reverse("seguridad:generar_qr_mfa", kwargs={"perfil_id": perfil_mfa_user2.pk})
    response = client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_login_with_mfa_redirect(client, django_user_model):
    """Prueba que el login redirige a MFA cuando está habilitado."""
    user = django_user_model.objects.create_user(
        nombre="MFA Login",
        email="mfalogin@ejemplo.com",
        password="testpass123",
        activo=True,
    )

    from apps.seguridad.models import PerfilMFA

    PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=True)

    url = reverse("seguridad:login")
    response = client.post(url, {"email": "mfalogin@ejemplo.com", "password": "testpass123"})

    assert response.status_code == 302
    assert "/seguridad/mfa/login/" in response.url


@pytest.mark.django_db
def test_verificar_mfa_login_get(client, django_user_model):
    """Prueba la vista de verificación MFA para login con GET."""
    user = django_user_model.objects.create_user(
        nombre="MFA Verify",
        email="mfaverify@ejemplo.com",
        password="testpass123",
        activo=True,
    )

    from apps.seguridad.models import PerfilMFA

    PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=True)

    # Simular pre-autenticación
    session = client.session
    session["mfa_pre_auth"] = True
    session["mfa_user_id"] = user.pk
    session.save()

    url = reverse("seguridad:verificar_mfa_login")
    response = client.get(url)

    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_verificar_mfa_login_invalid_session(client):
    """Prueba verificación MFA con sesión inválida."""
    url = reverse("seguridad:verificar_mfa_login")
    response = client.get(url)

    assert response.status_code == 302
    assert response.url == reverse("seguridad:login")


@pytest.mark.django_db
def test_verificar_mfa_transaccion_get(client, django_user_model):
    """Prueba la vista de verificación MFA para transacciones con GET."""
    user = django_user_model.objects.create_user(
        nombre="Trans MFA",
        email="transmfa@ejemplo.com",
        password="testpass123",
        activo=True,
    )
    client.force_login(user)

    # Simular datos de transacción en sesión
    session = client.session
    session["datos_transaccion_mfa"] = {"moneda_origen": "USD", "monto": "100.00", "cliente_id": 1}
    session.save()

    url = reverse("seguridad:verificar_mfa_transaccion")
    response = client.get(url)

    assert response.status_code == 200
    assert "form" in response.context
    assert "datos_transaccion" in response.context


@pytest.mark.django_db
def test_verificar_mfa_transaccion_no_data(client, django_user_model):
    """Prueba verificación MFA para transacciones sin datos en sesión."""
    user = django_user_model.objects.create_user(
        nombre="No Data Trans",
        email="nodatatrans@ejemplo.com",
        password="testpass123",
        activo=True,
    )
    client.force_login(user)

    url = reverse("seguridad:verificar_mfa_transaccion")
    response = client.get(url)

    assert response.status_code == 302
    assert "/transacciones/realizar-transaccion/" in response.url
