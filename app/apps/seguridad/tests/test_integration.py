"""Pruebas de integración para MFA.

Este módulo contiene pruebas que validan el flujo completo de MFA,
desde la configuración hasta la verificación en login y transacciones.
"""

import pytest
from django.test import Client
from django.urls import reverse

from apps.seguridad.models import PerfilMFA, RegistroMFA
from apps.usuarios.models import Usuario


@pytest.mark.django_db
def test_flujo_completo_configuracion_mfa():
    """Prueba el flujo completo de configuración MFA."""
    # Crear usuario
    user = Usuario.objects.create_user(
        nombre="Integration User",
        email="integration@example.com",
        password="testpass123",
        activo=True,
    )

    client = Client()
    client.force_login(user)

    # 1. Acceder a configuración MFA
    url = reverse("seguridad:configurar_mfa")
    response = client.get(url)
    assert response.status_code == 200

    # Verificar que se creó el perfil automáticamente
    perfil_mfa = PerfilMFA.objects.get(usuario=user)
    assert perfil_mfa is not None
    assert perfil_mfa.secreto_totp is not None

    # 2. Configurar MFA para transacciones solamente
    response = client.post(
        url,
        {
            "mfa_habilitado_login": False,
            "mfa_habilitado_transacciones": True,
        },
    )
    assert response.status_code == 302

    perfil_mfa.refresh_from_db()
    assert perfil_mfa.mfa_habilitado_login is False
    assert perfil_mfa.mfa_habilitado_transacciones is True


@pytest.mark.django_db
def test_flujo_completo_mfa_login_habilitacion():
    """Prueba el flujo completo de habilitación MFA para login con verificación TOTP."""
    # Crear usuario
    user = Usuario.objects.create_user(
        nombre="Login MFA User",
        email="loginmfa@example.com",
        password="testpass123",
        activo=True,
    )

    client = Client()
    client.force_login(user)

    # Acceder a configuración MFA
    url = reverse("seguridad:configurar_mfa")
    response = client.get(url)
    assert response.status_code == 200

    perfil_mfa = PerfilMFA.objects.get(usuario=user)

    # Intentar habilitar MFA para login sin código TOTP
    response = client.post(
        url,
        {
            "mfa_habilitado_login": True,
            "mfa_habilitado_transacciones": True,
        },
    )

    # Debe fallar sin código TOTP
    assert response.status_code == 200  # Formulario con errores
    perfil_mfa.refresh_from_db()
    assert perfil_mfa.mfa_habilitado_login is False  # No debería cambiar

    # Obtener código TOTP válido y habilitar MFA para login
    codigo_valido = perfil_mfa.obtener_codigo_actual()
    response = client.post(
        url,
        {
            "mfa_habilitado_login": True,
            "mfa_habilitado_transacciones": True,
            "codigo_verificacion": codigo_valido,
        },
    )

    assert response.status_code == 302  # Redirect después del éxito
    perfil_mfa.refresh_from_db()
    assert perfil_mfa.mfa_habilitado_login is True


@pytest.mark.django_db
def test_flujo_completo_login_con_mfa():
    """Prueba el flujo completo de login con MFA habilitado."""
    # Crear usuario con MFA habilitado para login
    user = Usuario.objects.create_user(
        nombre="MFA Login Flow",
        email="mfaloginflow@example.com",
        password="testpass123",
        activo=True,
    )

    perfil_mfa = PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=True, mfa_habilitado_transacciones=True)

    client = Client()

    # 1. Intentar login normal
    login_url = reverse("seguridad:login")
    response = client.post(login_url, {"email": "mfaloginflow@example.com", "password": "testpass123"})

    # Debe redirigir a verificación MFA
    assert response.status_code == 302
    assert "/seguridad/mfa/login/" in response.url

    # 2. Acceder a verificación MFA
    mfa_url = reverse("seguridad:verificar_mfa_login")
    response = client.get(mfa_url)
    assert response.status_code == 200

    # 3. Verificar con código TOTP válido
    codigo_valido = perfil_mfa.obtener_codigo_actual()
    response = client.post(mfa_url, {"codigo": codigo_valido})

    # Debe redirigir a selección de cliente después del login exitoso
    assert response.status_code == 302
    assert "/seguridad/seleccionar-cliente/" in response.url

    # Verificar que se creó un registro MFA exitoso
    registro = RegistroMFA.objects.filter(usuario=user, tipo_operacion="login", resultado="exitoso").first()
    assert registro is not None


