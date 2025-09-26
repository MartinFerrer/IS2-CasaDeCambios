"""Configuración común para tests de transacciones."""

import pytest

from apps.transacciones.models import EntidadFinanciera
from apps.usuarios.models import Cliente, TipoCliente, Usuario


@pytest.fixture
def tipo_cliente():
    """Fixture para crear un tipo de cliente."""
    return TipoCliente.objects.create(nombre="Regular")


@pytest.fixture
def usuario():
    """Fixture para crear un usuario."""
    return Usuario.objects.create(
        email="testuser@example.com",
        nombre="Test User",
        password="testpass123"
    )


@pytest.fixture
def cliente(tipo_cliente):
    """Fixture para crear un cliente."""
    return Cliente.objects.create(
        ruc="1234567-9",
        nombre="Test Cliente",
        email="cliente@example.com",
        telefono="123456789",
        direccion="Test Address",
        tipo_cliente=tipo_cliente,
    )


@pytest.fixture
def cliente2(tipo_cliente):
    """Fixture para crear un segundo cliente."""
    return Cliente.objects.create(
        ruc="2872301-5",
        nombre="Otro Cliente",
        email="otro@example.com",
        telefono="987654321",
        direccion="Otra dirección",
        tipo_cliente=tipo_cliente,
    )


@pytest.fixture
def entidad_bancaria():
    """Fixture para crear una entidad bancaria."""
    return EntidadFinanciera.objects.create(
        nombre="Banco Test",
        tipo="banco",
        activo=True,
    )


@pytest.fixture
def entidad_billetera():
    """Fixture para crear una entidad de billetera."""
    return EntidadFinanciera.objects.create(
        nombre="Personal Pay Test",
        tipo="proveedor_billetera",
        activo=True,
    )


@pytest.fixture
def entidad_billetera2():
    """Fixture para crear una segunda entidad de billetera."""
    return EntidadFinanciera.objects.create(
        nombre="Tigo Money Test",
        tipo="proveedor_billetera",
        activo=True,
    )


@pytest.fixture
def entidad_credito():
    """Fixture para crear una entidad de tarjeta de crédito."""
    return EntidadFinanciera.objects.create(
        nombre="Visa Test",
        tipo="emisor_tarjeta",
        activo=True,
    )


@pytest.fixture
def cliente_con_usuario(cliente, usuario):
    """Fixture para crear un cliente asociado a un usuario."""
    cliente.usuarios.add(usuario)
    return cliente


@pytest.fixture
def client_logueado(client, usuario):
    """Fixture para un cliente autenticado."""
    client.force_login(usuario)
    return client
