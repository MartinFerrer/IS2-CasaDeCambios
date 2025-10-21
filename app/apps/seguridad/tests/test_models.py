"""Módulo de pruebas para modelos de usuario y MFA.

Este módulo contiene pruebas para el modelo Usuario y los modelos MFA,
incluyendo creación, validación y funcionalidad TOTP.
"""

import pyotp
import pytest
from django.db import IntegrityError

from apps.seguridad.models import PerfilMFA, RegistroMFA
from apps.usuarios.models import Usuario


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


# Tests para PerfilMFA
@pytest.mark.django_db
def test_perfil_mfa_creation():
    """Prueba de creación de perfil MFA.

    Verifica que un perfil MFA se crea correctamente y genera secreto automáticamente.
    """
    user = Usuario.objects.create_user(nombre="MFA User", email="mfa@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    assert perfil_mfa.usuario == user
    assert perfil_mfa.secreto_totp is not None
    assert len(perfil_mfa.secreto_totp) == 32  # Base32 secret length
    assert perfil_mfa.mfa_habilitado_login is False  # Default
    assert perfil_mfa.mfa_habilitado_transacciones is True  # Default
    assert perfil_mfa.fecha_creacion is not None
    assert perfil_mfa.fecha_actualizacion is not None


@pytest.mark.django_db
def test_perfil_mfa_generate_secret_on_save():
    """Prueba que el perfil MFA genera secreto automáticamente al guardar."""
    user = Usuario.objects.create_user(nombre="Secret User", email="secret@example.com", password="testpass123")
    perfil_mfa = PerfilMFA(usuario=user)
    assert perfil_mfa.secreto_totp is None or perfil_mfa.secreto_totp == ""

    perfil_mfa.save()
    assert perfil_mfa.secreto_totp is not None
    assert len(perfil_mfa.secreto_totp) == 32


@pytest.mark.django_db
def test_perfil_mfa_generar_qr_uri():
    """Prueba la generación de URI para código QR."""
    user = Usuario.objects.create_user(nombre="QR User", email="qr@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    qr_uri = perfil_mfa.generar_qr_uri()

    assert "otpauth://totp/" in qr_uri
    assert "qr%40example.com" in qr_uri  # URL-encoded email
    assert "Global%20Exchange%20-%20Casa%20de%20Cambios" in qr_uri
    assert perfil_mfa.secreto_totp in qr_uri


@pytest.mark.django_db
def test_perfil_mfa_verificar_codigo():
    """Prueba la verificación de códigos TOTP."""
    user = Usuario.objects.create_user(nombre="TOTP User", email="totp@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    # Generar código válido usando el mismo secreto
    totp = pyotp.TOTP(perfil_mfa.secreto_totp)
    codigo_valido = totp.now()

    # Verificar código válido
    assert perfil_mfa.verificar_codigo(codigo_valido) is True

    # Verificar código inválido
    assert perfil_mfa.verificar_codigo("000000") is False
    assert perfil_mfa.verificar_codigo("invalid") is False


@pytest.mark.django_db
def test_perfil_mfa_obtener_codigo_actual():
    """Prueba la obtención del código TOTP actual."""
    user = Usuario.objects.create_user(nombre="Current User", email="current@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    codigo_actual = perfil_mfa.obtener_codigo_actual()

    assert len(codigo_actual) == 6
    assert codigo_actual.isdigit()

    # Verificar que el código actual es válido
    assert perfil_mfa.verificar_codigo(codigo_actual) is True


@pytest.mark.django_db
def test_perfil_mfa_str_representation():
    """Prueba la representación string del perfil MFA."""
    user = Usuario.objects.create_user(nombre="String User", email="string@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    assert str(perfil_mfa) == "MFA - string@example.com"


# Tests para RegistroMFA
@pytest.mark.django_db
def test_registro_mfa_creation():
    """Prueba de creación de registro MFA."""
    user = Usuario.objects.create_user(nombre="Log User", email="log@example.com", password="testpass123")

    registro = RegistroMFA.objects.create(
        usuario=user,
        tipo_operacion="login",
        resultado="exitoso",
        direccion_ip="192.168.1.1",
        user_agent="Mozilla/5.0 Test Browser",
    )

    assert registro.usuario == user
    assert registro.tipo_operacion == "login"
    assert registro.resultado == "exitoso"
    assert registro.direccion_ip == "192.168.1.1"
    assert registro.user_agent == "Mozilla/5.0 Test Browser"
    assert registro.fecha_intento is not None


@pytest.mark.django_db
def test_registro_mfa_with_transaction_reference():
    """Prueba de registro MFA con referencia de transacción."""
    import uuid

    user = Usuario.objects.create_user(nombre="Trans User", email="trans@example.com", password="testpass123")

    transaction_uuid = uuid.uuid4()

    registro = RegistroMFA.objects.create(
        usuario=user,
        tipo_operacion="transaccion",
        resultado="fallido",
        direccion_ip="10.0.0.1",
        referencia_transaccion=transaction_uuid,
    )

    assert registro.tipo_operacion == "transaccion"
    assert registro.resultado == "fallido"
    assert registro.referencia_transaccion == transaction_uuid


@pytest.mark.django_db
def test_registro_mfa_str_representation():
    """Prueba la representación string del registro MFA."""
    user = Usuario.objects.create_user(nombre="Repr User", email="repr@example.com", password="testpass123")

    registro = RegistroMFA.objects.create(usuario=user, tipo_operacion="login", resultado="exitoso")

    assert str(registro) == "repr@example.com - login - exitoso"


@pytest.mark.django_db
def test_registro_mfa_ordering():
    """Prueba que los registros MFA se ordenan por fecha descendente."""
    user = Usuario.objects.create_user(nombre="Order User", email="order@example.com", password="testpass123")

    # Crear múltiples registros
    registro1 = RegistroMFA.objects.create(usuario=user, tipo_operacion="login", resultado="exitoso")
    registro2 = RegistroMFA.objects.create(usuario=user, tipo_operacion="transaccion", resultado="fallido")

    registros = RegistroMFA.objects.all()

    # El registro más reciente debe aparecer primero
    assert registros.first() == registro2
    assert registros.last() == registro1