@pytest.mark.django_db
def test_flujo_login_mfa_codigo_invalido():
    """Prueba el flujo de login con código MFA inválido."""
    # Crear usuario con MFA habilitado
    user = Usuario.objects.create_user(
        nombre="Invalid MFA User",
        email="invalidmfa@example.com",
        password="testpass123",
        activo=True,
    )

    PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=True)

    client = Client()

    # Login normal - debe redirigir a MFA
    login_url = reverse("seguridad:login")
    response = client.post(login_url, {"email": "invalidmfa@example.com", "password": "testpass123"})
    assert response.status_code == 302

    # Verificar con código inválido
    mfa_url = reverse("seguridad:verificar_mfa_login")
    response = client.post(
        mfa_url,
        {
            "codigo": "000000"  # Código inválido
        },
    )

    # Debe permanecer en la página MFA con error
    assert response.status_code == 200
    assert "form" in response.context

    # Verificar que se creó un registro MFA fallido
    registro = RegistroMFA.objects.filter(usuario=user, tipo_operacion="login", resultado="fallido").first()
    assert registro is not None


@pytest.mark.django_db
def test_flujo_verificacion_mfa_transaccion():
    """Prueba el flujo de verificación MFA para transacciones."""
    # Crear usuario con MFA habilitado para transacciones
    user = Usuario.objects.create_user(
        nombre="Trans MFA Flow",
        email="transmfaflow@example.com",
        password="testpass123",
        activo=True,
    )

    perfil_mfa = PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=False, mfa_habilitado_transacciones=True)

    client = Client()
    client.force_login(user)

    # Simular datos de transacción en la sesión
    session = client.session
    session["datos_transaccion_mfa"] = {
        "moneda_origen": "USD",
        "moneda_destino": "EUR",
        "monto": "100.00",
        "cliente_id": 1,
    }
    session.save()

    # 1. Acceder a verificación MFA para transacción
    mfa_url = reverse("seguridad:verificar_mfa_transaccion")
    response = client.get(mfa_url)
    assert response.status_code == 200
    assert "datos_transaccion" in response.context

    # 2. Verificar con código TOTP válido
    codigo_valido = perfil_mfa.obtener_codigo_actual()
    response = client.post(mfa_url, {"codigo": codigo_valido})

    # Debe procesar la transacción y redirigir
    assert response.status_code == 302


@pytest.mark.django_db
def test_acceso_qr_solo_propietario():
    """Prueba que solo el propietario puede acceder a su código QR."""
    # Crear dos usuarios
    user1 = Usuario.objects.create_user(
        nombre="User 1",
        email="user1@example.com",
        password="testpass123",
        activo=True,
    )
    user2 = Usuario.objects.create_user(
        nombre="User 2",
        email="user2@example.com",
        password="testpass123",
        activo=True,
    )

    perfil_mfa1 = PerfilMFA.objects.create(usuario=user1)
    perfil_mfa2 = PerfilMFA.objects.create(usuario=user2)

    client = Client()

    # User1 puede acceder a su propio QR
    client.force_login(user1)
    qr_url1 = reverse("seguridad:generar_qr_mfa", kwargs={"perfil_id": perfil_mfa1.pk})
    response = client.get(qr_url1)
    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"

    # User1 NO puede acceder al QR de User2
    qr_url2 = reverse("seguridad:generar_qr_mfa", kwargs={"perfil_id": perfil_mfa2.pk})
    response = client.get(qr_url2)
    assert response.status_code == 404


@pytest.mark.django_db
def test_manejo_sesiones_mfa_login():
    """Prueba el manejo correcto de sesiones durante MFA login."""
    user = Usuario.objects.create_user(
        nombre="Session MFA User",
        email="sessionmfa@example.com",
        password="testpass123",
        activo=True,
    )

    PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=True)

    client = Client()

    # Login normal
    login_url = reverse("seguridad:login")
    response = client.post(login_url, {"email": "sessionmfa@example.com", "password": "testpass123"})

    # Verificar que se establecieron las variables de sesión
    session = client.session
    assert session.get("mfa_pre_auth") is True
    assert session.get("mfa_user_id") == user.pk

    # Intentar acceder a verificación MFA sin sesión válida
    client2 = Client()
    mfa_url = reverse("seguridad:verificar_mfa_login")
    response = client2.get(mfa_url)

    # Debe redirigir al login
    assert response.status_code == 302
    assert response.url == reverse("seguridad:login")
