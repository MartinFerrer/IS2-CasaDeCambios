import pytest
from apps.usuarios.models import Cliente, TipoCliente, Usuario


@pytest.mark.django_db
class TestClienteModel:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tipo_cliente = TipoCliente.objects.create(nombre="Regular")
        self.usuario = Usuario.objects.create(
            nombre="Test User",
            email="test@example.com",
            password="testpass",
        )
        self.cliente = Cliente.objects.create(
            ruc="12345678901",
            nombre="Test Cliente",
            email="cliente@example.com",
            telefono="123456789",
            direccion="Test Address",
            tipo_cliente=self.tipo_cliente,
        )
        self.cliente.usuarios.add(self.usuario)

    def test_cliente_creation(self):
        assert self.cliente.ruc == "12345678901"
        assert self.cliente.nombre == "Test Cliente"
        assert self.cliente.email == "cliente@example.com"
        assert self.cliente.telefono == "123456789"
        assert self.cliente.direccion == "Test Address"
        assert self.cliente.tipo_cliente == self.tipo_cliente

    def test_cliente_str(self):
        assert str(self.cliente) == "Test Cliente"

    def test_cliente_usuario_relation(self):
        assert self.usuario in self.cliente.usuarios.all()
