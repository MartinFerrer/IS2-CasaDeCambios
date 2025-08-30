import pytest
from apps.panel_admin.models import Usuario


@pytest.mark.django_db
class TestUsuarioModel:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.usuario = Usuario.objects.create(
            nombre="Test User",
            email="test@example.com",
            password="testpassword",
            rol=None,
            activo=True,
        )

    def test_usuario_creation(self):
        assert self.usuario.nombre == "Test User"
        assert self.usuario.email == "test@example.com"
        assert self.usuario.activo is True

    def test_usuario_str(self):
        assert str(self.usuario) == "Test User"
