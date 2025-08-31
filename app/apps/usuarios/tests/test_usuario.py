import pytest

from apps.usuarios.models import Cliente, TipoCliente, Usuario


@pytest.mark.django_db
class TestUsuarioModel:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.usuario = Usuario.objects.create(
            nombre="Test User",
            email="test@example.com",
            password="testpassword",
            activo=True,
        )

    def test_usuario_creation(self):
        assert self.usuario.nombre == "Test User"
        assert self.usuario.email == "test@example.com"
        assert self.usuario.activo is True

    def test_usuario_str(self):
        assert str(self.usuario) == "Test User"

    def test_create_user_without_email(self):
        with pytest.raises(ValueError):
            Usuario.objects.create_user(
                email="",
                nombre="Test User",
                password="testpassword",
            )

    def test_create_superuser(self):
        superuser = Usuario.objects.create_superuser(
            email="admin@example.com",
            nombre="Admin User",
            password="adminpass",
        )
        assert superuser.is_staff
        assert superuser.is_superuser

    def test_email_normalize(self):
        user = Usuario.objects.create_user(
            email="TEST@EXAMPLE.COM",
            nombre="Test User",
            password="testpass",
        )
        assert user.email == "TEST@example.com"


@pytest.mark.django_db
class TestTipoClienteModel:
    def test_tipo_cliente_creation(self):
        tipo = TipoCliente.objects.create(nombre="Regular")
        assert str(tipo) == "Regular"


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
