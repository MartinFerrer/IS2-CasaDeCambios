"""Pruebas para formularios de la aplicación seguridad.

Este módulo contiene pruebas para validar la funcionalidad de los formularios
de registro, MFA y configuración, incluyendo validación de datos y códigos TOTP.
"""

import pytest

from apps.seguridad.forms import CodigoMFAForm, ConfiguracionMFAForm, CustomUserCreationForm
from apps.seguridad.models import PerfilMFA
from apps.usuarios.models import Usuario


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


# Tests para CodigoMFAForm
def test_codigo_mfa_form_valid():
    """Prueba que el formulario de código MFA es válido con datos correctos."""
    form = CodigoMFAForm(data={"codigo": "123456"})
    assert form.is_valid()


def test_codigo_mfa_form_invalid_length():
    """Prueba que el formulario es inválido con códigos de longitud incorrecta."""
    # Código muy corto
    form = CodigoMFAForm(data={"codigo": "123"})
    assert not form.is_valid()
    assert "codigo" in form.errors

    # Código muy largo
    form = CodigoMFAForm(data={"codigo": "1234567"})
    assert not form.is_valid()
    assert "codigo" in form.errors


def test_codigo_mfa_form_invalid_characters():
    """Prueba que el formulario es inválido con caracteres no numéricos."""
    form = CodigoMFAForm(data={"codigo": "12abc6"})
    assert not form.is_valid()
    assert "codigo" in form.errors


def test_codigo_mfa_form_empty():
    """Prueba que el formulario es inválido sin código."""
    form = CodigoMFAForm(data={})
    assert not form.is_valid()
    assert "codigo" in form.errors


# Tests para ConfiguracionMFAForm
@pytest.mark.django_db
def test_configuracion_mfa_form_creation():
    """Prueba la creación básica del formulario de configuración MFA."""
    user = Usuario.objects.create_user(nombre="Config User", email="config@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    form = ConfiguracionMFAForm(usuario=user, perfil_mfa=perfil_mfa)
    assert form.fields["mfa_habilitado_login"] is not None
    assert form.fields["mfa_habilitado_transacciones"] is not None
    assert form.fields["codigo_verificacion"] is not None


@pytest.mark.django_db
def test_configuracion_mfa_form_valid_without_login_enable():
    """Prueba que el formulario es válido sin habilitar MFA para login."""
    user = Usuario.objects.create_user(nombre="No Login User", email="nologin@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user)

    form = ConfiguracionMFAForm(
        data={
            "mfa_habilitado_login": False,
            "mfa_habilitado_transacciones": True,
        },
        usuario=user,
        perfil_mfa=perfil_mfa,
        instance=perfil_mfa,
    )
    assert form.is_valid()


@pytest.mark.django_db
def test_configuracion_mfa_form_requires_totp_for_login():
    """Prueba que el formulario requiere código TOTP para habilitar login MFA."""
    user = Usuario.objects.create_user(nombre="Login TOTP User", email="logintotp@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=False)

    # Intentar habilitar login MFA sin código TOTP
    form = ConfiguracionMFAForm(
        data={
            "mfa_habilitado_login": True,
            "mfa_habilitado_transacciones": True,
        },
        usuario=user,
        perfil_mfa=perfil_mfa,
        instance=perfil_mfa,
    )
    assert not form.is_valid()
    assert "Para habilitar MFA en login" in str(form.errors)


@pytest.mark.django_db
def test_configuracion_mfa_form_invalid_totp_code():
    """Prueba que el formulario es inválido con código TOTP incorrecto."""
    user = Usuario.objects.create_user(
        nombre="Invalid TOTP User", email="invalidtotp@example.com", password="testpass123"
    )
    perfil_mfa = PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=False)

    form = ConfiguracionMFAForm(
        data={
            "mfa_habilitado_login": True,
            "mfa_habilitado_transacciones": True,
            "codigo_verificacion": "000000",  # Código inválido
        },
        usuario=user,
        perfil_mfa=perfil_mfa,
        instance=perfil_mfa,
    )
    assert not form.is_valid()
    assert "El código de verificación TOTP es incorrecto" in str(form.errors)


@pytest.mark.django_db
def test_configuracion_mfa_form_valid_totp_code():
    """Prueba que el formulario es válido con código TOTP correcto."""
    user = Usuario.objects.create_user(nombre="Valid TOTP User", email="validtotp@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=False)

    # Obtener código TOTP válido
    codigo_valido = perfil_mfa.obtener_codigo_actual()

    form = ConfiguracionMFAForm(
        data={
            "mfa_habilitado_login": True,
            "mfa_habilitado_transacciones": True,
            "codigo_verificacion": codigo_valido,
        },
        usuario=user,
        perfil_mfa=perfil_mfa,
        instance=perfil_mfa,
    )
    assert form.is_valid()


@pytest.mark.django_db
def test_configuracion_mfa_form_non_numeric_verification_code():
    """Prueba que el formulario es inválido con código de verificación no numérico."""
    user = Usuario.objects.create_user(
        nombre="Non Numeric User", email="nonnumeric@example.com", password="testpass123"
    )
    perfil_mfa = PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=False)

    form = ConfiguracionMFAForm(
        data={
            "mfa_habilitado_login": True,
            "mfa_habilitado_transacciones": True,
            "codigo_verificacion": "abc123",
        },
        usuario=user,
        perfil_mfa=perfil_mfa,
        instance=perfil_mfa,
    )
    assert not form.is_valid()
    assert "debe contener solo números" in str(form.errors)


@pytest.mark.django_db
def test_configuracion_mfa_form_preserves_state_on_error():
    """Prueba que el formulario mantiene el estado original cuando hay errores."""
    user = Usuario.objects.create_user(nombre="Preserve User", email="preserve@example.com", password="testpass123")
    perfil_mfa = PerfilMFA.objects.create(usuario=user, mfa_habilitado_login=False)

    form = ConfiguracionMFAForm(
        data={
            "mfa_habilitado_login": True,
            "mfa_habilitado_transacciones": True,
            "codigo_verificacion": "invalid",
        },
        usuario=user,
        perfil_mfa=perfil_mfa,
        instance=perfil_mfa,
    )

    # El formulario debe ser inválido
    assert not form.is_valid()

    # Pero los datos limpios deben mantener el estado original
    assert form.cleaned_data.get("mfa_habilitado_login") is False  # Estado original preservado
