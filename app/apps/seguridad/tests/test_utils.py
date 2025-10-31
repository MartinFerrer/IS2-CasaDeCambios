"""Pruebas para utilidades de MFA.

Este módulo contiene pruebas para las funciones de utilidad relacionadas
con autenticación multifactor, manejo de IP, registros y verificaciones.
"""

import uuid
from unittest.mock import Mock

import pytest
from django.http import HttpResponse

from apps.seguridad.models import PerfilMFA
from apps.seguridad.utils import (
    crear_perfil_mfa,
    generar_qr_response,
    obtener_ip_cliente,
    obtener_user_agent,
    registrar_intento_mfa,
    usuario_requiere_mfa_login,
    usuario_tiene_mfa_configurado,
    verificar_codigo_usuario,
)
from apps.usuarios.models import Usuario


@pytest.mark.django_db
def test_obtener_ip_cliente_with_forwarded():
    """Prueba obtener IP del cliente con cabecera X-Forwarded-For."""
    request = Mock()
    request.META = {"HTTP_X_FORWARDED_FOR": "192.168.1.1,10.0.0.1", "REMOTE_ADDR": "127.0.0.1"}

    ip = obtener_ip_cliente(request)
    assert ip == "192.168.1.1"


@pytest.mark.django_db
def test_obtener_ip_cliente_without_forwarded():
    """Prueba obtener IP del cliente sin cabecera X-Forwarded-For."""
    request = Mock()
    request.META = {"REMOTE_ADDR": "192.168.1.100"}

    ip = obtener_ip_cliente(request)
    assert ip == "192.168.1.100"


@pytest.mark.django_db
def test_obtener_user_agent():
    """Prueba obtener user agent del navegador."""
    request = Mock()
    request.META = {"HTTP_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    user_agent = obtener_user_agent(request)
    assert user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@pytest.mark.django_db
def test_obtener_user_agent_empty():
    """Prueba obtener user agent cuando no existe."""
    request = Mock()
    request.META = {}

    user_agent = obtener_user_agent(request)
    assert user_agent == ""


@pytest.mark.django_db
def test_crear_perfil_mfa_new_user():
    """Prueba crear perfil MFA para usuario nuevo."""
    user = Usuario.objects.create(nombre="New MFA User", email="newmfa@example.com", password="testpass123")

    perfil_mfa = crear_perfil_mfa(user)

    assert perfil_mfa.usuario == user
    assert perfil_mfa.secreto_totp is not None
    assert PerfilMFA.objects.filter(usuario=user).count() == 1


@pytest.mark.django_db
def test_crear_perfil_mfa_existing_user():
    """Prueba que no se crea perfil MFA duplicado para usuario existente."""
    user = Usuario.objects.create(nombre="Existing MFA User", email="existingmfa@example.com", password="testpass123")

    # Crear perfil inicial
    perfil_original = PerfilMFA.objects.create(usuario=user)

    # Intentar crear otro perfil
    perfil_mfa = crear_perfil_mfa(user)

    assert perfil_mfa == perfil_original
    assert PerfilMFA.objects.filter(usuario=user).count() == 1


@pytest.mark.django_db
def test_generar_qr_response():
    """Prueba la generación de respuesta HTTP con código QR."""
    user = Usuario.objects.create(nombre="QR Test User", email="qrtest@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    response = generar_qr_response(perfil_mfa)

    assert isinstance(response, HttpResponse)
    assert response["Content-Type"] == "image/png"
    assert "qr_mfa_qrtest@example.com.png" in response["Content-Disposition"]


@pytest.mark.django_db
def test_registrar_intento_mfa():
    """Prueba el registro de intento MFA."""
    user = Usuario.objects.create(nombre="Log Test User", email="logtest@example.com", password="testpass123")

    request = Mock()
    request.META = {"REMOTE_ADDR": "192.168.1.1", "HTTP_USER_AGENT": "Test Browser"}

    transaction_uuid = uuid.uuid4()

    registro = registrar_intento_mfa(
        usuario=user,
        tipo_operacion="transaccion",
        resultado="exitoso",
        request=request,
        referencia_transaccion=transaction_uuid,
    )

    assert registro.usuario == user
    assert registro.tipo_operacion == "transaccion"
    assert registro.resultado == "exitoso"
    assert registro.direccion_ip == "192.168.1.1"
    assert registro.user_agent == "Test Browser"
    assert registro.referencia_transaccion == transaction_uuid


@pytest.mark.django_db
def test_verificar_codigo_usuario_valid():
    """Prueba verificación de código TOTP válido."""
    user = Usuario.objects.create(nombre="Verify User", email="verify@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    # Generar código válido
    codigo_valido = perfil_mfa.obtener_codigo_actual()

    resultado = verificar_codigo_usuario(user, codigo_valido)
    assert resultado is True


@pytest.mark.django_db
def test_verificar_codigo_usuario_invalid():
    """Prueba verificación de código TOTP inválido."""
    user = Usuario.objects.create(nombre="Invalid User", email="invalid@example.com", password="testpass123")
    PerfilMFA.objects.create(usuario=user)

    resultado = verificar_codigo_usuario(user, "000000")
    assert resultado is False


@pytest.mark.django_db
def test_verificar_codigo_usuario_no_profile():
    """Prueba verificación de código cuando no existe perfil MFA."""
    user = Usuario.objects.create(nombre="No Profile User", email="noprofile@example.com", password="testpass123")

    resultado = verificar_codigo_usuario(user, "123456")
    assert resultado is False


@pytest.mark.django_db
def test_usuario_requiere_mfa_login_enabled():
    """Prueba verificación de MFA para login habilitado."""
    user = Usuario.objects.create(nombre="Login MFA User", email="loginmfa@example.com", password="testpass123")
    PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=True)

    resultado = usuario_requiere_mfa_login(user)
    assert resultado is True


@pytest.mark.django_db
def test_usuario_requiere_mfa_login_disabled():
    """Prueba verificación de MFA para login deshabilitado."""
    user = Usuario.objects.create(nombre="No Login MFA User", email="nologinmfa@example.com", password="testpass123")
    PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=False)

    resultado = usuario_requiere_mfa_login(user)
    assert resultado is False


@pytest.mark.django_db
def test_usuario_requiere_mfa_login_no_profile():
    """Prueba verificación de MFA para login sin perfil."""
    user = Usuario.objects.create(
        nombre="No Profile Login User", email="noprofilelogin@example.com", password="testpass123"
    )

    resultado = usuario_requiere_mfa_login(user)
    assert resultado is False


@pytest.mark.django_db
def test_usuario_tiene_mfa_configurado_true():
    """Prueba verificación de MFA configurado cuando existe perfil."""
    user = Usuario.objects.create(nombre="Has MFA User", email="hasmfa@example.com", password="testpass123")
    PerfilMFA.objects.create(usuario=user)

    resultado = usuario_tiene_mfa_configurado(user)
    assert resultado is True


@pytest.mark.django_db
def test_usuario_tiene_mfa_configurado_false():
    """Prueba verificación de MFA configurado cuando no existe perfil."""
    user = Usuario.objects.create(nombre="No MFA User", email="nomfa@example.com", password="testpass123")

    resultado = usuario_tiene_mfa_configurado(user)
    assert resultado is False
